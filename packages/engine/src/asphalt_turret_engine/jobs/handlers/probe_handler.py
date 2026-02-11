from __future__ import annotations
import logging
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.models.clip import Clip
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.services.probe_service import probe_clip

logger = logging.getLogger(__name__)


def handle_probe_batch(session: Session, job: Job) -> None:
    """
    Handle a batch probe job.
    
    Probes multiple clips in sequence, updating progress after each.
    Continues on individual failures (logs error and moves to next clip).
    
    Args:
        session: Database session
        job: Job with type=probe_batch and metadata containing clip_ids
        
    Raises:
        RuntimeError: If job metadata is invalid
        
    Note: Caller must commit the session after completion.
    """
    # 1. Parse metadata
    metadata = job_crud.get_batch_metadata(job)
    
    if not metadata:
        raise RuntimeError(f"Job {job.id} has no metadata")
    
    clip_ids = metadata.get("clip_ids", [])
    
    if not clip_ids:
        raise RuntimeError(f"Job {job.id} has no clip_ids in metadata")
    
    # 2. Process clips
    completed = []
    failed = []
    total = len(clip_ids)
    
    for idx, clip_id in enumerate(clip_ids, start=1):
        try:
            # Get clip
            clip = session.get(Clip, clip_id)
            if not clip:
                logger.warning(f"Clip {clip_id} not found, skipping")
                failed.append(clip_id)
                continue
            
            # Update progress message
            job.message = f"Probing clip {idx}/{total}: {clip.original_filename or clip.id}"
            session.flush()
            
            # Probe this clip
            probe_clip(session, clip)
            completed.append(clip_id)
            
            # Update progress after each clip
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()  # Commit after each clip (resumable)
            
            logger.info(f"Progress: {len(completed)}/{total} clips probed")
            
        except Exception as e:
            # Clip probe failed - log and continue
            logger.error(f"Failed to probe clip {clip_id}: {e}", exc_info=True)
            failed.append(clip_id)
            
            # Update progress to show failure
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()
    
    # 3. Final state
    job.progress = 100
    
    if failed:
        job.message = f"Probe complete: {len(completed)} succeeded, {len(failed)} failed"
        logger.warning(f"Job {job.id} completed with {len(failed)} failures")
    else:
        job.message = f"Probe complete: {len(completed)} clips probed successfully"
        logger.info(f"Job {job.id} completed successfully")
    
    session.flush()


def handle_probe_clip(session: Session, job: Job) -> None:
    """
    Handle a single-clip probe job.
    
    Args:
        session: Database session
        job: Job with type=probe_clip and clip_id set
        
    Raises:
        RuntimeError: If clip_id is missing or clip not found
        
    Note: Caller must commit the session after completion.
    """
    if job.clip_id is None:
        raise RuntimeError(f"Job {job.id} has no clip_id")
    
    clip = session.get(Clip, job.clip_id)
    if not clip:
        raise RuntimeError(f"Clip {job.clip_id} not found")
    
    job.message = f"Probing clip: {clip.original_filename or clip.id}"
    session.flush()
    
    # Probe the clip
    probe_clip(session, clip)
    
    job.progress = 100
    job.message = "Probe complete"
    session.flush()