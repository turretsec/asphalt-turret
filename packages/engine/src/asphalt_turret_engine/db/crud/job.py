from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.enums import JobStateEnum, JobTypeEnum

def claim_next_job(session: Session, *, job_type: JobTypeEnum | None = None) -> Job | None:
    """
    Try to claim the next queued job by marking it as running.
    Returns the claimed Job, or None if no job was available.
    """
    stmt = select(Job.id).where(Job.state == JobStateEnum.queued)
    if job_type is not None:
        stmt = stmt.where(Job.type == job_type)

    stmt = stmt.order_by(Job.created_at.asc()).limit(1)
    row = session.execute(stmt).first()
    if not row:
        return None

    job_id = row[0]

    upd = (
        update(Job)
        .where(Job.id == job_id, Job.state == JobStateEnum.queued)
        .values(
            state=JobStateEnum.running,
            updated_at=func.now(),
            progress=0,
        )
    )
    session.execute(upd)
    session.commit()

    job = session.get(Job, job_id)

    if job and job.state == JobStateEnum.running:
        return job

    return None

def mark_job_completed(session: Session, job: Job, *, message: str | None = None) -> None:
    job.state = JobStateEnum.completed
    job.progress = 100
    job.updated_at = datetime.now(timezone.utc)
    if message is not None:
        job.message = message
    session.commit()

def mark_job_failed(session: Session, job: Job, *, message: str | None = None) -> None:
    job.state = JobStateEnum.failed
    job.updated_at = datetime.now(timezone.utc)
    job.message = message
    session.commit()

def requeue_stale_running_jobs(session: Session, *, stale_after_minutes: int = 10) -> int:
    """
    Re-queue jobs that have been in the running state for too long.
    Returns the number of jobs re-queued.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
    stmt = (
        update(Job)
        .where(Job.state == JobStateEnum.running, Job.updated_at < cutoff)
        .values(
            state=JobStateEnum.queued,
            message="Re-queued due to staleness",
            progress=0,
            updated_at=datetime.now(timezone.utc),
        )
    )
    res = session.execute(stmt)
    session.commit()
    return int(res.rowcount or 0)  # type: ignore[attr-defined]

def create_import_batch_job(
    session: Session,
    *,
    sd_card_id: int,
    file_ids: list[int]
) -> Job:
    """
    Create a batch import job for multiple SD files.
    
    Args:
        session: Database session
        sd_card_id: ID of the SD card being imported
        file_ids: List of SDFile IDs to import
        
    Returns:
        Created Job instance
        
    Note: Caller must commit the session.
    """
    metadata = {
        "sd_card_id": sd_card_id,
        "file_ids": file_ids,
        "completed": [],  # Files successfully imported
        "failed": [],     # Files that failed (we skip and continue)
        "total": len(file_ids)
    }
    
    job = Job(
        type=JobTypeEnum.import_batch,
        state=JobStateEnum.queued,
        metadata_json=json.dumps(metadata) if metadata else None,
        progress=0,
        message=f"Queued: {len(file_ids)} files to import"
    )
    session.add(job)
    return job

def get_batch_metadata(job: Job) -> dict:
    """
    Parse and return batch job metadata.
    
    Args:
        job: Job with metadata_json field
        
    Returns:
        Parsed metadata dict, or empty dict if no metadata
    """
    if not job.metadata_json:
        return {}
    
    try:
        return json.loads(job.metadata_json)
    except json.JSONDecodeError:
        return {}


def update_batch_progress(
    session: Session,
    job: Job,
    *,
    completed: list[int],
    failed: list[int]
) -> None:
    """
    Update batch job progress based on completed/failed files.
    
    Args:
        session: Database session
        job: Job to update
        completed: List of successfully processed file IDs
        failed: List of failed file IDs
        
    Note: Caller must commit the session.
    """
    metadata = get_batch_metadata(job)
    total = metadata.get("total", 0)
    
    if total == 0:
        job.progress = 100
        return
    
    # Update metadata
    metadata["completed"] = completed
    metadata["failed"] = failed
    job.metadata_json = json.dumps(metadata)
    
    # Calculate progress (completed files / total files)
    job.progress = len(completed) * 100 // total
    
    # Update message
    if failed:
        job.message = f"Imported {len(completed)}/{total} files ({len(failed)} failed)"
    else:
        job.message = f"Imported {len(completed)}/{total} files"

def create_probe_batch_job(
    session: Session,
    *,
    clip_ids: list[int]
) -> Job:
    """
    Create a batch probe job for multiple clips.
    
    Args:
        session: Database session
        clip_ids: List of Clip IDs to probe
        
    Returns:
        Created Job instance
        
    Note: Caller must commit the session.
    """
    metadata = {
        "clip_ids": clip_ids,
        "completed": [],
        "failed": [],
        "total": len(clip_ids)
    }
    
    job = Job(
        type=JobTypeEnum.probe_batch,
        state=JobStateEnum.queued,
        metadata_json=json.dumps(metadata) if metadata else None,
        progress=0,
        message=f"Queued: {len(clip_ids)} clips to probe"
    )
    session.add(job)
    return job


def enqueue_clip_probe(session: Session, *, clip_id: int) -> Job:
    """
    Create a single-clip probe job (or return existing active one).
    
    Prevents duplicate jobs for the same clip.
    
    Args:
        session: Database session
        clip_id: Clip ID to probe
        
    Returns:
        Job instance (either existing or newly created)
        
    Note: Caller must commit the session.
    """
    from asphalt_turret_engine.db.enums import JobStateEnum
    
    # Check for existing active job for this clip
    active_states = (JobStateEnum.queued, JobStateEnum.running)
    
    existing = session.execute(
        select(Job).where(
            Job.type == JobTypeEnum.probe_clip,
            Job.clip_id == clip_id,
            Job.state.in_(active_states)
        ).order_by(Job.id.desc())
    ).scalar_one_or_none()
    
    if existing:
        return existing
    
    # Create new job
    job = Job(
        type=JobTypeEnum.probe_clip,
        state=JobStateEnum.queued,
        clip_id=clip_id,
        progress=0,
        message="Queued for probing"
    )
    session.add(job)
    return job

def create_thumb_batch_job(
    session: Session,
    *,
    clip_ids: list[int]
) -> Job:
    """
    Create a batch thumbnail generation job for multiple clips.

    Queued automatically after import alongside probe_batch so that
    thumbnails are ready by the time the user opens the clip browser.
    The HTTP thumbnail endpoint checks the cache and returns 404 if the
    thumbnail isn't ready yet — the frontend retries with backoff.

    Args:
        session: Database session
        clip_ids: List of Clip IDs to generate thumbnails for

    Returns:
        Created Job instance (caller must commit)
    """
    metadata = {
        "clip_ids": clip_ids,
        "completed": [],
        "failed": [],
        "total": len(clip_ids),
    }

    job = Job(
        type=JobTypeEnum.thumb_batch,
        state=JobStateEnum.queued,
        metadata_json=json.dumps(metadata),
        progress=0,
        message=f"Queued: thumbnails for {len(clip_ids)} clips",
    )
    session.add(job)
    return job