from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.enums import SDFileImportStateEnum
from asphalt_turret_engine.db.models.sd_card import SDCard
from asphalt_turret_engine.db.models.sd_file import SDFile


from asphalt_turret_engine.utils.fingerprint import meta_fingerprint

def get_by_sd_and_path(
    session: Session,
    *,
    sd_card_id: int,
    rel_path: str
) -> SDFile | None:
    """
    Get SDFile by SD card ID and relative path.
    """
    stmt = select(SDFile).where(
        SDFile.sd_card_id == sd_card_id,
        SDFile.rel_path == rel_path,
    )
    return session.execute(stmt).scalar_one_or_none()

def upsert_from_scan(
    session: Session,
    *,
    sd_card_id: int,
    rel_path: str,
    size_bytes: int,
    mtime: datetime,
) -> tuple[SDFile, str]:
    """
    Insert or update an SD file from scan.
    
    Note: Caller must commit the session.
    
    Returns:
        Tuple of (SDFile, status) where status is "new", "updated", or "unchanged"
    """
    now = datetime.now(timezone.utc)



    existing = get_by_sd_and_path(session, sd_card_id=sd_card_id, rel_path=rel_path)
    
    if existing:
        # Check if anything changed

        def _mtime_epoch_seconds(dt: datetime) -> int:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        
        existing_mtime_s = _mtime_epoch_seconds(existing.mtime)
        incoming_mtime_s = _mtime_epoch_seconds(mtime)

        changed = (existing.size_bytes != size_bytes) or (existing_mtime_s != incoming_mtime_s)
        
        if changed:
            existing.size_bytes = size_bytes
            existing.mtime = mtime
            existing.last_seen_at = now
            existing.fingerprint = meta_fingerprint(rel_path, size_bytes, mtime)
            return existing, "updated"
        else:
            existing.last_seen_at = now
            return existing, "unchanged"
    
    # Create new file record
    sd_file = SDFile(
        sd_card_id=sd_card_id,
        rel_path=rel_path,
        size_bytes=size_bytes,
        mtime=mtime,
        fingerprint=meta_fingerprint(rel_path, size_bytes, mtime),
        import_state=SDFileImportStateEnum.new,
        last_seen_at=now,
    )
    session.add(sd_file)
    return sd_file, "new"

def get_pending_files(db: Session, sd_card_id: int) -> list[SDFile]:
    """
    Get all files on an SD card that haven't been imported yet.
    
    Args:
        db: Database session
        sd_card_id: ID of the SD card
        
    Returns:
        List of SDFile records with import_state = pending
    """
    stmt = select(SDFile).where(
        SDFile.sd_card_id == sd_card_id,
        SDFile.import_state == SDFileImportStateEnum.pending
    )
    
    return list(db.execute(stmt).scalars())

def list_files(
    db: Session,
    sd_card_id: int,
    *,
    import_state: Optional[SDFileImportStateEnum] = None,
    limit: Optional[int] = None,
    offset: int = 0
) -> list[SDFile]:
    """
    List files on an SD card with optional filters.
    
    Args:
        db: Database session
        sd_card_id: ID of the SD card
        import_state: Filter by import state (optional - if None, returns all)
        limit: Max results to return
        offset: Pagination offset
        
    Returns:
        List of SDFile records
    """
    stmt = select(SDFile).where(SDFile.sd_card_id == sd_card_id)
    
    # Optional filter by import state
    if import_state is not None:
        stmt = stmt.where(SDFile.import_state == import_state)
    
    # Order by path for consistent results
    stmt = stmt.order_by(SDFile.rel_path)
    
    # Pagination
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)
    
    return list(db.execute(stmt).scalars())

def count_files(
    db: Session,
    sd_card_id: int,
    *,
    import_state: Optional[SDFileImportStateEnum] = None
) -> int:
    """
    Count files on an SD card with optional filter.
    
    Args:
        db: Database session
        sd_card_id: ID of the SD card
        import_state: Filter by import state (optional)
        
    Returns:
        Count of matching files
    """
    from sqlalchemy import func as sql_func
    
    stmt = select(sql_func.count()).select_from(SDFile).where(
        SDFile.sd_card_id == sd_card_id
    )
    
    if import_state is not None:
        stmt = stmt.where(SDFile.import_state == import_state)
    
    return db.execute(stmt).scalar_one()


def delete_stale_files(
    db: Session,
    sd_card_id: int,
    seen_file_ids: set[int]
) -> int:
    """
    Delete files that are no longer on the SD card and were never imported.
    """
    stmt = delete(SDFile).where(
        SDFile.sd_card_id == sd_card_id,
        SDFile.import_state != SDFileImportStateEnum.imported
    )
    
    if seen_file_ids:
        stmt = stmt.where(SDFile.id.notin_(seen_file_ids))
    
    result = db.execute(stmt)
    
    return getattr(result, "rowcount", 0) or 0

def get_by_ids(
    db: Session,
    file_ids: list[int],
    sd_card_id: int
) -> list[SDFile]:
    """
    Get multiple SD files by their IDs, ensuring they belong to the specified SD card.
    
    Args:
        db: Database session
        file_ids: List of file IDs to retrieve
        sd_card_id: ID of the SD card (for validation)
        
    Returns:
        List of SDFile records
    """
    stmt = select(SDFile).where(
        SDFile.id.in_(file_ids),
        SDFile.sd_card_id == sd_card_id
    )
    
    return list(db.execute(stmt).scalars())