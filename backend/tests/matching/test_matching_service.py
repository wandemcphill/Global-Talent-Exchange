from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.matching.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.auth.service import AuthService
from app.ingestion.models import Player
from app.matching.service import InvalidOrderTransitionError, MatchingService
from app.models.base import Base
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.orders.models import Order, OrderSide, OrderStatus
from app.orders.service import OrderService
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def service_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    yield session, OrderService()
    session.close()


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def _create_player(session, *, provider_external_id: str) -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Matching Test Player",
        is_tradable=True,
    )
    session.add(player)
    session.commit()
    return player


def _fund_user(session, current_user, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, current_user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"fund-{current_user.id}",
        description="Seed wallet credits for testing",
        actor=current_user,
    )
    session.commit()


def test_buy_sell_match_success(service_context) -> None:
    session, service = service_context
    player = _create_player(session, provider_external_id="matching-success")
    seller = _create_user(session, email="matching-seller-success@example.com", username="matchingsellersuccess")
    buyer = _create_user(session, email="matching-buyer-success@example.com", username="matchingbuyersuccess")
    _fund_user(session, buyer, amount=Decimal("100"))

    sell_order = service.place_order(
        session,
        user=seller,
        player_id=player.id,
        side=OrderSide.SELL,
        quantity=Decimal("3"),
        max_price=Decimal("7"),
    )
    buy_order = service.place_order(
        session,
        user=buyer,
        player_id=player.id,
        side=OrderSide.BUY,
        quantity=Decimal("3"),
        max_price=Decimal("7"),
    )

    snapshot = service.get_execution_snapshot(session, order_id=buy_order.id)

    assert buy_order.status is OrderStatus.FILLED
    assert sell_order.status is OrderStatus.FILLED
    assert snapshot.execution_count == 1
    assert snapshot.executions[0].maker_order_id == sell_order.id
    assert snapshot.executions[0].price == Decimal("7.0000")
    assert snapshot.executions[0].quantity == Decimal("3.0000")


def test_partial_fill_persists_remaining_quantity(service_context) -> None:
    session, service = service_context
    player = _create_player(session, provider_external_id="matching-partial")
    seller = _create_user(session, email="matching-seller-partial@example.com", username="matchingsellerpartial")
    buyer = _create_user(session, email="matching-buyer-partial@example.com", username="matchingbuyerpartial")
    _fund_user(session, buyer, amount=Decimal("100"))

    service.place_order(
        session,
        user=seller,
        player_id=player.id,
        side=OrderSide.SELL,
        quantity=Decimal("4"),
        max_price=Decimal("10"),
    )
    buy_order = service.place_order(
        session,
        user=buyer,
        player_id=player.id,
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        max_price=Decimal("10"),
    )

    assert buy_order.status is OrderStatus.PARTIALLY_FILLED
    assert buy_order.filled_quantity == Decimal("4.0000")
    assert buy_order.remaining_quantity == Decimal("6.0000")
    assert buy_order.reserved_amount == Decimal("60.0000")


def test_multi_order_matching_respects_price_time_priority(service_context) -> None:
    session, service = service_context
    player = _create_player(session, provider_external_id="matching-priority")
    seller_one = _create_user(session, email="seller-one-priority@example.com", username="selleronepriority")
    seller_two = _create_user(session, email="seller-two-priority@example.com", username="sellertwopriority")
    seller_three = _create_user(session, email="seller-three-priority@example.com", username="sellerthreepriority")
    buyer = _create_user(session, email="buyer-priority@example.com", username="buyerpriority")
    _fund_user(session, buyer, amount=Decimal("200"))

    sell_order_one = service.place_order(
        session,
        user=seller_one,
        player_id=player.id,
        side=OrderSide.SELL,
        quantity=Decimal("5"),
        max_price=Decimal("10"),
    )
    sell_order_two = service.place_order(
        session,
        user=seller_two,
        player_id=player.id,
        side=OrderSide.SELL,
        quantity=Decimal("4"),
        max_price=Decimal("9"),
    )
    sell_order_three = service.place_order(
        session,
        user=seller_three,
        player_id=player.id,
        side=OrderSide.SELL,
        quantity=Decimal("6"),
        max_price=Decimal("10"),
    )
    buy_order = service.place_order(
        session,
        user=buyer,
        player_id=player.id,
        side=OrderSide.BUY,
        quantity=Decimal("12"),
        max_price=Decimal("10"),
    )

    snapshot = service.get_execution_snapshot(session, order_id=buy_order.id)

    assert [execution.sell_order_id for execution in snapshot.executions] == [
        sell_order_two.id,
        sell_order_one.id,
        sell_order_three.id,
    ]
    assert [execution.price for execution in snapshot.executions] == [
        Decimal("9.0000"),
        Decimal("10.0000"),
        Decimal("10.0000"),
    ]
    assert sell_order_two.status is OrderStatus.FILLED
    assert sell_order_one.status is OrderStatus.FILLED
    assert sell_order_three.status is OrderStatus.PARTIALLY_FILLED
    assert sell_order_three.remaining_quantity == Decimal("3.0000")
    assert buy_order.status is OrderStatus.FILLED


def test_illegal_transition_rejection() -> None:
    order = Order(
        user_id="user-1",
        player_id="player-1",
        side=OrderSide.BUY,
        quantity=Decimal("1.0000"),
        filled_quantity=Decimal("1.0000"),
        max_price=Decimal("1.0000"),
        currency=LedgerUnit.CREDIT,
        reserved_amount=Decimal("0.0000"),
        status=OrderStatus.FILLED,
    )

    with pytest.raises(InvalidOrderTransitionError):
        MatchingService().transition_order(order, OrderStatus.OPEN)
