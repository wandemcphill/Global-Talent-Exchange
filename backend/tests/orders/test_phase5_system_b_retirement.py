"""PHASE5-A / PR-2A: System B is retired from the user-facing trading path.

System A (PlayerShareMarket / PlayerShareHolding / PlayerTokenMarketService) is
the canonical player-share economy. System B - exchange_orders, MatchingService
and the position:{user}:{player} ledger accounts - must no longer be able to
create new user positions.

Retirement here is deliberately narrow:

* ``POST /orders`` (and its /api and /api/v2 aliases) is GONE, following the
  repository's existing 410 convention for retired endpoints.
* Every read path is preserved, because historical records must survive.
* ``OrderService`` itself is untouched, so the simulation harness, admin tooling
  and historical settlement keep working.

Production evidence for the safety of this (queried read-only against the live
database before the change): exchange_orders 0, trade_executions 0,
position: ledger accounts 0, player_share_holdings 0, and all 25,986
player_share_events are of type ``issue``. No user has ever held a System B
position, so nothing needs migrating.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.market.router import router as market_router
from app.models.player_token_market import PlayerShareHolding
from app.models.user import UserRole
from app.orders.models import Order, OrderSide, OrderStatus
from app.orders.router import router as orders_router
from app.players import router as players_router_module
from app.players.router import router as players_router
from app.portfolio.router import router as portfolio_router

from tests.players.test_player_share_market_routes import (
    _build_session,
    _create_user,
    _seed_coin_balance,
    _seed_imported_real_player,
)

ISSUE_BODY = {"total_shares": 1000, "share_price_coin": "0.5000", "liquidity_coin": "200.0000"}
ORDER_BODY = {"player_id": None, "side": "buy", "quantity": "5.0000", "max_price": "0.5000"}


def _build_client(session, *, admin, user, monkeypatch) -> tuple[TestClient, dict]:
    app = FastAPI()
    app.include_router(players_router)
    app.include_router(market_router)
    app.include_router(orders_router)
    app.include_router(portfolio_router)
    auth_context = {"admin": admin, "user": user}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_admin] = lambda: auth_context["admin"]
    app.dependency_overrides[get_current_user] = lambda: auth_context["user"]
    monkeypatch.setattr(players_router_module, "_require_manager_supply_permission", lambda request, actor: None)
    return TestClient(app), auth_context


def _seed_historical_order(session, *, user, player, order_id: str) -> Order:
    """A System B order as it would exist in historical data, created through the
    model rather than the retired HTTP route."""
    order = Order(
        id=order_id,
        user_id=user.id,
        player_id=player.id,
        side=OrderSide.BUY,
        quantity=Decimal("5.0000"),
        filled_quantity=Decimal("0.0000"),
        max_price=Decimal("0.5000"),
        reserved_amount=Decimal("0.0000"),
        status=OrderStatus.OPEN,
    )
    session.add(order)
    session.flush()
    return order


def test_creating_a_system_b_order_is_gone(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sb-gone-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sb-gone-fan")
        player = _seed_imported_real_player(session, player_id="sb-gone-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        body = {**ORDER_BODY, "player_id": player.id}
        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            responses = {
                "/orders": client.post("/orders", json=body),
                "/api/orders": client.post("/api/orders", json=body),
            }

        for path, response in responses.items():
            assert response.status_code == 410, f"{path}: {response.status_code} {response.text}"
            detail = response.json()["detail"]
            assert "/market/buy" in detail and "/market/sell" in detail, f"{path}: {detail}"

        # Nothing was created, and no coin was reserved.
        assert session.query(Order).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_system_b_read_paths_survive_retirement(monkeypatch) -> None:
    """Historical records must remain readable: retirement is not deletion."""
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sb-read-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sb-read-fan")
        player = _seed_imported_real_player(session, player_id="sb-read-player")
        order = _seed_historical_order(session, user=fan, player=player, order_id="historical-order-1")
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            auth["user"] = fan
            listing = client.get("/orders")
            detail = client.get(f"/orders/{order.id}")
            book = client.get(f"/orders/book/{player.id}")

        assert listing.status_code == 200, listing.text
        assert [item["id"] for item in listing.json()["items"]] == [order.id]
        assert detail.status_code == 200, detail.text
        assert detail.json()["status"] == "open"
        assert book.status_code == 200, book.text
    finally:
        session.close()
        engine.dispose()


def test_a_historical_order_can_still_be_cancelled(monkeypatch) -> None:
    """Retiring creation must not strand an existing open order."""
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sb-cancel-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sb-cancel-fan")
        player = _seed_imported_real_player(session, player_id="sb-cancel-player")
        order = _seed_historical_order(session, user=fan, player=player, order_id="historical-order-2")
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            auth["user"] = fan
            cancelled = client.post(f"/orders/{order.id}/cancel")

        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
    finally:
        session.close()
        engine.dispose()


def test_system_a_is_the_surviving_trading_path(monkeypatch) -> None:
    """The whole canonical loop, end to end, with System B creation retired."""
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-loop-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-loop-fan")
        player = _seed_imported_real_player(session, player_id="sa-loop-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            retired = client.post("/orders", json={**ORDER_BODY, "player_id": player.id})
            bought = client.post(
                "/market/buy",
                json={"player_id": player.id, "share_count": 10, "idempotency_key": "loop-key-abcdef"},
            )
            portfolio = client.get("/portfolio")
            sold = client.post("/market/sell", json={"player_id": player.id, "share_count": 4})
            after_sell = client.get("/portfolio")

        assert retired.status_code == 410
        assert bought.status_code == 201, bought.text
        assert portfolio.status_code == 200, portfolio.text
        assert [item["player_id"] for item in portfolio.json()["holdings"]] == [player.id]
        assert Decimal(portfolio.json()["holdings"][0]["quantity"]) == Decimal("10")

        assert sold.status_code == 201, sold.text
        assert Decimal(after_sell.json()["holdings"][0]["quantity"]) == Decimal("6")

        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 6
        assert session.query(Order).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_realized_pl_is_reported_as_uncalculated_for_system_a_ownership(monkeypatch) -> None:
    """UNKNOWN != ZERO.

    System A cannot compute realized P/L: PlayerShareEvent records the sale price
    but not the cost basis at time of sale, and average_cost_coin is not
    snapshotted on sell. The repository has no lot/FIFO accounting to reuse, so
    rather than inventing one, the summary must say the figure is unavailable
    instead of reporting a confident 0.
    """
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-rpl-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-rpl-fan")
        player = _seed_imported_real_player(session, player_id="sa-rpl-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            before = client.get("/portfolio/summary")
            client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            client.post("/market/sell", json={"player_id": player.id, "share_count": 4})
            after = client.get("/portfolio/summary")

        # A user with no System A ownership keeps the legacy, genuinely-zero figure.
        assert before.json()["realized_pl_available"] is True
        assert Decimal(before.json()["realized_pl_total"]) == Decimal("0.0000")

        # Once System A ownership exists, realized P/L is explicitly not calculated.
        assert after.json()["realized_pl_available"] is False
        assert Decimal(after.json()["unrealized_pl_total"]) != Decimal("0.0000")
    finally:
        session.close()
        engine.dispose()
