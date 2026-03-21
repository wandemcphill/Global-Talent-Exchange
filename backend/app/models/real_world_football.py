from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

import app.models.user  # noqa: F401
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.ingestion.models import Player
    from app.models.user import User


class EventIngestionJobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class RealWorldEventSourceType(StrEnum):
    MANUAL = "manual"
    API = "api"
    IMPORT_FEED = "import_feed"


class RealWorldEventApprovalStatus(StrEnum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


class EffectRecordStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class EventIngestionJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_ingestion_jobs"
    __table_args__ = (
        Index("ix_event_ingestion_jobs_source_type", "source_type"),
        Index("ix_event_ingestion_jobs_status", "status"),
        Index("ix_event_ingestion_jobs_started_at", "started_at"),
    )

    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_label: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EventIngestionJobStatus.RUNNING.value,
        server_default=EventIngestionJobStatus.RUNNING.value,
    )
    submitted_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pending_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[list["RealWorldFootballEvent"]] = relationship(back_populates="ingestion_job")
    submitted_by_user: Mapped["User | None"] = relationship()


class RealWorldFootballEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "real_world_football_events"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_real_world_football_events_dedupe_key"),
        Index("ix_real_world_football_events_player_id", "player_id"),
        Index("ix_real_world_football_events_event_type", "event_type"),
        Index("ix_real_world_football_events_approval_status", "approval_status"),
        Index("ix_real_world_football_events_occurred_at", "occurred_at"),
    )

    ingestion_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("event_ingestion_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_label: Mapped[str] = mapped_column(String(80), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RealWorldEventApprovalStatus.APPROVED.value,
        server_default=RealWorldEventApprovalStatus.APPROVED.value,
    )
    requires_admin_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    effect_severity_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    effects_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    normalized_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    ingestion_job: Mapped[EventIngestionJob | None] = relationship(back_populates="events")
    player: Mapped["Player"] = relationship()
    approved_by_user: Mapped["User | None"] = relationship(foreign_keys=[approved_by_user_id])
    rejected_by_user: Mapped["User | None"] = relationship(foreign_keys=[rejected_by_user_id])
    form_modifiers: Mapped[list["PlayerFormModifier"]] = relationship(back_populates="event")
    trending_flags: Mapped[list["TrendingPlayerFlag"]] = relationship(back_populates="event")
    demand_signals: Mapped[list["PlayerDemandSignal"]] = relationship(back_populates="event")


class EventEffectRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_effect_rules"
    __table_args__ = (
        UniqueConstraint("event_type", "effect_type", "effect_code", name="uq_event_effect_rules_event_effect"),
        Index("ix_event_effect_rules_event_type", "event_type"),
        Index("ix_event_effect_rules_enabled", "is_enabled"),
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    effect_type: Mapped[str] = mapped_column(String(32), nullable=False)
    effect_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    base_magnitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gameplay_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    market_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    recommendation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerFormModifier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_form_modifiers"
    __table_args__ = (
        Index("ix_player_form_modifiers_player_id", "player_id"),
        Index("ix_player_form_modifiers_status", "status"),
        Index("ix_player_form_modifiers_expires_at", "expires_at"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_world_football_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    modifier_type: Mapped[str] = mapped_column(String(64), nullable=False)
    modifier_label: Mapped[str] = mapped_column(String(160), nullable=False)
    modifier_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    gameplay_effect_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    market_effect_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    recommendation_effect_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    visible_to_users: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EffectRecordStatus.ACTIVE.value,
        server_default=EffectRecordStatus.ACTIVE.value,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    event: Mapped[RealWorldFootballEvent] = relationship(back_populates="form_modifiers")
    player: Mapped["Player"] = relationship()


class TrendingPlayerFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trending_player_flags"
    __table_args__ = (
        Index("ix_trending_player_flags_player_id", "player_id"),
        Index("ix_trending_player_flags_flag_type", "flag_type"),
        Index("ix_trending_player_flags_status", "status"),
        Index("ix_trending_player_flags_expires_at", "expires_at"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_world_football_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    flag_type: Mapped[str] = mapped_column(String(64), nullable=False)
    flag_label: Mapped[str] = mapped_column(String(160), nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EffectRecordStatus.ACTIVE.value,
        server_default=EffectRecordStatus.ACTIVE.value,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    event: Mapped[RealWorldFootballEvent] = relationship(back_populates="trending_flags")
    player: Mapped["Player"] = relationship()


class PlayerDemandSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_demand_signals"
    __table_args__ = (
        Index("ix_player_demand_signals_player_id", "player_id"),
        Index("ix_player_demand_signals_signal_type", "signal_type"),
        Index("ix_player_demand_signals_status", "status"),
        Index("ix_player_demand_signals_expires_at", "expires_at"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("real_world_football_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    signal_label: Mapped[str] = mapped_column(String(160), nullable=False)
    demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    scouting_interest_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    recommendation_priority_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    market_buzz_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EffectRecordStatus.ACTIVE.value,
        server_default=EffectRecordStatus.ACTIVE.value,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    event: Mapped[RealWorldFootballEvent] = relationship(back_populates="demand_signals")
    player: Mapped["Player"] = relationship()
