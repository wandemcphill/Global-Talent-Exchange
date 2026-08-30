from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.testclient import TestClient
import pytest

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.ultimate_league.router import router


def mock_get_current_user(x_user_id: str | None = Header(default=None)) -> User:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth header")
    return User(id=x_user_id, email=f"{x_user_id}@example.com", is_active=True)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_current_user] = mock_get_current_user
    with TestClient(application) as test_client:
        yield test_client


def _competitor(
    competitor_id: str,
    display_name: str,
    elo_rating: int,
    *,
    user_id: str | None = None,
    wins: int = 0,
    draws: int = 0,
    losses: int = 0,
    region: str = "AF-WEST",
) -> dict[str, object]:
    return {
        "competitor_id": competitor_id,
        "display_name": display_name,
        "elo_rating": elo_rating,
        "user_id": user_id or competitor_id,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "region": region,
        "queue_entered_at": datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
    }


def _register(client: TestClient, prefix: str, *competitors: dict[str, object]) -> None:
    for competitor in competitors:
        user_id = str(competitor.get("user_id") or competitor["competitor_id"])
        response = client.put(
            f"{prefix}/competitors/{competitor['competitor_id']}",
            json=competitor,
            headers={"X-User-Id": user_id},
        )
        assert response.status_code == 200, response.text


@pytest.mark.parametrize("prefix", ["/ultimate-league", "/api/ultimate-league"])
def test_auth_behavioral_requirements(client: TestClient, prefix: str) -> None:
    payload_comp1 = _competitor("comp-1", "Competitor One", 1200, user_id="owner-1")
    payload_comp2 = _competitor("comp-2", "Competitor Two", 1250, user_id="owner-2")

    # 1. unauthenticated request -> 401
    unauth_resp = client.put(f"{prefix}/competitors/comp-1", json=payload_comp1)
    assert unauth_resp.status_code == 401

    # 2. authenticated owner updates own competitor -> success (200)
    auth_resp = client.put(
        f"{prefix}/competitors/comp-1",
        json=payload_comp1,
        headers={"X-User-Id": "owner-1"},
    )
    assert auth_resp.status_code == 200
    assert auth_resp.json()["user_id"] == "owner-1"

    # Register comp-2 for match result tests
    auth_comp2_resp = client.put(
        f"{prefix}/competitors/comp-2",
        json=payload_comp2,
        headers={"X-User-Id": "owner-2"},
    )
    assert auth_comp2_resp.status_code == 200

    # 3. authenticated user attempts to update another user's competitor -> 403
    forbidden_update_resp = client.put(
        f"{prefix}/competitors/comp-1",
        json=payload_comp1,
        headers={"X-User-Id": "other-user"},
    )
    assert forbidden_update_resp.status_code == 403

    # 4. authenticated participant submits own match result -> success (200)
    match_payload = {
        "home_competitor_id": "comp-1",
        "away_competitor_id": "comp-2",
        "home_score": 2,
        "away_score": 1,
        "importance": 1.0,
    }
    match_participant_resp = client.post(
        f"{prefix}/matches/result",
        json=match_payload,
        headers={"X-User-Id": "owner-1"},
    )
    assert match_participant_resp.status_code == 200

    # 5. authenticated non-participant submits result -> 403
    match_non_participant_resp = client.post(
        f"{prefix}/matches/result",
        json=match_payload,
        headers={"X-User-Id": "outsider-user"},
    )
    assert match_non_participant_resp.status_code == 403

    # 6. malformed/path mismatch -> existing 409 behavior preserved
    mismatch_payload = _competitor("comp-1", "Competitor One", 1200, user_id="owner-1")
    mismatch_resp = client.put(
        f"{prefix}/competitors/path-mismatch-id",
        json=mismatch_payload,
        headers={"X-User-Id": "owner-1"},
    )
    assert mismatch_resp.status_code == 409


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
        headers={"X-User-Id": "gold-1"},
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
        headers={"X-User-Id": "gold-1"},
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


@pytest.mark.parametrize("prefix", ["/ultimate-league", "/api/ultimate-league"])
def test_tactical_presets_and_competitor_availability_round_trip(client: TestClient, prefix: str) -> None:
    _register(
        client,
        prefix,
        _competitor("seller-1", "Seller One", 1510, wins=4, region="AF-WEST") | {"fatigue": 0.10},
        _competitor("buyer-1", "Buyer One", 1490, wins=3, region="AF-WEST") | {"fatigue": 0.20},
        _competitor("injured-1", "Injured One", 1480, wins=2, region="AF-WEST") | {"injury_status": "hamstring"},
    )

    ready_response = client.get(f"{prefix}/competitors/seller-1")
    injured_response = client.get(f"{prefix}/competitors/injured-1")
    assert ready_response.status_code == 200
    assert injured_response.status_code == 200
    assert ready_response.json()["availability_status"] == "ready"
    assert injured_response.json()["availability_status"] == "injured"

    preset_response = client.post(
        f"{prefix}/tactical-presets",
        json={
            "seller_competitor_id": "seller-1",
            "title": "Counter Press 4-3-3",
            "formation": "4-3-3",
            "style": "counter press",
            "price_gtex": "15.0000",
            "tags": ["press", "wide"],
            "fatigue_ceiling": 0.70,
            "injury_cover_enabled": True,
        },
        headers={"X-User-Id": "seller-1"},
    )
    assert preset_response.status_code == 200, preset_response.text
    preset = preset_response.json()
    assert preset["seller_competitor_id"] == "seller-1"
    assert preset["injury_cover_enabled"] is True

    listing_response = client.get(f"{prefix}/tactical-presets")
    assert listing_response.status_code == 200
    assert any(item["preset_id"] == preset["preset_id"] for item in listing_response.json())

    purchase_response = client.post(
        f"{prefix}/tactical-presets/{preset['preset_id']}/purchase",
        json={"buyer_competitor_id": "buyer-1"},
        headers={"X-User-Id": "buyer-1"},
    )
    assert purchase_response.status_code == 200, purchase_response.text
    assert purchase_response.json()["preset_id"] == preset["preset_id"]

    result_response = client.post(
        f"{prefix}/matches/result",
        json={
            "home_competitor_id": "seller-1",
            "away_competitor_id": "buyer-1",
            "home_score": 2,
            "away_score": 1,
            "importance": 2.5,
        },
        headers={"X-User-Id": "seller-1"},
    )
    assert result_response.status_code == 200, result_response.text
    body = result_response.json()
    assert body["home"]["fatigue"] > 0.10
    assert body["away"]["fatigue"] > 0.20
