from __future__ import annotations

from decimal import Decimal


def test_app_boots_and_health_endpoint_works(client) -> None:
    response = client.get("/health")
    ready_response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    assert ready_response.json()["checks"]["database"]["status"] == "ok"


def test_seeded_player_list_works(client, demo_seed) -> None:
    response = client.get(
        "/api/market/players",
        params={"limit": demo_seed.players_seeded},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == demo_seed.players_seeded
    assert len(payload["items"]) == demo_seed.players_seeded
    assert all(item["current_value_credits"] > 0 for item in payload["items"])
    assert all(item["player_name"] for item in payload["items"])


def test_seeded_wallet_summary_works(client, demo_seed, demo_auth_headers) -> None:
    response = client.get("/api/wallets/summary", headers=demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["currency"] == "credit"
    assert Decimal(str(payload["available_balance"])) == Decimal("1200.0000")
    assert Decimal(str(payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(payload["total_balance"])) == Decimal("1200.0000")


def test_seeded_portfolio_works(client, demo_seed, demo_auth_headers) -> None:
    response = client.get("/api/portfolio/snapshot", headers=demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["currency"] == "credit"
    assert Decimal(str(payload["available_balance"])) == Decimal("1200.0000")
    assert payload["holdings"] == []
