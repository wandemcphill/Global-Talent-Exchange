from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerValueSnapshotRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_value_snapshots"
    __table_args__ = (
        UniqueConstraint("player_id", "as_of", "snapshot_type", name="uq_player_value_snapshots_player_as_of_type"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(32), nullable=False, default="intraday", server_default="intraday", index=True)
    previous_credits: Mapped[float] = mapped_column(Float, nullable=False)
    target_credits: Mapped[float] = mapped_column(Float, nullable=False)
    movement_pct: Mapped[float] = mapped_column(Float, nullable=False)
    football_truth_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    market_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    scouting_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    egame_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0", index=True)
    confidence_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="low", server_default="low", index=True)
    liquidity_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default", index=True)
    market_integrity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    signal_trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trend_7d_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trend_30d_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trend_direction: Mapped[str] = mapped_column(String(16), nullable=False, default="flat", server_default="flat")
    trend_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="baseline-v1", server_default="baseline-v1")
    breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    drivers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reason_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class PlayerValueDailyCloseRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_value_daily_closes"
    __table_args__ = (
        UniqueConstraint("player_id", "close_date", name="uq_player_value_daily_closes_player_date"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    close_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    close_credits: Mapped[float] = mapped_column(Float, nullable=False)
    football_truth_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    market_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    scouting_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    egame_signal_value_credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    confidence_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="low", server_default="low", index=True)
    liquidity_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default", index=True)
    trend_7d_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trend_30d_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trend_direction: Mapped[str] = mapped_column(String(16), nullable=False, default="flat", server_default="flat")
    trend_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    reason_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class PlayerValueRecomputeCandidateRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_value_recompute_candidates"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_value_recompute_candidates_player_id"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending", index=True)
    requested_tempo: Mapped[str] = mapped_column(String(24), nullable=False, default="hourly", server_default="hourly", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50", index=True)
    trigger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    signal_delta_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class PlayerValueRunRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_value_run_records"

    run_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", server_default="queued", index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="baseline-v1", server_default="baseline-v1")
    triggered_by: Mapped[str] = mapped_column(String(32), nullable=False, default="system", server_default="system")
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class PlayerValueAdminAuditRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_value_admin_audits"

    action_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    config_version: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    target_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
