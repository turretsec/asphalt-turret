from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
from asphalt_turret_engine.jobs.worker import (
    worker_loop,
    stop_worker,
    FOREGROUND_TYPES,
    BACKGROUND_TYPES,
)
from asphalt_turret_engine.config import settings
from asphalt_turret_engine.db import check_db_connection

app = FastAPI(
    title="ASPHALT-TURRET API",
    version="0.1.0",
    description="Backend for ASPHALT-TURRET dashcam management"
)

worker_threads: list[threading.Thread] = []


@app.on_event("startup")
async def startup_event():
    print("Starting ASPHALT-TURRET API...")

    if not check_db_connection():
        raise RuntimeError("Database connection failed during startup.")

    fg = threading.Thread(
        target=worker_loop,
        kwargs={"job_types": FOREGROUND_TYPES, "name": "ForegroundWorker"},
        daemon=True,
        name="ForegroundWorker",
    )
    bg = threading.Thread(
        target=worker_loop,
        kwargs={"job_types": BACKGROUND_TYPES, "name": "BackgroundWorker"},
        daemon=True,
        name="BackgroundWorker",
    )

    fg.start()
    bg.start()
    worker_threads.extend([fg, bg])

    _queue_startup_scan()

    print("ASPHALT-TURRET API started successfully.")


def _queue_startup_scan() -> None:
    try:
        from asphalt_turret_engine.adapters.volumes import list_removable_volumes
        from asphalt_turret_engine.db.session import get_db_context
        from asphalt_turret_engine.db.models.job import Job
        from asphalt_turret_engine.db.enums import JobTypeEnum, JobStateEnum

        volumes = list_removable_volumes()
        thinkware = [v for v in volumes if v.get("is_removable") and _safe_is_thinkware(v["drive_root"])]

        if not thinkware:
            print("Startup scan: no Thinkware SD cards connected.")
            return

        with get_db_context() as session:
            job = Job(
                type     = JobTypeEnum.sd_scan,
                state    = JobStateEnum.queued,
                progress = 0,
                message  = f"Startup scan: {len(thinkware)} card(s) detected",
            )
            session.add(job)
            session.commit()
            print(f"Startup scan: queued job {job.id} for {len(thinkware)} Thinkware card(s).")

    except Exception as e:
        print(f"Startup scan: skipped due to error — {e}")


def _safe_is_thinkware(drive_root: str) -> bool:
    try:
        from asphalt_turret_engine.adapters.sd_scanner import is_thinkware_sd_card
        return is_thinkware_sd_card(drive_root)
    except Exception:
        return False


@app.on_event("shutdown")
async def shutdown():
    from asphalt_turret_engine.db.session import engine
    stop_worker()
    for t in worker_threads:
        t.join(timeout=30)
    print("Worker threads stopped")
    engine.dispose()
    print("Database connections closed")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"name": "ASPHALT-TURRET API", "version": "0.1.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

from asphalt_turret_api.routers import volumes
app.include_router(volumes.router)

from asphalt_turret_api.routers import sd_card
app.include_router(sd_card.router)

from asphalt_turret_api.routers import imports
app.include_router(imports.router)

from asphalt_turret_api.routers import clips
app.include_router(clips.router)

from asphalt_turret_api.routers import sd_files
app.include_router(sd_files.router)

from asphalt_turret_api.routers import settings
app.include_router(settings.router)