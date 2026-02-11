from __future__ import annotations
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.clip import Clip
from asphalt_turret_engine.db.enums import CameraEnum, ModeEnum, MetadataStatusEnum
from asphalt_turret_engine.utils.hashing import calculate_file_hash
from asphalt_turret_engine.utils.repo_paths import get_clip_repository_path
from asphalt_turret_engine.config import settings

logger = logging.getLogger(__name__)

def _safe_move_file(src: Path, dst: Path) -> None:
    """
    Move file from src to dst, with fallback for cross-filesystem moves.
    
    Args:
        src: Source path
        dst: Destination path
    """
    try:
        # Try atomic rename first (fast, works if same filesystem)
        src.rename(dst)
    except OSError:
        # Different filesystems - fall back to copy + delete
        import shutil
        shutil.copy2(src, dst)
        src.unlink()


def promote_to_repository(
    session: Session,
    incoming_path: Path,
    *,
    camera: CameraEnum = CameraEnum.unknown,
    mode: ModeEnum = ModeEnum.unknown,
    original_filename: str | None = None,
    recorded_at: datetime | None = None,
) -> Clip:
    """
    Move a file from incoming to repository and create Clip record.
    
    Handles deduplication: if file with same hash exists, returns existing clip
    and deletes the incoming file.
    
    Args:
        session: Database session
        incoming_path: Path to file in incoming directory
        camera: Camera that recorded this (front/rear/unknown)
        mode: Recording mode (continuous/event/parking/etc)
        original_filename: Original filename from SD card
        recorded_at: When video was recorded (for organization)
        
    Returns:
        Clip instance (either newly created or existing duplicate)
        
    Raises:
        FileNotFoundError: If incoming file doesn't exist
        
    Note: Caller must commit the session.
    """
    if not incoming_path.exists():
        raise FileNotFoundError(f"Incoming file not found: {incoming_path}")
    
    # 1. Calculate hash
    logger.info(f"Hashing file: {incoming_path.name}")
    file_hash = calculate_file_hash(incoming_path)
    file_size = incoming_path.stat().st_size
    
    logger.info(f"File hash: {file_hash[:16]}... (size: {file_size} bytes)")
    
    # 2. Check for existing clip with same hash (deduplication)
    existing_clip = session.execute(
        select(Clip).where(Clip.file_hash == file_hash)
    ).scalar_one_or_none()
    
    if existing_clip:
        logger.info(f"Duplicate detected! Clip {existing_clip.id} already exists with this hash")
        # Delete incoming file (it's a duplicate)
        incoming_path.unlink()
        logger.info(f"Deleted duplicate file: {incoming_path.name}")
        return existing_clip
    
    # 3. Generate repository path
    repo_rel_path = get_clip_repository_path(
        file_hash=file_hash,
        recorded_at=recorded_at,
        original_filename=original_filename
    )
    
    repo_abs_path = settings.repository_dir / repo_rel_path
    
    # 4. Create directory structure
    repo_abs_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 5. Move file to repository (atomic operation within same filesystem)
    logger.info(f"Moving to repository: {repo_rel_path}")
    _safe_move_file(incoming_path, repo_abs_path)
    
    # 6. Create Clip record
    clip = Clip(
        file_hash=file_hash,
        repo_path=str(repo_rel_path),
        original_filename=original_filename,
        camera=camera,
        mode=mode,
        recorded_at=recorded_at,
        imported_at=datetime.now(timezone.utc),
        metadata_status=MetadataStatusEnum.pending,
    )
    
    session.add(clip)
    session.flush()  # Get clip.id
    
    logger.info(f"Created clip {clip.id}: {repo_rel_path}")
    
    return clip