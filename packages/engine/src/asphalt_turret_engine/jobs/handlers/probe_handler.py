from __future__ import annotations
import logging
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.models.clip import Clip
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.services.probe_service import probe_clip

logger = logging.getLogger(__name__)

COMMIT_EVERY = 25

def handle_probe_batch(session: Session, job: Job) -> None:
    metadata = job_crud.get_batch_metadata(job)
    if not metadata:
        raise RuntimeError(f"Job {job.id} has no metadata")

    clip_ids = metadata.get("clip_ids", [])
    if not clip_ids:
        raise RuntimeError(f"Job {job.id} has no clip_ids in metadata")

    completed: list[int] = []
    failed:    list[int] = []
    total = len(clip_ids)

    for idx, clip_id in enumerate(clip_ids, start=1):
        try:
            clip = session.get(Clip, clip_id)
            if not clip:
                logger.warning(f"Clip {clip_id} not found, skipping")
                failed.append(clip_id)
                continue

            job.message = f"Probing clip {idx}/{total}: {clip.original_filename or clip.id}"
            probe_clip(session, clip)
            completed.append(clip_id)

        except Exception as e:
            logger.error(f"Failed to probe clip {clip_id}: {e}", exc_info=True)
            failed.append(clip_id)

        if idx % COMMIT_EVERY == 0:
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()
            logger.info(f"Probe progress: {len(completed)}/{total}")

    job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
    session.commit()
    logger.info(f"Probe batch done: {len(completed)} probed, {len(failed)} failed")


def handle_probe_clip(session: Session, job: Job) -> None:
    """Handle a single-clip probe job."""
    if not job.clip_id:
        raise RuntimeError(f"Job {job.id} has no clip_id")

    clip = session.get(Clip, job.clip_id)
    if not clip:
        raise RuntimeError(f"Clip {job.clip_id} not found")

    job.message = f"Probing: {clip.original_filename or clip.id}"
    probe_clip(session, clip)
    session.commit()