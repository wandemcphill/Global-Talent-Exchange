from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint
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
    EXPIRED = "expired"
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
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="applied", server_default="applied", index=True
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="bronze", server_default="bronze", index=True)
    verification_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="standard", server_default="standard", index=True
    )
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    average_release_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_volume_fiat: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    dispute_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    payment_methods_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    bank_accounts_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    liquidity_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class IdentityVerificationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "identity_verification_records"
    __table_args__ = (Index("ix_identity_verification_records_provider_ref", "provider", "provider_reference"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trader_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    verification_domain: Mapped[str] = mapped_column(
        String(32), nullable=False, default="coin_trader", server_default="coin_trader"
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    verification_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="full_kyc", server_default="full_kyc"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="initiated", server_default="initiated", index=True
    )
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checks_summary_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    history_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CoinTraderRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coin_trader_rates"
    __table_args__ = (
        UniqueConstraint(
            "trader_profile_id", "coin_unit", "fiat_currency", name="uq_coin_trader_rates_profile_unit_fiat"
        ),
    )

    trader_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coin_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False
    )
    fiat_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    buy_rate_fiat: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    sell_rate_fiat: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    min_coin_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    max_coin_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    available_liquidity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CoinAdvertSide(StrEnum):
    SELL = "sell"  # trader sells coins to the customer (customer buys)
    BUY = "buy"  # trader buys coins from the customer (customer sells)


class CoinAdvertStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ADMIN_PAUSED = "admin_paused"
    CLOSED = "closed"


class CoinAdvertPricingMode(StrEnum):
    FIXED = "fixed"
    FLOATING = "floating"


class CoinTraderAdvert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One advert per (trader, asset, fiat, side). Inventory is never stored here:
    sell-side availability is always derived live from the trader's canonical wallet."""

    __tablename__ = "coin_trader_adverts"
    __table_args__ = (
        UniqueConstraint(
            "trader_profile_id", "coin_unit", "fiat_currency", "side", name="uq_coin_trader_adverts_profile_unit_fiat_side"
        ),
        Index("ix_coin_trader_adverts_market", "coin_unit", "fiat_currency", "side", "status"),
    )

    trader_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coin_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False
    )
    fiat_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    pricing_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="fixed", server_default="fixed")
    price_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    spread_fiat: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    min_coin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    max_coin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    daily_limit_coin: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    payment_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15, server_default="15")
    payment_methods_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    terms_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active", index=True)
    admin_paused_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    coin_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False
    )
    coin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    quoted_rate_fiat: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fiat_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fiat_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created", server_default="created", index=True
    )
    escrow_owner_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    advert_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payment_window_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fee_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    fee_fiat: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
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


class CoinTradeMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coin_trade_messages"

    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("coin_trade_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_name: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)


class CoinTradeRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coin_trade_ratings"
    __table_args__ = (UniqueConstraint("order_id", name="uq_coin_trade_ratings_order_id"),)

    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("coin_trade_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trader_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("coin_trader_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)


__all__ = [
    "CoinTraderProfileStatus",
    "CoinTraderTier",
    "CoinTradeDirection",
    "CoinTradeOrderStatus",
    "CoinTraderProfile",
    "CoinTraderRate",
    "CoinAdvertSide",
    "CoinAdvertStatus",
    "CoinAdvertPricingMode",
    "CoinTraderAdvert",
    "CoinTradeOrder",
    "CoinTradeMessage",
    "CoinTradeRating",
    "IdentityVerificationRecord",
]
