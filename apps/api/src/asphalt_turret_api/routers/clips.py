from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from httpx import get
from sqlalchemy.orm import Session
from pathlib import Path

import mimetypes
import re

from asphalt_turret_engine.db.session import get_db
from asphalt_turret_engine.utils.repo_paths import get_absolute_clip_path
from asphalt_turret_api.schemas.clip import ClipResponse
from asphalt_turret_engine.db.crud.clip import get_clips, get_clip_by_id

from asphalt_turret_api.util.streaming import _stream_video_file

router = APIRouter(prefix="/clips", tags=["clips"])

@router.get("", response_model=list[ClipResponse])
def list_clips(db: Session = Depends(get_db)):
    """
    Get a list of all clips in the database.
    """
    clips = get_clips(db)

    if not clips:
        raise HTTPException(
            status_code=404,
            detail="No clips found in the database."
        )
    return clips

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")

@router.get("/{clip_id}/stream")
def stream_clip(clip_id: int, request: Request, db: Session = Depends(get_db)):
    """Stream a clip from repository."""
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    path = get_absolute_clip_path(clip)
    
    # Use shared streaming logic
    return _stream_video_file(path, request)



@router.get("/{clip_id}/stream-old")
def stream_clip_old(clip_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Stream a specific clip by its ID.
    """
    selected_clip = get_clip_by_id(db, clip_id)
    if not selected_clip:
        raise HTTPException(
            status_code=404,
            detail=f"Clip with ID {clip_id} not found."
        )
    
    path = get_absolute_clip_path(selected_clip)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Clip file not found at expected path: {path}"
        )
    
    file_size = path.stat().st_size

    # Guess mime type based on file extension
    mime, _ = mimetypes.guess_type(path.name)
    content_type = mime or "video/mp4"

    range_header = request.headers.get("range") or request.headers.get("Range")
    if not range_header:
        return FileResponse(
            path,
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{path.name}"',
            },
        )
    
    m = _RANGE_RE.match(range_header.strip())
    if not m:
        raise HTTPException(
            status_code=416,
            detail="Invalid Range header"
        )
    
    start_str, end_str = m.groups()

    if start_str == "" and end_str == "":
        raise HTTPException(status_code=416, detail="Invalid Range header")

    if start_str == "":
        # Suffix range: last N bytes
        suffix_len = int(end_str)
        if suffix_len <= 0:
            raise HTTPException(status_code=416, detail="Invalid Range header")
        start = max(file_size - suffix_len, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

    if start >= file_size:
        raise HTTPException(status_code=416, detail="Range start out of bounds")
    if end >= file_size:
        end = file_size - 1
    if end < start:
        raise HTTPException(status_code=416, detail="Invalid Range header")

    length = end - start + 1

    def file_iter(p: Path, offset: int, count: int, chunk_size: int = 1024 * 1024):
        with p.open("rb") as f:
            f.seek(offset)
            remaining = count
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": content_type,
        "Content-Disposition": f'inline; filename="{path.name}"',
    }

    return StreamingResponse(
        file_iter(path, start, length),
        status_code=206,
        headers=headers,
        media_type=content_type,
    )