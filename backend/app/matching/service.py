from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.matching.models import TradeExecution
from backend.app.orders.models import Order, OrderSide, OrderStatus

AMOUNT_QUANTUM = Decimal("0.0001")
ACTIVE_ORDER_STATUSES = (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)
VALID_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.OPEN: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REJECTED: set(),
}


class InvalidOrderTransitionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    price: Decimal
    quantity: Decimal
    order_count: int


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    player_id: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    executions: list[TradeExecution]
    execution_count: int
    total_notional: Decimal
    average_price: Decimal | None
    last_executed_at: datetime | None


class MatchingService:
    def build_order_book(self, session: Session, *, player_id: str) -> OrderBookSnapshot:
        orders = session.scalars(
            select(Order).where(
                Order.player_id == player_id,
                Order.status.in_(ACTIVE_ORDER_STATUSES),
            )
        ).all()
        bids = self._aggregate_order_levels(order for order in orders if order.side == OrderSide.BUY)
        asks = self._aggregate_order_levels(order for order in orders if order.side == OrderSide.SELL)
        return OrderBookSnapshot(
            player_id=player_id,
            bids=sorted(bids, key=lambda level: (-level.price, level.order_count)),
            asks=sorted(asks, key=lambda level: (level.price, level.order_count)),
            generated_at=datetime.now(timezone.utc),
        )

    def match_order(self, session: Session, *, order: Order) -> list[TradeExecution]:
        if order.status not in ACTIVE_ORDER_STATUSES or order.max_price is None:
            return []

        executions: list[TradeExecution] = []
        candidates = self._load_candidates(session, order=order)
        for candidate in candidates:
            if order.remaining_quantity <= Decimal("0.0000"):
                break
            if candidate.remaining_quantity <= Decimal("0.0000"):
                continue

            fill_quantity = self._normalize_amount(min(order.remaining_quantity, candidate.remaining_quantity))
            if fill_quantity <= Decimal("0.0000"):
                continue

            execution_price = self._execution_price(maker_order=candidate, taker_order=order)
            execution = TradeExecution(
                player_id=order.player_id,
                buy_order_id=order.id if order.side == OrderSide.BUY else candidate.id,
                sell_order_id=order.id if order.side == OrderSide.SELL else candidate.id,
                maker_order_id=candidate.id,
                taker_order_id=order.id,
                quantity=fill_quantity,
                price=execution_price,
                notional=self._normalize_amount(fill_quantity * execution_price),
            )
            session.add(execution)

            self.apply_fill(candidate, quantity=fill_quantity)
            self.apply_fill(order, quantity=fill_quantity)
            session.flush()
            executions.append(execution)

        return executions

    def apply_fill(self, order: Order, *, quantity: Decimal) -> Order:
        fill_quantity = self._normalize_amount(quantity)
        if fill_quantity <= Decimal("0.0000"):
            return order
        next_filled_quantity = self._normalize_amount(order.filled_quantity + fill_quantity)
        if next_filled_quantity > self._normalize_amount(order.quantity):
            raise InvalidOrderTransitionError(f"Order {order.id} cannot be overfilled.")

        order.filled_quantity = next_filled_quantity
        self.transition_order(order, self._status_for_filled_quantity(order))
        return order

    def transition_order(self, order: Order, next_status: OrderStatus) -> Order:
        if order.status == next_status:
            return order
        allowed_statuses = VALID_ORDER_TRANSITIONS[order.status]
        if next_status not in allowed_statuses:
            raise InvalidOrderTransitionError(
                f"Illegal order transition: {order.status.value} -> {next_status.value}."
            )
        order.status = next_status
        return order

    def build_execution_snapshot(self, session: Session, *, order_id: str) -> ExecutionSnapshot:
        executions = self.list_order_executions(session, order_id=order_id)
        total_notional = self._normalize_amount(sum((execution.notional for execution in executions), Decimal("0.0000")))
        total_quantity = self._normalize_amount(sum((execution.quantity for execution in executions), Decimal("0.0000")))
        average_price = None
        if total_quantity > Decimal("0.0000"):
            average_price = self._normalize_amount(total_notional / total_quantity)
        last_executed_at = executions[-1].created_at if executions else None
        return ExecutionSnapshot(
            executions=executions,
            execution_count=len(executions),
            total_notional=total_notional,
            average_price=average_price,
            last_executed_at=last_executed_at,
        )

    def list_order_executions(self, session: Session, *, order_id: str) -> list[TradeExecution]:
        return session.scalars(
            select(TradeExecution)
            .where(
                or_(
                    TradeExecution.buy_order_id == order_id,
                    TradeExecution.sell_order_id == order_id,
                )
            )
            .order_by(TradeExecution.created_at.asc(), TradeExecution.id.asc())
        ).all()

    def _load_candidates(self, session: Session, *, order: Order) -> list[Order]:
        opposite_side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
        statement = select(Order).where(
            Order.player_id == order.player_id,
            Order.side == opposite_side,
            Order.id != order.id,
            Order.status.in_(ACTIVE_ORDER_STATUSES),
            Order.max_price.is_not(None),
        )
        if order.side == OrderSide.BUY:
            statement = statement.where(Order.max_price <= order.max_price)
        else:
            statement = statement.where(Order.max_price >= order.max_price)
        candidates = session.scalars(statement).all()
        return sorted(candidates, key=lambda candidate: self._candidate_sort_key(order.side, candidate))

    def _aggregate_order_levels(self, orders: Iterable[Order]) -> list[OrderBookLevel]:
        levels: dict[Decimal, dict[str, Decimal | int]] = {}
        for order in orders:
            if order.max_price is None or order.remaining_quantity <= Decimal("0.0000"):
                continue
            level = levels.setdefault(
                self._normalize_amount(order.max_price),
                {"quantity": Decimal("0.0000"), "order_count": 0},
            )
            level["quantity"] = self._normalize_amount(level["quantity"] + order.remaining_quantity)
            level["order_count"] = int(level["order_count"]) + 1
        return [
            OrderBookLevel(
                price=price,
                quantity=self._normalize_amount(level["quantity"]),
                order_count=int(level["order_count"]),
            )
            for price, level in levels.items()
        ]

    def _candidate_sort_key(self, incoming_side: OrderSide, candidate: Order) -> tuple[Decimal, datetime, str]:
        price = self._normalize_amount(candidate.max_price)
        if incoming_side == OrderSide.BUY:
            return (price, candidate.created_at, candidate.id)
        return (-price, candidate.created_at, candidate.id)

    def _execution_price(self, *, maker_order: Order, taker_order: Order) -> Decimal:
        maker_price = maker_order.max_price if maker_order.max_price is not None else taker_order.max_price
        if maker_price is None:
            raise InvalidOrderTransitionError("Execution price could not be determined for an order without a limit price.")
        return self._normalize_amount(maker_price)

    def _status_for_filled_quantity(self, order: Order) -> OrderStatus:
        if order.filled_quantity <= Decimal("0.0000"):
            return OrderStatus.OPEN
        if order.remaining_quantity <= Decimal("0.0000"):
            return OrderStatus.FILLED
        return OrderStatus.PARTIALLY_FILLED

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
