from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Any, Optional


def run_ffprobe_json(
    *,
    ffprobe_path: str,
    media_path: Path,
    timeout_s: int = 15
) -> dict[str, Any]:
    """
    Run ffprobe and return parsed JSON.
    
    Args:
        ffprobe_path: Path to ffprobe executable
        media_path: Path to media file to probe
        timeout_s: Timeout in seconds
        
    Returns:
        Parsed JSON output from ffprobe
        
    Raises:
        FileNotFoundError: If media file doesn't exist
        RuntimeError: If ffprobe fails or times out
    """
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")
    
    args = [
        ffprobe_path,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    ]
    
    # Prevent console window popups on Windows
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"ffprobe timed out after {timeout_s}s") from e
    
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"ffprobe failed (code={result.returncode}): {stderr[:500]}")
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ffprobe returned invalid JSON: {e}") from e


def _parse_rational(value: str) -> Optional[float]:
    """
    Parse fractional values like "30000/1001" to float.
    
    Args:
        value: String like "30000/1001" or "30.0"
        
    Returns:
        Parsed float, or None if invalid
    """
    try:
        if "/" in value:
            num_str, den_str = value.split("/", 1)
            num = float(num_str)
            den = float(den_str)
            if den == 0:
                return None
            return num / den
        return float(value)
    except Exception:
        return None


def extract_basic_metadata(probe: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten ffprobe output into consistent structure.
    
    Args:
        probe: Raw ffprobe JSON output
        
    Returns:
        Dict with keys: duration_s, width, height, codec, fps, rotation, audio_codec
    """
    fmt = probe.get("format") or {}
    streams = probe.get("streams") or []
    
    # Find video and audio streams
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    # Parse duration
    duration_s = None
    if "duration" in fmt:
        try:
            duration_s = float(fmt["duration"])
        except Exception:
            pass
    
    # Parse video properties
    width = video.get("width") if video else None
    height = video.get("height") if video else None
    codec = video.get("codec_name") if video else None
    
    # Parse FPS
    fps = None
    if video:
        avg_frame_rate = video.get("avg_frame_rate")
        if isinstance(avg_frame_rate, str):
            fps = _parse_rational(avg_frame_rate)
    
    # Parse rotation (for vertical videos)
    rotation = None
    if video:
        tags = video.get("tags") or {}
        rot = tags.get("rotate")
        if rot is not None:
            try:
                rotation = int(rot)
            except Exception:
                pass
    
    # Audio codec
    audio_codec = audio.get("codec_name") if audio else None
    
    return {
        "duration_s": duration_s,
        "width": int(width) if isinstance(width, int) else None,
        "height": int(height) if isinstance(height, int) else None,
        "codec": codec if isinstance(codec, str) else None,
        "fps": float(fps) if isinstance(fps, (int, float)) else None,
        "rotation": rotation,
        "audio_codec": audio_codec,
    }