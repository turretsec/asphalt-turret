import shutil
from fastapi import APIRouter, Depends, HTTPException, Request, logger, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse, Response

from httpx import get
from sqlalchemy.orm import Session
from pathlib import Path

import mimetypes
import re

from asphalt_turret_engine.db.session import get_db
from asphalt_turret_engine.utils.repo_paths import get_absolute_clip_path
from asphalt_turret_api.schemas.clip import ClipResponse, DeleteClipsResponse, DeleteClipsRequest, ExportClipsRequest, ExportClipsResponse
from asphalt_turret_engine.db.models import Clip
from asphalt_turret_engine.db.crud.clip import get_clips, get_clip_by_id
from asphalt_turret_engine.config import settings
from asphalt_turret_engine.services.thumbnail_service import get_or_generate_thumbnail
from asphalt_turret_engine.services.thumbnail_service import get_thumbnail_path, generate_thumbnail

from asphalt_turret_api.util.streaming import _stream_video_file

router = APIRouter(prefix="/clips", tags=["clips"])

@router.get("", response_model=list[ClipResponse])
def list_clips(db: Session = Depends(get_db)):
    """Get all clips in the repository. Returns an empty list if none exist."""
    return get_clips(db)

@router.get("/{clip_id}/stream")
def stream_clip(clip_id: int, request: Request, db: Session = Depends(get_db)):
    """Stream a clip from the repository."""
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    path = get_absolute_clip_path(clip)
    return _stream_video_file(path, request)

@router.delete("", response_model=DeleteClipsResponse)
def delete_clips(
    request: DeleteClipsRequest,
    db: Session = Depends(get_db)
):
    """
    Delete multiple clips by ID.
    
    - Removes database records
    - Deletes physical files from repository
    - Returns count of successful/failed deletions
    """
    if not request.clip_ids:
        raise HTTPException(status_code=400, detail="No clip IDs provided")
    
    deleted = 0
    failed = 0
    
    for clip_id in request.clip_ids:
        try:
            # Get clip from database
            clip = db.get(Clip, clip_id)
            
            if not clip:
                failed += 1
                continue
            
            # Delete physical file
            file_path = settings.repository_dir / clip.repo_path
            if file_path.exists():
                file_path.unlink()
            
            # Delete database record
            db.delete(clip)
            deleted += 1
            
        except Exception as e:
            print(f"Failed to delete clip {clip_id}: {e}")
            failed += 1
    
    # Commit all deletions
    db.commit()
    
    return DeleteClipsResponse(
        deleted_count=deleted,
        failed_count=failed,
        message=f"Deleted {deleted} clips" + (f", {failed} failed" if failed > 0 else "")
    )

@router.post("/export", response_model=ExportClipsResponse)
def export_clips(
    request: ExportClipsRequest,
    db: Session = Depends(get_db)
):
    """
    Export clips by copying them to a destination directory.
    
    - Copies physical files to the specified directory
    - Uses original filenames
    - Handles filename conflicts by appending numbers
    - Returns count of successful/failed exports
    """
    if not request.clip_ids:
        raise HTTPException(status_code=400, detail="No clip IDs provided")
    
    dest_path = Path(request.destination_dir)
    
    # Validate destination exists and is writable
    if not dest_path.exists():
        raise HTTPException(status_code=400, detail="Destination directory does not exist")
    
    if not dest_path.is_dir():
        raise HTTPException(status_code=400, detail="Destination must be a directory")
    
    exported = 0
    failed = 0
    
    for clip_id in request.clip_ids:
        try:
            # Get clip from database
            clip = db.get(Clip, clip_id)
            
            if not clip:
                failed += 1
                continue
            
            # Source file
            source_path = settings.repository_dir / clip.repo_path
            if not source_path.exists():
                print(f"Source file not found: {source_path}")
                failed += 1
                continue
            
            # Destination file - use original filename
            dest_file = dest_path / (clip.original_filename or source_path.name)
            
            # Handle filename conflicts by appending a number
            counter = 1
            while dest_file.exists():
                stem = dest_file.stem
                suffix = dest_file.suffix
                dest_file = dest_path / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Copy file
            shutil.copy2(source_path, dest_file)
            exported += 1
            
        except Exception as e:
            print(f"Failed to export clip {clip_id}: {e}")
            failed += 1
    
    return ExportClipsResponse(
        exported_count=exported,
        failed_count=failed,
        message=f"Exported {exported} clips" + (f", {failed} failed" if failed > 0 else ""),
        destination=str(dest_path)
    )

@router.get("/{clip_id}/thumbnail")
def get_clip_thumbnail(
    clip_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Return cached thumbnail for a clip, generating it in the background if missing.

    First call: thumbnail missing → queue background generation → 202 Accepted
    Client retries after ~1.5s: thumbnail ready → 200 with image

    generate_thumbnail is idempotent, so multiple concurrent retries for the
    same clip are safe — only one ffmpeg process will actually run.
    """
    clip = db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")

    video_path = settings.repository_dir / clip.repo_path
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {clip.repo_path}")

    thumbnail_path = get_thumbnail_path(video_path)

    if thumbnail_path.exists():
        return FileResponse(
            thumbnail_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Not cached yet — generate in background and tell client to retry.
    # BackgroundTasks runs after the response is sent, in a thread pool thread,
    # so this never blocks the API.
    background_tasks.add_task(generate_thumbnail, video_path)

    return Response(
        status_code=202,
        headers={"Retry-After": "2"},
    )