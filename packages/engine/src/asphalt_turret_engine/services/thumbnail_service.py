from __future__ import annotations
import logging
import hashlib
import subprocess
import threading
from pathlib import Path

from asphalt_turret_engine.config import settings

logger = logging.getLogger(__name__)

# ─── Generation semaphore ─────────────────────────────────────────────────────
#
# Caps how many ffmpeg processes run simultaneously. Without this, 15 thumbnail
# requests arriving at once spawn 15 ffmpeg processes, each consuming a full
# CPU core and ~150MB RAM — they all thrash each other and finish slower than
# if they'd queued.
#
# 4 concurrent processes saturates a typical 4-8 core machine nicely.
# Increase if you have more cores and fast storage.

_GENERATION_SEMAPHORE = threading.Semaphore(4)

# ─── In-progress deduplication ───────────────────────────────────────────────
#
# Prevents two requests for the same thumbnail from spawning two ffmpeg
# processes that race to write the same output file.
#
# Pattern: check set → if not in set, add to set → generate → remove from set
# Protected by a lock so the check-and-add is atomic.

_IN_PROGRESS: set[Path] = set()
_IN_PROGRESS_LOCK = threading.Lock()


def get_thumbnail_path(
    file_path: Path,
    width: int | None = None,
    height: int | None = None,
) -> Path:
    """
    Generate consistent thumbnail path for a source file.
    Uses a hash of (absolute path + dimensions) to avoid filename conflicts.
    """
    width  = width  or settings.thumbnail_width
    height = height or settings.thumbnail_height

    path_hash = hashlib.md5(
        f"{file_path.absolute()}_{width}x{height}".encode()
    ).hexdigest()[:16]

    return settings.thumbnails_dir / f"{path_hash}.jpg"


def generate_thumbnail(
    video_path: Path,
    output_path: Path | None = None,
    timestamp: float = 1.0,
    width: int | None = None,
    height: int | None = None,
) -> Path:
    """
    Generate a thumbnail from a video file using bundled FFmpeg.

    Thread-safe: protected by a semaphore (max 4 concurrent) and a
    deduplication set (only one ffmpeg per unique output path at a time).

    Args:
        video_path:  Path to source video
        output_path: Where to save thumbnail (auto-generated if None)
        timestamp:   Which second to extract a frame from
        width:       Thumbnail width (default: settings.thumbnail_width)
        height:      Thumbnail height (default: settings.thumbnail_height)

    Returns:
        Path to generated (or already-cached) thumbnail

    Raises:
        FileNotFoundError: If video doesn't exist
        RuntimeError:      If FFmpeg fails or times out
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    width  = width  or settings.thumbnail_width
    height = height or settings.thumbnail_height

    if output_path is None:
        output_path = get_thumbnail_path(video_path, width, height)

    # Fast path: thumbnail already on disk
    if output_path.exists():
        logger.debug(f"Thumbnail cache hit: {output_path.name}")
        return output_path

    # Deduplication: only one thread generates a given output path at a time.
    # Other threads that arrive while generation is running just bail —
    # they'll find the file on disk when they retry.
    with _IN_PROGRESS_LOCK:
        if output_path in _IN_PROGRESS:
            logger.debug(f"Thumbnail already generating: {output_path.name}")
            return output_path  # caller will retry; file will be ready soon
        _IN_PROGRESS.add(output_path)

    try:
        # Semaphore: cap concurrent ffmpeg processes
        with _GENERATION_SEMAPHORE:
            # Re-check after acquiring semaphore — another thread may have
            # finished while we waited
            if output_path.exists():
                return output_path

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert quality setting (0-100) to ffmpeg's -q:v scale (1-31).
            # ffmpeg JPEG quality: 1 = best, 31 = worst (inverse of percentage).
            # quality=85 → q_v = max(1, int(31 * (1 - 0.85))) = max(1, 4) = 4
            q = settings.thumbnail_quality  # 10-100
            q_v = max(1, int(31 * (1.0 - q / 100.0)))

            cmd = [
                settings.ffmpeg_path,
                "-ss", str(timestamp),            # seek BEFORE -i (fast keyframe seek)
                "-i", str(video_path),
                "-frames:v", "1",                 # extract exactly 1 frame
                "-an",                            # skip audio processing entirely
                "-vf", f"scale={width}:{height}", # resize
                "-pix_fmt", "yuvj420p",           # convert limited→full range YUV for MJPEG
                "-q:v", str(q_v),                 # quality from settings
                "-y",                             # overwrite if somehow exists
                str(output_path),
            ]

            logger.info(f"Generating thumbnail for {video_path.name} ({width}x{height}, q={q_v})")

            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    check=True,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                logger.info(f"Thumbnail generated: {output_path.name}")
                return output_path

            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg error for {video_path.name}: {e.stderr.decode()}")
                raise RuntimeError(f"Failed to generate thumbnail: {e.stderr.decode()}")
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg timeout for {video_path.name}")
                raise RuntimeError("Thumbnail generation timed out")

    finally:
        with _IN_PROGRESS_LOCK:
            _IN_PROGRESS.discard(output_path)


def get_or_generate_thumbnail(
    video_path: Path,
    timestamp: float = 1.0,
    width: int | None = None,
    height: int | None = None,
) -> Path:
    """Convenience wrapper — get cached thumbnail or generate it."""
    thumbnail_path = get_thumbnail_path(video_path, width, height)
    if thumbnail_path.exists():
        return thumbnail_path
    return generate_thumbnail(video_path, thumbnail_path, timestamp, width, height)


def delete_thumbnail(video_path: Path) -> bool:
    """Delete thumbnail for a video file. Returns True if deleted."""
    thumbnail_path = get_thumbnail_path(video_path)
    if thumbnail_path.exists():
        thumbnail_path.unlink()
        logger.info(f"Deleted thumbnail: {thumbnail_path}")
        return True
    return False