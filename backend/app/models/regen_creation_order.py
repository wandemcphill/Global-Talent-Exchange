from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RegenCreationRequestType(StrEnum):
    SON = "son"
    ACADEMY_BOOST = "academy_boost"
    SCOUT_SPECIAL = "scout_special"


class RegenCreationPaymentMethod(StrEnum):
    WALLET = "wallet"
    KORAPAY = "korapay"


class RegenCreationOrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    GENERATING = "generating"
    GENERATED = "generated"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class RegenCreationOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_creation_orders"
    __table_args__ = (
        UniqueConstraint("payment_reference", name="uq_regen_creation_orders_payment_reference"),
        Index("ix_regen_creation_orders_status", "status"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_type: Mapped[RegenCreationRequestType] = mapped_column(
        Enum(
            RegenCreationRequestType,
            name="regen_creation_request_type",
            native_enum=False,
        ),
        nullable=False,
        default=RegenCreationRequestType.SON,
        server_default=RegenCreationRequestType.SON.value,
    )
    parent_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    requested_country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    requested_position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount_coin: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="COIN", server_default="COIN")
    payment_method: Mapped[RegenCreationPaymentMethod] = mapped_column(
        Enum(
            RegenCreationPaymentMethod,
            name="regen_creation_payment_method",
            native_enum=False,
        ),
        nullable=False,
        default=RegenCreationPaymentMethod.WALLET,
        server_default=RegenCreationPaymentMethod.WALLET.value,
    )
    payment_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[RegenCreationOrderStatus] = mapped_column(
        Enum(
            RegenCreationOrderStatus,
            name="regen_creation_order_status",
            native_enum=False,
        ),
        nullable=False,
        default=RegenCreationOrderStatus.PENDING_PAYMENT,
        server_default=RegenCreationOrderStatus.PENDING_PAYMENT.value,
    )
    generated_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generated_regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "RegenCreationOrder",
    "RegenCreationOrderStatus",
    "RegenCreationPaymentMethod",
    "RegenCreationRequestType",
]
