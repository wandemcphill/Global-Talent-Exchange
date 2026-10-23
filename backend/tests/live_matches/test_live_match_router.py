from __future__ import annotations

import os
from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import reset_settings_cache
from app.auth.dependencies import get_current_match_user
from app.live_matches.router import router as live_matches_router
from app.live_matches.service import LiveMatchHub
from app.live_matches.unity_access import issue_unity_live_access_token, issue_unity_live_refresh_token
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.broadcast_rights import BroadcastAccessGrant, BroadcastRight, ViewSession
from app.models.competition_match import CompetitionMatch
from app.models.spectator_session import SpectatorSession
from app.models.user import User
from backend.tests.match_engine.helpers import build_request
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()
    app = FastAPI()
    app.include_router(live_matches_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    return app, session_factory


def _insert_match(session_factory: sessionmaker[Session], replay_payload) -> None:
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=replay_payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=replay_payload.summary.home_stats.team_id,
                away_club_id=replay_payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": replay_payload.model_dump(mode="json")},
            )
        )
        session.commit()


def _issue_live_access_token(session_factory: sessionmaker[Session], match_id: str) -> str:
    with session_factory() as session:
        user = User(
            email="viewer@example.com",
            username="viewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        spectator_session = SpectatorSession(match_id=match_id, user_id=user.id)
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)

        token, _ = issue_unity_live_access_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=user.id,
        )
        return token


def _issue_live_refresh_token(session_factory: sessionmaker[Session], match_id: str) -> tuple[str, str]:
    with session_factory() as session:
        user = User(
            email="refresh-viewer@example.com",
            username="refreshviewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        spectator_session = SpectatorSession(match_id=match_id, user_id=user.id)
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)

        token, _ = issue_unity_live_refresh_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=user.id,
        )
        return token, spectator_session.id


def test_match_live_route_requires_unity_access_token() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/match/{replay_payload.match_id}/live")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unity live access token is required."


def test_active_live_matches_route_lists_current_live_matches() -> None:
    app, _session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    hub = LiveMatchHub(step_interval_seconds=0.01)
    app.state.live_match_hub = hub
    hub.start_stream(replay_payload.match_id, replay_payload)
    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="viewer-user-001",
        email="viewer@example.com",
        username="viewer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.get("/api/matches/live/active")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["match_id"] == replay_payload.match_id
    assert body["items"][0]["home_team_name"] == replay_payload.summary.home_stats.team_name
    assert body["items"][0]["away_team_name"] == replay_payload.summary.away_stats.team_name


def test_match_live_route_returns_frames_from_db_when_live_cache_is_empty() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    access_token = _issue_live_access_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.get(
            f"/match/{replay_payload.match_id}/live",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["matchId"] == replay_payload.match_id
    assert body["status"] == "completed"
    assert body["isLive"] is False
    assert body["frames"]
    assert body["timelineEvents"]
    assert body["payloadMode"] == "live_compact"
    assert len(body["frames"]) == 1
    assert len(body["timelineEvents"]) <= 24
    assert len(body["viewer"]["frames"]) == 1
    assert body["viewer"]["match_id"] == replay_payload.match_id
    assert body["score"]["home"] == replay_payload.summary.home_score
    assert body["score"]["away"] == replay_payload.summary.away_score


def test_match_live_route_can_opt_into_full_timeline_payload() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    access_token = _issue_live_access_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.get(
            f"/match/{replay_payload.match_id}/live",
            params={"include_full_timeline": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["payloadMode"] == "full"
    assert len(body["frames"]) > 1
    assert len(body["viewer"]["frames"]) == len(body["frames"])


def test_unity_live_refresh_route_issues_new_live_credentials() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    refresh_token, spectator_session_id = _issue_live_refresh_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.post(
            f"/match/{replay_payload.match_id}/unity-access/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == replay_payload.match_id
    assert body["spectator_session_id"] == spectator_session_id
    assert body["access_token"]
    assert body["refresh_token"]


def test_unity_live_refresh_route_rejects_invalid_refresh_token() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.post(
            f"/match/{replay_payload.match_id}/unity-access/refresh",
            json={"refresh_token": "not-a-real-unity-refresh-token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"]


def test_unity_live_access_requires_session_backed_rights_for_non_generated_matches() -> None:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    reset_settings_cache()

    app = FastAPI()
    app.include_router(live_matches_router)
    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="viewer-user-001",
        email="viewer@example.com",
        username="viewer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.post("/match/restricted-match-001/unity-access")

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Unity live access requires session-backed rights validation for non-generated matches."
    )


def test_unity_live_refresh_route_revalidates_restricted_match_access() -> None:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()

    app = FastAPI()
    app.include_router(live_matches_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CompetitionMatch.__table__,
            User.__table__,
            SpectatorSession.__table__,
            BroadcastAccessGrant.__table__,
            BroadcastRight.__table__,
            ViewSession.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory

    match_id = "restricted-match-002"
    today = date.today()

    with session_factory() as session:
        viewer = User(
            email="restricted-viewer@example.com",
            username="restrictedviewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(viewer)
        session.commit()
        session.refresh(viewer)

        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-locked-001",
                round_id="round-locked-001",
                round_number=1,
                home_club_id="home-club-001",
                away_club_id="away-club-001",
                match_date=today,
                status="live",
                metadata_json={},
            )
        )
        session.add(
            BroadcastRight(
                competition_id="competition-locked-001",
                owner_id="rights-owner-001",
                acquisition_price="10.0000",
                revenue_share_percentage="50.00",
                exclusivity=True,
                start_date=today,
                end_date=today,
                metadata_json={"viewing_fee_coin": "5.0000"},
            )
        )
        spectator_session = SpectatorSession(match_id=match_id, user_id=viewer.id, joined_at=datetime.now(UTC))
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)

        refresh_token, _ = issue_unity_live_refresh_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=viewer.id,
        )

    with TestClient(app) as client:
        response = client.post(
            f"/match/{match_id}/unity-access/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["message"] == "Broadcast rights access is restricted for this match."
    assert body["detail"]["access"]["has_access"] is False
    assert body["detail"]["access"]["requires_payment"] is True


def test_update_and_read_match_tactics() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=42))
    _insert_match(session_factory, replay_payload)
    match_id = replay_payload.match_id

    with TestClient(app) as client:
        # Initial read returns formations and baseline tactics
        get_res = client.get(f"/api/matches/{match_id}/tactics")
        assert get_res.status_code == 200
        get_body = get_res.json()
        assert get_body["match_id"] == match_id
        assert "home" in get_body and "away" in get_body
        assert get_body["home"]["press_intensity"] == 50

        # Submit tactical adjustments for home team
        post_res = client.post(
            f"/api/matches/{match_id}/tactics",
            json={
                "press_intensity": 78,
                "defensive_line": 64,
                "tempo": 82,
                "risk_level": 70,
                "formation": "4-2-3-1",
                "side": "home",
            },
        )
        assert post_res.status_code == 200
        post_body = post_res.json()
        assert post_body["status"] == "accepted"
        assert post_body["side"] == "home"
        assert post_body["tactics"]["press_intensity"] == 78
        assert post_body["tactics"]["defensive_line"] == 64
        assert post_body["tactics"]["tempo"] == 82
        assert post_body["tactics"]["formation"] == "4-2-3-1"
        assert post_body["tactics"]["mentality"] == "attacking"

        # Verify persisted tactics are reflected in GET
        refreshed = client.get(f"/api/matches/{match_id}/tactics")
        assert refreshed.status_code == 200
        refreshed_body = refreshed.json()
        assert refreshed_body["home"]["press_intensity"] == 78
        assert refreshed_body["home"]["defensive_line"] == 64
        assert refreshed_body["home"]["tempo"] == 82
        assert refreshed_body["home"]["formation"] == "4-2-3-1"
        assert refreshed_body["home"]["mentality"] == "attacking"

        # Update away tactics via legacy router path
        legacy_res = client.post(
            f"/matches/{match_id}/tactics",
            json={
                "press_intensity": 40,
                "defensive_line": 35,
                "tempo": 45,
                "risk_level": 25,
                "side": "away",
                "substitutions": [
                    {
                        "out_player_id": "player-away-1",
                        "in_player_id": "player-away-12",
                        "out_player_name": "Striker One",
                        "in_player_name": "Striker Two",
                    }
                ],
            },
        )
        assert legacy_res.status_code == 200
        legacy_body = legacy_res.json()
        assert legacy_body["status"] == "accepted"
        assert legacy_body["side"] == "away"
        assert legacy_body["tactics"]["mentality"] == "defensive"
        assert len(legacy_body["tactics"]["substitutions"]) == 1

        # Invalid side rejects
        bad_side = client.post(
            f"/api/matches/{match_id}/tactics",
            json={"side": "middle"},
        )
        assert bad_side.status_code == 400

        # Non-existent match returns 404
        missing = client.post(
            "/api/matches/non-existent-match-xyz/tactics",
            json={"side": "home"},
        )
        assert missing.status_code == 404
