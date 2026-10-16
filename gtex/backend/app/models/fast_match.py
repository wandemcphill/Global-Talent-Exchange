from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FastMatchResult(StrEnum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    ABANDONED = "abandoned"


class FastMatchSettlementStatus(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    REVERSED = "reversed"


class FastMatchSessionStatus(StrEnum):
    QUEUED = "queued"
    READY = "ready"
    SETTLED = "settled"
    ABANDONED = "abandoned"


class FastMatchEntitlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fast_match_entitlements"
    __table_args__ = (UniqueConstraint("user_id", "season_id", name="uq_fast_match_entitlements_user_season"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    free_match_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    free_matches_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    free_matches_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    wins_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    has_lost_free_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    free_eligibility_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    charge_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    last_match_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)


class FastMatchSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fast_match_sessions"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_fast_match_sessions_match_id"),
        UniqueConstraint("live_match_key", name="uq_fast_match_sessions_live_match_key"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    live_match_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    opponent_user_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    home_club_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    away_club_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entitlement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fast_match_entitlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    settlement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fast_match_settlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[FastMatchSessionStatus] = mapped_column(
        String(24),
        nullable=False,
        default=FastMatchSessionStatus.READY,
        server_default=FastMatchSessionStatus.READY.value,
        index=True,
    )
    charge_required_now: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    entry_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="credit", server_default="credit")
    fan_coin_entry_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0"), server_default="0")
    wallet_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    result: Mapped[str | None] = mapped_column(String(24), nullable=True)
    viewer_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    simulation_request_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FastMatchSettlement(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "fast_match_settlements"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_fast_match_settlements_match_id"),
        UniqueConstraint("idempotency_key", name="uq_fast_match_settlements_idempotency_key"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entitlement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("fast_match_entitlements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    result: Mapped[FastMatchResult] = mapped_column(String(24), nullable=False)
    was_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    fan_coin_charged: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0"), server_default="0")
    settlement_status: Mapped[FastMatchSettlementStatus] = mapped_column(
        String(24),
        nullable=False,
        default=FastMatchSettlementStatus.SETTLED,
        server_default=FastMatchSettlementStatus.SETTLED.value,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    wallet_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "FastMatchEntitlement",
    "FastMatchResult",
    "FastMatchSession",
    "FastMatchSessionStatus",
    "FastMatchSettlement",
    "FastMatchSettlementStatus",
]
