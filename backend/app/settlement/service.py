from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.wallet import LedgerAccount, LedgerEntry
from backend.app.orders.models import Order, OrderStatus
from backend.app.risk.service import RiskControlService, TradeSide
from backend.app.wallets.service import WalletService


class SettlementError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TradeExecution:
    execution_id: str
    player_id: str
    side: TradeSide | str
    quantity: Decimal
    price: Decimal
    order_id: str | None = None
    reserve_before_settlement: bool = False
    use_reserved_balance: bool = False


@dataclass(frozen=True, slots=True)
class SettlementResult:
    execution_id: str
    order_id: str | None
    player_id: str
    side: str
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    cash_entries: list[LedgerEntry]
    position_entries: list[LedgerEntry]


@dataclass(slots=True)
class SettlementService:
    wallet_service: WalletService = field(default_factory=WalletService)
    risk_service: RiskControlService = field(default_factory=RiskControlService)

    def __post_init__(self) -> None:
        if self.risk_service.wallet_service is not self.wallet_service:
            self.risk_service = RiskControlService(wallet_service=self.wallet_service)

    def reserve_execution_requirements(
        self,
        session: Session,
        *,
        user: User,
        execution: TradeExecution,
    ) -> list[LedgerEntry]:
        side, quantity, _price, gross_amount = self.risk_service.validate_trade(
            session,
            user,
            player_id=execution.player_id,
            side=execution.side,
            quantity=execution.quantity,
            price=execution.price,
        )
        reference = execution.order_id or execution.execution_id
        if side is TradeSide.BUY:
            return self.wallet_service.reserve_order_funds(
                session,
                user=user,
                amount=gross_amount,
                reference=reference,
                description=f"Reserve funds for settlement {execution.execution_id}",
            )
        return self.wallet_service.reserve_position_units(
            session,
            user=user,
            player_id=execution.player_id,
            quantity=quantity,
            reference=reference,
            description=f"Reserve units for settlement {execution.execution_id}",
        )

    def settle_order_execution(
        self,
        session: Session,
        *,
        user: User,
        execution_id: str,
        order_id: str,
        quantity: Decimal,
        price: Decimal,
    ) -> SettlementResult:
        order = session.get(Order, order_id)
        if order is None:
            raise SettlementError(f"Order {order_id} was not found.")
        if order.user_id != user.id:
            raise SettlementError(f"Order {order_id} does not belong to user {user.id}.")

        return self.settle_execution(
            session,
            user=user,
            execution=TradeExecution(
                execution_id=execution_id,
                order_id=order.id,
                player_id=order.player_id,
                side=order.side.value,
                quantity=quantity,
                price=price,
                use_reserved_balance=bool(order.hold_transaction_id),
            ),
        )

    def settle_execution(
        self,
        session: Session,
        *,
        user: User,
        execution: TradeExecution,
    ) -> SettlementResult:
        self.risk_service.ensure_execution_not_settled(session, execution.execution_id)
        order = session.get(Order, execution.order_id) if execution.order_id else None
        use_reserved_balance = execution.use_reserved_balance or bool(order is not None and order.hold_transaction_id)

        if execution.reserve_before_settlement and not use_reserved_balance:
            self.reserve_execution_requirements(session, user=user, execution=execution)
            use_reserved_balance = True

        side, quantity, price, gross_amount = self.risk_service.validate_trade(
            session,
            user,
            player_id=execution.player_id,
            side=execution.side,
            quantity=execution.quantity,
            price=execution.price,
            use_reserved_balance=use_reserved_balance,
        )

        reference = execution.order_id or execution.execution_id
        if side is TradeSide.BUY:
            cash_entries = (
                self.wallet_service.settle_reserved_funds(
                    session,
                    user=user,
                    amount=gross_amount,
                    reference=reference,
                    description=f"Settle buy execution {execution.execution_id}",
                    external_reference=execution.execution_id,
                )
                if use_reserved_balance
                else self.wallet_service.settle_available_funds(
                    session,
                    user=user,
                    amount=gross_amount,
                    reference=reference,
                    description=f"Settle buy execution {execution.execution_id}",
                    external_reference=execution.execution_id,
                )
            )
            position_entries = self.wallet_service.credit_position_units(
                session,
                user=user,
                player_id=execution.player_id,
                quantity=quantity,
                reference=reference,
                description=f"Receive units for execution {execution.execution_id}",
                external_reference=execution.execution_id,
            )
            self._release_buy_remainder_if_needed(
                session,
                user=user,
                order=order,
            )
        else:
            position_entries = (
                self.wallet_service.settle_reserved_position_units(
                    session,
                    user=user,
                    player_id=execution.player_id,
                    quantity=quantity,
                    reference=reference,
                    description=f"Settle sell execution {execution.execution_id}",
                    external_reference=execution.execution_id,
                )
                if use_reserved_balance
                else self.wallet_service.settle_available_position_units(
                    session,
                    user=user,
                    player_id=execution.player_id,
                    quantity=quantity,
                    reference=reference,
                    description=f"Settle sell execution {execution.execution_id}",
                    external_reference=execution.execution_id,
                )
            )
            cash_entries = self.wallet_service.credit_trade_proceeds(
                session,
                user=user,
                amount=gross_amount,
                reference=reference,
                description=f"Credit sell execution {execution.execution_id}",
                external_reference=execution.execution_id,
            )

        if order is not None and self._is_order_fully_settled(session, order=order):
            order.status = OrderStatus.FILLED
            session.flush()

        return SettlementResult(
            execution_id=execution.execution_id,
            order_id=execution.order_id,
            player_id=execution.player_id,
            side=side.value,
            quantity=quantity,
            price=price,
            gross_amount=gross_amount,
            cash_entries=cash_entries,
            position_entries=position_entries,
        )

    def _release_buy_remainder_if_needed(
        self,
        session: Session,
        *,
        user: User,
        order: Order | None,
    ) -> None:
        if order is None or not order.hold_transaction_id:
            return
        if not self._is_order_fully_settled(session, order=order):
            return

        reserved_amount = self.wallet_service._normalize_amount(order.reserved_amount)
        settled_gross = self._settled_gross_for_order(session, order)
        remaining_reserved_amount = self.wallet_service._normalize_amount(reserved_amount - settled_gross)
        if remaining_reserved_amount <= Decimal("0.0000"):
            return

        self.wallet_service.release_reserved_funds(
            session,
            user=user,
            amount=remaining_reserved_amount,
            reference=order.id,
            description=f"Release unused reserve for order {order.id}",
        )

    def _is_order_fully_settled(
        self,
        session: Session,
        *,
        order: Order,
    ) -> bool:
        settled_quantity = self._settled_quantity_for_order(session, order)
        return settled_quantity >= self.wallet_service._normalize_amount(order.quantity)

    def _settled_quantity_for_order(self, session: Session, order: Order) -> Decimal:
        rows = session.execute(
            select(LedgerEntry.amount)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerEntry.reason == self.wallet_service.trade_settlement_reason,
                LedgerEntry.reference == order.id,
                LedgerEntry.amount > Decimal("0.0000"),
                LedgerAccount.code == self.wallet_service._position_account_code(order.user_id, order.player_id),
            )
        ).all()
        total = sum((Decimal(row[0]) for row in rows), start=Decimal("0.0000"))
        return self.wallet_service._normalize_amount(total)

    def _settled_gross_for_order(self, session: Session, order: Order) -> Decimal:
        rows = session.execute(
            select(LedgerEntry.amount)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerEntry.reason == self.wallet_service.trade_settlement_reason,
                LedgerEntry.reference == order.id,
                LedgerEntry.amount < Decimal("0.0000"),
                LedgerAccount.code == self.wallet_service._user_escrow_account_code(order.user_id, order.currency),
            )
        ).all()
        total = sum((abs(Decimal(row[0])) for row in rows), start=Decimal("0.0000"))
        return self.wallet_service._normalize_amount(total)
