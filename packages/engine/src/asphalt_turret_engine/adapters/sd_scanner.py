from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator

# Thinkware U3000 specific directories
VIDEO_EXTENSIONS = {".mp4", ".mov"}
RECORDING_DIRS = {
    "cont_rec",              # Continuous recording
    "evt_rec",               # Event recording
    "manual_rec",            # Manual recording
    "parking_rec",           # Parking mode
    "motion_timelapse_rec",  # Motion timelapse
    "sos_rec",               # SOS/emergency
}


@dataclass(frozen=True)
class ScannedFile:
    """A video file discovered on an SD card."""
    rel_path: str
    size_bytes: int
    mtime: datetime  # Timezone-aware UTC


def iter_dashcam_files(drive_root: str | Path) -> Iterator[ScannedFile]:
    """
    Scan a Thinkware dashcam SD card for video files.
    
    Looks in specific recording directories (cont_rec, evt_rec, etc.)
    and yields metadata for each video file found.
    
    Args:
        drive_root: Root directory of the SD card (e.g., "E:\\" on Windows)
        
    Yields:
        ScannedFile objects for each discovered video
        
    Example:
        >>> for file in iter_dashcam_files("E:\\"):
        ...     print(f"{file.rel_path}: {file.size_bytes} bytes")
    """
    root = Path(drive_root)
    
    for dirname in RECORDING_DIRS:
        base = root / dirname
        if not base.exists():
            continue
        
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            
            if path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue
            
            stat = path.stat()
            rel_path = path.relative_to(root).as_posix()
            
            yield ScannedFile(
                rel_path=rel_path,
                size_bytes=int(stat.st_size),
                mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            )


def is_thinkware_sd_card(drive_root: str | Path) -> bool:
    """
    Check if a drive appears to be a Thinkware dashcam SD card.
    
    Args:
        drive_root: Root directory to check
        
    Returns:
        True if this looks like a Thinkware SD card
    """
    root = Path(drive_root)
    
    # Check if at least one recording directory exists
    for dirname in RECORDING_DIRS:
        if (root / dirname).exists():
            return True
    
    return False


def get_recording_stats(drive_root: str | Path) -> dict[str, int]:
    """
    Get statistics about recordings on the SD card.
    
    Args:
        drive_root: Root directory of the SD card
        
    Returns:
        Dict mapping recording type to file count
        
    Example:
        >>> stats = get_recording_stats("E:\\")
        >>> print(stats)
        {'cont_rec': 150, 'evt_rec': 12, 'parking_rec': 45, ...}
    """
    root = Path(drive_root)
    stats = {}
    
    for dirname in RECORDING_DIRS:
        base = root / dirname
        if not base.exists():
            stats[dirname] = 0
            continue
        
        count = sum(
            1 for p in base.rglob("*")
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        )
        stats[dirname] = count
    
    return stats