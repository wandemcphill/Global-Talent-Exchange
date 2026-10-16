from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.academy_graduation_event import AcademyGraduationEvent
    from app.models.academy_player_progress import AcademyPlayerProgress
    from app.models.academy_program import AcademyProgram


class AcademyPlayer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_players"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    program_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("academy_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_position: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[AcademyPlayerStatus] = mapped_column(
        Enum(
            AcademyPlayerStatus,
            name="academy_player_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_cycles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    development_attributes_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    pathway_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    program: Mapped["AcademyProgram | None"] = relationship(back_populates="players")
    progress_entries: Mapped[list["AcademyPlayerProgress"]] = relationship(back_populates="player")
    graduation_events: Mapped[list["AcademyGraduationEvent"]] = relationship(back_populates="player")


__all__ = ["AcademyPlayer"]
