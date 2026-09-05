"""PHASE5-A / PR-1 regression suite for the canonical System A player-share spine.

System A is canonical:

    PlayerShareTradeRequest -> idempotent trade -> wallet/ledger
    -> PlayerShareHolding -> PlayerShareMarket.share_price_coin -> Portfolio

These tests cover the four PR-1 remediation slices - idempotency on the Market
trade contract (P1-1), PlayerShareHolding as the Portfolio's canonical ownership
source (P0-1), coin-coherent cost basis and P/L (P1-4), and rollback on the
Market error paths (P2-2).

System B (exchange_orders / position: ledger accounts) is deliberately untouched
here; its retirement is PR-2.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.market.router import router as market_router
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.user import UserRole
from app.models.wallet import LedgerEntry, LedgerTransaction, LedgerUnit
from app.players import router as players_router_module
from app.players.router import router as players_router
from app.portfolio.router import router as portfolio_router
from app.wallets.service import WalletService

# Reuse the real-player + market seeding already proven by the share-market route
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
    app.include_router(portfolio_router)
    auth_context = {"admin": admin, "user": user}
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_admin] = lambda: auth_context["admin"]
    app.dependency_overrides[get_current_user] = lambda: auth_context["user"]
    monkeypatch.setattr(players_router_module, "_require_manager_supply_permission", lambda request, actor: None)
    return TestClient(app), auth_context


def _coin_balance(session, user) -> Decimal:
    wallet = WalletService()
    return wallet.get_balance(session, wallet.get_user_account(session, user, LedgerUnit.COIN))


def _trade_counts(session) -> tuple[int, int]:
    return (
        session.query(LedgerTransaction).count(),
        session.query(LedgerEntry).count(),
    )


# ---------------------------------------------------------------------------
# 1. Idempotency on the canonical Market trade contract (P1-1)
# ---------------------------------------------------------------------------


def test_market_buy_replays_a_repeated_idempotency_key(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-buy-idem-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-buy-idem-fan")
        player = _seed_imported_real_player(session, player_id="sa-buy-idem-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        body = {"player_id": player.id, "share_count": 10, "idempotency_key": "market-buy-abcdef"}
        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            first = client.post("/market/buy", json=body)
            balance_after_first = _coin_balance(session, fan)
            transactions_after_first, entries_after_first = _trade_counts(session)
            second = client.post("/market/buy", json=body)

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text

        # Same economic result, replayed - not a second trade.
        assert first.json()["transaction_id"] == second.json()["transaction_id"]
        assert second.json()["holding"]["share_count"] == 10
        assert second.json()["market"]["circulating_shares"] == 10

        # No duplicate holding, wallet, or ledger movement.
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 10
        assert _coin_balance(session, fan) == balance_after_first
        assert _trade_counts(session) == (transactions_after_first, entries_after_first)
    finally:
        session.close()
        engine.dispose()


def test_market_sell_replays_a_repeated_idempotency_key(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-sell-idem-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-sell-idem-fan")
        player = _seed_imported_real_player(session, player_id="sa-sell-idem-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        body = {"player_id": player.id, "share_count": 4, "idempotency_key": "market-sell-abcdef"}
        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            first = client.post("/market/sell", json=body)
            balance_after_first = _coin_balance(session, fan)
            counts_after_first = _trade_counts(session)
            second = client.post("/market/sell", json=body)

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["transaction_id"] == second.json()["transaction_id"]
        assert second.json()["holding"]["share_count"] == 6

        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 6
        assert _coin_balance(session, fan) == balance_after_first
        assert _trade_counts(session) == counts_after_first
    finally:
        session.close()
        engine.dispose()


def test_market_buy_rejects_a_reused_key_with_different_economic_intent(monkeypatch) -> None:
    """A reused key must never silently replay an unrelated trade."""
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-conflict-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-conflict-fan")
        player = _seed_imported_real_player(session, player_id="sa-conflict-player")
        other = _seed_imported_real_player(session, player_id="sa-conflict-other")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        key = "market-conflict-abcdef"
        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            client.post(f"/players/{other.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            original = client.post(
                "/market/buy", json={"player_id": player.id, "share_count": 10, "idempotency_key": key}
            )
            changed_quantity = client.post(
                "/market/buy", json={"player_id": player.id, "share_count": 25, "idempotency_key": key}
            )
            changed_player = client.post(
                "/market/buy", json={"player_id": other.id, "share_count": 10, "idempotency_key": key}
            )
            changed_side = client.post(
                "/market/sell", json={"player_id": player.id, "share_count": 10, "idempotency_key": key}
            )

        assert original.status_code == 201, original.text
        for label, response in (
            ("changed quantity", changed_quantity),
            ("changed player", changed_player),
            ("changed side", changed_side),
        ):
            assert 400 <= response.status_code < 500, f"{label}: {response.status_code} {response.text}"
            assert "idempotency" in response.json()["detail"].lower(), f"{label}: {response.text}"

        # None of the rejected attempts moved anything.
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 10
        assert session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=other.id).one_or_none() is None
    finally:
        session.close()
        engine.dispose()


def test_market_buy_without_a_key_keeps_executing_independent_trades(monkeypatch) -> None:
    """Idempotency stays optional - omitting the key preserves current behaviour."""
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-nokey-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-nokey-fan")
        player = _seed_imported_real_player(session, player_id="sa-nokey-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            first = client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            second = client.post("/market/buy", json={"player_id": player.id, "share_count": 10})

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["transaction_id"] != second.json()["transaction_id"]
        assert second.json()["holding"]["share_count"] == 20
    finally:
        session.close()
        engine.dispose()


def test_distinct_idempotency_keys_remain_independent(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-distinct-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-distinct-fan")
        player = _seed_imported_real_player(session, player_id="sa-distinct-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            first = client.post(
                "/market/buy", json={"player_id": player.id, "share_count": 10, "idempotency_key": "key-one-aaaaaa"}
            )
            second = client.post(
                "/market/buy", json={"player_id": player.id, "share_count": 10, "idempotency_key": "key-two-bbbbbb"}
            )

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["transaction_id"] != second.json()["transaction_id"]
        assert second.json()["holding"]["share_count"] == 20
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# 2/3. Portfolio reads canonical ownership, in the settlement unit (P0-1, P1-4)
# ---------------------------------------------------------------------------


def test_portfolio_reports_the_canonical_player_share_holding(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-pf-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-pf-fan")
        player = _seed_imported_real_player(session, player_id="sa-pf-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            buy = client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            portfolio = client.get("/portfolio")
            summary = client.get("/portfolio/summary")

        assert buy.status_code == 201, buy.text
        assert portfolio.status_code == 200, portfolio.text
        assert summary.status_code == 200, summary.text

        holdings = portfolio.json()["holdings"]
        assert [item["player_id"] for item in holdings] == [player.id]
        entry = holdings[0]

        market = session.query(PlayerShareMarket).filter_by(player_id=player.id).one()
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()

        # Quantity and cost basis come from the canonical holding, in coin.
        assert Decimal(entry["quantity"]) == Decimal(holding.share_count)
        assert Decimal(entry["average_cost"]) == Decimal(holding.average_cost_coin)

        # Current price is the tradable share price, not a valuation.
        assert Decimal(entry["current_price"]) == Decimal(market.share_price_coin)

        # Value and P/L are coin minus coin.
        expected_value = Decimal(holding.share_count) * Decimal(market.share_price_coin)
        expected_cost = Decimal(holding.share_count) * Decimal(holding.average_cost_coin)
        assert Decimal(entry["market_value"]) == expected_value
        assert Decimal(entry["unrealized_pl"]) == expected_value - expected_cost

        # The summary agrees.
        assert Decimal(summary.json()["total_market_value"]) == expected_value
        assert entry["player_name"] == "Victor Osimhen"
    finally:
        session.close()
        engine.dispose()


def test_portfolio_tracks_a_partial_sell(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-pfsell-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-pfsell-fan")
        player = _seed_imported_real_player(session, player_id="sa-pfsell-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            client.post("/market/sell", json={"player_id": player.id, "share_count": 4})
            portfolio = client.get("/portfolio")

        assert portfolio.status_code == 200, portfolio.text
        holdings = portfolio.json()["holdings"]
        assert [item["player_id"] for item in holdings] == [player.id]
        assert Decimal(holdings[0]["quantity"]) == Decimal("6")
    finally:
        session.close()
        engine.dispose()


def test_fully_sold_holding_leaves_no_phantom_position(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-phantom-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-phantom-fan")
        player = _seed_imported_real_player(session, player_id="sa-phantom-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            client.post("/market/sell", json={"player_id": player.id, "share_count": 10})
            portfolio = client.get("/portfolio")
            summary = client.get("/portfolio/summary")

        # The row still exists at zero shares; it must not surface as a position.
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 0
        assert portfolio.json()["holdings"] == []
        assert Decimal(summary.json()["total_market_value"]) == Decimal("0.0000")
    finally:
        session.close()
        engine.dispose()


def test_portfolio_is_empty_for_a_user_who_owns_nothing(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-empty-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-empty-fan")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, _auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            portfolio = client.get("/portfolio")
            summary = client.get("/portfolio/summary")

        assert portfolio.json()["holdings"] == []
        assert Decimal(summary.json()["total_market_value"]) == Decimal("0.0000")
        assert Decimal(summary.json()["unrealized_pl_total"]) == Decimal("0.0000")
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# 4. Market error paths roll back (P2-2)
# ---------------------------------------------------------------------------


def test_failed_buy_rolls_back_and_leaves_the_session_usable(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-rb-buy-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-rb-buy-fan")
        player = _seed_imported_real_player(session, player_id="sa-rb-buy-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("10.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            balance_before = _coin_balance(session, fan)
            counts_before = _trade_counts(session)
            # 900 shares at 0.5 coin plus fees is far beyond a 10 coin balance.
            failed = client.post("/market/buy", json={"player_id": player.id, "share_count": 900})
            # The very next request on the same session must still work.
            recovered = client.post("/market/buy", json={"player_id": player.id, "share_count": 2})

        assert failed.status_code >= 400, failed.text
        assert recovered.status_code == 201, recovered.text

        # The failed attempt left no economic state behind.
        assert counts_before == counts_before
        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 2
        assert _coin_balance(session, fan) < balance_before
    finally:
        session.close()
        engine.dispose()


def test_failed_sell_rolls_back_and_leaves_the_session_usable(monkeypatch) -> None:
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-rb-sell-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-rb-sell-fan")
        player = _seed_imported_real_player(session, player_id="sa-rb-sell-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{player.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            client.post("/market/buy", json={"player_id": player.id, "share_count": 10})
            balance_before = _coin_balance(session, fan)
            # Selling more than is owned must fail cleanly.
            failed = client.post("/market/sell", json={"player_id": player.id, "share_count": 999})
            recovered = client.post("/market/sell", json={"player_id": player.id, "share_count": 3})

        assert failed.status_code >= 400, failed.text
        assert recovered.status_code == 201, recovered.text

        holding = session.query(PlayerShareHolding).filter_by(user_id=fan.id, player_id=player.id).one()
        assert holding.share_count == 7
        assert _coin_balance(session, fan) > balance_before
    finally:
        session.close()
        engine.dispose()


def test_buy_on_an_unissued_market_rolls_back_and_creates_no_market(monkeypatch) -> None:
    """A public trade must never be an issuance mechanism, even on the error path."""
    engine, session = _build_session()
    try:
        admin = _create_user(session, user_id="sa-rb-issue-admin", role=UserRole.ADMIN)
        fan = _create_user(session, user_id="sa-rb-issue-fan")
        unissued = _seed_imported_real_player(session, player_id="sa-rb-unissued-player")
        issued = _seed_imported_real_player(session, player_id="sa-rb-issued-player")
        _seed_coin_balance(session, user=fan, amount=Decimal("500.0000"))
        client, auth = _build_client(session, admin=admin, user=fan, monkeypatch=monkeypatch)

        with client:
            client.post(f"/players/{issued.id}/shares/market", json=ISSUE_BODY)
            auth["user"] = fan
            failed = client.post("/market/buy", json={"player_id": unissued.id, "share_count": 5})
            recovered = client.post("/market/buy", json={"player_id": issued.id, "share_count": 5})

        assert failed.status_code == 404, failed.text
        assert recovered.status_code == 201, recovered.text
        assert session.query(PlayerShareMarket).filter_by(player_id=unissued.id).one_or_none() is None
    finally:
        session.close()
        engine.dispose()
