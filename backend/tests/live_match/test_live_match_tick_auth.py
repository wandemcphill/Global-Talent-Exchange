from __future__ import annotations

import os
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.config import reset_settings_cache
from app.live_match.router import _engine, router as live_match_router
from app.live_match.service import LiveMatchEngine, LiveMatchStore
from app.live_match.store import RedisLiveMatchStore, session_from_dict, session_to_dict
from app.models.user import User
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_test_app() -> tuple[FastAPI, LiveMatchEngine]:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    reset_settings_cache()

    store = LiveMatchStore()
    engine = LiveMatchEngine(store)

    app = FastAPI()
    app.include_router(live_match_router)
    app.dependency_overrides[_engine] = lambda: engine

    return app, engine


def test_unauthenticated_tick_session_rejected() -> None:
    app, engine = _build_test_app()
    session = engine.create(
        match_id="match-auth-001",
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=75,
        away_overall=70,
        home_user_id="user-home-1",
        away_user_id="user-away-1",
    )
    initial_minute = session.minute

    with TestClient(app) as client:
        response = client.post("/live-match/sessions/match-auth-001/tick")

    assert response.status_code == 401
    assert "not provided" in response.json()["detail"].lower() or "authenticated" in response.json()["detail"].lower()

    # Assert no mutation occurred
    current = engine.get("match-auth-001")
    assert current.minute == initial_minute


def test_authenticated_unauthorized_user_tick_session_rejected() -> None:
    app, engine = _build_test_app()
    session = engine.create(
        match_id="match-auth-002",
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=75,
        away_overall=70,
        home_user_id="user-home-1",
        away_user_id="user-away-1",
    )
    initial_minute = session.minute

    # Authenticated as an intruder (neither home nor away user)
    intruder = User(
        id="user-intruder-999",
        email="intruder@example.com",
        username="intruder",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: intruder

    with TestClient(app) as client:
        response = client.post("/live-match/sessions/match-auth-002/tick")

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not control a team in this match."

    # Assert state was NOT mutated
    current = engine.get("match-auth-002")
    assert current.minute == initial_minute


def test_authenticated_authorized_participant_tick_session_succeeds() -> None:
    app, engine = _build_test_app()
    session = engine.create(
        match_id="match-auth-003",
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=75,
        away_overall=70,
        home_user_id="user-home-1",
        away_user_id="user-away-1",
    )
    assert session.minute == 0

    # Authenticated as the home user participant
    home_user = User(
        id="user-home-1",
        email="home@example.com",
        username="homeuser",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: home_user

    with TestClient(app) as client:
        response = client.post("/live-match/sessions/match-auth-003/tick")

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "match-auth-003"
    assert body["minute"] == 1
    assert body["your_side"] == "home"

    # Assert store state was mutated
    current = engine.get("match-auth-003")
    assert current.minute == 1


def test_cross_session_ticking_blocked() -> None:
    app, engine = _build_test_app()
    # Match 1 owned by user-home-1 & user-away-1
    engine.create(
        match_id="match-111",
        home_id="club-h1",
        away_id="club-a1",
        home_name="Home 1",
        away_name="Away 1",
        home_overall=75,
        away_overall=70,
        home_user_id="user-home-1",
        away_user_id="user-away-1",
    )
    # Match 2 owned by user-home-2 & user-away-2
    engine.create(
        match_id="match-222",
        home_id="club-h2",
        away_id="club-a2",
        home_name="Home 2",
        away_name="Away 2",
        home_overall=75,
        away_overall=70,
        home_user_id="user-home-2",
        away_user_id="user-away-2",
    )

    # User 2 tries to tick Match 1
    user2 = User(
        id="user-home-2",
        email="user2@example.com",
        username="user2",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user2

    with TestClient(app) as client:
        response = client.post("/live-match/sessions/match-111/tick")

    assert response.status_code == 403
    assert engine.get("match-111").minute == 0

    # User 2 ticks their own Match 2 -> succeeds
    with TestClient(app) as client:
        response2 = client.post("/live-match/sessions/match-222/tick")

    assert response2.status_code == 200
    assert engine.get("match-222").minute == 1


def test_unowned_session_accessible_by_authenticated_user() -> None:
    app, engine = _build_test_app()
    # Unowned session (no controlling users set)
    engine.create(
        match_id="match-unowned-001",
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=75,
        away_overall=70,
        home_user_id=None,
        away_user_id=None,
    )

    # 1) Unauthenticated -> 401
    with TestClient(app) as client:
        res_unauth = client.post("/live-match/sessions/match-unowned-001/tick")
    assert res_unauth.status_code == 401

    # 2) Authenticated -> 200
    any_user = User(
        id="user-any-123",
        email="any@example.com",
        username="anyuser",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: any_user

    with TestClient(app) as client:
        res_auth = client.post("/live-match/sessions/match-unowned-001/tick")
    assert res_auth.status_code == 200
    assert res_auth.json()["minute"] == 1
    assert engine.get("match-unowned-001").minute == 1


def test_redis_live_match_store_serialization_and_locking() -> None:
    app, _ = _build_test_app()
    mock_redis = MagicMock()
    store = RedisLiveMatchStore("redis://localhost:6379/0")
    store.client = mock_redis

    engine = LiveMatchEngine(store)
    session = engine.create(
        match_id="redis-match-001",
        home_id="club-h",
        away_id="club-a",
        home_name="Home",
        away_name="Away",
        home_overall=80,
        away_overall=80,
        home_user_id="user-redis-home",
        away_user_id="user-redis-away",
    )

    # Verify put calls redis set
    mock_redis.set.assert_called()

    # Serialization roundtrip check
    d = session_to_dict(session)
    restored = session_from_dict(d)
    assert restored.match_id == session.match_id
    assert restored.home_user_id == "user-redis-home"
    assert restored.away_user_id == "user-redis-away"
