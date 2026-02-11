from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from asphalt_turret_engine.db.models.clip import Clip

def get_clip_by_id(session: Session, clip_id: int) -> Clip | None:
    stmt = select(Clip).where(Clip.id == clip_id)
    row = session.execute(stmt).first()
    if row:
        return row[0]
    return None

def get_clips(session: Session) -> list[Clip]:
    stmt = select(Clip)
    rows = session.execute(stmt).scalars().all()
    return list(rows)