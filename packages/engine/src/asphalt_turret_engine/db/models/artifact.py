from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, DateTime, UniqueConstraint, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict

from asphalt_turret_engine.db.base import Base
from asphalt_turret_engine.db.enums import ArtifactKindEnum

if TYPE_CHECKING:
    from asphalt_turret_engine.db.models.clip import Clip

class Artifact(Base):
    __tablename__ = "artifact"
    __table_args__ = (
        UniqueConstraint("clip_id", "kind", name="uq_artifact_clip_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(
        ForeignKey("clip.id"),
        nullable=False
    )
    kind: Mapped[ArtifactKindEnum] = mapped_column(
        Enum(ArtifactKindEnum, native_enum=False),
        nullable=False
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    params_json: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    clip: Mapped["Clip"] = relationship(
        back_populates="artifacts"
    )