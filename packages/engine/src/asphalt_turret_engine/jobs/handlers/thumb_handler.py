from __future__ import annotations
import logging
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.models.clip import Clip
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.services.thumbnail_service import generate_thumbnail
from asphalt_turret_engine.utils.repo_paths import get_absolute_clip_path

logger = logging.getLogger(__name__)

COMMIT_EVERY = 25


def handle_thumb_batch(session: Session, job: Job) -> None:
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
                logger.warning(f"Clip {clip_id} not found, skipping thumbnail")
                failed.append(clip_id)
                continue

            job.message = f"Generating thumbnail {idx}/{total}: {clip.original_filename or clip.id}"

            video_path = get_absolute_clip_path(clip)
            if not video_path.exists():
                logger.warning(f"Video file not found for clip {clip_id}: {video_path}")
                failed.append(clip_id)
            else:
                generate_thumbnail(video_path)
                completed.append(clip_id)

        except Exception as e:
            logger.error(f"Failed thumbnail for clip {clip_id}: {e}", exc_info=True)
            failed.append(clip_id)

        # Commit every N items instead of every item — reduces write-lock
        # contention with concurrent API requests significantly
        if idx % COMMIT_EVERY == 0:
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()
            logger.info(f"Thumbnail progress: {len(completed)}/{total}")

    # Final commit for the remainder
    job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
    session.commit()
    logger.info(f"Thumbnail batch done: {len(completed)} generated, {len(failed)} failed")