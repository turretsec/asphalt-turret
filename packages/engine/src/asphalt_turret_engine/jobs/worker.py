from __future__ import annotations

import time
import logging
import traceback
import threading

from asphalt_turret_engine.db.session import get_db_context
from asphalt_turret_engine.db.enums import JobTypeEnum
from asphalt_turret_engine.db.crud import job as job_crud

from asphalt_turret_engine.jobs.handlers.import_handler import handle_import_batch
from asphalt_turret_engine.jobs.handlers.probe_handler import handle_probe_batch, handle_probe_clip
from asphalt_turret_engine.jobs.handlers.thumb_handler import handle_thumb_batch
from asphalt_turret_engine.jobs.handlers.thumb_sd_handler import handle_thumb_sd_batch
from asphalt_turret_engine.jobs.handlers.sd_scan_handler import handle_sd_scan

logger = logging.getLogger(__name__)

IDLE_SLEEP_S = 2

# ── Job tiers ─────────────────────────────────────────────────────────────────
#
# FOREGROUND: user-triggered, they're waiting on these.
# BACKGROUND: nice-to-have, must never block foreground work.
#
# Each tier gets its own thread. claim_next_job filters by type list so the
# two threads never compete for the same job.

FOREGROUND_TYPES = [
    JobTypeEnum.sd_scan,
    JobTypeEnum.import_batch,
    JobTypeEnum.probe_batch,
    JobTypeEnum.probe_clip,
]

BACKGROUND_TYPES = [
    JobTypeEnum.thumb_batch,
    JobTypeEnum.thumb_sd_batch,
]

_STOP_EVENT = threading.Event()


def stop_worker() -> None:
    logger.info("Stop signal received")
    _STOP_EVENT.set()


def worker_loop(job_types: list[JobTypeEnum] | None = None, name: str = "worker") -> None:
    """
    Main worker loop. Processes jobs of the given types only.
    Pass job_types=None to process all types (legacy / single-worker mode).
    """
    logger.info(f"{name} started — types: {[t.value for t in job_types] if job_types else 'all'}")

    # On startup, requeue stale jobs. Only the foreground worker does this to
    # avoid double-requeue when both threads start simultaneously.
    if job_types == FOREGROUND_TYPES or job_types is None:
        with get_db_context() as session:
            requeued = job_crud.requeue_stale_running_jobs(session, stale_after_minutes=10)
            if requeued > 0:
                logger.info(f"{name}: requeued {requeued} stale jobs on startup")

    while not _STOP_EVENT.is_set():
        did_work = False

        while not _STOP_EVENT.is_set():
            with get_db_context() as session:
                job = job_crud.claim_next_job(session, job_types=job_types)

                if not job:
                    break

                did_work = True
                job_id   = job.id
                job_type = job.type.value
                logger.info(f"{name}: claimed job {job_id} ({job_type})")

                try:
                    if job.type == JobTypeEnum.import_batch:
                        handle_import_batch(session, job)
                    elif job.type == JobTypeEnum.probe_batch:
                        handle_probe_batch(session, job)
                    elif job.type == JobTypeEnum.probe_clip:
                        handle_probe_clip(session, job)
                    elif job.type == JobTypeEnum.thumb_batch:
                        handle_thumb_batch(session, job)
                    elif job.type == JobTypeEnum.thumb_sd_batch:
                        handle_thumb_sd_batch(session, job)
                    elif job.type == JobTypeEnum.sd_scan:
                        handle_sd_scan(session, job)
                    else:
                        logger.warning(f"{name}: unknown job type {job.type}")

                    job_crud.mark_job_completed(session, job)
                    logger.info(f"{name}: job {job_id} completed")

                except Exception as e:
                    full_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=10)}"
                    logger.error(f"{name}: job {job_id} failed: {full_msg}")
                    try:
                        session.rollback()
                        job_crud.mark_job_failed(session, job, message=full_msg[:1000])
                    except Exception as mark_err:
                        logger.error(f"{name}: also failed to mark job {job_id} as failed: {mark_err}")

        if not did_work:
            time.sleep(IDLE_SLEEP_S)

    logger.info(f"{name} stopped")