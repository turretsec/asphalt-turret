from __future__ import annotations
from datetime import datetime, timezone
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.models.sd_file import SDFile
from asphalt_turret_engine.db.models.sd_card import SDCard
from asphalt_turret_engine.db.crud import clip, job as job_crud
from asphalt_turret_engine.db.models.clip import Clip
from asphalt_turret_engine.db.crud import clip as clip_crud
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


def _resolve_sd_card_path(sd_card: SDCard) -> Path | None:
    """
    Find the current mount path for an SD card.
    
    Args:
        sd_card: SDCard model instance
        
    Returns:
        Path to SD card root, or None if not found
    """
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

    Processes SD files in sequence, updating progress after each one.
    Skips individual failures and continues — does not abort the whole batch.

    After all files are processed, creates a probe job for the newly imported clips.

    Args:
        session: Database session
        job: Job with type=import_batch and metadata containing sd_card_id + file_ids

    Raises:
        RuntimeError: If job metadata is invalid or SD card is not found / not connected
    """
    # 1. Parse metadata
    metadata = job_crud.get_batch_metadata(job)
    if not metadata:
        raise RuntimeError(f"Job {job.id} has no metadata")

    sd_card_id = metadata.get("sd_card_id")
    file_ids = metadata.get("file_ids", [])

    if not sd_card_id or not file_ids:
        raise RuntimeError(f"Job {job.id} has invalid metadata: missing sd_card_id or file_ids")

    # 2. Resolve SD card and its current mount path
    sd_card = session.get(SDCard, sd_card_id)
    if not sd_card:
        raise RuntimeError(f"SD card {sd_card_id} not found in database")

    sd_card_path = _resolve_sd_card_path(sd_card)
    if not sd_card_path:
        raise RuntimeError(
            f"SD card '{sd_card.volume_uid}' is not currently connected"
        )

    logger.info(f"Job {job.id}: importing {len(file_ids)} file(s) from {sd_card_path}")

    # 3. Process each file
    completed: list[int] = []
    failed: list[int] = []
    newly_imported_clip_ids: list[int] = []
    total = len(file_ids)

    for idx, file_id in enumerate(file_ids, start=1):
        sd_file = session.get(SDFile, file_id)
        if not sd_file:
            logger.warning(f"SDFile {file_id} not found, skipping")
            failed.append(file_id)
            continue

        job.message = f"Importing {idx}/{total}: {Path(sd_file.rel_path).name}"
        session.flush()

        try:
            clip = _import_single_file(session, sd_file, sd_card_path)
            completed.append(file_id)
            if clip is not None:
                newly_imported_clip_ids.append(clip.id)

        except Exception as e:
            # File failed - log and continue
            logger.error(f"Failed to import file {file_id}: {e}", exc_info=True)
            failed.append(file_id)
            
            # Update progress to show failure
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()

        # Commit progress after each file so the UI can poll it
        job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
        session.commit()

    # 4. Set final message
    job.progress = 100
    if failed:
        job.message = f"Import complete: {len(completed)} succeeded, {len(failed)} failed"
        logger.warning(f"Job {job.id} finished with {len(failed)} failure(s)")
    else:
        job.message = f"Import complete: {len(completed)} file(s) imported"
        logger.info(f"Job {job.id} finished successfully")

    session.flush()

    # 5. Queue a probe job for all newly imported clips
    if newly_imported_clip_ids:
        probe_job = job_crud.create_probe_batch_job(session, clip_ids=newly_imported_clip_ids)
        session.flush()
        logger.info(
            f"Created probe job {probe_job.id} for {len(newly_imported_clip_ids)} new clip(s)"
        )

def _import_single_file(
    session: Session,
    sd_file: SDFile,
    sd_card_path: Path,
) -> Clip:
    """
    Import a single SD file into the repository.

    Args:
        session: Database session
        sd_file: The SDFile record to import
        sd_card_path: Root path of the mounted SD card

    Returns:
        The newly created (or deduplicated) Clip record

    Raises:
        FileNotFoundError: If the source file doesn't exist on the SD card
    """
    source_path = sd_card_path / sd_file.rel_path

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found on SD card: {source_path}")

    logger.info(f"Importing {source_path.name}")

    # Stage to incoming directory
    incoming_dir = settings.incoming_dir
    incoming_dir.mkdir(parents=True, exist_ok=True)
    incoming_path = incoming_dir / f"{uuid.uuid4().hex}_{source_path.name}"
    shutil.copy2(source_path, incoming_path)

    # Promote to repository (handles hashing, dedup, moving)
    clip = promote_to_repository(
        session,
        incoming_path,
        camera=parse_camera_from_path(sd_file.rel_path),
        mode=parse_mode_from_path(sd_file.rel_path),
        original_filename=source_path.name,
        recorded_at=parse_recorded_at_from_filename(source_path.name),
    )

    # Record provenance
    clip_source = ClipSource(
        clip_id=clip.id,
        sd_card_id=sd_file.sd_card_id,
        rel_path=sd_file.rel_path,
        seen_at=datetime.now(timezone.utc),
    )
    session.add(clip_source)

    # Mark SD file as imported
    sd_file.import_state = SDFileImportStateEnum.imported
    session.flush()

    logger.info(f"Imported {source_path.name} → clip {clip.id}")
    return clip