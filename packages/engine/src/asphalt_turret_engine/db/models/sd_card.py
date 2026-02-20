from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asphalt_turret_engine.db.base import Base

if TYPE_CHECKING:
    from asphalt_turret_engine.db.models.sd_file import SDFile
    from asphalt_turret_engine.db.models.clip_source import ClipSource

class SDCard(Base):
    __tablename__ = "sd_card"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    volume_uid: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    volume_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # UUID written to .at_card_id on the physical card.
    card_identity: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    files: Mapped[list["SDFile"]] = relationship(
        back_populates="sd_card", cascade="all, delete-orphan"
    )
    sources: Mapped[list["ClipSource"]] = relationship(
        back_populates="sd_card", cascade="all, delete-orphan"
    )