from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.trader import (
    TraderMarket,
    TraderOrder,
    TraderOrderSide,
    TraderOrderStatus,
    TraderTrade,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService

QUANTUM = Decimal("0.0001")
TRADER_TRADE_FEE_BPS = 50  # taker fee, basis points
_BPS = Decimal("10000")
_RESTING_STATUSES = (TraderOrderStatus.OPEN, TraderOrderStatus.PARTIALLY_FILLED)


class TraderMatchingError(ValueError):
    pass


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(QUANTUM)


def _position_key(market_id: str) -> str:
    return f"trader:{market_id}"


def _remaining(order: TraderOrder) -> Decimal:
    return _q(order.quantity - order.filled_quantity)


@dataclass(slots=True)
class TraderMatchingEngine:
    session: Session
    wallet_service: WalletService

    def reserve_for_order(self, user: User, order: TraderOrder, market: TraderMarket) -> None:
        if order.side is TraderOrderSide.BUY:
            cap = order.limit_price if order.limit_price is not None else Decimal(market.price)
            self.wallet_service.reserve_order_funds(
                self.session,
                user=user,
                amount=_q(order.quantity * cap),
                reference=order.id,
                description=f"Reserve coins for trader order {order.id}",
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.TRADER_ORDER_BUY,
            )
        else:
            self.wallet_service.reserve_position_units(
                self.session,
                user=user,
                player_id=_position_key(order.market_id),
                quantity=order.quantity,
                reference=order.id,
                description=f"Reserve units for trader order {order.id}",
                source_tag=LedgerSourceTag.TRADER_ORDER_SELL,
            )

    def release_remaining_reservation(self, user: User, order: TraderOrder, market: TraderMarket) -> None:
        remaining = _remaining(order)
        if remaining <= QUANTUM and remaining <= Decimal("0.0000"):
            return
        if remaining <= Decimal("0.0000"):
            return
        if order.side is TraderOrderSide.BUY:
            cap = order.limit_price if order.limit_price is not None else Decimal(market.price)
            self.wallet_service.release_reserved_funds(
                self.session,
                user=user,
                amount=_q(remaining * cap),
                reference=order.id,
                description=f"Release unmatched coins for trader order {order.id}",
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.TRADER_ORDER_BUY,
            )
        else:
            self.wallet_service.release_reserved_position_units(
                self.session,
                user=user,
                player_id=_position_key(order.market_id),
                quantity=remaining,
                reference=order.id,
                description=f"Release unmatched units for trader order {order.id}",
            )

    def match(self, taker_user: User, order: TraderOrder, market: TraderMarket) -> list[TraderTrade]:
        opposite = (
            TraderOrderSide.SELL if order.side is TraderOrderSide.BUY else TraderOrderSide.BUY
        )
        stmt = (
            select(TraderOrder)
            .where(
                TraderOrder.market_id == order.market_id,
                TraderOrder.side == opposite,
                TraderOrder.status.in_(_RESTING_STATUSES),
                TraderOrder.user_id != order.user_id,
            )
            .with_for_update()
        )
        if order.side is TraderOrderSide.BUY:
            stmt = stmt.order_by(TraderOrder.limit_price.asc(), TraderOrder.created_at.asc())
        else:
            stmt = stmt.order_by(TraderOrder.limit_price.desc(), TraderOrder.created_at.asc())

        trades: list[TraderTrade] = []
        for maker in self.session.scalars(stmt).all():
            if _remaining(order) <= Decimal("0.0000"):
                break
            if maker.limit_price is None:
                continue
            if not self._crosses(order, maker):
                break
            trade = self._execute_fill(taker_user, order, maker, market)
            if trade is not None:
                trades.append(trade)
        return trades

    def _crosses(self, taker: TraderOrder, maker: TraderOrder) -> bool:
        price = Decimal(maker.limit_price)
        if taker.side is TraderOrderSide.BUY:
            return taker.limit_price is None or Decimal(taker.limit_price) >= price
        return taker.limit_price is None or Decimal(taker.limit_price) <= price

    def _execute_fill(
        self, taker_user: User, taker: TraderOrder, maker: TraderOrder, market: TraderMarket
    ) -> TraderTrade | None:
        qty = min(_remaining(taker), _remaining(maker))
        qty = _q(qty)
        if qty <= Decimal("0.0000"):
            return None
        price = _q(Decimal(maker.limit_price))
        notional = _q(qty * price)

        if taker.side is TraderOrderSide.BUY:
            buy_order, sell_order = taker, maker
            buyer, seller = taker_user, self._user(maker.user_id)
        else:
            buy_order, sell_order = maker, taker
            buyer, seller = self._user(maker.user_id), taker_user

        fee = _q(notional * Decimal(TRADER_TRADE_FEE_BPS) / _BPS)
        ref = f"{buy_order.id}:{sell_order.id}"

        # Cash leg: buyer escrow -> liquidity, liquidity -> seller (net of fee), liquidity -> fee account.
        self.wallet_service.settle_reserved_funds(
            self.session,
            user=buyer,
            amount=notional,
            reference=ref,
            description=f"Settle coins for trade {ref}",
            external_reference=ref,
            unit=LedgerUnit.COIN,
            source_tag=LedgerSourceTag.TRADER_ORDER_BUY,
        )
        buyer_cap = buy_order.limit_price if buy_order.limit_price is not None else Decimal(market.price)
        excess = _q((Decimal(buyer_cap) - price) * qty)
        if excess > Decimal("0.0000"):
            self.wallet_service.release_reserved_funds(
                self.session,
                user=buyer,
                amount=excess,
                reference=ref,
                description=f"Refund price improvement for trade {ref}",
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.TRADER_ORDER_BUY,
            )
        self.wallet_service.credit_trade_proceeds(
            self.session,
            user=seller,
            amount=_q(notional - fee),
            reference=ref,
            description=f"Trade proceeds {ref}",
            external_reference=ref,
            unit=LedgerUnit.COIN,
            source_tag=LedgerSourceTag.TRADER_ORDER_SELL,
        )
        if fee > Decimal("0.0000"):
            liquidity = self.wallet_service.ensure_market_liquidity_account(self.session, LedgerUnit.COIN)
            fee_account = self.wallet_service.ensure_trade_fee_account(self.session, LedgerUnit.COIN)
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(account=liquidity, amount=-fee),
                    LedgerPosting(account=fee_account, amount=fee),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.TRADER_TRADE_FEE,
                reference=ref,
                description=f"Trader trade fee {ref}",
            )

        # Position leg: seller escrow -> platform position, platform position -> buyer.
        self.wallet_service.settle_reserved_position_units(
            self.session,
            user=seller,
            player_id=_position_key(market.id),
            quantity=qty,
            reference=ref,
            description=f"Settle units for trade {ref}",
            external_reference=ref,
            source_tag=LedgerSourceTag.TRADER_ORDER_SELL,
        )
        self.wallet_service.credit_position_units(
            self.session,
            user=buyer,
            player_id=_position_key(market.id),
            quantity=qty,
            reference=ref,
            description=f"Receive units for trade {ref}",
            external_reference=ref,
            source_tag=LedgerSourceTag.TRADER_ORDER_BUY,
        )

        self._apply_fill(buy_order, qty, price)
        self._apply_fill(sell_order, qty, price)

        trade = TraderTrade(
            market_id=market.id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            buyer_user_id=buyer.id,
            seller_user_id=seller.id,
            quantity=qty,
            price=price,
            notional=notional,
            fee_amount=fee,
            taker_side=taker.side,
        )
        self.session.add(trade)
        market.price = price
        market.volume_24h = _q(Decimal(market.volume_24h) + notional)
        self.session.flush()
        return trade

    def _apply_fill(self, order: TraderOrder, qty: Decimal, price: Decimal) -> None:
        prior_filled = Decimal(order.filled_quantity)
        prior_avg = Decimal(order.average_fill_price) if order.average_fill_price is not None else Decimal("0.0000")
        new_filled = _q(prior_filled + qty)
        order.average_fill_price = _q((prior_avg * prior_filled + price * qty) / new_filled)
        order.filled_quantity = new_filled
        if new_filled >= Decimal(order.quantity):
            order.status = TraderOrderStatus.FILLED
        else:
            order.status = TraderOrderStatus.PARTIALLY_FILLED
        order.metadata_json = {**dict(order.metadata_json or {}), "last_fill_at": utcnow().isoformat()}

    def _user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise TraderMatchingError("Counterparty account not found.")
        return user
