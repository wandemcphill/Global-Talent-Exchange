from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SeasonPassTier(StrEnum):
    FREE = "free"
    PREMIUM = "premium"


class SeasonPass(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "season_passes"
    __table_args__ = (
        UniqueConstraint("user_id", "season_id", name="uq_season_passes_user_season"),
        Index("ix_season_passes_user_id", "user_id"),
        Index("ix_season_passes_season_id", "season_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[SeasonPassTier] = mapped_column(
        Enum(SeasonPassTier, name="season_pass_tier", native_enum=False),
        nullable=False,
        default=SeasonPassTier.FREE,
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    rewards_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class SeasonPassClaim(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "season_pass_claims"
    __table_args__ = (
        UniqueConstraint("season_pass_id", "level", name="uq_season_pass_claims_pass_level"),
        Index("ix_season_pass_claims_user_id", "user_id"),
    )

    season_pass_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("season_passes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SeasonPassXpGrant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "season_pass_xp_grants"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_season_pass_xp_grants_reference_key"),
        Index("ix_season_pass_xp_grants_user_id", "user_id"),
        Index("ix_season_pass_xp_grants_source_type", "source_type"),
    )

    season_pass_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("season_passes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiveEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "live_events"
    __table_args__ = (
        Index("ix_live_events_start_date", "start_date"),
        Index("ix_live_events_end_date", "end_date"),
        Index("ix_live_events_started_notification_sent_at", "started_notification_sent_at"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rules_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    rewards_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    started_notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "LiveEvent",
    "SeasonPass",
    "SeasonPassClaim",
    "SeasonPassTier",
    "SeasonPassXpGrant",
]
