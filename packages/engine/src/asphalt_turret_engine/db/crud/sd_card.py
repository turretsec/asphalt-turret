from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.sd_card import SDCard

def list_all(session: Session) -> list[SDCard]:
    """
    List all known SD cards.
    
    Returns:
        List of all SDCard records ordered by last_seen_at (most recent first)
    """
    stmt = select(SDCard).order_by(SDCard.last_seen_at.desc())
    return list(session.execute(stmt).scalars())

def get_by_volume_uid(session: Session, volume_uid: str) -> SDCard | None:
    """
        Get SDCard by volume UID.
        
        :param session: Database session
        :type session: Session
        :param volume_uid: Volume UID of the SD card
        :type volume_uid: str
        :return: SDCard instance or None if not found
        :rtype: SDCard | None
    """
    stmt = select(SDCard).where(SDCard.volume_uid == volume_uid)
    result = session.execute(stmt).scalar_one_or_none()
    return result

def register_or_touch(
    session: Session,
    *,
    volume_uid: str,
    volume_label: str | None = None,
) -> SDCard:
    """
    Register a new SD card or update last_seen_at if it already exists.
    
    Note: Caller must commit the session.
    
    Args:
        session: Database session
        volume_uid: Unique volume identifier
        volume_label: Optional volume label
        
    Returns:
        The SD card (either existing or newly created)
    """
    now = datetime.now(timezone.utc)
    
    sd_card = get_by_volume_uid(session, volume_uid)
    
    if sd_card:
        # Update existing card
        sd_card.last_seen_at = now
        if volume_label is not None:
            sd_card.volume_label = volume_label
        return sd_card
    
    # Create new card
    sd_card = SDCard(
        volume_uid=volume_uid,
        volume_label=volume_label,
        first_seen_at=now,
        last_seen_at=now,
    )
    session.add(sd_card)
    return sd_card