from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.models.competition import Competition
from backend.app.models.competition_prize_rule import CompetitionPrizeRule
from backend.app.models.competition_rule_set import CompetitionRuleSet

def _create(
    client,
    *,
    name: str,
    format: str,
    visibility: str,
    entry_fee: str,
    capacity: int,
    creator_id: str,
    beginner_friendly: bool | None,
    created_at: str,
):
    response = client.post(
        "/api/competitions",
        json={
            "name": name,
            "format": format,
            "visibility": visibility,
            "entry_fee": entry_fee,
            "currency": "credit",
            "capacity": capacity,
            "creator_id": creator_id,
            "beginner_friendly": beginner_friendly,
            "created_at": created_at,
        },
    )
    competition_id = response.json()["id"]
    client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})
    return competition_id


def test_discovery_filters_cover_public_format_fee_and_creator(client) -> None:
    creator_id = "discovery-filter"
    _create(
        client,
        name="Public League",
        format="league",
        visibility="public",
        entry_fee="10.00",
        capacity=10,
        creator_id=creator_id,
        beginner_friendly=True,
        created_at=datetime(2026, 3, 10, tzinfo=timezone.utc).isoformat(),
    )
    _create(
        client,
        name="Invite Cup",
        format="cup",
        visibility="invite_only",
        entry_fee="0.00",
        capacity=8,
        creator_id=creator_id,
        beginner_friendly=False,
        created_at=datetime(2026, 3, 11, tzinfo=timezone.utc).isoformat(),
    )
    _create(
        client,
        name="Private League",
        format="league",
        visibility="private",
        entry_fee="0.00",
        capacity=12,
        creator_id=creator_id,
        beginner_friendly=True,
        created_at=datetime(2026, 3, 9, tzinfo=timezone.utc).isoformat(),
    )

    public_response = client.get("/api/competitions", params={"public_only": True, "creator_id": creator_id})
    assert public_response.status_code == 200
    public_items = public_response.json()["items"]
    assert [item["name"] for item in public_items] == ["Public League"]

    league_response = client.get("/api/competitions", params={"format": "league", "creator_id": creator_id})
    league_names = {item["name"] for item in league_response.json()["items"]}
    assert league_names == {"Public League", "Private League"}

    free_response = client.get("/api/competitions", params={"fee_filter": "free", "creator_id": creator_id})
    free_names = {item["name"] for item in free_response.json()["items"]}
    assert free_names == {"Invite Cup", "Private League"}

    beginner_response = client.get("/api/competitions", params={"beginner_friendly": True, "creator_id": creator_id})
    beginner_names = {item["name"] for item in beginner_response.json()["items"]}
    assert beginner_names == {"Public League", "Private League"}


def test_discovery_sorting_supports_new_prize_pool_fill_rate_and_trending(client) -> None:
    creator_id = "discovery-sort"
    alpha_id = _create(
        client,
        name="Alpha Paid League",
        format="league",
        visibility="public",
        entry_fee="15.00",
        capacity=10,
        creator_id=creator_id,
        beginner_friendly=None,
        created_at=datetime(2026, 3, 9, tzinfo=timezone.utc).isoformat(),
    )
    beta_id = _create(
        client,
        name="Beta Free Cup",
        format="cup",
        visibility="public",
        entry_fee="0.00",
        capacity=8,
        creator_id=creator_id,
        beginner_friendly=None,
        created_at=datetime(2026, 3, 11, tzinfo=timezone.utc).isoformat(),
    )
    gamma_id = _create(
        client,
        name="Gamma Paid Cup",
        format="cup",
        visibility="public",
        entry_fee="25.00",
        capacity=8,
        creator_id=creator_id,
        beginner_friendly=None,
        created_at=datetime(2026, 3, 10, tzinfo=timezone.utc).isoformat(),
    )

    client.post(f"/api/competitions/{alpha_id}/join", json={"user_id": "club-1"})
    client.post(f"/api/competitions/{beta_id}/join", json={"user_id": "club-2"})
    client.post(f"/api/competitions/{beta_id}/join", json={"user_id": "club-3"})
    client.post(f"/api/competitions/{gamma_id}/join", json={"user_id": "club-4"})
    client.post(f"/api/competitions/{gamma_id}/join", json={"user_id": "club-5"})
    client.post(f"/api/competitions/{gamma_id}/join", json={"user_id": "club-6"})

    new_response = client.get("/api/competitions", params={"sort": "new", "creator_id": creator_id})
    assert [item["name"] for item in new_response.json()["items"]] == [
        "Beta Free Cup",
        "Gamma Paid Cup",
        "Alpha Paid League",
    ]

    prize_pool_response = client.get("/api/competitions", params={"sort": "prize_pool", "creator_id": creator_id})
    assert [item["name"] for item in prize_pool_response.json()["items"]] == [
        "Gamma Paid Cup",
        "Alpha Paid League",
        "Beta Free Cup",
    ]

    fill_rate_response = client.get("/api/competitions", params={"sort": "fill_rate", "creator_id": creator_id})
    assert [item["name"] for item in fill_rate_response.json()["items"]] == [
        "Gamma Paid Cup",
        "Beta Free Cup",
        "Alpha Paid League",
    ]

    trending_response = client.get("/api/competitions", params={"sort": "trending", "creator_id": creator_id})
    assert [item["name"] for item in trending_response.json()["items"]] == [
        "Gamma Paid Cup",
        "Beta Free Cup",
        "Alpha Paid League",
    ]


def test_discovery_skips_competitions_missing_rules(client, app_session_factory) -> None:
    creator_id = "discovery-missing-rules"
    competition_id = _create(
        client,
        name="Broken Rule Set Cup",
        format="cup",
        visibility="public",
        entry_fee="20.00",
        capacity=8,
        creator_id=creator_id,
        beginner_friendly=None,
        created_at=datetime(2026, 3, 12, tzinfo=timezone.utc).isoformat(),
    )

    with app_session_factory() as session:
        rule_set = session.scalar(
            select(CompetitionRuleSet).where(
                CompetitionRuleSet.competition_id == competition_id
            )
        )
        prize_rule = session.scalar(
            select(CompetitionPrizeRule).where(
                CompetitionPrizeRule.competition_id == competition_id
            )
        )
        assert rule_set is not None
        assert prize_rule is not None
        session.delete(rule_set)
        session.delete(prize_rule)
        session.commit()

    response = client.get("/api/competitions", params={"creator_id": creator_id})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_discovery_returns_empty_for_malformed_creator_league_metadata(client, app_session_factory) -> None:
    creator_id = "discovery-null-context"
    competition_id = _create(
        client,
        name="Broken Arena Creator League",
        format="league",
        visibility="public",
        entry_fee="0.00",
        capacity=10,
        creator_id=creator_id,
        beginner_friendly=None,
        created_at=datetime(2026, 3, 13, tzinfo=timezone.utc).isoformat(),
    )

    with app_session_factory() as session:
        competition = session.get(Competition, competition_id)
        assert competition is not None
        competition.source_type = "creator_league"
        competition.source_id = None
        competition.metadata_json = {
            "creator_league_config_id": None,
            "creator_league_season_id": None,
            "creator_league_season_tier_id": None,
            "creator_name": {"user_id": None},
        }
        session.commit()

    response = client.get("/api/competitions", params={"creator_id": creator_id})

    assert response.status_code == 200
    assert response.json()["items"] == []
