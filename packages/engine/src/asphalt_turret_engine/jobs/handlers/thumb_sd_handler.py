from __future__ import annotations
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.job import Job
from asphalt_turret_engine.db.models.sd_file import SDFile
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.services.thumbnail_service import generate_thumbnail, get_thumbnail_path

logger = logging.getLogger(__name__)

COMMIT_EVERY = 25

def handle_thumb_sd_batch(session: Session, job: Job) -> None:
    metadata = job_crud.get_batch_metadata(job)
    if not metadata:
        raise RuntimeError(f"Job {job.id} has no metadata")

    sd_file_ids = metadata.get("sd_file_ids", [])
    drive_root  = metadata.get("drive_root")

    if not sd_file_ids:
        raise RuntimeError(f"Job {job.id} has no sd_file_ids in metadata")
    if not drive_root:
        raise RuntimeError(f"Job {job.id} has no drive_root in metadata")

    card_path  = Path(drive_root)
    completed: list[int] = []
    failed:    list[int] = []
    skipped = 0
    total   = len(sd_file_ids)

    for idx, file_id in enumerate(sd_file_ids, start=1):
        try:
            sd_file = session.get(SDFile, file_id)
            if not sd_file:
                skipped += 1
                continue

            video_path = card_path / sd_file.rel_path

            if not video_path.exists():
                logger.debug(f"SD file not accessible (card unmounted?): {video_path}")
                skipped += 1
                continue

            if get_thumbnail_path(video_path).exists():
                completed.append(file_id)
                continue

            job.message = f"SD thumbnail {idx}/{total}: {sd_file.rel_path}"
            generate_thumbnail(video_path)
            completed.append(file_id)

        except Exception as e:
            logger.error(f"Failed SD thumbnail for file {file_id}: {e}", exc_info=True)
            failed.append(file_id)

        # Commit every N items
        if idx % COMMIT_EVERY == 0:
            job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
            session.commit()
            logger.info(f"SD thumbnail progress: {len(completed)}/{total - skipped}")

    # Final commit
    parts = [f"{len(completed)} generated"]
    if skipped:
        parts.append(f"{skipped} skipped (card unmounted)")
    if failed:
        parts.append(f"{len(failed)} failed")

    job.message = "SD thumbnails complete: " + ", ".join(parts)
    job_crud.update_batch_progress(session, job, completed=completed, failed=failed)
    session.commit()
    logger.info(f"Job {job.id} done: {job.message}")