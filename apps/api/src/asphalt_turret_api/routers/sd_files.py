from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pathlib import Path
from asphalt_turret_api.util.streaming import _stream_video_file
from asphalt_turret_engine.db.session import get_db
from asphalt_turret_engine.db.models.sd_file import SDFile
import asphalt_turret_engine.db.crud.sd_card as sd_card_crud
from asphalt_turret_engine.adapters.volumes import list_removable_volumes

router = APIRouter(prefix="/sd-files", tags=["sd-files"])


@router.get("/{file_id}/stream")
def stream_sd_file(
    file_id: int,
    volume_uid: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stream a file directly from SD card.
    """
    from asphalt_turret_engine.db.models.sd_file import SDFile
    
    # Get SD file record
    sd_file = db.get(SDFile, file_id)
    if not sd_file:
        raise HTTPException(status_code=404, detail="File not found in database")
    
    # Get SD card
    card = sd_card_crud.get_by_volume_uid(db, volume_uid)
    if not card:
        raise HTTPException(status_code=404, detail="SD card not found")
    
    # Find connected volume
    connected_volumes = list_removable_volumes()
    drive_root = None
    
    for v in connected_volumes:
        if v["volume_uid"] == volume_uid:
            drive_root = Path(v["drive_root"])
            break
    
    if not drive_root:
        raise HTTPException(
            status_code=404,
            detail="SD card not currently connected. Please insert the SD card."
        )
    
    # Build full path to file
    file_path = drive_root / sd_file.rel_path
    print(file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found on SD card at: {sd_file.rel_path}"
        )
    
    # Use shared streaming logic from clips
    from asphalt_turret_api.util.streaming import _stream_video_file
    return _stream_video_file(file_path, request)