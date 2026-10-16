from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.main import create_app


@pytest.fixture()
def contract_app(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'gte_contract_test.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        yield app, client


def _resolve_response_component(openapi: dict, schema: dict) -> tuple[str, dict]:
    if "$ref" in schema:
        component_name = schema["$ref"].rsplit("/", 1)[-1]
        return component_name, openapi["components"]["schemas"][component_name]

    items = schema.get("items", {})
    if "$ref" in items:
        component_name = items["$ref"].rsplit("/", 1)[-1]
        return component_name, openapi["components"]["schemas"][component_name]

    raise AssertionError(f"Unsupported response schema shape: {schema}")


def test_target_api_contracts_are_documented_with_stable_operation_ids(contract_app) -> None:
    app, _client = contract_app
    openapi = app.openapi()
    expected_operations = {
        ("/api/orders", "get"): "api_list_orders_api_orders_get",
        ("/api/orders", "post"): "api_place_order_api_orders_post",
        ("/api/orders/book/{player_id}", "get"): "api_get_order_book_api_orders_book_player_id_get",
        ("/api/orders/{order_id}", "get"): "api_get_order_detail_api_orders_order_id_get",
        ("/api/orders/{order_id}/cancel", "post"): "api_cancel_order_api_orders_order_id_cancel_post",
        ("/api/market/ticker/{player_id}", "get"): "get_market_ticker_api_market_ticker__player_id__get",
        (
            "/api/market/players/{player_id}/candles",
            "get",
        ): "get_market_player_candles_api_market_players__player_id__candles_get",
        ("/api/market/movers", "get"): "get_market_movers_api_market_movers_get",
        ("/api/portfolio", "get"): "api_get_portfolio_api_portfolio_get",
        ("/api/portfolio/snapshot", "get"): "api_get_portfolio_snapshot_api_portfolio_snapshot_get",
        ("/api/portfolio/summary", "get"): "api_get_portfolio_summary_api_portfolio_summary_get",
        ("/api/wallets/accounts", "get"): "api_list_wallet_accounts_api_wallets_accounts_get",
        ("/api/wallets/summary", "get"): "api_get_wallet_summary_api_wallets_summary_get",
        ("/api/wallets/ledger", "get"): "api_list_wallet_ledger_api_wallets_ledger_get",
        ("/api/wallets/payment-events", "post"): "api_create_payment_event_api_wallets_payment-events_post",
    }
    legacy_aliases = {
        "/orders": "/api/orders",
        "/orders/book/{player_id}": "/api/orders/book/{player_id}",
        "/orders/{order_id}": "/api/orders/{order_id}",
        "/orders/{order_id}/cancel": "/api/orders/{order_id}/cancel",
        "/market/ticker/{player_id}": "/api/market/ticker/{player_id}",
        "/market/players/{player_id}/candles": "/api/market/players/{player_id}/candles",
        "/market/movers": "/api/market/movers",
        "/wallets/accounts": "/api/wallets/accounts",
        "/wallets/summary": "/api/wallets/summary",
        "/wallets/ledger": "/api/wallets/ledger",
        "/wallets/payment-events": "/api/wallets/payment-events",
    }

    operation_ids = []
    for methods in openapi["paths"].values():
        for payload in methods.values():
            operation_ids.append(payload["operationId"])
    assert len(operation_ids) == len(set(operation_ids))

    for (path, method), operation_id in expected_operations.items():
        assert path in openapi["paths"]
        operation = openapi["paths"][path][method]
        assert operation["operationId"] == operation_id
        status_code = "201" if method == "post" and path in {"/api/orders", "/api/wallets/payment-events"} else "200"
        schema = operation["responses"][status_code]["content"]["application/json"]["schema"]
        component_name, component_schema = _resolve_response_component(openapi, schema)
        assert component_name in openapi["components"]["schemas"]
        assert "example" in component_schema

    for legacy_path, api_path in legacy_aliases.items():
        assert legacy_path in openapi["paths"]
        assert api_path in openapi["paths"]

    assert "/api/api/orders" not in openapi["paths"]
    assert "/api/api/orders/book/{player_id}" not in openapi["paths"]
    assert "/api/api/orders/{order_id}" not in openapi["paths"]
    assert "/api/api/orders/{order_id}/cancel" not in openapi["paths"]


def test_versioned_contract_paths_publish_standard_response_and_error_schemas(contract_app) -> None:
    app, _client = contract_app
    openapi = app.openapi()

    assert "/auth/register" not in openapi["paths"]
    assert "/api/auth/register" not in openapi["paths"]
    assert "/api/v2/auth/register" not in openapi["paths"]
    assert "/api/v2/orders" in openapi["paths"]
    assert "/api/v2/auth/signup/user" in openapi["paths"]
    assert "/api/v2/auth/signup/creator" in openapi["paths"]
    assert "/api/v2/auth/signup/trader" in openapi["paths"]
    assert "/api/v2/trader/overview" in openapi["paths"]
    assert "/api/v2/trader/markets" in openapi["paths"]
    assert "/api/v2/trader/orders" in openapi["paths"]
    assert "/api/v2/trader/p2p" in openapi["paths"]
    assert "/api/v2/trader/watchlist" in openapi["paths"]
    assert "/api/v2/trader/security/totp/setup" in openapi["paths"]
    assert "/api/v2/national-team-engine/competitions" in openapi["paths"]
    assert "/api/v2/national-team-engine/rankings" in openapi["paths"]
    assert "/api/v2/regen-universe/national-regens" in openapi["paths"]
    assert "/api/v2/wallets/accounts" in openapi["paths"]

    list_orders = openapi["paths"]["/api/v2/orders"]["get"]
    success_schema_ref = list_orders["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    success_component = openapi["components"]["schemas"][success_schema_ref.rsplit("/", 1)[-1]]
    assert success_component["required"] == ["success", "data"]
    assert success_component["properties"]["success"]["enum"] == [True]
    assert "data" in success_component["properties"]

    error_schema_ref = list_orders["responses"]["401"]["content"]["application/json"]["schema"]["$ref"]
    error_component = openapi["components"]["schemas"][error_schema_ref.rsplit("/", 1)[-1]]
    assert error_component["required"] == ["error", "message", "code"]
    assert error_component["properties"]["error"]["enum"] == [True]

    place_order = openapi["paths"]["/api/v2/orders"]["post"]
    assert "requestBody" in place_order
    request_schema = place_order["requestBody"]["content"]["application/json"]["schema"]
    assert "$ref" in request_schema

    public_account_type = openapi["components"]["schemas"]["PublicAccountType"]
    assert public_account_type["enum"] == ["user", "creator", "coin_trader"]
    assert "admin" not in public_account_type["enum"]
    assert "super_admin" not in public_account_type["enum"]


@pytest.mark.parametrize("path", ["/auth/register", "/api/auth/register", "/api/v2/auth/register"])
def test_old_public_register_is_removed_from_contract_and_returns_gone(contract_app, path: str) -> None:
    _app, client = contract_app
    response = client.post(
        path,
        json={
            "email": "contract-user@example.com",
            "full_name": "Contract User",
            "phone_number": "08000000000",
            "is_over_18": True,
            "region_code": "NG",
            "password": "SuperSecret1",
        },
    )

    assert response.status_code == 410, response.text


def test_versioned_signup_user_wraps_success_envelope(contract_app) -> None:
    _app, client = contract_app
    response = client.post(
        "/api/v2/auth/signup/user",
        headers={"X-API-Version": "2"},
        json={
            "email": "contract-user@example.com",
            "full_name": "Contract User",
            "username": "contract_user",
            "country": "NG",
            "state": "Lagos",
            "city": "Lagos",
            "password": "SuperSecret1",
            "club_name": "Contract Sporting",
            "club_short_tag": "CSP",
            "club_country": "NG",
            "club_state": "Lagos",
            "club_locality": "Yaba",
            "club_type": "academy",
            "football_identity": "club_owner",
            "compliance": {
                "government_id_attachment_id": "gov-contract",
                "selfie_attachment_id": "selfie-contract",
                "country_confirmation": "NG",
            },
        },
    )

    assert response.status_code < 300, response.text
    payload = response.json()
    assert payload["success"] is True
    assert "error" not in payload
    assert "code" not in payload
    assert "access_token" in payload["data"]


def test_contract_guard_does_not_turn_valid_or_unknown_routes_into_gone(contract_app) -> None:
    _app, client = contract_app

    valid_response = client.get("/world-super-cup/countdown")
    assert valid_response.status_code == 200, valid_response.text

    unknown_response = client.get("/api/not-a-real-route")
    assert unknown_response.status_code == 404, unknown_response.text

    legacy_unknown_response = client.get("/api/v1/not-a-real-route")
    assert legacy_unknown_response.status_code == 404, legacy_unknown_response.text
