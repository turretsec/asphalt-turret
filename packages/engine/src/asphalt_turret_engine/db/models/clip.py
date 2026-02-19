from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Enum, Float, Integer, String, DateTime, Text, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asphalt_turret_engine.db.base import Base
from asphalt_turret_engine.db.enums import CameraEnum, ModeEnum, MetadataStatusEnum

if TYPE_CHECKING:
    from asphalt_turret_engine.db.models.clip_source import ClipSource
    from asphalt_turret_engine.db.models.artifact import Artifact
    from asphalt_turret_engine.db.models.job import Job

class Clip(Base):
    __tablename__ = "clip"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    repo_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    camera: Mapped[CameraEnum] = mapped_column(
        Enum(CameraEnum, native_enum=False),
        nullable=False,
    )
    mode: Mapped[ModeEnum] = mapped_column(
        Enum(ModeEnum, native_enum=False),
        nullable=False,
    )

    recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # removed duplicate
    codec: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    probe_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    probed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_status: Mapped[MetadataStatusEnum] = mapped_column(
        Enum(MetadataStatusEnum, native_enum=False),
        nullable=False,
        server_default=text("'pending'"),
    )
    metadata_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source: Mapped[Optional["ClipSource"]] = relationship(
        back_populates="clip",
        uselist=False,
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="clip",
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="clip",
        passive_deletes=True,
    )