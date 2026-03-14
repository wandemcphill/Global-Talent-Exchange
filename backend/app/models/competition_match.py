from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_matches"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "round_id",
            "home_club_id",
            "away_club_id",
            name="uq_competition_matches_round_clubs",
        ),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="league", server_default="league")
    group_key: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    home_club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    away_club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    match_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    window: Mapped[str | None] = mapped_column(String(32), nullable=True)
    slot_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled", server_default="scheduled", index=True)
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    winner_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decided_by_penalties: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requires_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    stats_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionMatch"]
