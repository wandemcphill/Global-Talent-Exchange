"""HTTP-boundary coverage for the live-match tick authorization boundary.

`POST /live-match/sessions/{match_id}/tick` advances a *shared* session clock:
it changes the minute, the score and the phase that every viewer of that match
reads back. These tests pin the boundary at the router, not at the engine, since
that is where the defect lived: the endpoint took no authentication dependency
at all, so any anonymous caller could fast-forward somebody else's match.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth.dependencies import get_current_user
from app.live_match.router import router
from app.live_match.service import LiveMatchEngine, LiveMatchPermissionError, LiveMatchStore

live_match_router_module = importlib.import_module("app.live_match.router")

HOME_USER = SimpleNamespace(id="user-home")
AWAY_USER = SimpleNamespace(id="user-away")
OUTSIDER = SimpleNamespace(id="user-outsider")


@pytest.fixture()
def engine() -> LiveMatchEngine:
    return LiveMatchEngine(LiveMatchStore())


def _build_client(engine: LiveMatchEngine, user: object | None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[live_match_router_module._engine] = lambda: engine
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _create_owned_session(engine: LiveMatchEngine, match_id: str = "owned-match") -> None:
    engine.create(
        match_id=match_id,
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=80,
        away_overall=72,
        home_user_id=HOME_USER.id,
        away_user_id=AWAY_USER.id,
    )


def _create_unowned_session(engine: LiveMatchEngine, match_id: str = "unowned-match") -> None:
    engine.create(
        match_id=match_id,
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=80,
        away_overall=72,
    )


def test_tick_rejects_unauthenticated_callers(engine: LiveMatchEngine) -> None:
    _create_owned_session(engine)
    with _build_client(engine, user=None) as client:
        response = client.post("/live-match/sessions/owned-match/tick")

    assert response.status_code == 401
    session = engine.get("owned-match")
    assert session.minute == 0
    assert session.phase == "pre_match"


def test_tick_rejects_authenticated_non_participants(engine: LiveMatchEngine) -> None:
    _create_owned_session(engine)
    with _build_client(engine, user=OUTSIDER) as client:
        response = client.post("/live-match/sessions/owned-match/tick")

    assert response.status_code == 403
    session = engine.get("owned-match")
    assert session.minute == 0
    assert session.phase == "pre_match"


def test_tick_allows_each_participant(engine: LiveMatchEngine) -> None:
    _create_owned_session(engine)

    with _build_client(engine, user=HOME_USER) as client:
        first = client.post("/live-match/sessions/owned-match/tick")
    assert first.status_code == 200
    assert first.json()["minute"] == 1
    assert first.json()["your_side"] == "home"

    with _build_client(engine, user=AWAY_USER) as client:
        second = client.post("/live-match/sessions/owned-match/tick")
    assert second.status_code == 200
    assert second.json()["minute"] == 2
    assert second.json()["your_side"] == "away"


def test_tick_keeps_unowned_sessions_drivable_by_any_authenticated_user(engine: LiveMatchEngine) -> None:
    """Sessions created without controlling users stay single-player drivable."""
    _create_unowned_session(engine)
    with _build_client(engine, user=OUTSIDER) as client:
        response = client.post("/live-match/sessions/unowned-match/tick")

    assert response.status_code == 200
    assert engine.get("unowned-match").minute == 1


def test_tick_on_unknown_session_is_not_found(engine: LiveMatchEngine) -> None:
    with _build_client(engine, user=HOME_USER) as client:
        response = client.post("/live-match/sessions/does-not-exist/tick")

    assert response.status_code == 404


def test_tick_cannot_reach_another_session_through_a_participant_identity(engine: LiveMatchEngine) -> None:
    """A participant in match A must not be able to advance match B."""
    _create_owned_session(engine, match_id="match-a")
    engine.create(
        match_id="match-b",
        home_id="club-x",
        away_id="club-y",
        home_name="X FC",
        away_name="Y FC",
        home_overall=75,
        away_overall=75,
        home_user_id="user-x",
        away_user_id="user-y",
    )

    with _build_client(engine, user=HOME_USER) as client:
        response = client.post("/live-match/sessions/match-b/tick")

    assert response.status_code == 403
    assert engine.get("match-b").minute == 0
    assert engine.get("match-a").minute == 0


def test_tactics_rejects_non_participants_with_forbidden(engine: LiveMatchEngine) -> None:
    _create_owned_session(engine)
    with _build_client(engine, user=OUTSIDER) as client:
        response = client.post(
            "/live-match/sessions/owned-match/tactics",
            json={"side": "home", "mentality": "attacking"},
        )

    assert response.status_code == 403
    assert engine.get("owned-match").home_tactics.mentality == "balanced"


def test_tactics_rejects_a_participant_steering_the_other_side(engine: LiveMatchEngine) -> None:
    _create_owned_session(engine)
    with _build_client(engine, user=HOME_USER) as client:
        response = client.post(
            "/live-match/sessions/owned-match/tactics",
            json={"side": "away", "mentality": "defensive"},
        )

    assert response.status_code == 403
    assert engine.get("owned-match").away_tactics.mentality == "balanced"


def test_halftime_ready_rejects_non_participants(engine: LiveMatchEngine) -> None:
    _create_owned_session(engine)
    with _build_client(engine, user=OUTSIDER) as client:
        response = client.post(
            "/live-match/sessions/owned-match/halftime/ready",
            json={"side": "home"},
        )

    assert response.status_code == 403
    assert engine.get("owned-match").halftime_ready == set()


def test_assert_participant_leaves_the_session_untouched(engine: LiveMatchEngine) -> None:
    """The guard is a pure read: rejecting a caller must not mutate state."""
    _create_owned_session(engine)

    with pytest.raises(LiveMatchPermissionError):
        engine.assert_participant(match_id="owned-match", user_id=OUTSIDER.id)

    session = engine.get("owned-match")
    assert session.minute == 0
    assert session.events == []


def test_server_ticker_path_still_advances_without_a_user(engine: LiveMatchEngine) -> None:
    """The daemon ticker drives the engine directly and must stay unaffected."""
    _create_owned_session(engine)

    engine.tick("owned-match")

    assert engine.get("owned-match").minute == 1
