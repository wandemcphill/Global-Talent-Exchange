"""N45 money-lane invariants: no over-fill across multiple takers, no
reservation leak, conserved units/cash through the matching+ledger path."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.auth.service import AuthService
from app.models.trader import TraderOrderSide, TraderOrderStatus
from app.models.user import KycStatus, PublicAccountType
from app.models.wallet import LedgerUnit
from app.trader.service import TraderService
from app.wallets.service import WalletService
from backend.tests.support.secrets import TEST_PASSWORD
from backend.tests.trader.test_trader_service import (
    _create_market,
    _fund_coins,
    _fund_units,
    _verify_trader,
)


@pytest.fixture()
def session(gtex_db_session):
    yield gtex_db_session


def _trader(session, suffix: str):
    user = AuthService().register_user(
        session,
        email=f"{suffix}@example.com",
        username=suffix.replace("-", "_"),
        password=TEST_PASSWORD,
        display_name=suffix,
        account_type=PublicAccountType.COIN_TRADER,
    )
    user.kyc_status = KycStatus.VERIFIED
    TraderService(session).ensure_profile(
        user,
        trading_alias=f"alias-{suffix}",
        preferred_currency="USD",
        trading_experience="beginner",
        interests=["GTEX"],
        wallet_label="GTEX Trading Wallet",
    )
    session.flush()
    return user


def test_multiple_takers_cannot_overfill_a_single_resting_ask(session) -> None:
    svc = TraderService(session)
    market = _create_market(session)
    seller = _trader(session, "n45-seller")
    _verify_trader(session, seller)
    _fund_units(session, seller, market.id, Decimal("5.0000"))

    resting = svc.place_order(
        seller, market_id=market.id, side=TraderOrderSide.SELL,
        quantity=Decimal("5.0000"), limit_price=Decimal("2.0000"),
    )

    buyers = []
    for i in range(4):
        b = _trader(session, f"n45-buyer-{i}")
        _verify_trader(session, b)
        _fund_coins(session, b, Decimal("100.0000"))
        buyers.append(b)

    # Each buyer takes 2 units; ask only has 5. Total demand 8 > supply 5.
    total_filled = Decimal("0.0000")
    for b in buyers:
        order = svc.place_order(
            b, market_id=market.id, side=TraderOrderSide.BUY,
            quantity=Decimal("2.0000"), limit_price=Decimal("2.5000"),
        )
        total_filled += Decimal(order.filled_quantity)

    session.refresh(resting)
    wallet = WalletService()

    # INVARIANT 1: never fill more than the resting ask quantity.
    assert Decimal(resting.filled_quantity) == Decimal("5.0000")
    assert resting.status == TraderOrderStatus.FILLED
    # INVARIANT 2: total units delivered to buyers == ask filled (units conserved).
    delivered = sum(
        wallet.get_available_position_quantity(session, b, f"trader:{market.id}") for b in buyers
    )
    assert delivered == Decimal("5.0000")
    assert total_filled == Decimal("5.0000")
    # INVARIANT 3: seller has zero units left reserved or available (all sold).
    assert wallet.get_reserved_position_quantity(session, seller, f"trader:{market.id}") == Decimal("0.0000")
    assert wallet.get_available_position_quantity(session, seller, f"trader:{market.id}") == Decimal("0.0000")


def test_reserve_then_cancel_is_leak_free(session) -> None:
    svc = TraderService(session)
    market = _create_market(session)
    buyer = _trader(session, "n45-leak")
    _verify_trader(session, buyer)
    _fund_coins(session, buyer, Decimal("100.0000"))
    wallet = WalletService()

    before = wallet.get_wallet_summary(session, buyer, currency=LedgerUnit.COIN)
    order = svc.place_order(
        buyer, market_id=market.id, side=TraderOrderSide.BUY,
        quantity=Decimal("10.0000"), limit_price=Decimal("3.0000"),
    )
    held = wallet.get_wallet_summary(session, buyer, currency=LedgerUnit.COIN)
    # Reservation moved 30 from available to reserved.
    assert held.reserved_balance == Decimal("30.0000")
    assert held.available_balance == before.available_balance - Decimal("30.0000")

    svc.cancel_order(buyer, order_id=order.id)
    after = wallet.get_wallet_summary(session, buyer, currency=LedgerUnit.COIN)
    # INVARIANT: cancel returns the full reservation; no leak, totals conserved.
    assert after.reserved_balance == Decimal("0.0000")
    assert after.available_balance == before.available_balance
    assert after.total_balance == before.total_balance


def test_idempotent_reservation_does_not_double_debit(session) -> None:
    wallet = WalletService()
    buyer = _trader(session, "n45-idem")
    _fund_coins(session, buyer, Decimal("50.0000"))

    before = wallet.get_wallet_summary(session, buyer, currency=LedgerUnit.COIN)
    key = "n45-idem-key-001"
    wallet.reserve_order_funds(
        session, user=buyer, amount=Decimal("10.0000"),
        reference="n45-idem", description="first", unit=LedgerUnit.COIN,
        idempotency_key=key,
    )
    # Replay with the same idempotency key must NOT debit again.
    wallet.reserve_order_funds(
        session, user=buyer, amount=Decimal("10.0000"),
        reference="n45-idem", description="replay", unit=LedgerUnit.COIN,
        idempotency_key=key,
    )
    after = wallet.get_wallet_summary(session, buyer, currency=LedgerUnit.COIN)
    assert after.reserved_balance == Decimal("10.0000")
    assert after.available_balance == before.available_balance - Decimal("10.0000")
