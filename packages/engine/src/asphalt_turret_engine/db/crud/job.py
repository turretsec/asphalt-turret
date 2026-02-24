from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.enums import JobStateEnum, JobTypeEnum


# ── Startup recovery ──────────────────────────────────────────────────────────

def recover_interrupted_jobs(
    session: Session,
    *,
    foreground_types: list[JobTypeEnum],
    background_types: list[JobTypeEnum],
) -> tuple[int, int]:
    """
    Called once at startup. Any job still marked as running couldn't have been
    legitimately running — the worker process was killed. Handle by tier:

    Foreground (user was waiting): requeue so they complete on next run.
    Background (thumbnails etc.):  mark as failed — they're idempotent and
                                   will be recreated by the next sd_scan.

    Returns (requeued_count, failed_count).
    """
    now = datetime.now(timezone.utc)

    # Requeue foreground
    requeue_result = session.execute(
        update(Job)
        .where(
            Job.state == JobStateEnum.running,
            Job.type.in_(foreground_types),
        )
        .values(
            state=JobStateEnum.queued,
            message="Re-queued: worker was interrupted",
            progress=0,
            updated_at=now,
        )
    )
    requeued = getattr(requeue_result, 'rowcount', 0) or 0

    # Fail background
    fail_result = session.execute(
        update(Job)
        .where(
            Job.state == JobStateEnum.running,
            Job.type.in_(background_types),
        )
        .values(
            state=JobStateEnum.failed,
            message="Failed: worker was interrupted (will be recreated on next scan)",
            updated_at=now,
        )
    )
    failed = getattr(fail_result,   'rowcount', 0) or 0

    session.commit()
    return requeued, failed


def requeue_stale_running_jobs(session: Session, *, stale_after_minutes: int = 10) -> int:
    """
    Re-queue foreground jobs that have been stuck in running state mid-run.
    (Background jobs are excluded — they're low-priority and idempotent.)
    Called periodically during normal operation, not at startup.
    """
    from asphalt_turret_engine.jobs.worker import FOREGROUND_TYPES  # avoid circular at module level

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
    stmt = (
        update(Job)
        .where(
            Job.state == JobStateEnum.running,
            Job.type.in_(FOREGROUND_TYPES),
            Job.updated_at < cutoff,
        )
        .values(
            state=JobStateEnum.queued,
            message="Re-queued due to staleness",
            progress=0,
            updated_at=datetime.now(timezone.utc),
        )
    )
    res = session.execute(stmt)
    session.commit()
    return getattr(res, 'rowcount', 0) or 0


# ── Job claiming ──────────────────────────────────────────────────────────────

def claim_next_job(
    session: Session,
    *,
    job_types: list[JobTypeEnum] | None = None,
) -> Job | None:
    """
    Try to claim the next queued job by marking it as running.
    Returns the claimed Job, or None if no job was available.

    job_types: if provided, only jobs of those types are eligible.
    """
    stmt = select(Job.id).where(Job.state == JobStateEnum.queued)

    if job_types is not None:
        stmt = stmt.where(Job.type.in_(job_types))

    stmt = stmt.order_by(Job.created_at.asc()).limit(1)
    row = session.execute(stmt).first()
    if not row:
        return None

    job_id = row[0]

    upd = (
        update(Job)
        .where(Job.id == job_id, Job.state == JobStateEnum.queued)
        .values(state=JobStateEnum.running, updated_at=func.now(), progress=0)
    )
    session.execute(upd)
    session.commit()

    job = session.get(Job, job_id)
    if job and job.state == JobStateEnum.running:
        return job

    return None


# ── Thumbnail job creators with dedup ─────────────────────────────────────────

def create_thumb_batch_job(session: Session, *, clip_ids: list[int]) -> Job:
    """
    Create a thumb_batch job, or return the existing active one if present.
    'Active' means queued or running — no point queuing a second pass while
    one is already in flight.
    """
    active_states = (JobStateEnum.queued, JobStateEnum.running)

    existing = session.execute(
        select(Job)
        .where(Job.type == JobTypeEnum.thumb_batch, Job.state.in_(active_states))
        .order_by(Job.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    if existing:
        return existing

    metadata = {
        "clip_ids":  clip_ids,
        "completed": [],
        "failed":    [],
        "total":     len(clip_ids),
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


def create_thumb_sd_batch_job(session, *, volume_uid, drive_root, sd_file_ids) -> Job:
    active_states = (JobStateEnum.queued, JobStateEnum.running)

    # Cancel any existing active job for this card — the scan just produced
    # fresh file IDs so a new job reflects current reality. Already-generated
    # thumbnails are skipped instantly (idempotent), so no real work is lost.
    existing = session.execute(
        select(Job)
        .where(
            Job.type == JobTypeEnum.thumb_sd_batch,
            Job.state.in_(active_states),
            Job.metadata_json.like(f'%{volume_uid}%'),
        )
    ).scalars().all()

    for old_job in existing:
        old_job.state = JobStateEnum.failed
        old_job.message = "Superseded by newer scan"
        old_job.updated_at = datetime.now(timezone.utc)

    # Create fresh job with current file IDs
    metadata = {
        "volume_uid":  volume_uid,
        "drive_root":  drive_root,
        "sd_file_ids": sd_file_ids,
        "completed":   [],
        "failed":      [],
        "total":       len(sd_file_ids),
    }
    job = Job(
        type=JobTypeEnum.thumb_sd_batch,
        state=JobStateEnum.queued,
        metadata_json=json.dumps(metadata),
        progress=0,
        message=f"Queued: SD thumbnails for {len(sd_file_ids)} files ({volume_uid})",
    )
    session.add(job)
    return job


# ── Remaining existing functions (unchanged) ──────────────────────────────────

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


def get_batch_metadata(job: Job) -> dict | None:
    if not job.metadata_json:
        return None
    return json.loads(job.metadata_json)


def update_batch_progress(
    session: Session,
    job: Job,
    *,
    completed: list,
    failed: list,
) -> None:
    metadata = get_batch_metadata(job) or {}
    total = metadata.get("total", len(completed) + len(failed))
    metadata["completed"] = completed
    metadata["failed"] = failed
    job.metadata_json = json.dumps(metadata)
    job.progress = int(len(completed) / total * 100) if total > 0 else 0
    job.updated_at = datetime.now(timezone.utc)

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