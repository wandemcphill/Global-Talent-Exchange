from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.enums.academy_player_status import AcademyPlayerStatus
from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.academy_player import AcademyPlayer
    from backend.app.models.academy_training_cycle import AcademyTrainingCycle


class AcademyPlayerProgress(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "academy_player_progress"

    academy_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    training_cycle_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("academy_training_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status_before: Mapped[AcademyPlayerStatus] = mapped_column(
        Enum(
            AcademyPlayerStatus,
            name="academy_player_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status_after: Mapped[AcademyPlayerStatus] = mapped_column(
        Enum(
            AcademyPlayerStatus,
            name="academy_player_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    delta_overall: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metrics_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)

    player: Mapped["AcademyPlayer"] = relationship(back_populates="progress_entries")
    training_cycle: Mapped["AcademyTrainingCycle | None"] = relationship(back_populates="progress_entries")


__all__ = ["AcademyPlayerProgress"]
