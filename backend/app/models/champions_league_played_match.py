from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChampionsLeaguePlayedMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One Champions League result. Payment reads this row, not process memory."""

    __tablename__ = "champions_league_played_matches"
    __table_args__ = (
        UniqueConstraint("season_id", "match_id", name="uq_champions_league_played_matches_season_match"),
    )

    season_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    home_club_id: Mapped[str] = mapped_column(String(64), nullable=False)
    away_club_id: Mapped[str] = mapped_column(String(64), nullable=False)
    home_goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_reached: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    club_user_ids: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fee_status: Mapped[str] = mapped_column(String(16), nullable=False, default="owed", server_default="owed")
