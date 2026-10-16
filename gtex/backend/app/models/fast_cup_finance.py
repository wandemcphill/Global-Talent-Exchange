from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FastCupEscrowStatus(StrEnum):
    NONE = "none"
    RESERVED = "reserved"
    ESCROWED = "escrowed"
    REFUNDED = "refunded"
    RELEASED = "released"
    FAILED = "failed"


class FastCupPayoutStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REVERSED = "reversed"


class FastCupRegistration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fast_cup_registrations"
    __table_args__ = (
        UniqueConstraint("cup_id", "club_id", name="uq_fast_cup_registrations_cup_club"),
    )

    cup_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    lineup_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entry_fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0"), server_default="0")
    entry_fee_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="credit", server_default="credit")
    escrow_status: Mapped[FastCupEscrowStatus] = mapped_column(
        String(24),
        nullable=False,
        default=FastCupEscrowStatus.NONE,
        server_default=FastCupEscrowStatus.NONE.value,
        index=True,
    )
    wallet_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FastCupPayout(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "fast_cup_payouts"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_fast_cup_payouts_idempotency_key"),
        UniqueConstraint("cup_id", "registration_id", "finish", name="uq_fast_cup_payouts_cup_registration_finish"),
    )

    cup_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    registration_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fast_cup_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    finish: Mapped[str] = mapped_column(String(32), nullable=False)
    payout_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0"), server_default="0")
    payout_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="credit", server_default="credit")
    payout_status: Mapped[FastCupPayoutStatus] = mapped_column(
        String(24),
        nullable=False,
        default=FastCupPayoutStatus.PENDING,
        server_default=FastCupPayoutStatus.PENDING.value,
        index=True,
    )
    wallet_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "FastCupEscrowStatus",
    "FastCupPayout",
    "FastCupPayoutStatus",
    "FastCupRegistration",
]
