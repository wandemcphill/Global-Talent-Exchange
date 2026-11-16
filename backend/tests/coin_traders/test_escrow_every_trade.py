from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coin_traders.schemas import CoinTradeOrderCreateRequest, CoinTradeProofRequest
from app.coin_traders.service import CoinTraderService, CoinTraderValidationError
from app.models.base import utcnow
from app.models.coin_trader import CoinTradeOrder, CoinTradeOrderStatus
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.wallets.service import WalletService
from backend.tests.coin_traders.test_coin_trader_service import (  # noqa: F401
    _approve_trader_with_rate,
    _seed_users,
    coin_trader_session,
)

# (unit, coins that clear the buyer minimum: GTEX >= N200,000 / Fan >= N50,000)
UNITS = [(LedgerUnit.COIN, Decimal("5000")), (LedgerUnit.CREDIT, Decimal("20000"))]


def _fund(session: Session, ws: WalletService, user, unit, amount: str) -> None:
    ws.credit_trade_proceeds(
        session,
        user=user,
        amount=Decimal(amount),
        unit=unit,
        reference=f"seed:{user.id}:{unit.value}",
        description="seed",
        external_reference="seed",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    session.commit()


def _order(profile, unit, amount, direction, key):
    return CoinTradeOrderCreateRequest(
        trader_profile_id=profile.id,
        direction=direction,
        coin_unit=unit,
        coin_amount=amount,
        fiat_currency="NGN",
        payment_method="bank_transfer",
        idempotency_key=f"escrow-test-{key}",
    )


def _setup(session, unit):
    users = _seed_users(session)
    ws = WalletService()
    svc = CoinTraderService(session, wallet_service=ws)
    profile = _approve_trader_with_rate(svc, users, coin_unit=unit)
    return users, ws, svc, profile


def _summary(session, ws, user, unit):
    return ws.get_wallet_summary(session, user, currency=unit)


@pytest.mark.parametrize(("unit", "amount"), UNITS)
def test_user_buys_locks_trader_inventory_at_creation(coin_trader_session, unit, amount) -> None:
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    _fund(coin_trader_session, ws, users["trader"], unit, "100000")

    order = svc.create_order(_order(profile, unit, amount, "user_buys", "k-buy"), actor=users["buyer"])

    assert order.status == CoinTradeOrderStatus.CREATED.value
    assert order.escrow_owner_user_id == users["trader"].id
    assert order.ledger_refs["escrow_lock_entry_ids"]
    s = _summary(coin_trader_session, ws, users["trader"], unit)
    assert s.reserved_balance == amount
    assert s.available_balance == Decimal("100000.0000") - amount


@pytest.mark.parametrize("unit", [LedgerUnit.COIN, LedgerUnit.CREDIT])
def test_user_sells_locks_customer_coins_at_creation(coin_trader_session, unit) -> None:
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    _fund(coin_trader_session, ws, users["buyer"], unit, "5000")

    order = svc.create_order(_order(profile, unit, Decimal("1000"), "user_sells", "k-sell"), actor=users["buyer"])

    assert order.escrow_owner_user_id == users["buyer"].id
    assert order.ledger_refs["escrow_lock_entry_ids"]
    s = _summary(coin_trader_session, ws, users["buyer"], unit)
    assert s.reserved_balance == Decimal("1000.0000")


def test_cannot_oversell_trader_inventory(coin_trader_session) -> None:
    unit, amount = LedgerUnit.COIN, Decimal("5000")
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    _fund(coin_trader_session, ws, users["trader"], unit, "5000")  # exactly one order of inventory

    svc.create_order(_order(profile, unit, amount, "user_buys", "k1"), actor=users["buyer"])
    with pytest.raises(CoinTraderValidationError):
        svc.create_order(_order(profile, unit, amount, "user_buys", "k2"), actor=users["second_buyer"])

    assert len(coin_trader_session.scalars(select(CoinTradeOrder)).all()) == 1
    s = _summary(coin_trader_session, ws, users["trader"], unit)
    assert s.reserved_balance == amount
    assert s.available_balance == Decimal("0.0000")


def test_sell_order_rejected_without_balance_and_leaves_no_order(coin_trader_session) -> None:
    unit = LedgerUnit.COIN
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    with pytest.raises(CoinTraderValidationError):
        svc.create_order(_order(profile, unit, Decimal("1000"), "user_sells", "k"), actor=users["buyer"])
    assert coin_trader_session.scalars(select(CoinTradeOrder)).all() == []


def test_cancel_before_accept_refunds_escrow_exactly_once(coin_trader_session) -> None:
    unit, amount = LedgerUnit.COIN, Decimal("5000")
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    _fund(coin_trader_session, ws, users["trader"], unit, "100000")
    order = svc.create_order(_order(profile, unit, amount, "user_buys", "k"), actor=users["buyer"])

    svc.cancel_order(order.id, actor=users["buyer"])
    with pytest.raises(CoinTraderValidationError):
        svc.cancel_order(order.id, actor=users["buyer"])  # duplicate request

    s = _summary(coin_trader_session, ws, users["trader"], unit)
    assert s.reserved_balance == Decimal("0.0000")
    assert s.available_balance == Decimal("100000.0000")


def test_unaccepted_orders_expire_and_release_escrow(coin_trader_session) -> None:
    unit, amount = LedgerUnit.COIN, Decimal("5000")
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    _fund(coin_trader_session, ws, users["trader"], unit, "100000")
    order = svc.create_order(_order(profile, unit, amount, "user_buys", "k"), actor=users["buyer"])

    db_order = svc._require_order(order.id)
    db_order.created_at = utcnow() - timedelta(minutes=svc.UNACCEPTED_ORDER_TTL_MINUTES + 1)
    coin_trader_session.commit()

    expired = svc.expire_stale_orders()
    assert [o.status for o in expired] == [CoinTradeOrderStatus.EXPIRED.value]
    assert svc.expire_stale_orders() == []  # re-running the sweep is a no-op
    s = _summary(coin_trader_session, ws, users["trader"], unit)
    assert s.reserved_balance == Decimal("0.0000")
    assert s.available_balance == Decimal("100000.0000")


def test_frozen_trader_cannot_take_new_orders_but_existing_order_still_settles(coin_trader_session) -> None:
    unit, amount = LedgerUnit.COIN, Decimal("5000")
    users, ws, svc, profile = _setup(coin_trader_session, unit)
    _fund(coin_trader_session, ws, users["trader"], unit, "100000")
    order = svc.create_order(_order(profile, unit, amount, "user_buys", "k"), actor=users["buyer"])
    svc.accept_order(order.id, actor=users["trader"])
    svc.submit_proof(order.id, CoinTradeProofRequest(proof_reference="ref-1"), actor=users["buyer"])

    svc.freeze_trader(profile.id, admin=users["admin"], note="investigation")

    with pytest.raises(CoinTraderValidationError):
        svc.create_order(_order(profile, unit, amount, "user_buys", "k-new"), actor=users["second_buyer"])
    released = svc.confirm_and_release(order.id, actor=users["trader"])
    assert released.status == CoinTradeOrderStatus.RELEASED.value
    assert _summary(coin_trader_session, ws, users["buyer"], unit).available_balance == amount
    assert _summary(coin_trader_session, ws, users["trader"], unit).reserved_balance == Decimal("0.0000")
    with pytest.raises(CoinTraderValidationError):
        svc.confirm_and_release(order.id, actor=users["trader"])  # duplicate release rejected
