from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class FanPredictionFixtureStatus(StrEnum):
    SCHEDULED = "scheduled"
    OPEN = "open"
    LOCKED = "locked"
    PENDING_SETTLEMENT = "pending_settlement"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class FanPredictionSubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class FanPredictionTokenReason(StrEnum):
    DAILY_REFILL = "daily_refill"
    SEASON_PASS_BONUS = "season_pass_bonus"
    PREDICTION_SUBMISSION = "prediction_submission"
    PREDICTION_REFUND = "prediction_refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class FanPredictionRewardType(StrEnum):
    FANCOIN = "fancoin"
    BADGE = "badge"


class FanPredictionLeaderboardScope(StrEnum):
    MATCH = "match"
    WEEKLY = "weekly"
    CREATOR_CLUB_WEEKLY = "creator_club_weekly"


class FanPredictionFixture(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_prediction_fixtures"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_fan_prediction_fixtures_match"),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    home_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    away_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FanPredictionFixtureStatus] = mapped_column(
        Enum(FanPredictionFixtureStatus, name="fan_prediction_fixture_status", native_enum=False),
        nullable=False,
        default=FanPredictionFixtureStatus.SCHEDULED,
        server_default=FanPredictionFixtureStatus.SCHEDULED.value,
    )
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    locks_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    rewards_disbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    promo_pool_fancoin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    reward_funding_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="gtex_promotional_pool",
        server_default="gtex_promotional_pool",
    )
    badge_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_reward_winners: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    allow_creator_club_segmentation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    settlement_rule_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="fan_prediction_v1",
        server_default="fan_prediction_v1",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_by_user: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])


class FanPredictionOutcome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_prediction_outcomes"
    __table_args__ = (
        UniqueConstraint("fixture_id", name="uq_fan_prediction_outcomes_fixture"),
    )

    fixture_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fan_prediction_fixtures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    winner_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    first_goal_scorer_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    total_goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    mvp_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default="match_completion",
        server_default="match_completion",
    )
    settled_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    settled_by_user: Mapped["User | None"] = relationship(foreign_keys=[settled_by_user_id])


class FanPredictionSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_prediction_submissions"
    __table_args__ = (
        UniqueConstraint("fixture_id", "user_id", name="uq_fan_prediction_submissions_fixture_user"),
    )

    fixture_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fan_prediction_fixtures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_segment_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fan_group_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_fan_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    leaderboard_week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    winner_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_goal_scorer_player_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    total_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    mvp_player_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tokens_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[FanPredictionSubmissionStatus] = mapped_column(
        Enum(FanPredictionSubmissionStatus, name="fan_prediction_submission_status", native_enum=False),
        nullable=False,
        default=FanPredictionSubmissionStatus.SUBMITTED,
        server_default=FanPredictionSubmissionStatus.SUBMITTED.value,
    )
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    correct_pick_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    perfect_card: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    reward_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])


class FanPredictionTokenLedger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_prediction_token_ledger"
    __table_args__ = (
        UniqueConstraint("unique_key", name="uq_fan_prediction_token_ledger_unique_key"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_pass_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_season_passes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submission_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fan_prediction_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[FanPredictionTokenReason] = mapped_column(
        Enum(FanPredictionTokenReason, name="fan_prediction_token_reason", native_enum=False),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    unique_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    created_by_user: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])


class FanPredictionRewardGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_prediction_reward_grants"
    __table_args__ = (
        UniqueConstraint("unique_key", name="uq_fan_prediction_reward_grants_unique_key"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fixture_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fan_prediction_fixtures.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submission_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fan_prediction_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reward_settlement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("reward_settlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    awarded_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    leaderboard_scope: Mapped[FanPredictionLeaderboardScope] = mapped_column(
        Enum(FanPredictionLeaderboardScope, name="fan_prediction_leaderboard_scope", native_enum=False),
        nullable=False,
        default=FanPredictionLeaderboardScope.MATCH,
        server_default=FanPredictionLeaderboardScope.MATCH.value,
    )
    reward_type: Mapped[FanPredictionRewardType] = mapped_column(
        Enum(FanPredictionRewardType, name="fan_prediction_reward_type", native_enum=False),
        nullable=False,
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    badge_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fancoin_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    promo_pool_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    unique_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    awarded_by_user: Mapped["User | None"] = relationship(foreign_keys=[awarded_by_user_id])


__all__ = [
    "FanPredictionFixture",
    "FanPredictionFixtureStatus",
    "FanPredictionLeaderboardScope",
    "FanPredictionOutcome",
    "FanPredictionRewardGrant",
    "FanPredictionRewardType",
    "FanPredictionSubmission",
    "FanPredictionSubmissionStatus",
    "FanPredictionTokenLedger",
    "FanPredictionTokenReason",
]
