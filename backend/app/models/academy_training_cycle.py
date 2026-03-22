from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.academy_player_progress import AcademyPlayerProgress
    from app.models.academy_program import AcademyProgram


class AcademyTrainingCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_training_cycles"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    program_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cycle_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    focus_attributes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    average_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    program: Mapped["AcademyProgram"] = relationship(back_populates="training_cycles")
    progress_entries: Mapped[list["AcademyPlayerProgress"]] = relationship(back_populates="training_cycle")


__all__ = ["AcademyTrainingCycle"]
