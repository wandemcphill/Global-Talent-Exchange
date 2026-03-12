from __future__ import annotations

from sqlalchemy import Boolean, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionRuleSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_rule_sets"
    __table_args__ = (
        UniqueConstraint("competition_id", name="uq_competition_rule_sets_competition_id"),
    )

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(24), nullable=False)

    min_participants: Mapped[int] = mapped_column(Integer, nullable=False)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False)

    league_win_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    league_draw_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    league_loss_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    league_tie_break_order: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    league_home_away: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    cup_single_elimination: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cup_two_leg_tie: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cup_extra_time: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cup_penalties: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cup_allowed_participant_sizes: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
