from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import event, select

from app.models.competition import Competition
from app.models.competition_prize_rule import CompetitionPrizeRule
from app.models.competition_rule_set import CompetitionRuleSet
from app.services.competition_orchestrator import CompetitionOrchestrator

def _create(
    client,
    admin_headers,
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
    client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=admin_headers,
        json={"open_for_join": True},
    )
    return competition_id


def test_discovery_route_bypasses_lazy_module_hydration(app, client) -> None:
    assert app.state.modules_hydrated is False

    response = client.get("/api/competitions")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}
    assert app.state.modules_hydrated is False


def test_discovery_filters_cover_public_format_fee_and_creator(client, competition_admin_headers) -> None:
    creator_id = "discovery-filter"
    _create(
        client,
        competition_admin_headers,
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
        competition_admin_headers,
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
        competition_admin_headers,
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


def test_discovery_sorting_supports_new_prize_pool_fill_rate_and_trending(
    client,
    competition_admin_headers,
    auth_user_factory,
) -> None:
    creator_id = "discovery-sort"
    alpha_id = _create(
        client,
        competition_admin_headers,
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
        competition_admin_headers,
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
        competition_admin_headers,
        name="Gamma Paid Cup",
        format="cup",
        visibility="public",
        entry_fee="25.00",
        capacity=8,
        creator_id=creator_id,
        beginner_friendly=None,
        created_at=datetime(2026, 3, 10, tzinfo=timezone.utc).isoformat(),
    )

    alpha_user = auth_user_factory(suffix="discovery-alpha", funded_credit="100.0000")
    beta_users = [
        auth_user_factory(suffix=f"discovery-beta-{index}")
        for index in range(1, 3)
    ]
    gamma_users = [
        auth_user_factory(suffix=f"discovery-gamma-{index}", funded_credit="100.0000")
        for index in range(1, 4)
    ]

    client.post(
        f"/api/competitions/{alpha_id}/join",
        headers=alpha_user["headers"],
        json={"user_id": alpha_user["user_id"]},
    )
    for user in beta_users:
        client.post(
            f"/api/competitions/{beta_id}/join",
            headers=user["headers"],
            json={"user_id": user["user_id"]},
        )
    for user in gamma_users:
        client.post(
            f"/api/competitions/{gamma_id}/join",
            headers=user["headers"],
            json={"user_id": user["user_id"]},
        )

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


def test_discovery_skips_competitions_missing_rules(client, app_session_factory, competition_admin_headers) -> None:
    creator_id = "discovery-missing-rules"
    competition_id = _create(
        client,
        competition_admin_headers,
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


def test_discovery_returns_empty_for_malformed_creator_league_metadata(
    client,
    app_session_factory,
    competition_admin_headers,
) -> None:
    creator_id = "discovery-null-context"
    competition_id = _create(
        client,
        competition_admin_headers,
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


def test_discovery_query_budget_is_batched(
    client,
    app_session_factory,
    competition_admin_headers,
) -> None:
    creator_id = "discovery-query-budget"
    competition_ids = [
        _create(
            client,
            competition_admin_headers,
            name=f"Batched Discovery {index}",
            format="league" if index % 2 == 0 else "cup",
            visibility="public",
            entry_fee="0.00",
            capacity=10 if index % 2 == 0 else 8,
            creator_id=creator_id,
            beginner_friendly=(index % 2 == 0),
            created_at=datetime(2026, 3, 15, tzinfo=timezone.utc).isoformat(),
        )
        for index in range(12)
    ]
    for index, competition_id in enumerate(competition_ids):
        for join_index in range((index % 4) + 1):
            response = client.post(
                f"/api/competitions/{competition_id}/join",
                json={"user_id": f"batch-user-{index}-{join_index}"},
            )
            assert response.status_code == 200, response.text

    query_count = 0

    def _count_query(*_args, **_kwargs) -> None:
        nonlocal query_count
        query_count += 1

    with app_session_factory() as session:
        bind = session.bind
        assert bind is not None
        event.listen(bind, "after_cursor_execute", _count_query)
        try:
            payload = CompetitionOrchestrator(session).list(
                public_only=True,
                creator_id=creator_id,
                sort="trending",
            )
        finally:
            event.remove(bind, "after_cursor_execute", _count_query)

    assert payload.total == 12
    assert query_count <= 6
