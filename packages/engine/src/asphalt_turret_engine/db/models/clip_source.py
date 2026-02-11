from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asphalt_turret_engine.db.base import Base

if TYPE_CHECKING:
    from asphalt_turret_engine.db.models.sd_card import SDCard
    from asphalt_turret_engine.db.models.clip import Clip

class ClipSource(Base):
    __tablename__ = "clip_source"
    __table_args__ = (
        UniqueConstraint("clip_id", name="uq_clip_source_clip_id"),
        UniqueConstraint("sd_card_id", "rel_path", name="uq_clip_source_sd_card_rel_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(
        ForeignKey("clip.id"),
        nullable=False
    )
    sd_card_id: Mapped[int] = mapped_column(
        ForeignKey("sd_card.id"),
        nullable=False
    )
    rel_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    clip: Mapped["Clip"] = relationship(
        back_populates="source"
    )

    sd_card: Mapped["SDCard"] = relationship(
        back_populates="sources"
    )