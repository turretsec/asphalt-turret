from __future__ import annotations
from datetime import datetime, timezone
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.models.sd_file import SDFile
from asphalt_turret_engine.db.models.sd_card import SDCard
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.services.clip_service import promote_to_repository
from asphalt_turret_engine.db.models.clip_source import ClipSource
from asphalt_turret_engine.db.enums import CameraEnum, ModeEnum

from asphalt_turret_engine.utils.filename_parser import (
    parse_camera_from_path,
    parse_mode_from_path,
    parse_recorded_at_from_filename
)

from asphalt_turret_engine.config import settings
from asphalt_turret_engine.db.enums import SDFileImportStateEnum
import shutil
import uuid

logger = logging.getLogger(__name__)


def _resolve_sd_card_path(session: Session, sd_card: SDCard) -> Path | None:
    """
    Find the current mount path for an SD card.
    
    Args:
        session: Database session
        sd_card: SDCard model instance
        
    Returns:
        Path to SD card root, or None if not found
    """
    # TODO: Implement actual volume detection
    # For now, you'll need to import your volume scanner
    from asphalt_turret_engine.adapters.volumes import list_removable_volumes
    
    volumes = list_removable_volumes()
    
    for volume in volumes:
        if volume.get("volume_uid") == sd_card.volume_uid:
            return Path(volume["drive_root"])
    
    return None


def _get_sd_file_source_path(sd_card_path: Path, sd_file: SDFile) -> Path:
    """
    Get the full path to a file on the SD card.
    
    Args:
        sd_card_path: Root path of SD card (e.g., "E:\\")
        sd_file: SDFile with relative path
        
    Returns:
        Full path to the file
    """
    return sd_card_path / sd_file.rel_path

def handle_import_batch(session: Session, job: Job) -> None:
    """
    Handle a batch import job.
    
    Processes multiple SD files in sequence, updating progress after each file.
    Continues on individual file failures (logs error and moves to next file).
    
    Args:
        session: Database session
        job: Job with type=import_batch and metadata containing file_ids
        
    Raises:
        RuntimeError: If job metadata is invalid or SD card not found
        
    Note: Caller must commit the session after completion.
    """
    # 1. Parse metadata
    metadata = job_crud.get_batch_metadata(job)
    
    if not metadata:
        raise RuntimeError(f"Job {job.id} has no metadata")
    
    sd_card_id = metadata.get("sd_card_id")
    file_ids = metadata.get("file_ids", [])
    
    if not sd_card_id or not file_ids:
        raise RuntimeError(f"Job {job.id} has invalid metadata")
    
    # 2. Get SD card and resolve path
    sd_card = session.get(SDCard, sd_card_id)
    if not sd_card:
        raise RuntimeError(f"SDCard {sd_card_id} not found")
    
    job.message = f"Resolving SD card path (volume_uid={sd_card.volume_uid})"
    session.flush()
    
    sd_card_path = _resolve_sd_card_path(session, sd_card)
    if not sd_card_path:
        raise RuntimeError(
            f"SD card {sd_card.volume_uid} not found. Is it inserted?"
        )
    
    logger.info(f"Found SD card at: {sd_card_path}")
    
    # 3. Process files
    completed = []
    failed = []
    total = len(file_ids)
    
    for idx, file_id in enumerate(file_ids, start=1):
        try:
            # Get SD file
            sd_file = session.get(SDFile, file_id)
            if not sd_file:
                logger.warning(f"SDFile {file_id} not found, skipping")
                failed.append(file_id)
                continue
            
            # Update progress message
            job.message = f"Importing file {idx}/{total}: {sd_file.rel_path}"
            session.flush()
            
            # Import this file
            _import_single_file(session, sd_file, sd_card_path)
            completed.append(file_id)
            
            # Update progress after each file
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()  # Commit after each file (resumable!)
            
            logger.info(f"Progress: {len(completed)}/{total} files")
            
        except Exception as e:
            # File failed - log and continue
            logger.error(f"Failed to import file {file_id}: {e}", exc_info=True)
            failed.append(file_id)
            
            # Update progress to show failure
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()
    
    # 4. Final state
    job.progress = 100
    
    if failed:
        job.message = f"Import complete: {len(completed)} succeeded, {len(failed)} failed"
        logger.warning(f"Job {job.id} completed with {len(failed)} failures")
    else:
        job.message = f"Import complete: {len(completed)} files imported successfully"
        logger.info(f"Job {job.id} completed successfully")
    
    session.flush()

def _import_single_file(
    session: Session,
    sd_file: SDFile,
    sd_card_path: Path
) -> None:
    """Import a single file from SD card to repository."""
    
    # 1. Get source path
    source_path = _get_sd_file_source_path(sd_card_path, sd_file)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    logger.info(f"Importing {source_path.name}")
    
    # 2. Copy to incoming
    incoming_dir = settings.incoming_dir
    incoming_dir.mkdir(parents=True, exist_ok=True)
    
    unique_name = f"{uuid.uuid4().hex}_{source_path.name}"
    incoming_path = incoming_dir / unique_name
    
    shutil.copy2(source_path, incoming_path)
    
    # 3. Promote to repository (NEW!)
    clip = promote_to_repository(
        session,
        incoming_path,
        camera=parse_camera_from_path(sd_file.rel_path),
        mode=parse_mode_from_path(sd_file.rel_path),
        original_filename=source_path.name,
        recorded_at=parse_recorded_at_from_filename(source_path.name),
    )
    
    # 4. Create ClipSource (provenance)
    clip_source = ClipSource(
        clip_id=clip.id,
        sd_card_id=sd_file.sd_card_id,
        rel_path=sd_file.rel_path,
        seen_at=datetime.now(timezone.utc)
    )
    session.add(clip_source)
    
    # 5. Mark as imported
    sd_file.import_state = SDFileImportStateEnum.imported
    session.flush()
    logger.info(f"Successfully imported as clip {clip.id}")