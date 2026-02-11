from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, DateTime, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from asphalt_turret_engine.db.base import Base
from asphalt_turret_engine.db.enums import SDFileImportStateEnum

if TYPE_CHECKING:
    from asphalt_turret_engine.db.models.sd_card import SDCard
    from asphalt_turret_engine.db.models.job import Job

class SDFile(Base):
    __tablename__ = "sd_file"
    __table_args__ = (
        UniqueConstraint("sd_card_id", "rel_path", name="uq_sd_file_sd_card_rel_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sd_card_id: Mapped[int] = mapped_column(
        ForeignKey("sd_card.id"),
        nullable=False
    )
    rel_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    mtime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    import_state: Mapped[SDFileImportStateEnum] = mapped_column(
        SAEnum(SDFileImportStateEnum, native_enum=False),
        nullable=False,
        default=SDFileImportStateEnum.new,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    sd_card: Mapped["SDCard"] = relationship(
        back_populates="files"
    )

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="sd_file",
        passive_deletes=True,
    )