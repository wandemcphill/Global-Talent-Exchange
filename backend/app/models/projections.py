from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProjectionEventReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projection_event_receipts"
    __table_args__ = (
        UniqueConstraint("projection_name", "event_id", name="uq_projection_event_receipts_projection_event"),
    )

    projection_name: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CompetitionStandingProjection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_standing_projections"
    __table_args__ = (
        UniqueConstraint("competition_id", "club_id", name="uq_competition_standing_projections_competition_club"),
    )

    competition_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    season_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    competition_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    club_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_name: Mapped[str] = mapped_column(String(160), nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goal_difference: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_fixture_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class PlayerStatsProjection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_stats_projections"
    __table_args__ = (
        UniqueConstraint("competition_id", "player_id", name="uq_player_stats_projections_competition_player"),
    )

    competition_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    season_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    competition_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    player_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    team_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(160), nullable=False)
    appearances: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    starts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    minutes_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    yellow_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    red_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cumulative_xg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    average_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    rating_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_fixture_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


__all__ = [
    "CompetitionStandingProjection",
    "PlayerStatsProjection",
    "ProjectionEventReceipt",
]
