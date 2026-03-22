from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.matching.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.auth.dependencies import get_current_user, get_session
from app.auth.service import AuthService
from app.ingestion.models import Player
from app.ledger.models import LedgerEventRecord
from app.models.base import Base
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.orders.models import Order
from app.orders.router import router
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def api_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    current_user = _create_user(
        session,
        email="orders-http@example.com",
        username="ordershttp",
    )
    auth_state = {"user": current_user}

    app = FastAPI()
    app.include_router(router)

    def override_session():
        yield session

    def override_current_user():
        return auth_state["user"]

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield client, session, auth_state

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


def _create_player(session, *, provider_external_id: str = "player-order-1") -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Order Test Player",
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


def _ledger_events_for_order(session, order_id: str) -> list[LedgerEventRecord]:
    return session.scalars(
        select(LedgerEventRecord)
        .where(LedgerEventRecord.aggregate_id == order_id)
        .order_by(LedgerEventRecord.created_at.asc(), LedgerEventRecord.id.asc())
    ).all()


def test_place_order_returns_open_order_with_hold_details(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session)
    _fund_user(session, auth_state["user"], amount=Decimal("100"))

    response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 10,
            "max_price": 5,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert set(payload) == {
        "id",
        "user_id",
        "player_id",
        "side",
        "quantity",
        "filled_quantity",
        "remaining_quantity",
        "max_price",
        "currency",
        "reserved_amount",
        "status",
        "hold_transaction_id",
        "created_at",
        "updated_at",
        "execution_summary",
    }
    assert payload["player_id"] == player.id
    assert payload["side"] == "buy"
    assert payload["status"] == "open"
    assert Decimal(str(payload["quantity"])) == Decimal("10.0000")
    assert Decimal(str(payload["filled_quantity"])) == Decimal("0.0000")
    assert Decimal(str(payload["remaining_quantity"])) == Decimal("10.0000")
    assert Decimal(str(payload["reserved_amount"])) == Decimal("50.0000")
    assert payload["hold_transaction_id"] is not None
    assert set(payload["execution_summary"]) == {
        "execution_count",
        "total_notional",
        "average_price",
        "last_executed_at",
        "executions",
    }
    assert payload["execution_summary"]["execution_count"] == 0

    order_id = payload["id"]
    ledger_events = _ledger_events_for_order(session, order_id)
    assert {event.event_type.value for event in ledger_events} == {"order.accepted", "order.funds_reserved"}


def test_get_order_detail_returns_execution_summary(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-detail")
    seller = _create_user(session, email="seller-order-detail@example.com", username="sellerorderdetail")
    buyer = auth_state["user"]
    _fund_user(session, buyer, amount=Decimal("100"))

    auth_state["user"] = seller
    sell_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "sell",
            "quantity": 5,
            "max_price": 5,
        },
    )
    assert sell_response.status_code == 201
    sell_order_id = sell_response.json()["id"]

    auth_state["user"] = buyer
    buy_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 5,
            "max_price": 5,
        },
    )
    assert buy_response.status_code == 201
    buy_order_id = buy_response.json()["id"]

    response = client.get(f"/api/orders/{buy_order_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "filled"
    assert Decimal(str(payload["filled_quantity"])) == Decimal("5.0000")
    assert Decimal(str(payload["remaining_quantity"])) == Decimal("0.0000")
    assert payload["execution_summary"]["execution_count"] == 1
    assert Decimal(str(payload["execution_summary"]["total_notional"])) == Decimal("25.0000")
    assert Decimal(str(payload["execution_summary"]["average_price"])) == Decimal("5.0000")
    assert payload["execution_summary"]["last_executed_at"] is not None
    assert set(payload["execution_summary"]["executions"][0]) == {
        "id",
        "buy_order_id",
        "sell_order_id",
        "maker_order_id",
        "taker_order_id",
        "quantity",
        "price",
        "notional",
        "created_at",
    }
    assert payload["execution_summary"]["executions"][0]["maker_order_id"] == sell_order_id


def test_list_orders_returns_recent_orders_with_status_filter(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-list")
    _fund_user(session, auth_state["user"], amount=Decimal("100"))

    open_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 5,
            "max_price": 4,
        },
    )
    assert open_response.status_code == 201
    open_order_id = open_response.json()["id"]

    cancelled_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 2,
            "max_price": 3,
        },
    )
    assert cancelled_response.status_code == 201
    cancelled_order_id = cancelled_response.json()["id"]

    cancel_response = client.post(f"/api/orders/{cancelled_order_id}/cancel")
    assert cancel_response.status_code == 200

    all_orders_response = client.get("/api/orders", params={"limit": 10})
    assert all_orders_response.status_code == 200
    all_orders_payload = all_orders_response.json()
    assert all_orders_payload["limit"] == 10
    assert all_orders_payload["offset"] == 0
    assert all_orders_payload["total"] >= 2
    assert {item["id"] for item in all_orders_payload["items"]} >= {open_order_id, cancelled_order_id}

    open_orders_response = client.get("/api/orders", params=[("status", "open"), ("limit", "10")])
    assert open_orders_response.status_code == 200
    open_orders_payload = open_orders_response.json()
    assert open_order_id in {item["id"] for item in open_orders_payload["items"]}
    assert cancelled_order_id not in {item["id"] for item in open_orders_payload["items"]}
    assert all(item["status"] == "open" for item in open_orders_payload["items"])


def test_cancel_open_order(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-cancel-open")
    _fund_user(session, auth_state["user"], amount=Decimal("100"))

    create_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 4,
            "max_price": 5,
        },
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["id"]

    cancel_response = client.post(f"/api/orders/{order_id}/cancel")

    assert cancel_response.status_code == 200
    payload = cancel_response.json()
    assert set(payload) == {
        "id",
        "user_id",
        "player_id",
        "side",
        "quantity",
        "filled_quantity",
        "remaining_quantity",
        "max_price",
        "currency",
        "reserved_amount",
        "status",
        "hold_transaction_id",
        "created_at",
        "updated_at",
        "execution_summary",
    }
    assert payload["status"] == "cancelled"
    assert Decimal(str(payload["filled_quantity"])) == Decimal("0.0000")
    assert Decimal(str(payload["remaining_quantity"])) == Decimal("4.0000")
    assert Decimal(str(payload["reserved_amount"])) == Decimal("0.0000")
    ledger_events = _ledger_events_for_order(session, order_id)
    assert {event.event_type.value for event in ledger_events} == {
        "order.accepted",
        "order.funds_reserved",
        "order.released",
        "order.cancelled",
    }


def test_partial_fill_emits_execution_event_and_keeps_remaining_hold(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-partial-fill-events")
    seller = _create_user(
        session,
        email="seller-order-partial-fill-events@example.com",
        username="sellerorderpartialfillevents",
    )
    buyer = auth_state["user"]
    _fund_user(session, buyer, amount=Decimal("100"))

    auth_state["user"] = seller
    sell_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "sell",
            "quantity": 4,
            "max_price": 10,
        },
    )
    assert sell_response.status_code == 201
    sell_order_id = sell_response.json()["id"]

    auth_state["user"] = buyer
    buy_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 10,
            "max_price": 10,
        },
    )
    assert buy_response.status_code == 201
    buy_order_id = buy_response.json()["id"]

    order = session.get(Order, buy_order_id)
    assert order is not None
    assert order.status.value == "partially_filled"
    assert Decimal(str(order.filled_quantity)) == Decimal("4.0000")
    assert Decimal(str(order.remaining_quantity)) == Decimal("6.0000")
    assert Decimal(str(order.reserved_amount)) == Decimal("60.0000")

    buyer_events = _ledger_events_for_order(session, buy_order_id)
    assert {event.event_type.value for event in buyer_events} == {
        "order.accepted",
        "order.funds_reserved",
        "order.executed",
    }
    seller_events = _ledger_events_for_order(session, sell_order_id)
    assert {event.event_type.value for event in seller_events} == {
        "order.accepted",
        "order.executed",
    }


def test_cancel_partially_filled_order_releases_remaining_hold(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-cancel-partial")
    seller = _create_user(session, email="seller-order-partial@example.com", username="sellerorderpartial")
    buyer = auth_state["user"]
    _fund_user(session, buyer, amount=Decimal("100"))

    auth_state["user"] = seller
    sell_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "sell",
            "quantity": 4,
            "max_price": 10,
        },
    )
    assert sell_response.status_code == 201

    auth_state["user"] = buyer
    buy_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 10,
            "max_price": 10,
        },
    )
    assert buy_response.status_code == 201
    order_id = buy_response.json()["id"]

    cancel_response = client.post(f"/api/orders/{order_id}/cancel")

    assert cancel_response.status_code == 200
    payload = cancel_response.json()
    assert payload["status"] == "cancelled"
    assert Decimal(str(payload["filled_quantity"])) == Decimal("4.0000")
    assert Decimal(str(payload["remaining_quantity"])) == Decimal("6.0000")
    assert Decimal(str(payload["reserved_amount"])) == Decimal("0.0000")
    buyer_events = _ledger_events_for_order(session, order_id)
    assert {event.event_type.value for event in buyer_events} == {
        "order.accepted",
        "order.funds_reserved",
        "order.executed",
        "order.released",
        "order.cancelled",
    }
    seller_order = session.scalar(select(Order).where(Order.user_id == seller.id, Order.player_id == player.id))
    assert seller_order is not None
    seller_events = _ledger_events_for_order(session, seller_order.id)
    assert {event.event_type.value for event in seller_events} == {
        "order.accepted",
        "order.executed",
    }

    wallet_summary = WalletService().get_wallet_summary(session, buyer)
    assert wallet_summary.available_balance == Decimal("60.0000")
    assert wallet_summary.reserved_balance == Decimal("0.0000")
    assert wallet_summary.total_balance == Decimal("60.0000")


def test_reject_cancel_for_filled_order(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-cancel-filled")
    seller = _create_user(session, email="seller-order-filled@example.com", username="sellerorderfilled")
    buyer = auth_state["user"]
    _fund_user(session, buyer, amount=Decimal("100"))

    auth_state["user"] = seller
    sell_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "sell",
            "quantity": 5,
            "max_price": 5,
        },
    )
    assert sell_response.status_code == 201

    auth_state["user"] = buyer
    buy_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 5,
            "max_price": 5,
        },
    )
    assert buy_response.status_code == 201
    order_id = buy_response.json()["id"]

    cancel_response = client.post(f"/api/orders/{order_id}/cancel")

    assert cancel_response.status_code == 409
    assert "Only open or partially filled orders can be cancelled." in cancel_response.json()["detail"]


def test_order_book_endpoint_returns_aggregated_depth(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-book")
    buyer_one = auth_state["user"]
    buyer_two = _create_user(session, email="buyer-two-order-book@example.com", username="buyertwoorderbook")
    buyer_three = _create_user(session, email="buyer-three-order-book@example.com", username="buyerthreeorderbook")
    seller_one = _create_user(session, email="seller-one-order-book@example.com", username="selleroneorderbook")
    seller_two = _create_user(session, email="seller-two-order-book@example.com", username="sellertwoorderbook")

    for user in (buyer_one, buyer_two, buyer_three):
        _fund_user(session, user, amount=Decimal("200"))

    auth_state["user"] = buyer_one
    assert client.post(
        "/api/orders",
        json={"player_id": player.id, "side": "buy", "quantity": 5, "max_price": 10},
    ).status_code == 201
    auth_state["user"] = buyer_two
    assert client.post(
        "/api/orders",
        json={"player_id": player.id, "side": "buy", "quantity": 3, "max_price": 10},
    ).status_code == 201
    auth_state["user"] = buyer_three
    assert client.post(
        "/api/orders",
        json={"player_id": player.id, "side": "buy", "quantity": 2, "max_price": 9},
    ).status_code == 201
    auth_state["user"] = seller_one
    assert client.post(
        "/api/orders",
        json={"player_id": player.id, "side": "sell", "quantity": 4, "max_price": 11},
    ).status_code == 201
    auth_state["user"] = seller_two
    assert client.post(
        "/api/orders",
        json={"player_id": player.id, "side": "sell", "quantity": 1, "max_price": 12},
    ).status_code == 201

    response = client.get(f"/api/orders/book/{player.id}")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"player_id", "bids", "asks", "generated_at"}
    assert set(payload["bids"][0]) == {"price", "quantity", "order_count"}
    assert set(payload["asks"][0]) == {"price", "quantity", "order_count"}
    assert payload["player_id"] == player.id
    assert payload["bids"] == [
        {"price": "10.0000", "quantity": "8.0000", "order_count": 2},
        {"price": "9.0000", "quantity": "2.0000", "order_count": 1},
    ]
    assert payload["asks"] == [
        {"price": "11.0000", "quantity": "4.0000", "order_count": 1},
        {"price": "12.0000", "quantity": "1.0000", "order_count": 1},
    ]


def test_execution_events_are_written_for_both_orders(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-events")
    seller = _create_user(session, email="seller-order-events@example.com", username="sellerorderevents")
    buyer = auth_state["user"]
    _fund_user(session, buyer, amount=Decimal("100"))

    auth_state["user"] = seller
    sell_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "sell",
            "quantity": 5,
            "max_price": 5,
        },
    )
    assert sell_response.status_code == 201
    sell_order_id = sell_response.json()["id"]

    auth_state["user"] = buyer
    buy_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 5,
            "max_price": 5,
        },
    )
    assert buy_response.status_code == 201
    buy_order_id = buy_response.json()["id"]

    buy_events = session.scalars(
        select(LedgerEventRecord)
        .where(LedgerEventRecord.aggregate_id == buy_order_id)
        .order_by(LedgerEventRecord.created_at.asc(), LedgerEventRecord.id.asc())
    ).all()
    sell_events = _ledger_events_for_order(session, sell_order_id)

    assert {event.event_type.value for event in buy_events} == {
        "order.accepted",
        "order.funds_reserved",
        "order.executed",
    }
    assert {event.event_type.value for event in sell_events} == {
        "order.accepted",
        "order.executed",
    }

    order = session.get(Order, buy_order_id)
    assert order is not None
    assert order.status.value == "filled"


def test_price_improvement_releases_unused_reserved_funds(api_context) -> None:
    client, session, auth_state = api_context
    player = _create_player(session, provider_external_id="player-order-price-improvement")
    seller = _create_user(
        session,
        email="seller-order-price-improvement@example.com",
        username="sellerorderpriceimprovement",
    )
    buyer = auth_state["user"]
    _fund_user(session, buyer, amount=Decimal("100"))

    auth_state["user"] = seller
    sell_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "sell",
            "quantity": 3,
            "max_price": 7,
        },
    )
    assert sell_response.status_code == 201

    auth_state["user"] = buyer
    buy_response = client.post(
        "/api/orders",
        json={
            "player_id": player.id,
            "side": "buy",
            "quantity": 3,
            "max_price": 10,
        },
    )
    assert buy_response.status_code == 201
    buy_order_id = buy_response.json()["id"]

    order = session.get(Order, buy_order_id)
    assert order is not None
    assert order.status.value == "filled"
    assert Decimal(str(order.reserved_amount)) == Decimal("0.0000")

    buyer_events = _ledger_events_for_order(session, buy_order_id)
    assert {event.event_type.value for event in buyer_events} == {
        "order.accepted",
        "order.funds_reserved",
        "order.executed",
        "order.released",
    }
    release_event = next(event for event in buyer_events if event.event_type.value == "order.released")
    assert release_event.payload_json["reason"] == "price_improvement"
    assert Decimal(release_event.payload_json["released_amount"]) == Decimal("9.0000")
