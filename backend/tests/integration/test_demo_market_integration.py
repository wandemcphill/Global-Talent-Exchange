from __future__ import annotations

import os
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app.core.config import load_settings
from backend.app.ingestion.demo_bootstrap import DemoBootstrapService
from backend.app.ingestion.dev_cli import (
    migrate_database,
    rebuild_demo_market,
    reset_local_database,
    run_simulation_ticks_database,
    seed_demo_liquidity_database,
)
from backend.app.main import create_app
from backend.app.simulation.app_factory import create_demo_simulation_app
from backend.app.simulation.service import DemoMarketSimulationService


def test_login_returns_access_token_for_demo_user(integration_client, demo_secondary_user) -> None:
    response = integration_client.post(
        "/auth/login",
        json={
            "email": demo_secondary_user.email,
            "password": demo_secondary_user.password,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == demo_secondary_user.email


def test_market_players_endpoint_exposes_frontend_demo_states(
    integration_client,
    rising_player,
    falling_player,
    liquid_player,
    illiquid_player,
) -> None:
    response = integration_client.get("/api/market/players", params={"limit": 50})

    assert response.status_code == 200
    payload = response.json()
    items_by_id = {item["player_id"]: item for item in payload["items"]}

    assert rising_player["player_id"] in items_by_id
    assert items_by_id[rising_player["player_id"]]["movement_pct"] > 0
    assert falling_player["player_id"] in items_by_id
    assert items_by_id[falling_player["player_id"]]["movement_pct"] < 0
    assert liquid_player.player_id in items_by_id
    assert illiquid_player.player_id in items_by_id


def test_market_player_detail_returns_frontend_ready_profile(integration_client, rising_player) -> None:
    response = integration_client.get(f"/api/market/players/{rising_player['player_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_id"] == rising_player["player_id"]
    assert payload["identity"]["player_name"] == rising_player["player_name"]
    assert payload["market_profile"]["is_tradable"] is True
    assert payload["value"]["current_value_credits"] is not None
    assert payload["trend"]["drivers"] is not None


def test_seeded_market_has_visible_order_book(integration_client, liquid_player) -> None:
    response = integration_client.get(f"/api/orders/book/{liquid_player.player_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_id"] == liquid_player.player_id
    assert payload["bids"]
    assert payload["asks"]


def test_ticker_responds_for_seeded_players(integration_client, liquid_player) -> None:
    response = integration_client.get(f"/api/market/ticker/{liquid_player.player_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_id"] == liquid_player.player_id
    assert payload["best_bid"] is not None
    assert payload["best_ask"] is not None
    assert payload["spread"] is not None
    assert payload["volume_24h"] > 0


def test_candles_respond_for_seeded_players(integration_client, liquid_player) -> None:
    response = integration_client.get(
        f"/api/market/players/{liquid_player.player_id}/candles",
        params={"interval": "1h", "limit": 6},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_id"] == liquid_player.player_id
    assert payload["interval"] == "1h"
    assert payload["candles"]
    assert any(candle["volume"] > 0 for candle in payload["candles"])
    assert all(candle["high"] >= candle["low"] for candle in payload["candles"])


def test_wallet_and_portfolio_summary_reflect_seeded_holdings(integration_client, demo_auth_headers) -> None:
    wallet_response = integration_client.get("/api/wallets/summary", headers=demo_auth_headers)
    assert wallet_response.status_code == 200
    wallet_payload = wallet_response.json()
    assert wallet_payload["currency"] == "credit"
    assert Decimal(str(wallet_payload["available_balance"])) == Decimal("1200.0000")
    assert Decimal(str(wallet_payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(wallet_payload["total_balance"])) == Decimal("1200.0000")

    summary_response = integration_client.get("/api/portfolio/summary", headers=demo_auth_headers)
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert Decimal(str(summary_payload["cash_balance"])) == Decimal("1200.0000")
    assert Decimal(str(summary_payload["total_market_value"])) > Decimal("0.0000")
    assert Decimal(str(summary_payload["total_equity"])) > Decimal(str(summary_payload["cash_balance"]))

    snapshot_response = integration_client.get("/api/portfolio/snapshot", headers=demo_auth_headers)
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["holdings"]
    assert Decimal(str(snapshot_payload["available_balance"])) == Decimal("1200.0000")

    response = integration_client.get("/portfolio", headers=demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload == snapshot_payload


def test_order_detail_and_cancel_work_for_resting_orders(
    integration_client,
    demo_auth_headers,
    illiquid_player,
) -> None:
    order_book_response = integration_client.get(f"/api/orders/book/{illiquid_player.player_id}")
    assert order_book_response.status_code == 200
    best_ask = Decimal(order_book_response.json()["asks"][0]["price"])

    create_response = integration_client.post(
        "/api/orders",
        headers=demo_auth_headers,
        json={
            "player_id": illiquid_player.player_id,
            "side": "buy",
            "quantity": 1,
            "max_price": str(max((best_ask * Decimal("0.80")).quantize(Decimal("0.0001")), Decimal("0.0100"))),
        },
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    assert created_payload["status"] == "open"
    assert created_payload["execution_summary"]["execution_count"] == 0

    detail_response = integration_client.get(f"/api/orders/{created_payload['id']}", headers=demo_auth_headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == created_payload["id"]
    assert detail_payload["status"] == "open"
    assert Decimal(str(detail_payload["remaining_quantity"])) == Decimal("1")

    wallet_during_order = integration_client.get("/api/wallets/summary", headers=demo_auth_headers)
    assert wallet_during_order.status_code == 200
    assert Decimal(str(wallet_during_order.json()["reserved_balance"])) > Decimal("0.0000")

    cancel_response = integration_client.post(
        f"/api/orders/{created_payload['id']}/cancel",
        headers=demo_auth_headers,
    )
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["id"] == created_payload["id"]
    assert cancel_payload["status"] == "cancelled"

    wallet_after_cancel = integration_client.get("/api/wallets/summary", headers=demo_auth_headers)
    assert wallet_after_cancel.status_code == 200
    assert Decimal(str(wallet_after_cancel.json()["reserved_balance"])) == Decimal("0.0000")


def test_placing_an_order_interacts_with_seeded_liquidity(
    integration_client,
    demo_auth_headers,
    liquid_player,
) -> None:
    order_book_response = integration_client.get(f"/api/orders/book/{liquid_player.player_id}")
    assert order_book_response.status_code == 200
    best_ask = Decimal(order_book_response.json()["asks"][0]["price"])

    response = integration_client.post(
        "/api/orders",
        headers=demo_auth_headers,
        json={
            "player_id": liquid_player.player_id,
            "side": "buy",
            "quantity": 1,
            "max_price": str(best_ask),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] in {"filled", "partially_filled"}
    assert payload["execution_summary"]["execution_count"] >= 1


def test_open_orders_list_returns_recent_orders_with_status_filter(
    integration_client,
    demo_secondary_auth_headers,
    liquid_player,
    illiquid_player,
) -> None:
    illiquid_book_response = integration_client.get(f"/api/orders/book/{illiquid_player.player_id}")
    assert illiquid_book_response.status_code == 200
    illiquid_best_ask = Decimal(illiquid_book_response.json()["asks"][0]["price"])

    open_order_response = integration_client.post(
        "/api/orders",
        headers=demo_secondary_auth_headers,
        json={
            "player_id": illiquid_player.player_id,
            "side": "buy",
            "quantity": 1,
            "max_price": str(max((illiquid_best_ask * Decimal("0.80")).quantize(Decimal("0.0001")), Decimal("0.0100"))),
        },
    )
    assert open_order_response.status_code == 201
    open_order_id = open_order_response.json()["id"]

    liquid_book_response = integration_client.get(f"/api/orders/book/{liquid_player.player_id}")
    assert liquid_book_response.status_code == 200
    liquid_best_ask = Decimal(liquid_book_response.json()["asks"][0]["price"])

    filled_order_response = integration_client.post(
        "/api/orders",
        headers=demo_secondary_auth_headers,
        json={
            "player_id": liquid_player.player_id,
            "side": "buy",
            "quantity": 1,
            "max_price": str(liquid_best_ask),
        },
    )
    assert filled_order_response.status_code == 201
    filled_order_id = filled_order_response.json()["id"]

    all_orders_response = integration_client.get(
        "/api/orders",
        headers=demo_secondary_auth_headers,
        params={"limit": 20},
    )
    assert all_orders_response.status_code == 200
    all_orders_payload = all_orders_response.json()
    assert all_orders_payload["limit"] == 20
    assert all_orders_payload["offset"] == 0
    assert all_orders_payload["total"] >= 2
    all_order_ids = {item["id"] for item in all_orders_payload["items"]}
    assert open_order_id in all_order_ids
    assert filled_order_id in all_order_ids

    open_orders_response = integration_client.get(
        "/api/orders",
        headers=demo_secondary_auth_headers,
        params=[("status", "open"), ("status", "partially_filled"), ("limit", "20")],
    )
    assert open_orders_response.status_code == 200
    open_orders_payload = open_orders_response.json()
    filtered_ids = {item["id"] for item in open_orders_payload["items"]}
    assert open_order_id in filtered_ids
    assert filled_order_id not in filtered_ids
    assert all(item["status"] in {"open", "partially_filled"} for item in open_orders_payload["items"])


def test_app_still_boots_with_demo_simulation_enabled(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'simulation-enabled.db').as_posix()}"
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        bootstrap_app = create_app(settings=settings, engine=engine, run_migration_check=True)
        with TestClient(bootstrap_app):
            DemoBootstrapService(
                session_factory=bootstrap_app.state.session_factory,
                settings=bootstrap_app.state.settings,
                event_publisher=bootstrap_app.state.event_publisher,
            ).seed(player_target_count=12, batch_size=6)
            DemoMarketSimulationService(
                session_factory=bootstrap_app.state.session_factory,
                event_publisher=bootstrap_app.state.event_publisher,
            ).seed_demo_liquidity()

        os.environ["GTE_DEMO_SIMULATION_ENABLED"] = "1"
        os.environ["GTE_DEMO_SIMULATION_BOOTSTRAP"] = "0"
        os.environ["GTE_DEMO_SIMULATION_SEED_ON_BOOT"] = "0"
        os.environ["GTE_DATABASE_URL"] = database_url
        app = create_demo_simulation_app(settings=settings, engine=engine, run_migration_check=True)
        with TestClient(app) as client:
            assert hasattr(app.state, "demo_simulation")
            ticker_response = client.get(f"/api/market/ticker/{app.state.demo_simulation['liquidity']['liquid_player_id']}")
        assert ticker_response.status_code == 200
    finally:
        for key in (
            "GTE_DEMO_SIMULATION_ENABLED",
            "GTE_DEMO_SIMULATION_BOOTSTRAP",
            "GTE_DEMO_SIMULATION_SEED_ON_BOOT",
            "GTE_DATABASE_URL",
        ):
            os.environ.pop(key, None)
        engine.dispose()


def test_demo_operator_flow_smoke(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'demo-operator-flow.db').as_posix()}"

    removed_paths = reset_local_database(database_url)
    assert removed_paths == []

    heads = migrate_database(database_url)
    assert heads

    rebuild = rebuild_demo_market(
        database_url=database_url,
        player_count=12,
        provider="qa-demo",
        signal_provider="qa-demo-signals",
        password="DemoPass123",
        seed=20260311,
        batch_size=6,
        liquid_player_count=3,
        illiquid_player_count=1,
    )
    assert rebuild["seed_summary"]["players_seeded"] == 12
    assert rebuild["seed_summary"]["liquidity_seed"]["trade_executions_seeded"] > 0

    liquidity = seed_demo_liquidity_database(
        database_url=database_url,
        seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )
    assert liquidity["player_count"] == 4
    assert liquidity["trade_executions_seeded"] > 0

    tick_summary = run_simulation_ticks_database(
        database_url=database_url,
        tick_count=2,
        start_tick=1,
        seed=20260311,
        liquid_player_count=3,
        illiquid_player_count=1,
    )
    assert tick_summary["tick_count"] == 2
    assert all(item["orders_created"] > 0 for item in tick_summary["summaries"])
    assert all(item["trade_executions_created"] > 0 for item in tick_summary["summaries"])

    settings = load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    demo_user = rebuild["seed_summary"]["demo_users"][0]

    monkeypatch.setenv("GTE_DATABASE_URL", database_url)
    monkeypatch.setenv("GTE_DEMO_SIMULATION_ENABLED", "1")
    monkeypatch.setenv("GTE_DEMO_SIMULATION_BOOTSTRAP", "0")
    monkeypatch.setenv("GTE_DEMO_SIMULATION_SEED_ON_BOOT", "0")
    monkeypatch.setenv("GTE_DEMO_SIMULATION_PLAYER_COUNT", "12")
    monkeypatch.setenv("GTE_DEMO_SIMULATION_SEED", "20260311")
    monkeypatch.setenv("GTE_DEMO_SIMULATION_LIQUID_PLAYERS", "3")
    monkeypatch.setenv("GTE_DEMO_SIMULATION_ILLIQUID_PLAYERS", "1")

    try:
        app = create_demo_simulation_app(settings=settings, engine=engine, run_migration_check=True)
        with TestClient(app) as client:
            login_response = client.post(
                "/auth/login",
                json={
                    "email": demo_user["email"],
                    "password": demo_user["password"],
                },
            )
            assert login_response.status_code == 200
            auth_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

            ticker_response = client.get(f"/api/market/ticker/{liquidity['liquid_player_id']}")
            assert ticker_response.status_code == 200
            assert ticker_response.json()["spread"] is not None

            wallet_response = client.get("/api/wallets/summary", headers=auth_headers)
            assert wallet_response.status_code == 200
            assert Decimal(str(wallet_response.json()["available_balance"])) == Decimal("1200.0000")
    finally:
        engine.dispose()
