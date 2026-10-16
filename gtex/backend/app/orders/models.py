from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.wallet import LedgerUnit


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exchange_orders"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    side: Mapped[OrderSide] = mapped_column(
        Enum(
            OrderSide,
            name="order_side",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    currency: Mapped[LedgerUnit] = mapped_column(
        Enum(
            LedgerUnit,
            name="ledger_unit",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=LedgerUnit.COIN,
    )
    reserved_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=OrderStatus.OPEN,
    )
    hold_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    @property
    def remaining_quantity(self) -> Decimal:
        return Decimal(self.quantity) - Decimal(self.filled_quantity)

    @property
    def is_active(self) -> bool:
        return self.status in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}
