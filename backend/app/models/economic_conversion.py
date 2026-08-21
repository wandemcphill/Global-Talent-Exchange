from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.wallet import LedgerUnit, PayoutRequest


class EconomicConversionStatus(StrEnum):
    PENDING = "pending"
    SETTLED = "settled"
    REVERSED = "reversed"
    FAILED = "failed"


class EconomicConversionType(StrEnum):
    FANCOIN_GIFT = "fancoin_gift"
    FUTURE = "future"


class EconomicConversion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Durable bridge between unit-specific ledger accounting and a cross-currency event."""

    __tablename__ = "economic_conversions"
    __table_args__ = (
        UniqueConstraint("conversion_key", name="uq_economic_conversions_conversion_key"),
        UniqueConstraint("idempotency_key", name="uq_economic_conversions_idempotency_key"),
    )

    conversion_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    conversion_type: Mapped[EconomicConversionType] = mapped_column(
        Enum(EconomicConversionType, name="economic_conversion_type", native_enum=False),
        nullable=False,
        default=EconomicConversionType.FANCOIN_GIFT,
        server_default=EconomicConversionType.FANCOIN_GIFT.value,
    )
    status: Mapped[EconomicConversionStatus] = mapped_column(
        Enum(EconomicConversionStatus, name="economic_conversion_status", native_enum=False),
        nullable=False,
        default=EconomicConversionStatus.PENDING,
        server_default=EconomicConversionStatus.PENDING.value,
        index=True,
    )

    source_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gift_transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gift_transactions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    source_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="economic_conversion_source_unit", native_enum=False),
        nullable=False,
    )
    destination_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="economic_conversion_destination_unit", native_enum=False),
        nullable=False,
    )
    source_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    platform_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), nullable=False, default=0, server_default="0"
    )
    destination_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), nullable=False
    )
    conversion_rate: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=1, server_default="1"
    )

    source_ledger_transaction_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    destination_ledger_transaction_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    fee_rule_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fee_rule_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


def _assert_withdrawable_payout_currency(_: Any, __: Any, payout: PayoutRequest) -> None:
    if payout.unit is LedgerUnit.CREDIT or str(payout.unit) == LedgerUnit.CREDIT.value:
        raise ValueError(
            "FanCoin is never withdrawable. Withdrawal requests must use GTEX Coin."
        )


event.listen(
    PayoutRequest,
    "before_insert",
    _assert_withdrawable_payout_currency,
    propagate=True,
)
event.listen(
    PayoutRequest,
    "before_update",
    _assert_withdrawable_payout_currency,
    propagate=True,
)


__all__ = ["EconomicConversion", "EconomicConversionStatus", "EconomicConversionType"]
