from __future__ import annotations
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.sd_card import SDCard
from asphalt_turret_engine.db.models.sd_file import SDFile
from asphalt_turret_engine.db.models.clip_source import ClipSource

logger = logging.getLogger(__name__)


def list_all(session: Session) -> list[SDCard]:
    stmt = select(SDCard).order_by(SDCard.last_seen_at.desc())
    return list(session.execute(stmt).scalars())


def get_by_volume_uid(session: Session, volume_uid: str) -> SDCard | None:
    stmt = select(SDCard).where(SDCard.volume_uid == volume_uid)
    return session.execute(stmt).scalar_one_or_none()


def get_by_card_identity(session: Session, card_identity: str) -> SDCard | None:
    stmt = select(SDCard).where(SDCard.card_identity == card_identity)
    return session.execute(stmt).scalar_one_or_none()


def register_or_touch(
    session: Session,
    *,
    volume_uid: str,
    volume_label: str | None = None,
    card_identity: str | None = None,
    drive_root: str | None = None,
) -> SDCard:
    """
    Register a new SD card or reconcile an existing one.

    Lookup priority:
      1. volume_uid     — fast path, normal reconnection
      2. card_identity  — same physical card, new volume UID (heals duplicates)
      3. create new     — genuinely first-ever scan of this card

    When found via card_identity (path 2), updates volume_uid on the existing
    record so future lookups hit path 1 again. No duplicate is ever created.
    """
    now = datetime.now(timezone.utc)

    # Path 1: known volume UID
    card = get_by_volume_uid(session, volume_uid)
    if card:
        card.last_seen_at = now
        if volume_label is not None:
            card.volume_label = volume_label
        if card_identity and not card.card_identity:
            card.card_identity = card_identity
            logger.info(f"Stored card identity {card_identity} on existing card {card.id}")
        return card

    # Path 2: same physical card, new volume UID
    if card_identity:
        card = get_by_card_identity(session, card_identity)
        if card:
            old_uid = card.volume_uid
            card.volume_uid   = volume_uid
            card.last_seen_at = now
            if volume_label is not None:
                card.volume_label = volume_label
            logger.info(
                f"Recognised card {card.id} ({card.volume_label!r}) by identity {card_identity}. "
                f"Healed volume_uid {old_uid!r} → {volume_uid!r}"
            )
            return card

    # Path 3: genuinely new card
    card = SDCard(
        volume_uid    = volume_uid,
        volume_label  = volume_label,
        card_identity = card_identity,
        first_seen_at = now,
        last_seen_at  = now,
    )
    session.add(card)
    logger.info(
        f"Registered new SD card volume_uid={volume_uid!r} "
        f"label={volume_label!r} identity={card_identity!r} "
        f"drive={drive_root!r}"
    )
    return card


def merge_into(
    session: Session,
    *,
    winner_id: int,
    loser_id: int,
    new_volume_uid: str | None = None,
    new_card_identity: str | None = None,
) -> int:
    """
    Merge loser SDCard into winner, re-parenting all child rows.

    Called by the post-scan merge pass when fingerprint matching determines
    two DB records represent the same physical card.

    - SDFile rows: loser → winner (fingerprint duplicates are deleted)
    - ClipSource rows: loser → winner
    - Optionally updates winner's volume_uid and card_identity
    - Deletes the loser record

    Returns the number of SDFile rows re-parented.
    """
    winner = session.get(SDCard, winner_id)
    loser  = session.get(SDCard, loser_id)
    if not winner or not loser:
        raise ValueError(f"merge_into: card {winner_id} or {loser_id} not found")

    logger.info(
        f"Merging card {loser_id} (uid={loser.volume_uid!r}) "
        f"into card {winner_id} (uid={winner.volume_uid!r})"
    )

    # Fingerprints already on the winner to detect true duplicates
    winner_fingerprints: set[str] = set(
        session.execute(
            select(SDFile.fingerprint).where(SDFile.sd_card_id == winner_id)
        ).scalars()
    )

    loser_files = list(
        session.execute(
            select(SDFile).where(SDFile.sd_card_id == loser_id)
        ).scalars()
    )

    reparented = 0
    for sd_file in loser_files:
        if sd_file.fingerprint in winner_fingerprints:
            session.delete(sd_file)       # genuine duplicate, drop loser copy
        else:
            sd_file.sd_card_id = winner_id
            winner_fingerprints.add(sd_file.fingerprint)
            reparented += 1

    # Re-parent ClipSource rows
    for source in session.execute(
        select(ClipSource).where(ClipSource.sd_card_id == loser_id)
    ).scalars():
        source.sd_card_id = winner_id

    session.flush()

    if new_volume_uid:
        winner.volume_uid = new_volume_uid
    if new_card_identity and not winner.card_identity:
        winner.card_identity = new_card_identity
    winner.last_seen_at = datetime.now(timezone.utc)

    session.delete(loser)
    session.flush()

    logger.info(
        f"Merge complete: {reparented} files re-parented, "
        f"{len(loser_files) - reparented} duplicates removed"
    )
    return reparented