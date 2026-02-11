from __future__ import annotations
import logging
import hashlib
import subprocess
from pathlib import Path

from asphalt_turret_engine.config import settings

logger = logging.getLogger(__name__)


def get_thumbnail_path(file_path: Path, width: int | None = None, height: int | None = None) -> Path:
    """
    Generate consistent thumbnail path based on source file.
    
    Uses hash of file path to avoid filename conflicts.
    """
    width = width or settings.thumbnail_width
    height = height or settings.thumbnail_height
    
    # Create hash of source file path + dimensions
    path_hash = hashlib.md5(
        f"{file_path.absolute()}_{width}x{height}".encode()
    ).hexdigest()[:16]
    
    return settings.thumbnails_dir / f"{path_hash}.jpg"


def generate_thumbnail(
    video_path: Path,
    output_path: Path | None = None,
    timestamp: float = 1.0,
    width: int | None = None,
    height: int | None = None
) -> Path:
    """
    Generate thumbnail from video file using bundled FFmpeg.
    
    Args:
        video_path: Path to source video
        output_path: Where to save thumbnail (auto-generated if None)
        timestamp: Which second to extract frame from
        width: Thumbnail width
        height: Thumbnail height
        
    Returns:
        Path to generated thumbnail
        
    Raises:
        FileNotFoundError: If video doesn't exist
        RuntimeError: If FFmpeg fails
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    width = width or settings.thumbnail_width
    height = height or settings.thumbnail_height
    
    # Auto-generate output path if not provided
    if output_path is None:
        output_path = get_thumbnail_path(video_path, width, height)
    
    # Skip if thumbnail already exists
    if output_path.exists():
        logger.debug(f"Thumbnail already exists: {output_path}")
        return output_path
    
    logger.info(f"Generating thumbnail for {video_path.name}")
    
    # Ensure thumbnails directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build ffmpeg command
    cmd = [
        settings.ffmpeg_path,
        "-ss", str(timestamp),           # Seek to timestamp
        "-i", str(video_path),            # Input file
        "-vframes", "1",                  # Extract 1 frame
        "-vf", f"scale={width}:{height}", # Resize
        "-q:v", "2",                      # High quality JPEG
        "-y",                             # Overwrite output
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        logger.info(f"Thumbnail generated: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        raise RuntimeError(f"Failed to generate thumbnail: {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout generating thumbnail for {video_path}")
        raise RuntimeError("Thumbnail generation timed out")


def get_or_generate_thumbnail(
    video_path: Path,
    timestamp: float = 1.0,
    width: int | None = None,
    height: int | None = None
) -> Path:
    """
    Get existing thumbnail or generate new one.
    
    This is the main entry point for thumbnail generation.
    """
    thumbnail_path = get_thumbnail_path(video_path, width, height)
    
    if thumbnail_path.exists():
        return thumbnail_path
    
    return generate_thumbnail(
        video_path,
        thumbnail_path,
        timestamp=timestamp,
        width=width,
        height=height
    )


def delete_thumbnail(video_path: Path) -> bool:
    """
    Delete thumbnail for a video file.
    
    Returns True if deleted, False if didn't exist.
    """
    thumbnail_path = get_thumbnail_path(video_path)
    
    if thumbnail_path.exists():
        thumbnail_path.unlink()
        logger.info(f"Deleted thumbnail: {thumbnail_path}")
        return True
    
    return False