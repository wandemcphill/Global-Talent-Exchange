from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.models.user import User


class RewardSettlementStatus(StrEnum):
    SETTLED = "settled"
    REVERSED = "reversed"


class RewardSettlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reward_settlements"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    competition_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reward_source: Mapped[str] = mapped_column(String(64), nullable=False, default="gtex_promotional_pool", server_default="gtex_promotional_pool")
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0.0000")
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ledger_unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False, default=LedgerUnit.CREDIT)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RewardSettlementStatus] = mapped_column(
        Enum(RewardSettlementStatus, name="reward_settlement_status", native_enum=False),
        nullable=False,
        default=RewardSettlementStatus.SETTLED,
        server_default="settled",
    )
    settled_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    settled_by_user: Mapped["User | None"] = relationship(foreign_keys=[settled_by_user_id])
