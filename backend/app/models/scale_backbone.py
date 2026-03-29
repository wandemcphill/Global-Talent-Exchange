from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin


MONEY_SCALE = 4
MONEY_PRECISION = 18


class OrchestratorClipStateRecord(TimestampMixin, Base):
    __tablename__ = "orchestrator_clip_states"
    __table_args__ = (
        Index("ix_orchestrator_clip_states_stage_updated_at", "stage", "updated_at"),
        Index("ix_orchestrator_clip_states_base_clip_id", "base_clip_id"),
    )

    clip_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="test", server_default="test")
    allocated_impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consumed_impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    velocity_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    is_ad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_moment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    bid_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1")
    age_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    base_clip_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    winner_variant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OrchestratorConfigRecord(TimestampMixin, Base):
    __tablename__ = "orchestrator_configs"

    config_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ViralLeaderboardEntryRecord(TimestampMixin, Base):
    __tablename__ = "viral_leaderboard_entries"
    __table_args__ = (
        Index("ix_viral_leaderboard_entries_score_clip_id", "score", "clip_id"),
    )

    clip_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PersonalizedFeedCacheEntryRecord(TimestampMixin, Base):
    __tablename__ = "personalized_feed_cache_entries"
    __table_args__ = (
        UniqueConstraint("subject_key", "clip_id", name="uq_personalized_feed_cache_entries_subject_clip"),
        Index("ix_personalized_feed_cache_entries_subject_position", "subject_key", "position"),
        Index("ix_personalized_feed_cache_entries_subject_score", "subject_key", "score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False)
    clip_id: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PersonalizedFeedHistoryEntryRecord(CreatedAtMixin, Base):
    __tablename__ = "personalized_feed_history_entries"
    __table_args__ = (
        Index("ix_personalized_feed_history_entries_subject_served_at", "subject_key", "served_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_key: Mapped[str] = mapped_column(String(128), nullable=False)
    clip_id: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    format_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    similarity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PersonalizedFeedSeenClipRecord(Base):
    __tablename__ = "personalized_feed_seen_clips"
    __table_args__ = (
        Index("ix_personalized_feed_seen_clips_user_seen_at", "user_id", "seen_at"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    clip_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ViralDispatchPoolEntryRecord(TimestampMixin, Base):
    __tablename__ = "viral_dispatch_pool_entries"
    __table_args__ = (
        Index("ix_viral_dispatch_pool_entries_score_inserted_at", "score", "created_at"),
        Index("ix_viral_dispatch_pool_entries_expires_at", "expires_at"),
    )

    clip_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CreatorClipEarningsProjectionRecord(TimestampMixin, Base):
    __tablename__ = "creator_clip_earnings_projections"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    generated_clip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    monetized_clip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_gross_revenue_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    total_creator_payout_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    total_platform_share_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    total_growth_pool_retained_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    total_viral_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    total_referral_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    total_weekly_top_creator_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    viral_clip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wallet_balance_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    wallet_available_credit: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    wallet_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="CREDIT", server_default="CREDIT")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
