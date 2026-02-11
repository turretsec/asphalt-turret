from tabnanny import check
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
from asphalt_turret_engine.jobs.worker import worker_loop, stop_worker

from asphalt_turret_engine.config import settings
from asphalt_turret_engine.db import check_db_connection

app = FastAPI(
    title="ASPHALT-TURRET API",
    version="0.1.0",
    description="Backend for ASPHALT-TURRET dashcam management"
)

@app.on_event("startup")
async def startup_event():
    print("Starting ASPHALT-TURRET API...")
    global worker_thread

    if not check_db_connection():
        raise RuntimeError("Database connection failed during startup.")
    
    print ("Starting Worker thread...")
    worker_thread = threading.Thread(target=worker_loop, daemon=True, name="JobWorker")
    worker_thread.start()
    
    print("ASPHALT-TURRET API started successfully.")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    from asphalt_turret_engine.db.session import engine

    stop_worker()
    
    if worker_thread:
        worker_thread.join(timeout=30)
    print("Worker thread stopped")
    engine.dispose()
    print("Database connections closed")

# CORS for Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "ASPHALT-TURRET API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}


# Routers
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