"""PHASE5-A transaction-spine audit.

These tests pin the divergence between the two player-ownership systems that
both exist on main:

* System A - PlayerShareMarket / PlayerShareHolding, written by
  PlayerTokenMarketService and reached over POST /market/buy and
  POST /players/{player_id}/shares/buy. This is where production issuance put
  every real-league share market.
* System B - exchange_orders plus the position:{user}:{player} ledger accounts,
  written by OrderService/MatchingService and reached over POST /orders. This is
  what GET /portfolio reports and what the Flutter order ticket actually calls.

PR-1 made System A internally coherent: ownership bought through the canonical
Market path now reaches the Portfolio (P0-1) and the Market trade contract
honours an idempotency key (P1-1). Those two are hard assertions below.

P0-2 - the unbridged ownership stores themselves - is still open and stays
marked xfail(strict); it closes in PR-2 when the order book is retired, at
which point the marker must be removed rather than the assertion weakened.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.market.router import router as market_router
from app.models.player_token_market import PlayerShareHolding
from app.models.user import UserRole
from app.orders.router import router as orders_router
from app.players import router as players_router_module
from app.players.router import router as players_router
from app.portfolio.router import router as portfolio_router
from app.wallets.service import WalletService

# Reuse the real-player/market seeding already proven by the share-market route
# suite rather than duplicating ~150 lines of ingestion fixture setup.
from tests.players.test_player_share_market_routes import (
    _build_session,
    _create_user,
    _seed_coin_balance,
    _seed_imported_real_player,
)

ISSUE_BODY = {"total_shares": 1000, "share_price_coin": "0.5000", "liquidity_coin": "200.0000"}


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


def test_market_buy_is_visible_in_the_portfolio(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="p5-portfolio-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="p5-portfolio-fan")
        player = _seed_imported_real_player(session, player_id="p5-portfolio-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            issue_response = client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            buy_response = client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            portfolio_response = client.get("/portfolio")

        assert issue_response.status_code == 200, issue_response.text
        assert buy_response.status_code == 201, buy_response.text

        # The buy really happened: the holding exists and the wallet was debited.
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 10

        # ... so the portfolio must show it.
        assert portfolio_response.status_code == 200, portfolio_response.text
        holdings = portfolio_response.json()["holdings"]
        assert [item["player_id"] for item in holdings] == [player.id]
        assert Decimal(holdings[0]["quantity"]) == Decimal("10")
    finally:
        session.close()
        engine.dispose()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "PHASE5-A P0-2: PlayerShareHolding and the position:{user}:{player} "
        "ledger accounts are two unreconciled ownership stores. Buying through "
        "System A leaves System B at zero, so the order book rejects a sell of "
        "shares the user demonstrably owns."
    ),
)
def test_the_two_ownership_stores_agree_after_a_market_buy(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="p5-ownership-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="p5-ownership-fan")
        player = _seed_imported_real_player(session, player_id="p5-ownership-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            buy_response = client.post("/market/buy", json={"player_id": player.id, "share_count": 10})

        assert buy_response.status_code == 201, buy_response.text
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 10

        position_quantity = WalletService().get_available_position_quantity(session, fan, player.id)
        assert position_quantity == Decimal("10.0000")
    finally:
        session.close()
        engine.dispose()


def test_market_buy_honours_a_repeated_idempotency_key(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="p5-idem-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="p5-idem-fan")
        player = _seed_imported_real_player(session, player_id="p5-idem-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        body = {"player_id": player.id, "share_count": 10, "idempotency_key": "market-retry-abcdef"}
        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            first = client.post("/market/buy", json=body)
            second = client.post("/market/buy", json=body)

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["transaction_id"] == second.json()["transaction_id"]
        assert second.json()["holding"]["share_count"] == 10
    finally:
        session.close()
        engine.dispose()


def test_player_shares_buy_replays_a_repeated_idempotency_key(monkeypatch) -> None:
    """The idempotency mechanism itself is sound - it is simply not wired to /market.

    This is the working reference implementation the /market endpoints should
    reuse; it exists to stop a future change regressing it.
    """
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="p5-idem2-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="p5-idem2-fan")
        player = _seed_imported_real_player(session, player_id="p5-idem2-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        body = {"share_count": 10, "idempotency_key": "player-retry-abcdef"}
        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            first = client.post(f"/players/{player.id}/shares/buy", json=body)
            second = client.post(f"/players/{player.id}/shares/buy", json=body)

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["transaction_id"] == second.json()["transaction_id"]
        assert second.json()["holding"]["share_count"] == 10
        assert second.json()["market"]["circulating_shares"] == 10
    finally:
        session.close()
        engine.dispose()


def test_order_book_buy_cannot_fill_and_parks_the_reservation(monkeypatch) -> None:
    """The venue the app actually trades on has no supply to match against.

    Production issuance writes PlayerShareMarket.circulating_shares; it never
    credits position:{user}:{player} units, and only a settled execution can. So
    a buy order placed from the canonical Player Detail order ticket reserves the
    user's coin and stays OPEN with zero executions indefinitely.
    """
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="p5-book-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="p5-book-fan")
        player = _seed_imported_real_player(session, player_id="p5-book-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            order_response = client.post(
                "/orders",
                json={"player_id": player.id, "side": "buy", "quantity": "5.0000", "max_price": "0.5000"},
            )
            book_response = client.get(f"/orders/book/{player.id}")

        assert order_response.status_code == 201, order_response.text
        order = order_response.json()
        assert order["status"] == "open"
        assert order["filled_quantity"] == "0.0000"
        assert order["execution_summary"]["execution_count"] == 0
        assert Decimal(order["reserved_amount"]) == Decimal("2.5000")
        assert order["hold_transaction_id"]

        # The issued market holds 1000 shares, yet the book the app trades on
        # shows no ask at all.
        assert book_response.status_code == 200, book_response.text
        assert book_response.json()["asks"] == []
    finally:
        session.close()
        engine.dispose()
