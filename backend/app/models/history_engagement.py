from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class HistoricalRecordType(str, Enum):
    MATCH = "match"
    SEASON = "season"
    PLAYER = "player"
    CLUB = "club"
    COMPETITION = "competition"


class AchievementCategory(str, Enum):
    PERFORMANCE = "performance"
    PROGRESSION = "progression"
    RARE = "rare"
    SOCIAL = "social"


class FollowTargetType(str, Enum):
    MANAGER = "manager"
    CLUB = "club"


class ObjectiveFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class HistoricalRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "historical_records"

    type: Mapped[HistoricalRecordType] = mapped_column(
        SqlEnum(HistoricalRecordType, name="historicalrecordtype"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )


class HistoricalLeaderboardEntry(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "historical_leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("board_key", "entity_id", name="uq_historical_leaderboard_entries_board_entity"),
    )

    board_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(180), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    score_breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Achievement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "achievements"
    __table_args__ = (
        UniqueConstraint("achievement_key", name="uq_achievements_achievement_key"),
    )

    achievement_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[AchievementCategory] = mapped_column(
        SqlEnum(AchievementCategory, name="achievementcategory"),
        nullable=False,
        default=AchievementCategory.PERFORMANCE,
    )
    condition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reward: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class UserAchievement(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievements_user_achievement"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id: Mapped[str] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    reward_settlement_id: Mapped[str | None] = mapped_column(
        ForeignKey("reward_settlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reward_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MilestoneProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "milestone_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "milestone_key", name="uq_milestone_progress_user_key"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    best_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class UserProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    followers: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    following: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reputation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    profile_boost_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    badge_inventory_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cosmetic_inventory_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class UserFollow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_follows"
    __table_args__ = (
        UniqueConstraint("follower_user_id", "target_key", name="uq_user_follows_follower_target"),
    )

    follower_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    target_type: Mapped[FollowTargetType] = mapped_column(
        SqlEnum(FollowTargetType, name="followtargettype"),
        nullable=False,
    )
    target_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    target_club_id: Mapped[str | None] = mapped_column(
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class SocialActivity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "social_activities"

    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    activity_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    target_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_club_id: Mapped[str | None] = mapped_column(
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rivalry_key: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DailyTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_tasks"
    __table_args__ = (
        UniqueConstraint("task_key", name="uq_daily_tasks_task_key"),
    )

    task_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reward: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    condition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")


class WeeklyTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "weekly_tasks"
    __table_args__ = (
        UniqueConstraint("task_key", name="uq_weekly_tasks_task_key"),
    )

    task_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reward: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    condition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")


class SeasonPassSeason(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "season_pass_seasons"
    __table_args__ = (
        UniqueConstraint("season_id", name="uq_season_pass_seasons_season_id"),
    )

    season_id: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    levels: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    xp_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    premium_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class SeasonPassReward(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "season_pass_rewards"
    __table_args__ = (
        UniqueConstraint(
            "season_id",
            "level",
            "premium_only",
            name="uq_season_pass_rewards_season_level_track",
        ),
    )

    season_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    premium_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reward_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")


class SeasonPassMission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "season_pass_missions"
    __table_args__ = (
        UniqueConstraint(
            "season_id",
            "mission_key",
            "frequency",
            name="uq_season_pass_missions_season_key_frequency",
        ),
    )

    season_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mission_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="daily", server_default="daily")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reward_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")


class UserObjectiveProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_objective_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "task_frequency",
            "task_key",
            "period_key",
            name="uq_user_objective_progress_user_task_period",
        ),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_frequency: Mapped[ObjectiveFrequency] = mapped_column(
        SqlEnum(ObjectiveFrequency, name="objectivefrequency"),
        nullable=False,
        index=True,
    )
    task_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    progress_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    reward_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reward_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reward_settlement_id: Mapped[str | None] = mapped_column(
        ForeignKey("reward_settlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reward_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class UserSeasonProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_season_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "season_id", name="uq_user_season_progress_user_season"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    xp_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    has_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class UserSeasonRewardClaim(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_season_reward_claims"
    __table_args__ = (
        UniqueConstraint("user_id", "reward_id", name="uq_user_season_reward_claims_user_reward"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reward_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_rewards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    granted_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class UserSeasonMissionProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_season_mission_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "mission_id",
            "period_key",
            name="uq_user_season_mission_progress_user_mission_period",
        ),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("season_pass_missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_key: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="daily", server_default="daily")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    progress_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reward_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reward_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class UserStreak(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_streaks"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_streaks_user_id"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    longest_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_completed_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reward_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    xp_boost_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    coin_boost_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1.0000",
    )
    warning_sent_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "Achievement",
    "AchievementCategory",
    "DailyTask",
    "FollowTargetType",
    "HistoricalLeaderboardEntry",
    "HistoricalRecord",
    "HistoricalRecordType",
    "MilestoneProgress",
    "ObjectiveFrequency",
    "SocialActivity",
    "SeasonPassMission",
    "SeasonPassReward",
    "SeasonPassSeason",
    "UserAchievement",
    "UserFollow",
    "UserObjectiveProgress",
    "UserProfile",
    "UserSeasonMissionProgress",
    "UserSeasonProgress",
    "UserSeasonRewardClaim",
    "UserStreak",
    "WeeklyTask",
]
