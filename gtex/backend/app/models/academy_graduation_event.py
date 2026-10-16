from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.academy_player import AcademyPlayer


class AcademyGraduationEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "academy_graduation_events"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    academy_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[AcademyPlayerStatus] = mapped_column(
        Enum(
            AcademyPlayerStatus,
            name="academy_player_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    to_status: Mapped[AcademyPlayerStatus] = mapped_column(
        Enum(
            AcademyPlayerStatus,
            name="academy_player_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    player: Mapped["AcademyPlayer"] = relationship(back_populates="graduation_events")


__all__ = ["AcademyGraduationEvent"]
