from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ClipEarningEventType(StrEnum):
    IMPRESSION = "impression"
    LIKE = "like"
    SHARE = "share"


class CreatorWallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_wallet"
    __table_args__ = (
        UniqueConstraint("creator_user_id", name="uq_creator_wallet_creator_user_id"),
        Index("ix_creator_wallet_last_event_at", "last_event_at"),
    )

    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_impressions: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total_likes: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total_shares: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total_earnings_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    available_balance_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClipEarningsLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "clip_earnings_log"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_clip_earnings_log_reference_key"),
        Index("ix_clip_earnings_log_clip_id", "clip_id"),
        Index("ix_clip_earnings_log_creator_user_id", "creator_user_id"),
        Index("ix_clip_earnings_log_event_type", "event_type"),
    )

    clip_id: Mapped[str] = mapped_column(String(200), nullable=False)
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    viewer_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[ClipEarningEventType] = mapped_column(
        Enum(ClipEarningEventType, name="clip_earning_event_type", native_enum=False),
        nullable=False,
    )
    reference_key: Mapped[str] = mapped_column(String(191), nullable=False)
    impression_delta: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    like_delta: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    share_delta: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    base_rate_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    engagement_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    virality_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    earnings_delta_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    creator_wallet_balance_credit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "ClipEarningEventType",
    "ClipEarningsLog",
    "CreatorWallet",
]


@event.listens_for(ClipEarningsLog, "before_update", propagate=True)
def _prevent_clip_earnings_log_update(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("clip_earnings_log is append-only and cannot be updated.")


@event.listens_for(ClipEarningsLog, "before_delete", propagate=True)
def _prevent_clip_earnings_log_delete(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("clip_earnings_log is append-only and cannot be deleted.")
