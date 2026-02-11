from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from asphalt_turret_engine.db.session import get_db
from asphalt_turret_engine.db.crud import sd_card as sd_card_crud
from asphalt_turret_engine.db.crud import sd_file as sd_file_crud
from asphalt_turret_engine.db.crud import job as job_crud
from asphalt_turret_engine.db.enums import SDFileImportStateEnum

router = APIRouter(prefix="/imports", tags=["imports"])


class ImportRequest(BaseModel):
    """Request to import files from an SD card."""
    volume_uid: str
    file_ids: Optional[list[int]] = None
    limit: Optional[int] = None


class ImportResponse(BaseModel):
    """Response after creating import job."""
    job_id: int
    total_files: int
    message: str

@router.post("/sd-card", response_model=ImportResponse)
def import_sd_card(
    request: ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Create a batch import job for files on an SD card.
    
    If file_ids is provided, imports those specific files.
    Otherwise imports pending files (optionally limited by limit parameter).
    """
    # 1. Find SD card
    card = sd_card_crud.get_by_volume_uid(db, request.volume_uid)
    
    if not card:
        raise HTTPException(
            status_code=404,
            detail=f"SD card with volume_uid '{request.volume_uid}' not found"
        )
    
    # 2. Get files to import
    if request.file_ids:
        # Import specific files by ID
        files_to_import = sd_file_crud.get_by_ids(db, request.file_ids, card.id)
        
        # Validate all files belong to this SD card
        if len(files_to_import) != len(request.file_ids):
            raise HTTPException(
                status_code=400,
                detail="Some file IDs not found or don't belong to this SD card"
            )
    else:
        # Import pending files (old behavior)
        files_to_import = sd_file_crud.list_files(
            db, 
            card.id, 
            import_state=SDFileImportStateEnum.pending
        )

    if request.file_ids:
        files_to_import = sd_file_crud.get_by_ids(db, request.file_ids, card.id)
        
        # Filter out already-imported files
        importable_files = [
            f for f in files_to_import 
            if f.import_state != SDFileImportStateEnum.imported
        ]
        
        if len(importable_files) < len(files_to_import):
            skipped = len(files_to_import) - len(importable_files)
            print(f"Skipped {skipped} already-imported files")

        files_to_import = importable_files
    else:
        # Old behavior - only pending files
        files_to_import = sd_file_crud.list_files(
            db, card.id, import_state=SDFileImportStateEnum.pending
        )
        
        if request.limit is not None:
            files_to_import = files_to_import[:request.limit]
    
    if not files_to_import:
        return ImportResponse(
            job_id=0,
            total_files=0,
            message="No files to import"
        )
    
    # 3. Create batch import job
    file_ids = [f.id for f in files_to_import]
    job = job_crud.create_import_batch_job(
        db,
        sd_card_id=card.id,
        file_ids=file_ids
    )

    db.commit()
    
    return ImportResponse(
        job_id=job.id,
        total_files=len(file_ids),
        message=f"Import job created for {len(file_ids)} files"
    )


@router.get("/jobs/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """
    Get status of an import job.
    
    Returns current progress, state, and message.
    """
    from asphalt_turret_engine.db.models.job import Job
    
    job = db.get(Job, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return {
        "job_id": job.id,
        "type": job.type.value,
        "state": job.state.value,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }

@router.post("/probe-clips")
def probe_imported_clips(
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Create a probe job for clips that haven't been probed yet.
    
    Optionally limit the number of clips to probe (useful for testing).
    """
    from asphalt_turret_engine.db.models.clip import Clip
    from asphalt_turret_engine.db.enums import MetadataStatusEnum
    
    # Find clips that need probing
    stmt = select(Clip).where(
        Clip.metadata_status == MetadataStatusEnum.pending
    )
    
    pending_clips = list(db.execute(stmt).scalars())
    
    if not pending_clips:
        return {
            "job_id": 0,
            "total_clips": 0,
            "message": "No clips need probing"
        }
    
    # Apply limit if specified
    if limit is not None:
        pending_clips = pending_clips[:limit]
    
    # Create batch probe job
    clip_ids = [c.id for c in pending_clips]
    job = job_crud.create_probe_batch_job(db, clip_ids=clip_ids)
    db.commit()
    
    return {
        "job_id": job.id,
        "total_clips": len(clip_ids),
        "message": f"Probe job created for {len(clip_ids)} clips"
    }