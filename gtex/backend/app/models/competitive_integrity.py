from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ManagerType(StrEnum):
    USER = "user"
    REAL_MANAGER = "real_manager"


class CompetitiveMatchCompetitionType(StrEnum):
    GTEX_HOSTED = "gtex_hosted"
    FAST_GAME = "fast_game"
    CASUAL = "casual"


class CompetitiveMatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class CompetitiveNotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class CompetitiveNotificationChannel(StrEnum):
    PUSH = "push"
    SMS = "sms"


class MatchControlSide(StrEnum):
    HOME = "home"
    AWAY = "away"


class MatchControllerType(StrEnum):
    USER = "user"
    MANAGER = "manager"
    FROZEN = "frozen"


class Manager(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competitive_managers"
    __table_args__ = (
        Index("ix_competitive_managers_user_id", "user_id"),
        Index("ix_competitive_managers_type", "type"),
        Index("ix_competitive_managers_appointed_user_id", "appointed_user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ManagerType] = mapped_column(
        Enum(ManagerType, name="competitive_manager_type", native_enum=False),
        nullable=False,
    )
    appointed_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    instructions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    tactical_profile: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0, server_default="1000")

    owner: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    appointed_user: Mapped["User | None"] = relationship("User", foreign_keys=[appointed_user_id])


class FastGameRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fast_game_runs"
    __table_args__ = (
        Index("ix_fast_game_runs_user_id", "user_id"),
        Index("ix_fast_game_runs_is_active", "is_active"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    wins: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    manager_locked_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competitive_managers.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    base_reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    base_rating: Mapped[int] = mapped_column(nullable=False, default=1200, server_default="1200")
    scaling_factor: Mapped[int] = mapped_column(nullable=False, default=25, server_default="25")
    reward_amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reward_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    locked_manager: Mapped["Manager | None"] = relationship("Manager", foreign_keys=[manager_locked_id])


class Match(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competitive_matches"
    __table_args__ = (
        Index("ix_competitive_matches_competition_type", "competition_type"),
        Index("ix_competitive_matches_home_user_id", "home_user_id"),
        Index("ix_competitive_matches_away_user_id", "away_user_id"),
        Index("ix_competitive_matches_kickoff_at", "kickoff_at"),
        Index("ix_competitive_matches_status", "status"),
    )

    competition_type: Mapped[CompetitiveMatchCompetitionType] = mapped_column(
        Enum(CompetitiveMatchCompetitionType, name="competitive_match_competition_type", native_enum=False),
        nullable=False,
    )
    home_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    away_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    home_manager_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competitive_managers.id", ondelete="SET NULL"),
        nullable=True,
    )
    away_manager_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competitive_managers.id", ondelete="SET NULL"),
        nullable=True,
    )
    fast_game_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fast_game_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_user_online_home: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_user_online_away: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    locked_lineup_home: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    locked_lineup_away: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    kickoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[CompetitiveMatchStatus] = mapped_column(
        Enum(CompetitiveMatchStatus, name="competitive_match_status", native_enum=False),
        nullable=False,
        default=CompetitiveMatchStatus.SCHEDULED,
        server_default=CompetitiveMatchStatus.SCHEDULED.value,
    )
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    home_user: Mapped["User"] = relationship("User", foreign_keys=[home_user_id])
    away_user: Mapped["User"] = relationship("User", foreign_keys=[away_user_id])
    home_manager: Mapped["Manager | None"] = relationship("Manager", foreign_keys=[home_manager_id])
    away_manager: Mapped["Manager | None"] = relationship("Manager", foreign_keys=[away_manager_id])
    fast_game_run: Mapped["FastGameRun | None"] = relationship("FastGameRun", foreign_keys=[fast_game_run_id])
    control_logs: Mapped[list["MatchControlLog"]] = relationship(
        "MatchControlLog",
        back_populates="match",
        cascade="all, delete-orphan",
    )


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competitive_notifications"
    __table_args__ = (
        Index("ix_competitive_notifications_user_id", "user_id"),
        Index("ix_competitive_notifications_status", "status"),
        Index("ix_competitive_notifications_channel", "channel"),
        Index("ix_competitive_notifications_scheduled_for", "scheduled_for"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[CompetitiveNotificationStatus] = mapped_column(
        Enum(CompetitiveNotificationStatus, name="competitive_notification_status", native_enum=False),
        nullable=False,
        default=CompetitiveNotificationStatus.PENDING,
        server_default=CompetitiveNotificationStatus.PENDING.value,
    )
    channel: Mapped[CompetitiveNotificationChannel] = mapped_column(
        Enum(CompetitiveNotificationChannel, name="competitive_notification_channel", native_enum=False),
        nullable=False,
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class MatchControlLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "match_control_logs"
    __table_args__ = (
        Index("ix_match_control_logs_match_id", "match_id"),
        Index("ix_match_control_logs_side", "side"),
    )

    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competitive_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    side: Mapped[MatchControlSide] = mapped_column(
        Enum(MatchControlSide, name="match_control_side", native_enum=False),
        nullable=False,
    )
    controller_type: Mapped[MatchControllerType] = mapped_column(
        Enum(MatchControllerType, name="match_controller_type", native_enum=False),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    match: Mapped["Match"] = relationship(Match, back_populates="control_logs")


__all__ = [
    "CompetitiveMatchCompetitionType",
    "CompetitiveMatchStatus",
    "CompetitiveNotificationChannel",
    "CompetitiveNotificationStatus",
    "FastGameRun",
    "Manager",
    "ManagerType",
    "Match",
    "MatchControllerType",
    "MatchControlLog",
    "MatchControlSide",
    "Notification",
]
