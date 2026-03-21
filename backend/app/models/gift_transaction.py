from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.models.economy_config import GiftCatalogItem
    from app.models.user import User


class GiftTransactionStatus(StrEnum):
    SETTLED = "settled"
    REFUNDED = "refunded"


class GiftTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gift_transactions"

    sender_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gift_catalog_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("gift_catalog.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=1, server_default="1.0000")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    platform_rake_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    recipient_net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="user_hosted", server_default="user_hosted")
    ledger_unit: Mapped[LedgerUnit] = mapped_column(Enum(LedgerUnit, name="ledger_unit", native_enum=False), nullable=False, default=LedgerUnit.CREDIT)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[GiftTransactionStatus] = mapped_column(
        Enum(GiftTransactionStatus, name="gift_transaction_status", native_enum=False),
        nullable=False,
        default=GiftTransactionStatus.SETTLED,
        server_default="settled",
    )

    sender_user: Mapped["User"] = relationship(foreign_keys=[sender_user_id])
    recipient_user: Mapped["User"] = relationship(foreign_keys=[recipient_user_id])
    gift_catalog_item: Mapped["GiftCatalogItem"] = relationship()
