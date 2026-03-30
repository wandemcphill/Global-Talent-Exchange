from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


def _enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


class SeasonStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"


class ResetStrategy(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class RewardDeliveryStatus(StrEnum):
    PENDING = "pending"
    DISTRIBUTED = "distributed"
    FAILED = "failed"


class LeaderboardSeason(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leaderboard_seasons"
    __table_args__ = (
        Index("ix_leaderboard_seasons_status_dates", "status", "start_date", "end_date"),
    )

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[SeasonStatus] = mapped_column(
        Enum(
            SeasonStatus,
            name="leaderboard_season_status",
            native_enum=False,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=SeasonStatus.ACTIVE,
        server_default=SeasonStatus.ACTIVE.value,
    )
    default_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=1200, server_default="1200")
    k_factor: Mapped[int] = mapped_column(Integer, nullable=False, default=32, server_default="32")
    reset_strategy: Mapped[ResetStrategy] = mapped_column(
        Enum(
            ResetStrategy,
            name="leaderboard_reset_strategy",
            native_enum=False,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=ResetStrategy.SOFT,
        server_default=ResetStrategy.SOFT.value,
    )
    soft_reset_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rewards_distributed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class LeaderboardPlayerRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leaderboard_player_ratings"
    __table_args__ = (
        UniqueConstraint("season_id", "player_id", name="uq_leaderboard_player_ratings_season_player"),
        Index("ix_leaderboard_player_ratings_season_rating", "season_id", "rating"),
        Index("ix_leaderboard_player_ratings_season_region", "season_id", "region"),
        Index("ix_leaderboard_player_ratings_season_division", "season_id", "division"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leaderboard_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    division: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=1200, server_default="1200")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    highest_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=1200, server_default="1200")
    last_rating_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_match_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_result: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class LeaderboardMatchResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "leaderboard_match_results"
    __table_args__ = (
        UniqueConstraint("season_id", "match_id", name="uq_leaderboard_match_results_season_match"),
        UniqueConstraint("source_event_id", name="uq_leaderboard_match_results_source_event"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leaderboard_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    player_a_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    player_b_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result: Mapped[float] = mapped_column(Float, nullable=False)
    player_a_rating_before: Mapped[int] = mapped_column(Integer, nullable=False)
    player_b_rating_before: Mapped[int] = mapped_column(Integer, nullable=False)
    player_a_rating_after: Mapped[int] = mapped_column(Integer, nullable=False)
    player_b_rating_after: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class LeaderboardSeasonSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "leaderboard_season_snapshots"
    __table_args__ = (
        UniqueConstraint("season_id", "board_key", "player_id", name="uq_leaderboard_season_snapshots_board_player"),
        Index("ix_leaderboard_season_snapshots_season_board_rank", "season_id", "board_key", "rank_position"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leaderboard_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    board_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    division: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class LeaderboardSeasonReward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leaderboard_season_rewards"
    __table_args__ = (
        UniqueConstraint("season_id", "board_key", "player_id", name="uq_leaderboard_season_rewards_board_player"),
        Index("ix_leaderboard_season_rewards_season_rank", "season_id", "board_key", "rank_position"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leaderboard_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    board_key: Mapped[str] = mapped_column(String(96), nullable=False, default="global", server_default="global")
    player_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    coins: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    trophies: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    badges_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[RewardDeliveryStatus] = mapped_column(
        Enum(
            RewardDeliveryStatus,
            name="leaderboard_reward_delivery_status",
            native_enum=False,
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=RewardDeliveryStatus.PENDING,
        server_default=RewardDeliveryStatus.PENDING.value,
    )
    distributed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "LeaderboardMatchResult",
    "LeaderboardPlayerRating",
    "LeaderboardSeason",
    "LeaderboardSeasonReward",
    "LeaderboardSeasonSnapshot",
    "ResetStrategy",
    "RewardDeliveryStatus",
    "SeasonStatus",
]
