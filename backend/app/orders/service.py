from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.core.config import Settings, get_settings
from backend.app.ingestion.models import Player
from backend.app.ledger.models import LedgerEventType
from backend.app.ledger.service import LedgerEventService
from backend.app.matching.models import TradeExecution
from backend.app.matching.service import ExecutionSnapshot, InvalidOrderTransitionError, MatchingService
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.orders.admin_buyback import AdminBuybackExecution, AdminBuybackPreview, AdminBuybackService
from backend.app.orders.models import Order, OrderSide, OrderStatus
from backend.app.risk.service import RiskControlService, RiskValidationError
from backend.app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


class OrderPlacementError(ValueError):
    pass


class PlayerNotFoundError(OrderPlacementError):
    pass


class OrderNotFoundError(OrderPlacementError):
    pass


class OrderService:
    def __init__(
        self,
        event_publisher: EventPublisher | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        self.settings = settings or get_settings()
        self.wallet_service = WalletService(event_publisher=self.event_publisher)
        self.ledger_event_service = LedgerEventService(event_publisher=self.event_publisher)
        self.matching_service = MatchingService()
        self.risk_service = RiskControlService(wallet_service=self.wallet_service)
        self.admin_buyback_service = AdminBuybackService(
            settings=self.settings,
            wallet_service=self.wallet_service,
        )

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
        try:
            self.risk_service.validate_trade(
                session,
                user,
                player_id=player.id,
                side=side,
                quantity=normalized_quantity,
                price=normalized_max_price,
            )
        except RiskValidationError as exc:
            raise OrderPlacementError(str(exc)) from exc
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
            currency=LedgerUnit.CREDIT,
            reserved_amount=reserved_amount,
            status=OrderStatus.OPEN,
        )
        session.add(order)
        session.flush()

        if order.side == OrderSide.BUY and order.reserved_amount > Decimal("0.0000"):
            self._reserve_buy_order_funds(session, order=order, user=user)
        elif order.side == OrderSide.SELL and order.quantity > Decimal("0.0000"):
            self._reserve_sell_order_units(session, order=order, user=user)

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
        elif order.side == OrderSide.SELL and order.hold_transaction_id:
            self._release_reserved_position_units(
                session,
                order=order,
                quantity=order.remaining_quantity,
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
                "released_quantity": str(order.remaining_quantity if order.side == OrderSide.SELL else Decimal("0.0000")),
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

    def preview_admin_buyback(
        self,
        session: Session,
        *,
        order_id: str,
        user: User,
    ) -> AdminBuybackPreview:
        order = self.get_order(session, order_id=order_id, user=user)
        return self.admin_buyback_service.preview(session, user=user, order=order)

    def execute_admin_buyback(
        self,
        session: Session,
        *,
        order_id: str,
        user: User,
    ) -> tuple[Order, AdminBuybackExecution]:
        order = self.get_order(session, order_id=order_id, user=user)
        preview = self.admin_buyback_service.preview(session, user=user, order=order)
        if not preview.eligible:
            raise OrderPlacementError(preview.message)

        remaining_quantity = self._normalize_amount(order.remaining_quantity)
        execution_id = f"admin-buyback:{order.id}:{uuid4()}"
        if order.hold_transaction_id:
            self.wallet_service.settle_reserved_position_units(
                session,
                user=user,
                player_id=order.player_id,
                quantity=remaining_quantity,
                reference=order.id,
                description=f"Admin buyback settled sell order {order.id}",
                external_reference=execution_id,
            )
        else:
            self.wallet_service.settle_available_position_units(
                session,
                user=user,
                player_id=order.player_id,
                quantity=remaining_quantity,
                reference=order.id,
                description=f"Admin buyback settled sell order {order.id}",
                external_reference=execution_id,
            )
        self.wallet_service.credit_trade_proceeds(
            session,
            user=user,
            amount=preview.admin_total,
            reference=order.id,
            description=f"Admin buyback credited sell order {order.id}",
            external_reference=execution_id,
        )

        order.filled_quantity = self._normalize_amount(order.quantity)
        self.matching_service.transition_order(order, OrderStatus.FILLED)
        self._append_order_event(
            session,
            order=order,
            event_type=LedgerEventType.ORDER_EXECUTED,
            payload={
                "execution_id": execution_id,
                "player_id": order.player_id,
                "price": str(preview.admin_unit_price),
                "quantity": str(remaining_quantity),
                "notional": str(preview.admin_total),
                "order_id": order.id,
                "counterparty_order_id": "admin_buyback",
                "counterparty_type": "admin_buyback",
                "remaining_quantity": str(order.remaining_quantity),
                "status": order.status.value,
                "buyback_band": preview.buyback_band,
                "payout_ratio": str(preview.payout_ratio),
            },
        )
        session.flush()
        settled_at = datetime.now(timezone.utc)
        self.event_publisher.publish(
            DomainEvent(
                name="orders.admin_buyback.executed",
                payload={
                    "execution_id": execution_id,
                    "order_id": order.id,
                    "user_id": user.id,
                    "player_id": order.player_id,
                    "quantity": str(remaining_quantity),
                    "price": str(preview.admin_unit_price),
                    "notional": str(preview.admin_total),
                    "buyback_band": preview.buyback_band,
                },
            )
        )
        return order, AdminBuybackExecution(
            preview=preview,
            execution_id=execution_id,
            settled_at=settled_at,
        )

    def _reserve_buy_order_funds(self, session: Session, *, order: Order, user: User) -> None:
        entries = self.wallet_service.reserve_order_funds(
            session,
            user=user,
            amount=order.reserved_amount,
            reference=order.id,
            description=f"Reserve funds for order {order.id}",
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

    def _reserve_sell_order_units(self, session: Session, *, order: Order, user: User) -> None:
        entries = self.wallet_service.reserve_position_units(
            session,
            user=user,
            player_id=order.player_id,
            quantity=order.quantity,
            reference=order.id,
            description=f"Reserve units for order {order.id}",
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
                "reserved_quantity": str(order.quantity),
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

        if buy_order.hold_transaction_id:
            self.wallet_service.settle_reserved_funds(
                session,
                user=buyer,
                amount=execution.notional,
                reference=buy_order.id,
                description=f"Trade settlement for execution {execution.id}",
                external_reference=execution.id,
            )
        else:
            self.wallet_service.settle_available_funds(
                session,
                user=buyer,
                amount=execution.notional,
                reference=buy_order.id,
                description=f"Trade settlement for execution {execution.id}",
                external_reference=execution.id,
            )

        if sell_order.hold_transaction_id:
            self.wallet_service.settle_reserved_position_units(
                session,
                user=seller,
                player_id=sell_order.player_id,
                quantity=execution.quantity,
                reference=sell_order.id,
                description=f"Trade settlement for execution {execution.id}",
                external_reference=execution.id,
            )
        else:
            self.wallet_service.settle_available_position_units(
                session,
                user=seller,
                player_id=sell_order.player_id,
                quantity=execution.quantity,
                reference=sell_order.id,
                description=f"Trade settlement for execution {execution.id}",
                external_reference=execution.id,
            )

        self.wallet_service.credit_trade_proceeds(
            session,
            user=seller,
            amount=execution.notional,
            reference=sell_order.id,
            description=f"Trade settlement for execution {execution.id}",
            external_reference=execution.id,
        )
        self.wallet_service.credit_position_units(
            session,
            user=buyer,
            player_id=buy_order.player_id,
            quantity=execution.quantity,
            reference=buy_order.id,
            description=f"Trade settlement for execution {execution.id}",
            external_reference=execution.id,
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
        available_account = self.wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
        escrow_account = self.wallet_service.get_user_escrow_account(session, user, LedgerUnit.CREDIT)
        entries = self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-release_amount),
                LedgerPosting(account=available_account, amount=release_amount),
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

    def _release_reserved_position_units(
        self,
        session: Session,
        *,
        order: Order,
        quantity: Decimal,
    ) -> Decimal:
        release_quantity = self._normalize_amount(quantity)
        if release_quantity <= Decimal("0.0000"):
            return Decimal("0.0000")

        user = session.get(User, order.user_id)
        if user is None:
            raise OrderPlacementError("Order references a missing user.")
        entries = self.wallet_service.release_reserved_position_units(
            session,
            user=user,
            player_id=order.player_id,
            quantity=release_quantity,
            reference=order.id,
            description=f"Release reserved units for order {order.id}",
        )
        self._append_order_event(
            session,
            order=order,
            event_type=LedgerEventType.ORDER_RELEASED,
            payload={
                "order_id": order.id,
                "player_id": order.player_id,
                "released_quantity": str(release_quantity),
                "transaction_id": entries[0].transaction_id if entries else None,
                "remaining_quantity": str(order.remaining_quantity),
            },
        )
        return release_quantity

    def _reserved_amount_for_order(self, order: Order) -> Decimal:
        if order.side != OrderSide.BUY or order.max_price is None:
            return Decimal("0.0000")
        return self._normalize_amount(order.remaining_quantity * order.max_price)

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
