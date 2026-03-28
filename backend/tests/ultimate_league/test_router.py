from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.ultimate_league.router import router


@pytest.fixture()
def client() -> TestClient:
    application = FastAPI()
    application.include_router(router)
    with TestClient(application) as test_client:
        yield test_client


def _competitor(
    competitor_id: str,
    display_name: str,
    elo_rating: int,
    *,
    wins: int = 0,
    draws: int = 0,
    losses: int = 0,
    region: str = "AF-WEST",
) -> dict[str, object]:
    return {
        "competitor_id": competitor_id,
        "display_name": display_name,
        "elo_rating": elo_rating,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "region": region,
        "queue_entered_at": datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
    }


def _register(client: TestClient, prefix: str, *competitors: dict[str, object]) -> None:
    for competitor in competitors:
        response = client.put(f"{prefix}/competitors/{competitor['competitor_id']}", json=competitor)
        assert response.status_code == 200


@pytest.mark.parametrize("prefix", ["/ultimate-league", "/api/ultimate-league"])
def test_competitor_upsert_and_standings_round_trip(client: TestClient, prefix: str) -> None:
    _register(
        client,
        prefix,
        _competitor("bronze-1", "Bronze One", 1180, wins=3, draws=1),
        _competitor("bronze-2", "Bronze Two", 1190, wins=4, draws=0),
    )

    competitor_response = client.get(f"{prefix}/competitors/bronze-1")
    tiers_response = client.get(f"{prefix}/tiers")
    standings_response = client.get(f"{prefix}/standings/bronze")

    assert competitor_response.status_code == 200
    assert tiers_response.status_code == 200
    assert standings_response.status_code == 200
    assert competitor_response.json()["tier"] == "bronze"

    bronze_tier = next(item for item in tiers_response.json() if item["tier"] == "bronze")
    assert bronze_tier["competitor_count"] == 2

    standings = standings_response.json()["entries"]
    assert [entry["competitor"]["competitor_id"] for entry in standings] == ["bronze-2", "bronze-1"]
    assert standings[0]["zone"] == "promotion"


@pytest.mark.parametrize("prefix", ["/ultimate-league", "/api/ultimate-league"])
def test_matchmaking_tournament_and_payout_preview(client: TestClient, prefix: str) -> None:
    _register(
        client,
        prefix,
        _competitor("gold-1", "Gold One", 1580, wins=6),
        _competitor("gold-2", "Gold Two", 1560, wins=5),
        _competitor("gold-3", "Gold Three", 1540, wins=4),
        _competitor("gold-4", "Gold Four", 1520, wins=3),
    )

    matchmaking_response = client.post(
        f"{prefix}/matchmaking/batch",
        json={"competitor_ids": ["gold-1", "gold-2", "gold-3", "gold-4"], "prefer_same_tier": True},
    )
    assert matchmaking_response.status_code == 200
    assert len(matchmaking_response.json()["proposals"]) == 2

    tournament_response = client.post(
        f"{prefix}/tournaments",
        json={
            "tournament_id": "gold-cup-1",
            "tier": "gold",
            "starts_at": datetime(2026, 4, 5, 18, 0, tzinfo=timezone.utc).isoformat(),
            "competitor_ids": ["gold-1", "gold-2", "gold-3", "gold-4"],
            "field_size": 4,
            "parallel_matches": 2,
        },
    )
    assert tournament_response.status_code == 200
    body = tournament_response.json()
    assert body["tournament_id"] == "gold-cup-1"
    assert body["bracket_size"] == 4
    assert [round_view["round_name"] for round_view in body["rounds"]] == ["Semifinal", "Final"]

    payout_response = client.post(
        f"{prefix}/tournaments/gold-cup-1/payouts/preview",
        json={
            "placements": ["gold-1", "gold-2"],
            "gross_pool_gtex": "1000.0000",
            "entrant_count": 4,
        },
    )
    assert payout_response.status_code == 200
    payout_body = payout_response.json()
    assert Decimal(str(payout_body["total_gtex"])) == Decimal("1000.0000")
    assert [Decimal(str(item["amount"])) for item in payout_body["payouts"]] == [
        Decimal("700.0000"),
        Decimal("300.0000"),
    ]
