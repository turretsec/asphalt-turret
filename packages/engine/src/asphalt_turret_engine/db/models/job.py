from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asphalt_turret_engine.db.base import Base
from asphalt_turret_engine.db.enums import JobStateEnum, JobTypeEnum

if TYPE_CHECKING:
    from asphalt_turret_engine.db.models.sd_file import SDFile
    from asphalt_turret_engine.db.models.clip import Clip

class Job(Base):
    __tablename__ = "job"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[JobTypeEnum] = mapped_column(
        Enum(JobTypeEnum, native_enum=False),
        nullable=False
    )
    state: Mapped[JobStateEnum] = mapped_column(
        Enum(JobStateEnum, native_enum=False),
        nullable=False
    )

    sd_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sd_file.id", ondelete="SET NULL"),
        nullable=True
    )

    sd_file: Mapped[Optional["SDFile"]] = relationship("SDFile", back_populates="jobs")

    clip_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clip.id", ondelete="SET NULL"),
        nullable=True
    )

    clip: Mapped[Optional["Clip"]] = relationship("Clip", back_populates="jobs")

    metadata_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    progress: Mapped[int] = mapped_column(
        nullable=False, 
        server_default=text("0")
    )
    message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )