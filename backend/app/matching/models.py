from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class TradeExecution(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "trade_executions"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    buy_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exchange_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sell_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exchange_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    maker_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exchange_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    taker_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exchange_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)


@event.listens_for(TradeExecution, "before_update", propagate=True)
def _prevent_trade_execution_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Trade executions are append-only and cannot be updated.")


@event.listens_for(TradeExecution, "before_delete", propagate=True)
def _prevent_trade_execution_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Trade executions are append-only and cannot be deleted.")
