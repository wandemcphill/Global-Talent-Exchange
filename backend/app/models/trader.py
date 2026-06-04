from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TraderExperience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    PROFESSIONAL = "professional"


class TraderOrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    CONVERT = "convert"


class TraderOrderStatus(StrEnum):
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"


class TraderP2PStatus(StrEnum):
    OPEN = "open"
    MATCHED = "matched"
    CANCELLED = "cancelled"


class TraderProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_trader_profiles_user_id"),
        UniqueConstraint("trading_alias", name="uq_trader_profiles_trading_alias"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trading_alias: Mapped[str] = mapped_column(String(120), nullable=False)
    preferred_currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    trading_experience: Mapped[TraderExperience] = mapped_column(
        Enum(
            TraderExperience,
            name="trader_experience",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=TraderExperience.BEGINNER,
        server_default=TraderExperience.BEGINNER.value,
    )
    interests_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    wallet_label: Mapped[str] = mapped_column(String(120), nullable=False, default="GTEX Trading Wallet")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    liquidity_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    completion_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    average_release_seconds: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    rating_score: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    metrics_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TraderSecurity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_security"
    __table_args__ = (UniqueConstraint("user_id", name="uq_trader_security_user_id"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    totp_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    backup_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recovery_phrase_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    security_pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class TraderMarket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_markets"
    __table_args__ = (UniqueConstraint("symbol", name="uq_trader_markets_symbol"),)

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(24), nullable=False, default="gtex_coin", server_default="gtex_coin")
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("1.0000"))
    daily_change_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    market_cap: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    volume_24h: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    liquidity_score: Mapped[int] = mapped_column(nullable=False, default=50, server_default="50")


class TraderPriceTick(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_price_ticks"
    __table_args__ = (Index("ix_trader_price_ticks_market_created", "market_id", "created_at"),)

    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("trader_markets.id", ondelete="CASCADE"), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    timeframe: Mapped[str] = mapped_column(String(12), nullable=False, default="1h", server_default="1h")


class TraderOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_orders"
    __table_args__ = (Index("ix_trader_orders_user_status", "user_id", "status"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("trader_markets.id", ondelete="CASCADE"), nullable=False)
    side: Mapped[TraderOrderSide] = mapped_column(
        Enum(
            TraderOrderSide,
            name="trader_order_side",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    status: Mapped[TraderOrderStatus] = mapped_column(
        Enum(
            TraderOrderStatus,
            name="trader_order_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=TraderOrderStatus.OPEN,
        server_default=TraderOrderStatus.OPEN.value,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TraderP2POffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_p2p_offers"
    __table_args__ = (Index("ix_trader_p2p_offers_user_status", "user_id", "status"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("trader_markets.id", ondelete="CASCADE"), nullable=False)
    side: Mapped[TraderOrderSide] = mapped_column(
        Enum(
            TraderOrderSide,
            name="trader_p2p_side",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    status: Mapped[TraderP2PStatus] = mapped_column(
        Enum(
            TraderP2PStatus,
            name="trader_p2p_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=TraderP2PStatus.OPEN,
        server_default=TraderP2PStatus.OPEN.value,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    preferred_currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD")


class TraderWatchlist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_watchlists"
    __table_args__ = (UniqueConstraint("user_id", "market_id", name="uq_trader_watchlists_user_market"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(String(36), ForeignKey("trader_markets.id", ondelete="CASCADE"), nullable=False)


class TraderSecurityEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trader_security_events"
    __table_args__ = (Index("ix_trader_security_events_user_created", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "TraderExperience",
    "TraderMarket",
    "TraderOrder",
    "TraderOrderSide",
    "TraderOrderStatus",
    "TraderP2POffer",
    "TraderP2PStatus",
    "TraderPriceTick",
    "TraderProfile",
    "TraderSecurity",
    "TraderSecurityEvent",
    "TraderWatchlist",
]
