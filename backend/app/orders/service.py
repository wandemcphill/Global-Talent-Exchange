from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.ingestion.models import Player
from app.ledger.models import LedgerEventType
from app.ledger.service import LedgerEventService
from app.matching.models import TradeExecution
from app.matching.service import ExecutionSnapshot, InvalidOrderTransitionError, MatchingService
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.orders.models import Order, OrderSide, OrderStatus
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


class OrderPlacementError(ValueError):
    pass


class PlayerNotFoundError(OrderPlacementError):
    pass


class OrderNotFoundError(OrderPlacementError):
    pass


class OrderService:
    def __init__(self, event_publisher: EventPublisher | None = None) -> None:
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        self.wallet_service = WalletService(event_publisher=self.event_publisher)
        self.ledger_event_service = LedgerEventService(event_publisher=self.event_publisher)
        self.matching_service = MatchingService()

    def place_order(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        side: OrderSide,
        quantity: Decimal,
        max_price: Decimal | None = None,
    ) -> Order:
        player = session.get(Player, player_id)
        if player is None:
            raise PlayerNotFoundError(f"Player {player_id} was not found.")
        if not player.is_tradable:
            raise OrderPlacementError(f"Player {player_id} is not tradable.")
        if max_price is None:
            raise OrderPlacementError("Limit price is required for player asset orders.")

        normalized_quantity = self._normalize_amount(quantity)
        normalized_max_price = self._normalize_amount(max_price)
        reserved_amount = Decimal("0.0000")
        if side == OrderSide.BUY:
            reserved_amount = self._normalize_amount(normalized_quantity * normalized_max_price)

        order = Order(
            user_id=user.id,
            player_id=player.id,
            side=side,
            quantity=normalized_quantity,
            filled_quantity=Decimal("0.0000"),
            max_price=normalized_max_price,
            currency=LedgerUnit.COIN,
            reserved_amount=reserved_amount,
            status=OrderStatus.OPEN,
        )
        session.add(order)
        session.flush()

        if order.side == OrderSide.BUY and order.reserved_amount > Decimal("0.0000"):
            self._reserve_buy_order_funds(session, order=order, user=user)

        self._append_order_event(
            session,
            order=order,
            event_type=LedgerEventType.ORDER_ACCEPTED,
            payload={
                "order_id": order.id,
                "player_id": player.id,
                "side": order.side.value,
                "quantity": str(order.quantity),
                "max_price": str(order.max_price),
                "reserved_amount": str(order.reserved_amount),
                "status": order.status.value,
            },
        )

        executions = self.matching_service.match_order(session, order=order)
        for execution in executions:
            self._settle_execution(session, execution=execution)

        session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="orders.accepted",
                payload={
                    "order_id": order.id,
                    "user_id": user.id,
                    "player_id": player.id,
                    "side": order.side.value,
                    "quantity": str(order.quantity),
                    "status": order.status.value,
                    "reserved_amount": str(order.reserved_amount),
                },
            )
        )
        return order

    def cancel_order(self, session: Session, *, order_id: str, user: User) -> Order:
        order = self.get_order(session, order_id=order_id, user=user)
        if order.status not in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}:
            raise InvalidOrderTransitionError(
                f"Only open or partially filled orders can be cancelled. Current status: {order.status.value}."
            )

        released_amount = Decimal("0.0000")
        if order.side == OrderSide.BUY and order.reserved_amount > Decimal("0.0000"):
            released_amount = self._release_reserved_funds(
                session,
                order=order,
                amount=order.reserved_amount,
                reason="cancel",
            )

        self.matching_service.transition_order(order, OrderStatus.CANCELLED)
        self._append_order_event(
            session,
            order=order,
            event_type=LedgerEventType.ORDER_CANCELLED,
            payload={
                "order_id": order.id,
                "player_id": order.player_id,
                "released_amount": str(released_amount),
                "remaining_quantity": str(order.remaining_quantity),
                "status": order.status.value,
            },
        )
        session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="orders.cancelled",
                payload={
                    "order_id": order.id,
                    "user_id": order.user_id,
                    "status": order.status.value,
                },
            )
        )
        return order

    def get_order(self, session: Session, *, order_id: str, user: User | None = None) -> Order:
        order = session.get(Order, order_id)
        if order is None or (user is not None and order.user_id != user.id):
            raise OrderNotFoundError(f"Order {order_id} was not found.")
        return order

    def get_order_book(self, session: Session, *, player_id: str):
        return self.matching_service.build_order_book(session, player_id=player_id)

    def get_execution_snapshot(self, session: Session, *, order_id: str) -> ExecutionSnapshot:
        return self.matching_service.build_execution_snapshot(session, order_id=order_id)

    def list_orders(
        self,
        session: Session,
        *,
        user: User,
        statuses: Sequence[OrderStatus] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[tuple[Order, ...], int]:
        status_filter = tuple(statuses or ())
        filters = [Order.user_id == user.id]
        if status_filter:
            filters.append(Order.status.in_(status_filter))

        total = session.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
        orders = session.scalars(
            select(Order)
            .where(*filters)
            .order_by(Order.updated_at.desc(), Order.created_at.desc(), Order.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return tuple(orders), total

    def _reserve_buy_order_funds(self, session: Session, *, order: Order, user: User) -> None:
        entries = self.wallet_service.reserve_order_funds(
            session,
            user=user,
            amount=order.reserved_amount,
            reference=order.id,
            description=f"Reserve funds for order {order.id}",
            unit=LedgerUnit.COIN,
            source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
        )
        if not entries:
            return
        order.hold_transaction_id = entries[0].transaction_id
        self._append_order_event(
            session,
            order=order,
            event_type=LedgerEventType.ORDER_FUNDS_RESERVED,
            payload={
                "order_id": order.id,
                "player_id": order.player_id,
                "reserved_amount": str(order.reserved_amount),
                "transaction_id": order.hold_transaction_id,
            },
        )

    def _settle_execution(self, session: Session, *, execution: TradeExecution) -> None:
        buy_order = self.get_order(session, order_id=execution.buy_order_id)
        sell_order = self.get_order(session, order_id=execution.sell_order_id)
        buyer = session.get(User, buy_order.user_id)
        seller = session.get(User, sell_order.user_id)
        if buyer is None or seller is None:
            raise OrderPlacementError("Execution references a missing user.")

        buyer_escrow = self.wallet_service.get_user_escrow_account(session, buyer, LedgerUnit.COIN)
        seller_account = self.wallet_service.get_user_account(session, seller, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=buyer_escrow, amount=-execution.notional, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
                LedgerPosting(account=seller_account, amount=execution.notional, source_tag=LedgerSourceTag.PLAYER_CARD_SALE),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            reference=execution.id,
            description=f"Trade settlement for execution {execution.id}",
            actor=buyer,
        )

        price_improvement = Decimal("0.0000")
        if buy_order.max_price is not None and buy_order.max_price > execution.price:
            price_improvement = self._normalize_amount((buy_order.max_price - execution.price) * execution.quantity)
        if price_improvement > Decimal("0.0000"):
            self._release_reserved_funds(
                session,
                order=buy_order,
                amount=price_improvement,
                reason="price_improvement",
            )

        buy_order.reserved_amount = self._reserved_amount_for_order(buy_order)
        self._append_execution_events(session, buy_order=buy_order, sell_order=sell_order, execution=execution)
        self.event_publisher.publish(
            DomainEvent(
                name="orders.executed",
                payload={
                    "execution_id": execution.id,
                    "player_id": execution.player_id,
                    "buy_order_id": buy_order.id,
                    "sell_order_id": sell_order.id,
                    "quantity": str(execution.quantity),
                    "price": str(execution.price),
                },
            )
        )

    def _append_execution_events(
        self,
        session: Session,
        *,
        buy_order: Order,
        sell_order: Order,
        execution: TradeExecution,
    ) -> None:
        shared_payload = {
            "execution_id": execution.id,
            "player_id": execution.player_id,
            "price": str(execution.price),
            "quantity": str(execution.quantity),
            "notional": str(execution.notional),
            "maker_order_id": execution.maker_order_id,
            "taker_order_id": execution.taker_order_id,
        }
        self._append_order_event(
            session,
            order=buy_order,
            event_type=LedgerEventType.ORDER_EXECUTED,
            payload={
                **shared_payload,
                "order_id": buy_order.id,
                "counterparty_order_id": sell_order.id,
                "remaining_quantity": str(buy_order.remaining_quantity),
                "status": buy_order.status.value,
            },
        )
        self._append_order_event(
            session,
            order=sell_order,
            event_type=LedgerEventType.ORDER_EXECUTED,
            payload={
                **shared_payload,
                "order_id": sell_order.id,
                "counterparty_order_id": buy_order.id,
                "remaining_quantity": str(sell_order.remaining_quantity),
                "status": sell_order.status.value,
            },
        )

    def _append_order_event(
        self,
        session: Session,
        *,
        order: Order,
        event_type: LedgerEventType,
        payload: dict[str, str | None],
    ) -> None:
        self.ledger_event_service.append_event(
            session,
            aggregate_type="order",
            aggregate_id=order.id,
            user_id=order.user_id,
            event_type=event_type,
            payload=payload,
        )

    def _release_reserved_funds(
        self,
        session: Session,
        *,
        order: Order,
        amount: Decimal,
        reason: str,
    ) -> Decimal:
        release_amount = self._normalize_amount(amount)
        if release_amount <= Decimal("0.0000"):
            return Decimal("0.0000")

        user = session.get(User, order.user_id)
        if user is None:
            raise OrderPlacementError("Order references a missing user.")
        available_account = self.wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        escrow_account = self.wallet_service.get_user_escrow_account(session, user, LedgerUnit.COIN)
        entries = self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-release_amount, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
                LedgerPosting(account=available_account, amount=release_amount, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
            ],
            reason=LedgerEntryReason.WITHDRAWAL_SETTLEMENT,
            reference=order.id,
            description=f"Release reserved funds for order {order.id}",
            actor=user,
        )
        order.reserved_amount = self._normalize_amount(order.reserved_amount - release_amount)
        self._append_order_event(
            session,
            order=order,
            event_type=LedgerEventType.ORDER_RELEASED,
            payload={
                "order_id": order.id,
                "player_id": order.player_id,
                "released_amount": str(release_amount),
                "reason": reason,
                "transaction_id": entries[0].transaction_id,
                "remaining_quantity": str(order.remaining_quantity),
            },
        )
        return release_amount

    def _reserved_amount_for_order(self, order: Order) -> Decimal:
        if order.side != OrderSide.BUY or order.max_price is None:
            return Decimal("0.0000")
        return self._normalize_amount(order.remaining_quantity * order.max_price)

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
