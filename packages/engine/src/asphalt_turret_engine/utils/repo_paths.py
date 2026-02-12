from __future__ import annotations
from pathlib import Path
from datetime import datetime

from asphalt_turret_engine.config import settings


def get_clip_repository_path(
    file_hash: str,
    recorded_at: datetime | None,
    original_filename: str | None = None
) -> Path:
    """
    Generate organized path for a clip in the repository.
    
    Structure: repository/YYYY/MM/DD/hash_originalname.ext
    
    Args:
        file_hash: SHA256 hash of the file
        recorded_at: When video was recorded (for organization)
        original_filename: Original filename (optional, for human readability)
        
    Returns:
        Relative path within repository
        
    Example:
        recorded_at = 2024-01-07 12:30:45
        file_hash = "abc123...def"
        original_filename = "FRONT_20240107_123045.mp4"
        
        Returns: Path("2024/01/07/abc123def_FRONT_20240107_123045.mp4")
    """
    # Use recorded date for organization, or today if unknown
    date = recorded_at or datetime.now()
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")
    
    # Filename: hash (first 16 chars) + original name
    if original_filename:
        # Keep extension from original
        filename = f"{file_hash[:16]}_{original_filename}"
    else:
        # Just hash with .mp4 extension
        filename = f"{file_hash[:16]}.mp4"
    
    return Path(year) / month / day / filename


def get_absolute_clip_path(clip) -> Path:
    """
    Get absolute filesystem path for a clip.
    
    Args:
        clip: Clip model instance with repo_path
        
    Returns:
        Absolute path to clip file
    """

    return settings.repository_dir / clip.repo_path
