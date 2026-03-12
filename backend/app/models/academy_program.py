from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.enums.academy_program_type import AcademyProgramType
from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.academy_player import AcademyPlayer
    from backend.app.models.academy_training_cycle import AcademyTrainingCycle


class AcademyProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_programs"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    program_type: Mapped[AcademyProgramType] = mapped_column(
        Enum(
            AcademyProgramType,
            name="academy_program_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    budget_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cycle_length_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=6, server_default="6")
    focus_attributes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    players: Mapped[list["AcademyPlayer"]] = relationship(back_populates="program")
    training_cycles: Mapped[list["AcademyTrainingCycle"]] = relationship(back_populates="program")


__all__ = ["AcademyProgram"]
