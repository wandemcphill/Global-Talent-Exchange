from __future__ import annotations

from decimal import Decimal


def test_health_endpoint_reports_ok(test_client) -> None:
    health_response = test_client.get("/health")
    ready_response = test_client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    assert ready_response.json()["checks"]["database"]["status"] == "ok"


def test_market_players_endpoint_returns_seeded_players(test_client, seeded_demo_environment) -> None:
    response = test_client.get(
        "/api/market/players",
        params={"limit": seeded_demo_environment.players_seeded},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == seeded_demo_environment.players_seeded
    assert payload["offset"] == 0
    assert payload["total"] == seeded_demo_environment.players_seeded
    assert len(payload["items"]) == seeded_demo_environment.players_seeded
    assert all(item["current_value_credits"] > 0 for item in payload["items"])
    assert all(item["player_name"] for item in payload["items"])


def test_wallet_summary_endpoint_returns_seeded_balances(
    test_client,
    seeded_demo_auth_headers,
) -> None:
    response = test_client.get("/api/wallets/summary", headers=seeded_demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["currency"] == "credit"
    assert Decimal(str(payload["available_balance"])) == Decimal("1200.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("1200.0000")


def test_portfolio_endpoint_returns_seeded_portfolio_snapshot(
    test_client,
    seeded_demo_environment,
    seeded_demo_primary_user,
    seeded_demo_auth_headers,
) -> None:
    response = test_client.get("/api/portfolio/snapshot", headers=seeded_demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    expected_player_ids = {
        holding.player_id
        for holding in seeded_demo_environment.sample_holdings
        if holding.owner_username == seeded_demo_primary_user.username
    }

    assert expected_player_ids
    assert payload["user_id"] == seeded_demo_primary_user.user_id
    assert payload["currency"] == "credit"
    assert Decimal(str(payload["available_balance"])) == Decimal("1200.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("1200.0000")
    assert {item["player_id"] for item in payload["holdings"]} == expected_player_ids
    assert all(Decimal(str(item["quantity"])) == Decimal("1.0000") for item in payload["holdings"])
