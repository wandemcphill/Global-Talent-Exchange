from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine

from app.core.module import DomainModule


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-create-publish-app") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-create-publish-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "GTE_INGESTION_PROVIDER": "mock",
        "GTE_REAL_PLAYER_IMPORT_PROVIDER": "mock",
        "GTE_RUN_STARTUP_SEEDING": "0",
        "GTE_TASK_QUEUE_ENABLED": "0",
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}

    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        reset_settings_cache()
        yield load_settings()
    finally:
        reset_settings_cache()
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        reset_settings_cache()


@pytest.fixture(scope="module")
def app(test_settings):
    from app.main import create_app

    modules = (
        DomainModule("auth", router_path="app.auth.router:router"),
        DomainModule("competitions", router_path="app.routes.competitions:router"),
    )
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(
        settings=test_settings,
        engine=engine,
        modules=modules,
        run_migration_check=True,
    )
    yield application
    startup_thread = getattr(application.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    engine.dispose()


def _error_message(response) -> str:
    payload = response.json()
    return payload.get("message") or payload.get("detail")


def test_create_patch_publish_join_leave_flow(
    client,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="create-publish-host")
    entrant = auth_user_factory(suffix="create-publish-join-leave", funded_credit="25.00")
    entrant_club_id = competition_club_factory(
        owner_user_id=entrant["user_id"],
        slug="create-publish-join-leave-club",
        name="Create Publish Join Leave Club",
    )
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Weekend Skills League",
            "format": "league",
            "visibility": "public",
            "entry_fee": "12.50",
            "currency": "credit",
            "capacity": 12,
            "creator_id": "host-1",
            "creator_name": "Host One",
            "platform_fee_pct": "0.10",
            "host_fee_pct": "0.05",
            "payout_structure": [
                {"place": 1, "percent": "0.50"},
                {"place": 2, "percent": "0.30"},
                {"place": 3, "percent": "0.20"},
            ],
            "rules_summary": "Highest fantasy points across the league calendar.",
            "beginner_friendly": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    competition_id = created["id"]
    assert created["status"] == "draft"
    assert created["name"] == "Weekend Skills League"
    assert created["creator_id"] == host["user_id"]
    assert created["participant_count"] == 0
    assert created["entry_fee"] == "12.50"
    assert created["platform_fee_pct"] == "0.30"
    assert created["host_fee_pct"] == "0.05"
    assert created["prize_pool"] == "0.0000"
    assert created["join_eligibility"] == {
        "eligible": False,
        "reason": "competition_not_open",
        "requires_invite": False,
        "requires_passcode": False,
    }

    patch_response = client.patch(
        f"/api/competitions/{competition_id}",
        headers=host["headers"],
        json={
            "name": "Weekend Skills League Reloaded",
            "capacity": 16,
            "rules_summary": "Transparent player-vs-player fantasy scoring.",
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["name"] == "Weekend Skills League Reloaded"
    assert patched["capacity"] == 16
    assert patched["rules_summary"] == "Transparent player-vs-player fantasy scoring."

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["status"] == "open"

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"club_id": entrant_club_id, "user_name": "Club 22"},
    )
    assert join_response.status_code == 200
    joined = join_response.json()
    assert joined["participant_count"] == 1
    assert joined["join_eligibility"] == {
        "eligible": True,
        "reason": "already_joined",
        "requires_invite": False,
        "requires_passcode": False,
    }
    assert joined["prize_pool"] == "8.1250"

    detail_response = client.get(f"/api/competitions/{competition_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == "Weekend Skills League Reloaded"
    assert detail["participant_count"] == 1
    assert detail["status"] == "open"

    summary_response = client.get(f"/api/competitions/{competition_id}/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["id"] == competition_id
    assert summary["rules_summary"] == "Transparent player-vs-player fantasy scoring."

    leave_response = client.post(
        f"/api/competitions/{competition_id}/leave",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"]},
    )
    assert leave_response.status_code == 200
    left = leave_response.json()
    assert left["participant_count"] == 0
    assert left["status"] == "open"


def test_join_returns_conflict_before_publish(client, auth_user_factory, competition_club_factory) -> None:
    host = auth_user_factory(suffix="join-before-publish-host")
    entrant = auth_user_factory(suffix="join-before-publish")
    entrant_club_id = competition_club_factory(
        owner_user_id=entrant["user_id"],
        slug="join-before-publish-club",
        name="Join Before Publish Club",
    )
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Private Draft Cup",
            "format": "cup",
            "visibility": "private",
            "entry_fee": "5.00",
            "currency": "credit",
            "capacity": 8,
            "creator_id": "host-2",
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
        },
    )
    competition_id = create_response.json()["id"]

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"club_id": entrant_club_id},
    )
    assert join_response.status_code == 409
    assert _error_message(join_response) == "competition_not_open"


def test_creator_can_publish_and_launch_full_competition(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="creator-host")
    challenger = auth_user_factory(suffix="creator-challenger")

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Creator Clash League",
            "format": "league",
            "type": "user_hosted",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user_id"],
            "creator_name": "Host Club",
            "payout_structure": [
                {"place": 1, "percent": "1.00"},
            ],
            "rules": "Winner takes the league match.",
        },
    )
    assert create_response.status_code == 201
    competition_id = create_response.json()["id"]
    assert create_response.json()["match_type"] == "user_hosted"

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "open"

    host_join = client.post(
        "/api/competitions/join",
        headers=host["headers"],
        json={
            "competition_id": competition_id,
            "user_id": host["user_id"],
            "user_name": "Host Club",
        },
    )
    assert host_join.status_code == 200
    assert host_join.json()["status"] == "open"

    challenger_join = client.post(
        "/api/competitions/join",
        headers=challenger["headers"],
        json={
            "competition_id": competition_id,
            "user_id": challenger["user_id"],
            "user_name": "Challenger Club",
        },
    )
    assert challenger_join.status_code == 200
    launched = challenger_join.json()
    assert launched["status"] == "live"
    assert launched["participant_count"] == 2

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures")
    assert fixtures.status_code == 200
    fixture_payload = fixtures.json()
    assert len(fixture_payload) == 1
    assert fixture_payload[0]["status"] == "scheduled"

    events = client.get(f"/api/competitions/{competition_id}/matches/{fixture_payload[0]['id']}/events")
    assert events.status_code == 200
    assert events.json() == []


def test_non_owner_cannot_publish_someone_elses_competition(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="creator-owner")
    intruder = auth_user_factory(suffix="creator-intruder")

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Private Owner League",
            "format": "league",
            "type": "user_hosted",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "creator_id": host["user_id"],
            "creator_name": "Owner Club",
            "payout_structure": [
                {"place": 1, "percent": "1.00"},
            ],
            "rules": "Only the owner should be allowed to publish.",
        },
    )
    assert create_response.status_code == 201
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=intruder["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 403
    assert _error_message(publish_response) == "Admin access is required for this action."
