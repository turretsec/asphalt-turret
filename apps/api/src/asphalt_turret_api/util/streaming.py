import re
import mimetypes
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

def _stream_video_file(path: Path, request: Request):
    """
    Shared logic for streaming video files with range support.
    """
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    file_size = path.stat().st_size
    mime, _ = mimetypes.guess_type(path.name)
    content_type = mime or "video/mp4"
    
    range_header = request.headers.get("range") or request.headers.get("Range")
    
    if not range_header:
        # No range - return full file
        return FileResponse(
            path,
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{path.name}"',
            },
        )
    
    # Parse range header
    m = _RANGE_RE.match(range_header.strip())
    if not m:
        raise HTTPException(status_code=416, detail="Invalid Range header")
    
    start_str, end_str = m.groups()
    
    if start_str == "" and end_str == "":
        raise HTTPException(status_code=416, detail="Invalid Range header")
    
    if start_str == "":
        # Suffix range
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