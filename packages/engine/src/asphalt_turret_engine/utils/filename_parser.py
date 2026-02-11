from __future__ import annotations
from pathlib import Path
import re
from datetime import datetime

from asphalt_turret_engine.db.enums import CameraEnum, ModeEnum


def parse_camera_from_path(rel_path: str) -> CameraEnum:
    """
    Guess camera from filename or path.
    
    Thinkware format: FRONT_YYYYMMDD_HHMMSS.mp4 or REAR_YYYYMMDD_HHMMSS.mp4
    """
    path_upper = rel_path.upper()
    
    if "FRONT" in path_upper or "_F_" in path_upper:
        return CameraEnum.front
    elif "REAR" in path_upper or "_R_" in path_upper:
        return CameraEnum.rear
    else:
        return CameraEnum.unknown


def parse_mode_from_path(rel_path: str) -> ModeEnum:
    """
    Guess recording mode from directory path.
    
    Thinkware directories: cont_rec/, evt_rec/, parking_rec/, etc.
    """
    path_lower = rel_path.lower()
    
    if "cont_rec" in path_lower:
        return ModeEnum.continuous
    elif "evt_rec" in path_lower:
        return ModeEnum.event
    elif "parking_rec" in path_lower:
        return ModeEnum.parking
    elif "manual_rec" in path_lower:
        return ModeEnum.manual
    elif "sos_rec" in path_lower:
        return ModeEnum.sos
    else:
        return ModeEnum.unknown

def parse_recorded_at_from_filename(filename: str) -> datetime | None:
    """
    Parse recording timestamp from Thinkware filename.
    
    Format: FRONT_20240107_123045.mp4 → 2024-01-07 12:30:45
    """
    # Pattern: FRONT_YYYYMMDD_HHMMSS.mp4
    match = re.search(r'(\d{8})_(\d{6})', filename)
    
    if not match:
        return None
    
    date_str = match.group(1)  # YYYYMMDD
    time_str = match.group(2)  # HHMMSS
    
    try:
        return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
    except ValueError:
        return None