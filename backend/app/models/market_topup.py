from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from backend.app.models.user import User


class MarketTopupStatus(StrEnum):
    REQUESTED = "requested"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    PROCESSING = "processing"
    SETTLED = "settled"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    REVERSED = "reversed"
    DISPUTED = "disputed"


class MarketTopup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_topups"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_market_topups_reference"),
        Index("ix_market_topups_status", "status"),
        Index("ix_market_topups_created_at", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[MarketTopupStatus] = mapped_column(
        Enum(MarketTopupStatus, name="market_topup_status", native_enum=False),
        nullable=False,
        default=MarketTopupStatus.REQUESTED,
    )
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.CREDIT,
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="market", server_default="market")
    processor_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="internal_transfer", server_default="internal_transfer")
    payout_channel: Mapped[str] = mapped_column(String(64), nullable=False, default="internal", server_default="internal")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    requested_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    settled_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    requested_by: Mapped["User | None"] = relationship("User", foreign_keys=[requested_by_user_id])
    reviewed_by: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_user_id])
    settled_by: Mapped["User | None"] = relationship("User", foreign_keys=[settled_by_user_id])


__all__ = ["MarketTopup", "MarketTopupStatus"]
