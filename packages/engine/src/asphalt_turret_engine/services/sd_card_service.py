from __future__ import annotations
import logging
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.orm import Session

from asphalt_turret_engine.adapters.volumes import list_removable_volumes
from asphalt_turret_engine.adapters.sd_scanner import iter_dashcam_files, is_thinkware_sd_card
from asphalt_turret_engine.adapters.card_identity import ensure_card_identity
from asphalt_turret_engine.db.crud import sd_card as sd_card_crud
from asphalt_turret_engine.db.crud import sd_file as sd_file_crud
from asphalt_turret_engine.db.models.sd_file import SDFile

logger = logging.getLogger(__name__)

# Post-scan merge thresholds.
# New card record must match at least this many fingerprints on an existing
# card, AND at least this percentage of its own files, to trigger a merge.
MERGE_MIN_MATCHES   = 10
MERGE_MIN_MATCH_PCT = 0.30


@dataclass
class ScanResult:
    sd_card_id:     int
    drive_root:     str
    found:          int
    new:            int
    updated:        int
    unchanged:      int
    skipped:        int
    deleted:        int
    merged_from_id: int | None = field(default=None)


def scan_sd_card(db: Session, *, volume_uid: str) -> ScanResult:
    """
    Scan an SD card and register discovered files.

    Additions over original:
    1. Reads/writes .at_card_id identity file on the card.
    2. Passes card_identity to register_or_touch — UID changes are healed
       automatically at registration time (no duplicate created).
    3. Post-scan merge pass — for cards first seen before identity files were
       introduced, detects fingerprint overlap with an existing record and
       merges rather than keeping two orphaned records.
    """
    volumes = list_removable_volumes()
    volume  = next((v for v in volumes if v["volume_uid"] == volume_uid), None)
    if not volume:
        raise ValueError(f"SD card volume '{volume_uid}' not found")

    drive_root = volume["drive_root"]
    if not is_thinkware_sd_card(drive_root):
        raise ValueError(f"Drive {drive_root} does not appear to be a Thinkware SD card")

    # ── Identity file ─────────────────────────────────────────────────────────
    card_identity = ensure_card_identity(drive_root)

    # ── Register or reconcile ─────────────────────────────────────────────────
    card = sd_card_crud.register_or_touch(
        db,
        volume_uid    = volume_uid,
        volume_label  = volume.get("volume_label"),
        card_identity = card_identity,
        drive_root    = drive_root,
    )
    db.flush()

    # Track whether register_or_touch just created this record so we know
    # whether to run the merge pass. A new record has first_seen_at ≈ now.
    card_was_new = _is_new_record(card)

    # ── File scan ─────────────────────────────────────────────────────────────
    stats = {"found": 0, "new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    seen_file_ids:    set[int] = set()
    new_fingerprints: set[str] = set()

    for scanned_file in iter_dashcam_files(drive_root):
        stats["found"] += 1
        try:
            sd_file, status = sd_file_crud.upsert_from_scan(
                db,
                sd_card_id = card.id,
                rel_path   = scanned_file.rel_path,
                size_bytes = scanned_file.size_bytes,
                mtime      = scanned_file.mtime,
            )
            seen_file_ids.add(sd_file.id)
            stats[status] += 1
            if status == "new":
                new_fingerprints.add(sd_file.fingerprint)
        except Exception as e:
            stats["skipped"] += 1
            logger.warning(f"Error processing {scanned_file.rel_path}: {e}")

    deleted_count = sd_file_crud.delete_stale_files(
        db, sd_card_id=card.id, seen_file_ids=seen_file_ids
    )
    db.commit()

    # ── Post-scan merge pass ──────────────────────────────────────────────────
    # Only runs when this was a brand-new card record AND we found files whose
    # fingerprints might already exist on an older record (legacy card scenario).
    # After a successful merge, the identity file is on the card so this will
    # never trigger again for this card.
    merged_from_id: int | None = None

    if card_was_new and new_fingerprints:
        merged_from_id = _maybe_merge(
            db,
            new_card_id      = card.id,
            new_fingerprints = new_fingerprints,
            card_identity    = card_identity,
            new_volume_uid   = volume_uid,
        )
        if merged_from_id:
            # The new record was deleted; winner has the new volume_uid now.
            # Refresh our card reference.
            card = sd_card_crud.get_by_volume_uid(db, volume_uid)
            db.commit()

    if card is None:
        raise RuntimeError("Failed to retrieve SD card record after merge; card is None")
    return ScanResult(
        sd_card_id     = card.id,
        drive_root     = drive_root,
        deleted        = deleted_count,
        merged_from_id = merged_from_id,
        **stats,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_new_record(card) -> bool:
    """
    Heuristic: if first_seen_at and last_seen_at are within 5 seconds of each
    other the record was just created by this scan, not found in the DB.

    SQLite returns naive datetimes; register_or_touch sets aware datetimes.
    A brand-new in-memory record may have one of each, so we strip tzinfo
    before subtracting.
    """
    fc = getattr(card, 'first_seen_at', None)
    lc = getattr(card, 'last_seen_at', None)
    if fc is None or lc is None:
        return True
    # Strip timezone info so we can always subtract safely
    fc = fc.replace(tzinfo=None) if hasattr(fc, 'tzinfo') else fc
    lc = lc.replace(tzinfo=None) if hasattr(lc, 'tzinfo') else lc
    return abs((lc - fc).total_seconds()) <= 5


def _maybe_merge(
    db: Session,
    *,
    new_card_id:      int,
    new_fingerprints: set[str],
    card_identity:    str,
    new_volume_uid:   str,
) -> int | None:
    """
    Check whether a newly-created card record heavily overlaps an existing one.
    If thresholds are met, merges new (loser) into existing (winner).

    Returns the ID of the record that was deleted (the loser), or None.
    """
    rows = db.execute(
        select(SDFile.sd_card_id, SDFile.fingerprint)
        .where(
            SDFile.fingerprint.in_(new_fingerprints),
            SDFile.sd_card_id != new_card_id,
        )
    ).all()

    if not rows:
        return None

    # Find the candidate with the most fingerprint matches
    match_counts: dict[int, int] = {}
    for card_id, _ in rows:
        match_counts[card_id] = match_counts.get(card_id, 0) + 1

    best_id      = max(match_counts, key=lambda k: match_counts[k])
    best_matches = match_counts[best_id]
    total_new    = len(new_fingerprints)

    if best_matches < MERGE_MIN_MATCHES or (best_matches / total_new) < MERGE_MIN_MATCH_PCT:
        logger.debug(
            f"Merge candidate card {best_id} matched {best_matches}/{total_new} files "
            f"— below threshold, skipping merge"
        )
        return None

    logger.info(
        f"Post-scan merge triggered: new card {new_card_id} matches "
        f"{best_matches}/{total_new} files on existing card {best_id}. Merging."
    )

    sd_card_crud.merge_into(
        db,
        winner_id         = best_id,
        loser_id          = new_card_id,
        new_volume_uid    = new_volume_uid,
        new_card_identity = card_identity,
    )

    return new_card_id