from __future__ import annotations
import threading
import time
import traceback
import logging

from asphalt_turret_engine.db.session import get_db_context
from asphalt_turret_engine.db.enums import JobTypeEnum
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.jobs.handlers.import_handler import handle_import_batch
from asphalt_turret_engine.jobs.handlers.probe_handler import handle_probe_batch, handle_probe_clip


# Logger for worker
logger = logging.getLogger(__name__)

# Global stop event for graceful shutdown
_STOP_EVENT = threading.Event()

# How long to sleep when no jobs available
IDLE_SLEEP_S = 0.5


def stop_worker() -> None:
    """Signal the worker to stop gracefully."""
    logger.info("Stop signal received")
    _STOP_EVENT.set()


def worker_loop() -> None:
    """Main worker loop."""
    logger.info("Worker started")
    
    # On startup, requeue stale jobs
    with get_db_context() as session:  # ← Change from get_db
        requeued = job_crud.requeue_stale_running_jobs(session, stale_after_minutes=10)
        if requeued > 0:
            logger.info(f"Requeued {requeued} stale jobs on startup")
    
    while not _STOP_EVENT.is_set():
        did_work = False
        
        while not _STOP_EVENT.is_set():
            with get_db_context() as session:  # ← Change from get_db
                job = job_crud.claim_next_job(session)
                
                if not job:
                    break
                
                did_work = True
                logger.info(f"Claimed job {job.id}: {job.type.value}")
                
                try:
                    # Dispatch to handler based on job type
                    if job.type == JobTypeEnum.import_batch:
                        handle_import_batch(session, job)
                    elif job.type == JobTypeEnum.probe_batch:
                        handle_probe_batch(session, job)
                    elif job.type == JobTypeEnum.probe_clip:
                        handle_probe_clip(session, job)
                    else:
                        logger.warning(f"Unknown job type: {job.type}")
                    
                    # Mark job as completed
                    job_crud.mark_job_completed(session, job)
                    logger.info(f"Job {job.id} completed successfully")
                    
                except Exception as e:
                    # Job failed - log error and mark as failed
                    error_msg = f"{type(e).__name__}: {e}"
                    traceback_str = traceback.format_exc(limit=10)
                    full_msg = f"{error_msg}\n{traceback_str}"
                    
                    logger.error(f"Job {job.id} failed: {full_msg}")
                    job_crud.mark_job_failed(session, job, message=full_msg[:1000])
        
        # No work available - sleep before checking again
        if not did_work:
            time.sleep(IDLE_SLEEP_S)
    
    logger.info("Worker stopped")