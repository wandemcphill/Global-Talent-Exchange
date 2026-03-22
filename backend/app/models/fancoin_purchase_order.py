from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.treasury import RateDirection
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.models.user import User


class PurchaseOrderStatus(StrEnum):
    REQUESTED = "requested"
    REVIEWING = "reviewing"
    PROCESSING = "processing"
    SETTLED = "settled"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    CHARGEBACK = "chargeback"
    REVERSED = "reversed"
    DISPUTED = "disputed"


class FancoinPurchaseOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fancoin_purchase_orders"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_fancoin_purchase_order_reference"),
        Index("ix_fancoin_purchase_orders_status", "status"),
        Index("ix_fancoin_purchase_orders_created_at", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus, name="purchase_order_status", native_enum=False),
        nullable=False,
        default=PurchaseOrderStatus.REQUESTED,
    )
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.CREDIT,
    )
    amount_fiat: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN", server_default="NGN")
    rate_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    rate_direction: Mapped[RateDirection] = mapped_column(
        Enum(RateDirection, name="rate_direction", native_enum=False),
        nullable=False,
    )
    processor_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="automatic_gateway", server_default="automatic_gateway")
    payout_channel: Mapped[str] = mapped_column(String(64), nullable=False, default="gateway", server_default="gateway")
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="wallet", server_default="wallet")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chargeback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


__all__ = ["FancoinPurchaseOrder", "PurchaseOrderStatus"]
