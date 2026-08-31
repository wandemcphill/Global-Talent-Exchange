from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import event, select

from app.models.competition import Competition
from app.models.competition_prize_rule import CompetitionPrizeRule
from app.models.competition_rule_set import CompetitionRuleSet
from app.services.competition_orchestrator import CompetitionOrchestrator


def _create_user_hosted(
    client,
    host: dict[str, str],
    *,
    name: str,
    format: str = "league",
    visibility: str = "public",
    entry_fee: str = "0.00",
    capacity: int = 12,
    beginner_friendly: bool | None = None,
    created_at: datetime | None = None,
    publish: bool = True,
    extra: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "name": name,
        "format": format,
        "visibility": visibility,
        "entry_fee": entry_fee,
        "currency": "credit",
        "capacity": capacity,
        "rules_summary": f"{name} discovery fixture.",
    }
    if beginner_friendly is not None:
        payload["beginner_friendly"] = beginner_friendly
    if created_at is not None:
        payload["created_at"] = created_at.isoformat()
    if extra:
        payload.update(extra)
    response = client.post("/api/competitions", headers=host["headers"], json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["creator_id"] == host["user_id"]
    assert created["host_type"] == "user_hosted"
    competition_id = created["id"]
    if publish:
        publish_response = client.post(
            f"/api/competitions/{competition_id}/publish",
            headers=host["headers"],
            json={"open_for_join": True},
        )
        assert publish_response.status_code == 200, publish_response.text
    return competition_id


def _create_admin_hosted(
    client,
    admin_headers: dict[str, str],
    *,
    name: str,
    format: str = "cup",
    visibility: str = "public",
    entry_fee: str = "0.00",
    capacity: int = 8,
    created_at: datetime | None = None,
    publish: bool = True,
    extra: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "name": name,
        "format": format,
        "visibility": visibility,
        "entry_fee": entry_fee,
        "capacity": capacity,
        "rules_summary": f"{name} admin discovery fixture.",
    }
    if created_at is not None:
        payload["created_at"] = created_at.isoformat()
    if extra:
        payload.update(extra)
    response = client.post("/api/admin/competitions", headers=admin_headers, json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["host_type"] == "gtex_hosted"
    competition_id = created["id"]
    if publish:
        publish_response = client.post(
            f"/api/competitions/{competition_id}/publish",
            headers=admin_headers,
            json={"open_for_join": True},
        )
        assert publish_response.status_code == 200, publish_response.text
    return competition_id


def _join(
    client,
    competition_club_factory,
    *,
    competition_id: str,
    user: dict[str, str],
    club_slug: str,
) -> dict[str, object]:
    club_id = competition_club_factory(
        owner_user_id=user["user_id"],
        slug=club_slug,
        name=club_slug.replace("-", " ").title(),
    )
    response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=user["headers"],
        json={"club_id": club_id},
    )
    assert response.status_code == 200, response.text
    return {"club_id": club_id, "summary": response.json()}


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()["items"]]


def test_discovery_route_bypasses_lazy_module_hydration(app, client) -> None:
    assert app.state.modules_hydrated is False

    response = client.get("/api/competitions")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}
    assert app.state.modules_hydrated is False


def test_competition_creation_requires_authentication(client) -> None:
    response = client.post(
        "/api/competitions",
        json={
            "name": "Anonymous Cup",
            "format": "cup",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 8,
        },
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Authentication credentials were not provided."


def test_discovery_filters_cover_public_format_fee_and_creator(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="discovery-filter-host")
    _create_user_hosted(
        client,
        host,
        name="Public League",
        format="league",
        visibility="public",
        entry_fee="10.00",
        capacity=12,
        beginner_friendly=True,
        created_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        extra={"is_ranked": True},
    )
    _create_user_hosted(
        client,
        host,
        name="Invite Cup",
        format="cup",
        visibility="invite_only",
        entry_fee="0.00",
        capacity=8,
        beginner_friendly=False,
        created_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
        extra={"prize_mode": "none", "is_ranked": False},
    )
    _create_user_hosted(
        client,
        host,
        name="Private League",
        format="league",
        visibility="private",
        entry_fee="0.00",
        capacity=12,
        beginner_friendly=True,
        created_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
        extra={"prize_mode": "none"},
    )

    creator_params = {"creator_id": host["user_id"]}
    assert _names(client.get("/api/competitions", params={**creator_params, "public_only": True})) == ["Public League"]
    assert set(_names(client.get("/api/competitions", params={**creator_params, "format": "league"}))) == {
        "Public League",
        "Private League",
    }
    assert set(_names(client.get("/api/competitions", params={**creator_params, "fee_filter": "free"}))) == {
        "Invite Cup",
        "Private League",
    }
    assert set(_names(client.get("/api/competitions", params={**creator_params, "beginner_friendly": True}))) == {
        "Public League",
        "Private League",
    }


def test_discovery_cards_surface_competition_economics_and_ranked_metadata(
    client,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="discovery-card-host", funded_credit="200.0000")
    paid_id = _create_user_hosted(
        client,
        host,
        name="Ranked Paid Ladder Cup",
        format="cup",
        entry_fee="5.00",
        capacity=12,
        extra={
            "is_ranked": True,
            "online_now": True,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    entrant = auth_user_factory(suffix="discovery-card-entrant", funded_credit="50.0000")
    _join(
        client,
        competition_club_factory,
        competition_id=paid_id,
        user=entrant,
        club_slug="discovery-card-paid-club",
    )

    _create_user_hosted(
        client,
        host,
        name="Ranked Free No Prize",
        format="league",
        entry_fee="0.00",
        capacity=12,
        extra={"is_ranked": True, "prize_mode": "none"},
    )

    _create_user_hosted(
        client,
        host,
        name="Guaranteed Host Prize",
        format="cup",
        entry_fee="0.00",
        capacity=8,
        extra={
            "currency": "coin",
            "prize_mode": "host_funded_fixed",
            "fixed_prizes": {"first": "60.00", "second": "25.00", "third": "15.00"},
            "host_funded_prize_total": "100.00",
        },
    )

    items = {
        item["name"]: item
        for item in client.get("/api/competitions", params={"creator_id": host["user_id"]}).json()["items"]
    }
    paid = items["Ranked Paid Ladder Cup"]
    assert paid["entry_fee"] == "5.00"
    assert paid["gross_pot"] == "5.0000"
    assert paid["platform_fee_pct"] == "0.20"
    assert paid["platform_fee_amount"] == "1.0000"
    assert paid["net_payout_pot"] == "4.0000"
    assert paid["prize_mode"] == "entry_funded"
    assert paid["is_ranked"] is True
    assert paid["online_now"] is True

    free = items["Ranked Free No Prize"]
    assert free["entry_fee"] == "0.00"
    assert free["gross_pot"] == "0.0000"
    assert free["platform_fee_amount"] == "0.0000"
    assert free["prize_mode"] == "none"
    assert free["is_ranked"] is True

    guaranteed = items["Guaranteed Host Prize"]
    assert guaranteed["prize_mode"] == "host_funded_fixed"
    assert Decimal(guaranteed["host_funded_prize_total"]) == Decimal("100.0000")
    assert Decimal(guaranteed["host_funding_required"]) == Decimal("125.0000")
    assert Decimal(guaranteed["host_funding_escrowed"]) == Decimal("125.0000")
    assert Decimal(guaranteed["host_platform_fee"]) == Decimal("25.0000")
    assert {key: Decimal(value) for key, value in guaranteed["fixed_prizes"].items()} == {
        "first": Decimal("60.0000"),
        "second": Decimal("25.0000"),
        "third": Decimal("15.0000"),
    }


def test_discovery_filters_cover_reward_time_ranking_host_and_national_modes(
    client,
    auth_user_factory,
    competition_admin_headers,
) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    host = auth_user_factory(suffix="discovery-mode-host", funded_credit="200.0000")
    _create_user_hosted(
        client,
        host,
        name="User Paid Rewards",
        format="cup",
        entry_fee="5.00",
        capacity=8,
        created_at=now - timedelta(days=2),
        extra={
            "scheduled_start_at": (now + timedelta(hours=2)).isoformat(),
            "is_ranked": True,
            "online_now": True,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    _create_user_hosted(
        client,
        host,
        name="User Free Unranked",
        format="league",
        entry_fee="0.00",
        capacity=12,
        created_at=now - timedelta(days=1),
        extra={
            "scheduled_start_at": (now + timedelta(days=10)).isoformat(),
            "is_ranked": False,
            "prize_mode": "none",
        },
    )
    _create_admin_hosted(
        client,
        competition_admin_headers,
        name="Official Elite Stage",
        format="cup",
        entry_fee="0.00",
        capacity=8,
        extra={
            "featured": True,
            "manual_approval_required": True,
            "min_club_ranking": 1000,
        },
    )
    _create_admin_hosted(
        client,
        competition_admin_headers,
        name="National Rental Cup",
        format="cup",
        entry_fee="0.00",
        capacity=8,
        extra={
            "competition_type": "national_team",
            "special_rules": "Club ranking is not required; entry depends on national team rental affordability.",
            "prize_mode": "none",
        },
    )

    assert "User Paid Rewards" in _names(client.get("/api/competitions", params={"reward_filter": "has_rewards"}))
    assert "User Free Unranked" in _names(client.get("/api/competitions", params={"reward_filter": "no_rewards"}))
    assert "User Free Unranked" in _names(client.get("/api/competitions", params={"fee_filter": "free"}))
    assert "User Paid Rewards" in _names(client.get("/api/competitions", params={"fee_filter": "paid"}))
    assert "User Paid Rewards" in _names(client.get("/api/competitions", params={"starts": "online_now"}))
    assert "User Paid Rewards" in _names(
        client.get(
            "/api/competitions",
            params={
                "start_from": (now + timedelta(hours=1)).isoformat(),
                "start_to": (now + timedelta(hours=3)).isoformat(),
            },
        )
    )
    assert "User Paid Rewards" in _names(client.get("/api/competitions", params={"ranked": True}))
    assert "User Free Unranked" in _names(client.get("/api/competitions", params={"ranked": False}))
    assert {"User Paid Rewards", "User Free Unranked"}.issubset(
        set(_names(client.get("/api/competitions", params={"host_type": "user_hosted"})))
    )
    assert "Official Elite Stage" in _names(client.get("/api/competitions", params={"host_type": "admin"}))
    assert "National Rental Cup" in _names(client.get("/api/competitions", params={"host_type": "national"}))

    official = next(
        item
        for item in client.get("/api/competitions", params={"host_type": "admin"}).json()["items"]
        if item["name"] == "Official Elite Stage"
    )
    assert official["host_type"] == "gtex_hosted"
    assert official["featured"] is True
    assert official["manual_approval_required"] is True
    assert official["eligibility_rules"]["min_club_ranking"] == 1000

    national = next(
        item
        for item in client.get("/api/competitions", params={"host_type": "national"}).json()["items"]
        if item["name"] == "National Rental Cup"
    )
    assert national["competition_type"] == "national_team"
    assert "min_club_ranking" not in national["eligibility_rules"]
    assert "national team rental affordability" in national["special_rules"]


def test_discovery_sorting_supports_new_prize_pool_fill_rate_and_trending(
    client,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="discovery-sort-host")
    alpha_id = _create_user_hosted(
        client,
        host,
        name="Alpha Paid League",
        format="league",
        visibility="public",
        entry_fee="15.00",
        capacity=12,
        created_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
    )
    beta_id = _create_user_hosted(
        client,
        host,
        name="Beta Free Cup",
        format="cup",
        visibility="public",
        entry_fee="0.00",
        capacity=8,
        created_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
        extra={"prize_mode": "none"},
    )
    gamma_id = _create_user_hosted(
        client,
        host,
        name="Gamma Paid Cup",
        format="cup",
        visibility="public",
        entry_fee="25.00",
        capacity=8,
        created_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
    )

    alpha_user = auth_user_factory(suffix="discovery-alpha", funded_credit="100.0000")
    beta_users = [auth_user_factory(suffix=f"discovery-beta-{index}") for index in range(1, 3)]
    gamma_users = [
        auth_user_factory(suffix=f"discovery-gamma-{index}", funded_credit="100.0000") for index in range(1, 4)
    ]

    _join(
        client,
        competition_club_factory,
        competition_id=alpha_id,
        user=alpha_user,
        club_slug="discovery-alpha-club",
    )
    for index, user in enumerate(beta_users, start=1):
        _join(
            client,
            competition_club_factory,
            competition_id=beta_id,
            user=user,
            club_slug=f"discovery-beta-club-{index}",
        )
    for index, user in enumerate(gamma_users, start=1):
        _join(
            client,
            competition_club_factory,
            competition_id=gamma_id,
            user=user,
            club_slug=f"discovery-gamma-club-{index}",
        )

    creator_params = {"creator_id": host["user_id"]}
    assert _names(client.get("/api/competitions", params={**creator_params, "sort": "new"})) == [
        "Beta Free Cup",
        "Gamma Paid Cup",
        "Alpha Paid League",
    ]
    assert _names(client.get("/api/competitions", params={**creator_params, "sort": "prize_pool"})) == [
        "Gamma Paid Cup",
        "Alpha Paid League",
        "Beta Free Cup",
    ]
    assert _names(client.get("/api/competitions", params={**creator_params, "sort": "fill_rate"})) == [
        "Gamma Paid Cup",
        "Beta Free Cup",
        "Alpha Paid League",
    ]
    assert _names(client.get("/api/competitions", params={**creator_params, "sort": "trending"})) == [
        "Gamma Paid Cup",
        "Beta Free Cup",
        "Alpha Paid League",
    ]


def test_discovery_skips_competitions_missing_rules(client, app_session_factory, auth_user_factory) -> None:
    host = auth_user_factory(suffix="discovery-missing-rules-host")
    competition_id = _create_user_hosted(
        client,
        host,
        name="Broken Rule Set Cup",
        format="cup",
        visibility="public",
        entry_fee="20.00",
        capacity=8,
        created_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )

    with app_session_factory() as session:
        rule_set = session.scalar(select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == competition_id))
        prize_rule = session.scalar(
            select(CompetitionPrizeRule).where(CompetitionPrizeRule.competition_id == competition_id)
        )
        assert rule_set is not None
        assert prize_rule is not None
        session.delete(rule_set)
        session.delete(prize_rule)
        session.commit()

    response = client.get("/api/competitions", params={"creator_id": host["user_id"]})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_discovery_returns_empty_for_malformed_creator_league_metadata(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="discovery-null-context-host")
    competition_id = _create_user_hosted(
        client,
        host,
        name="Broken Arena Creator League",
        format="league",
        visibility="public",
        entry_fee="0.00",
        capacity=12,
        created_at=datetime(2026, 3, 13, tzinfo=timezone.utc),
        extra={"prize_mode": "none"},
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

    response = client.get("/api/competitions", params={"creator_id": host["user_id"]})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_discovery_query_budget_is_batched(
    client,
    app_session_factory,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="discovery-query-budget-host")
    competition_ids = [
        _create_user_hosted(
            client,
            host,
            name=f"Batched Discovery {index}",
            format="league" if index % 2 == 0 else "cup",
            visibility="public",
            entry_fee="0.00",
            capacity=12 if index % 2 == 0 else 8,
            beginner_friendly=(index % 2 == 0),
            created_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
            extra={"prize_mode": "none"},
        )
        for index in range(12)
    ]
    for index, competition_id in enumerate(competition_ids):
        for join_index in range((index % 4) + 1):
            user = auth_user_factory(suffix=f"batch-user-{index}-{join_index}")
            _join(
                client,
                competition_club_factory,
                competition_id=competition_id,
                user=user,
                club_slug=f"batch-club-{index}-{join_index}",
            )

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
                creator_id=host["user_id"],
                sort="trending",
            )
        finally:
            event.remove(bind, "after_cursor_execute", _count_query)

    assert payload.total == 12
    assert query_count <= 6
