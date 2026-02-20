from datetime import datetime
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

from asphalt_turret_api.schemas.sd_card import SDCardListItem, SDCardsListResponse, ScanRequest, ScanResponse, SDFilesListResponse, SDFileResponse, TreeNode
from asphalt_turret_engine.db.session import get_db
from asphalt_turret_engine.services.sd_card_service import scan_sd_card
from asphalt_turret_engine.db.enums import SDFileImportStateEnum, ModeEnum, JobStateEnum
from asphalt_turret_engine.db.models.sd_file import SDFile
from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.db.enums import JobTypeEnum
import asphalt_turret_engine.db.crud.sd_card as sd_card_crud
import asphalt_turret_engine.db.crud.sd_file as sd_file_crud

from asphalt_turret_engine.services.thumbnail_service import get_thumbnail_path, generate_thumbnail

import time as _time
from pathlib import Path

_volume_cache: dict[str, tuple[Path, float]] = {}   # volume_uid → (mount_path, expires_at)
VOLUME_CACHE_TTL_S = 30.0

def _get_mount_path(volume_uid: str) -> Path | None:
    """Return the mount path for a volume UID, using a short-lived cache."""
    cached = _volume_cache.get(volume_uid)
    if cached and _time.monotonic() < cached[1]:
        return cached[0]

    from asphalt_turret_engine.adapters.volumes import list_removable_volumes
    for vol in list_removable_volumes():
        if vol.get("volume_uid") == volume_uid:
            path = Path(vol["drive_root"])
            _volume_cache[volume_uid] = (path, _time.monotonic() + VOLUME_CACHE_TTL_S)
            return path

    # Card not found — evict stale cache entry if present
    _volume_cache.pop(volume_uid, None)
    return None

router = APIRouter(prefix="/sd-card", tags=["sd-card"])
logger = logging.getLogger(__name__)

@router.post("/scan")
def trigger_sd_scan(db: Session = Depends(get_db)):
    """
    Trigger a scan of all connected SD cards.
    
    Creates a background job to scan for new/updated files.
    Returns immediately - scan happens asynchronously.
    """
    # Create SD scan job
    job = Job(
        type=JobTypeEnum.sd_scan,
        state=JobStateEnum.queued,
        progress=0,
        message="Queued: SD card scan"
    )
    db.add(job)
    db.commit()
    
    return {
        "job_id": job.id,
        "message": "SD card scan started"
    }
    
@router.get("/{volume_uid}/files", response_model=list[SDFileResponse])
def list_sd_card_files(
    volume_uid: str,
    import_state: Optional[SDFileImportStateEnum] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List files on an SD card.

    If the card has no DB record yet (never scanned, or UID changed and
    identity file not yet written), auto-registers it using the full
    register_or_touch logic — which checks card_identity first, so a
    UID-changed card that has an identity file on disk will find its
    existing record rather than creating a new one.

    Returns empty list for unscanned cards — prompt the user to scan.
    """
    card = sd_card_crud.get_by_volume_uid(db, volume_uid)

    if not card:
        from asphalt_turret_engine.adapters.volumes import list_removable_volumes
        from asphalt_turret_engine.adapters.card_identity import read_card_identity

        volumes = list_removable_volumes()
        vol = next((v for v in volumes if v["volume_uid"] == volume_uid), None)

        if not vol:
            raise HTTPException(
                status_code=404,
                detail=f"SD card '{volume_uid}' not found in database or connected volumes"
            )

        # Read identity file if it exists — allows register_or_touch to find
        # the existing record for a UID-changed card that was already scanned once
        card_identity = read_card_identity(vol["drive_root"])

        card = sd_card_crud.register_or_touch(
            db,
            volume_uid    = volume_uid,
            volume_label  = vol.get("volume_label"),
            card_identity = card_identity,
            drive_root    = vol["drive_root"],
        )
        db.commit()
        logger.info(
            f"Auto-registered SD card {volume_uid} "
            f"(identity={card_identity!r}) on first file list request"
        )

        # If register_or_touch found an existing record via card_identity,
        # it will have files. Otherwise it's genuinely new — return empty.
        # Either way, fall through to the normal file query below.

    files = sd_file_crud.list_files(
        db,
        card.id,
        import_state = import_state,
        limit        = limit,
        offset       = offset,
    )
    return [SDFileResponse.model_validate(f) for f in files]

@router.get("", response_model=list[SDCardListItem])
def list_sd_cards(
    include_stats: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all known SD cards, plus any connected Thinkware cards not yet scanned.

    A card that was never scanned (or whose volume UID changed) won't have a
    DB record, so it would never appear here — the user would have no way to
    trigger a scan on it. We fix this by also enumerating live volumes and
    including any Thinkware card that isn't already covered by a DB record.
    """
    from asphalt_turret_engine.adapters.volumes import list_removable_volumes
    from asphalt_turret_engine.adapters.sd_scanner import is_thinkware_sd_card
    from datetime import datetime, timezone

    # DB records
    cards = sd_card_crud.list_all(db)
    connected_volumes = list_removable_volumes()

    # volume_uid → drive_root for all currently connected volumes
    connected_map = {v["volume_uid"]: v["drive_root"] for v in connected_volumes}

    card_items = []
    seen_uids: set[str] = set()

    for card in cards:
        is_connected = card.volume_uid in connected_map
        drive_root   = connected_map.get(card.volume_uid)

        total_files   = 0
        pending_files = 0
        if include_stats:
            total_files   = sd_file_crud.count_files(db, card.id)
            pending_files = sd_file_crud.count_files(
                db, card.id, import_state=SDFileImportStateEnum.pending
            )

        card_items.append(SDCardListItem(
            volume_uid    = card.volume_uid,
            volume_label  = card.volume_label,
            first_seen_at = card.first_seen_at,
            last_seen_at  = card.last_seen_at,
            is_connected  = is_connected,
            drive_root    = drive_root,
            total_files   = total_files,
            pending_files = pending_files,
        ))
        seen_uids.add(card.volume_uid)

    # Live volumes not yet in DB
    # A card whose UID changed (or was never scanned) has no DB record.
    # Include it so the user can see it and trigger a scan.
    now = datetime.now(timezone.utc)

    for vol in connected_volumes:
        uid = vol["volume_uid"]
        if uid in seen_uids:
            continue  # already covered above

        drive_root = vol["drive_root"]

        # Only include it if it actually looks like a Thinkware card —
        # we don't want to surface every random USB drive.
        try:
            if not is_thinkware_sd_card(drive_root):
                continue
        except Exception:
            continue

        card_items.append(SDCardListItem(
            volume_uid    = uid,
            volume_label  = vol.get("volume_label"),
            first_seen_at = now,   # hasn't been scanned yet
            last_seen_at  = now,
            is_connected  = True,
            drive_root    = drive_root,
            total_files   = 0,
            pending_files = 0,
        ))

    return card_items

# TREEEEEES

@router.get("/{volume_uid}/tree", response_model=list[TreeNode])
def get_sd_card_tree(
    volume_uid: str,
    db: Session = Depends(get_db)
):
    """
    Get hierarchical tree of files on SD card grouped by mode and date.
    """
    print(f"[TREE] Getting tree for volume_uid: {volume_uid}")
    card = sd_card_crud.get_by_volume_uid(db, volume_uid)
    if not card:
        raise HTTPException(status_code=404, detail="SD card not found")
    
    print(f"[TREE] Found card ID: {card.id}")
    
    # Get all pending files
    files = sd_file_crud.list_files(
        db,
        card.id,
        import_state=SDFileImportStateEnum.new
    )

    print(f"[TREE] Found {len(files)} pending files")
    
    # Build tree structure
    from collections import defaultdict
    
    # Group by mode
    mode_groups = defaultdict(list)
    for file in files:
        # Parse mode from path
        mode = parse_mode_from_path(file.rel_path)
        mode_groups[mode].append(file)

    print(f"[TREE] Mode groups: {list(mode_groups.keys())}")
    
    tree = []
    
    for mode, mode_files in mode_groups.items():
        print(f"[TREE] Processing mode {mode} with {len(mode_files)} files")
        # Group files by date
        date_groups = defaultdict(list)
        total_size = 0
        
        for file in mode_files:
            # Parse date from filename
            date = parse_date_from_filename(file.rel_path)
            date_str = date.strftime("%B %d, %Y") if date else "Unknown Date"
            date_groups[date_str].append(file)
            total_size += file.size_bytes
        
        # Build date children
        date_children = []
        for date_str, date_files in sorted(date_groups.items(), reverse=True):
            date_size = sum(f.size_bytes for f in date_files)
            
            date_children.append(TreeNode(
                key=f"{card.id}-{mode.value}-{date_str}",
                label=f"{date_str} ({len(date_files)} files) - {format_size(date_size)}",
                icon="pi pi-calendar",
                data={
                    "type": "date",
                    "mode": mode.value,
                    "date": date_str,
                    "count": len(date_files),
                    "size": date_size
                },
                children=None
            ))
        
        # Build mode node
        tree.append(TreeNode(
            key=f"{card.id}-{mode.value}",
            label=f"{mode_label(mode)} ({len(mode_files)} files)",
            icon=mode_icon(mode),
            data={
                "type": "mode",
                "mode": mode.value,
                "count": len(mode_files),
                "size": total_size
            },
            children=date_children
        ))
    print(f"[TREE] Returning tree with {len(tree)} top-level nodes")
    return tree


def mode_label(mode: ModeEnum) -> str:
    """Get display label for mode."""
    labels = {
        ModeEnum.continuous: "Continuous Recording",
        ModeEnum.event: "Event Recording",
        ModeEnum.parking: "Parking Mode",
        ModeEnum.manual: "Manual Recording",
        ModeEnum.sos: "SOS/Emergency",
        ModeEnum.unknown: "Unknown"
    }
    return labels.get(mode, "Unknown")


def mode_icon(mode: ModeEnum) -> str:
    """Get PrimeVue icon for mode."""
    icons = {
        ModeEnum.continuous: "pi pi-circle",
        ModeEnum.event: "pi pi-exclamation-circle",
        ModeEnum.parking: "pi pi-car",
        ModeEnum.manual: "pi pi-video",
        ModeEnum.sos: "pi pi-shield",
        ModeEnum.unknown: "pi pi-question-circle"
    }
    return icons.get(mode, "pi pi-file")


def parse_mode_from_path(rel_path: str) -> ModeEnum:
    """Parse mode from file path."""
    path_lower = rel_path.lower()
    
    if "cont_rec" in path_lower:
        return ModeEnum.continuous
    elif "evt_rec" in path_lower:
        return ModeEnum.event
    elif "parking_rec" in path_lower:
        return ModeEnum.parking
    elif "manual_rec" in path_lower:
        return ModeEnum.manual
    elif "sos_rec" in path_lower:
        return ModeEnum.sos
    else:
        return ModeEnum.unknown


def parse_date_from_filename(filename: str) -> Optional[datetime]:
    """Parse date from Thinkware filename."""
    import re
    
    # Pattern: FRONT_20260113_080000.mp4
    match = re.search(r'(\d{8})_\d{6}', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            pass
    
    return None

def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    size = float(size_bytes)
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    
    return f"{size:.2f} PB"

@router.get("/{volume_uid}/files/{file_id}/thumbnail")
def get_sd_file_thumbnail(
    volume_uid: str,
    file_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Return cached thumbnail for an SD file, generating it in the background
    if not yet cached.

    The DB session is released as soon as we return — ffmpeg runs after the
    response is sent via BackgroundTasks, so it never holds a DB connection.
    This prevents QueuePool exhaustion when many thumbnails load concurrently.

    202 → not ready yet / card not mounted, client retries
    200 → thumbnail ready
    404 → file/card record not found in DB (genuine missing)
    """
    # ── Fast DB lookups — connection held only for this block ────────────────
    card = sd_card_crud.get_by_volume_uid(db, volume_uid)
    if not card:
        raise HTTPException(status_code=404, detail=f"SD card {volume_uid} not found")

    sd_file = db.get(SDFile, file_id)
    if not sd_file or sd_file.sd_card_id != card.id:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found on this SD card")

    rel_path = sd_file.rel_path   # copy out before session closes
    # DB session closes automatically after endpoint returns

    # ── Resolve mount path (cached) ──────────────────────────────────────────
    sd_card_path = _get_mount_path(volume_uid)
    if not sd_card_path:
        # Card not mounted — client retries, cache will refresh when it reconnects
        return Response(status_code=202, headers={"Retry-After": "5"})

    video_path = sd_card_path / rel_path
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {rel_path}")

    # ── Cache check — return immediately if thumbnail exists ─────────────────
    thumbnail_path = get_thumbnail_path(video_path)
    if thumbnail_path.exists():
        return FileResponse(
            thumbnail_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # ── Not cached — generate after response, tell client to retry ───────────
    # generate_thumbnail is idempotent: if two requests race, the second call
    # finds the file already exists and returns immediately.
    background_tasks.add_task(generate_thumbnail, video_path)

    return Response(status_code=202, headers={"Retry-After": "2"})
