from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.wallet import LedgerUnit


class CoinTraderProfileStatus(StrEnum):
    APPLIED = "applied"
    APPROVED = "approved"
    REJECTED = "rejected"
    FROZEN = "frozen"
    SUSPENDED = "suspended"


class CoinTraderTier(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PREMIER = "premier"


class CoinTradeDirection(StrEnum):
    USER_BUYS = "user_buys"
    USER_SELLS = "user_sells"


class CoinTradeOrderStatus(StrEnum):
    CREATED = "created"
    ACCEPTED = "accepted"
    ESCROW_LOCKED = "escrow_locked"
    PAYMENT_PENDING = "payment_pending"
    PROOF_SUBMITTED = "proof_submitted"
    RELEASED = "released"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    ADMIN_RELEASED = "admin_released"
    ADMIN_REFUNDED = "admin_refunded"


class CoinTraderProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coin_trader_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_coin_trader_profiles_user_id"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="applied", server_default="applied", index=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="bronze", server_default="bronze", index=True)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    average_release_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    payment_methods_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    bank_accounts_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    liquidity_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CoinTraderRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coin_trader_rates"
    __table_args__ = (
        UniqueConstraint("trader_profile_id", "coin_unit", "fiat_currency", name="uq_coin_trader_rates_profile_unit_fiat"),
    )

    trader_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coin_unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False)
    fiat_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    buy_rate_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    sell_rate_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    min_coin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    max_coin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    available_liquidity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CoinTradeOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coin_trade_orders"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_coin_trade_orders_idempotency_key"),)

    trader_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    coin_unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False)
    coin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    quoted_rate_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fiat_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fiat_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", server_default="created", index=True)
    escrow_owner_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payment_window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proof_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proof_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    terms_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    ledger_refs_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
