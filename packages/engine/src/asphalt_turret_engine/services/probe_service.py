from __future__ import annotations
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.clip import Clip
from asphalt_turret_engine.db.enums import MetadataStatusEnum
from asphalt_turret_engine.adapters.ffprobe import run_ffprobe_json, extract_basic_metadata
from asphalt_turret_engine.config import settings
from asphalt_turret_engine.utils.repo_paths import get_absolute_clip_path

logger = logging.getLogger(__name__)


def probe_clip(session: Session, clip: Clip) -> None:
    """
    Extract metadata from a clip using ffprobe.
    
    Updates the clip record with:
    - duration_s, width, height, codec, fps
    - metadata_json (raw ffprobe output)
    - probe_version, probed_at
    - metadata_status
    
    Args:
        session: Database session
        clip: Clip to probe
        
    Raises:
        FileNotFoundError: If clip file doesn't exist
        RuntimeError: If ffprobe fails
        
    Note: Caller must commit the session.
    """
    # Check if already probed with current version
    if (clip.metadata_status == MetadataStatusEnum.extracted and 
        clip.probe_version == settings.probe_version):
        logger.info(f"Clip {clip.id} already probed with current version, skipping")
        return
    
    # Get absolute path to clip file
    clip_path = get_absolute_clip_path(clip)
    
    if not clip_path.exists():
        raise FileNotFoundError(f"Clip file not found: {clip_path}")
    
    logger.info(f"Probing clip {clip.id}: {clip_path.name}")
    
    try:
        # Run ffprobe
        probe_data = run_ffprobe_json(
            ffprobe_path=settings.ffprobe_path,
            media_path=clip_path,
            timeout_s=settings.ffprobe_timeout_s
        )
        
        # Extract basic metadata
        metadata = extract_basic_metadata(probe_data)
        
        # Update clip fields
        clip.duration_s = metadata.get("duration_s")
        clip.codec = metadata.get("codec")
        clip.width = metadata.get("width")
        clip.height = metadata.get("height")
        clip.fps = metadata.get("fps")
        
        # Store raw ffprobe output (for future use)
        clip.metadata_json = json.dumps(probe_data, ensure_ascii=False)
        
        # Mark as successful
        clip.metadata_status = MetadataStatusEnum.extracted
        clip.metadata_error = None
        clip.probe_version = settings.probe_version
        clip.probed_at = datetime.now(timezone.utc)
        
        logger.info(f"Successfully probed clip {clip.id}: {metadata.get('codec')} "
                   f"{metadata.get('width')}x{metadata.get('height')} @ {metadata.get('fps')}fps")
        
    except Exception as e:
        # Probe failed - store error
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Failed to probe clip {clip.id}: {error_msg}")
        
        clip.metadata_status = MetadataStatusEnum.failed
        clip.metadata_error = error_msg[:1000]  # Limit error message length
        clip.probe_version = settings.probe_version
        clip.probed_at = datetime.now(timezone.utc)
        
        raise