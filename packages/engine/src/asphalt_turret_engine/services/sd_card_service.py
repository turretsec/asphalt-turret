from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from asphalt_turret_engine.adapters.volumes import list_removable_volumes
from asphalt_turret_engine.adapters.sd_scanner import iter_dashcam_files, is_thinkware_sd_card
from asphalt_turret_engine.db.crud import sd_card as sd_card_crud
from asphalt_turret_engine.db.crud import sd_file as sd_file_crud

@dataclass
class ScanResult:
    """Result of scanning an SD card."""
    sd_card_id: int
    drive_root: str
    found: int
    new: int
    updated: int
    unchanged: int
    skipped: int
    deleted: int


def scan_sd_card(db: Session, *, volume_uid: str) -> ScanResult:
    """
    Scan an SD card and register discovered files.
    
    Args:
        db: Database session
        volume_uid: Volume UID to scan
        
    Returns:
        Statistics about the scan
        
    Raises:
        ValueError: If volume not found
        
    Note: Caller must commit the session.
    """
    volumes = list_removable_volumes()
    volume = next((v for v in volumes if v["volume_uid"] == volume_uid), None)
    
    if not volume:
        raise ValueError(f"SD card volume '{volume_uid}' not found")
    
    drive_root = volume["drive_root"]
    
    if not is_thinkware_sd_card(drive_root):
        raise ValueError(f"Drive {drive_root} does not appear to be a Thinkware SD card")
    
    sd_card = sd_card_crud.register_or_touch(
        db,
        volume_uid=volume_uid,
        volume_label=volume.get("volume_label")
    )
    db.flush()
    
    stats = {"found": 0, "new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    seen_file_ids = set()
    
    for scanned_file in iter_dashcam_files(drive_root):
        stats["found"] += 1
        
        try:
            sd_file, status = sd_file_crud.upsert_from_scan(
                db,
                sd_card_id=sd_card.id,
                rel_path=scanned_file.rel_path,
                size_bytes=scanned_file.size_bytes,
                mtime=scanned_file.mtime,
            )
            
            seen_file_ids.add(sd_file.id)
            stats[status] += 1
            
        except Exception as e:
            stats["skipped"] += 1
            print(f"Error processing {scanned_file.rel_path}: {e}")
    
    deleted_count = sd_file_crud.delete_stale_files(
        db,
        sd_card_id=sd_card.id,
        seen_file_ids=seen_file_ids
    )
    
    return ScanResult(
        sd_card_id=sd_card.id,
        drive_root=drive_root,
        deleted=deleted_count,
        **stats
    )