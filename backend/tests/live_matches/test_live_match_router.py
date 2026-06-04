from __future__ import annotations

import os
import time
from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.events import DomainEvent, InMemoryEventPublisher
from app.core.config import reset_settings_cache
from app.auth.dependencies import get_current_match_user
from app.live_matches.router import router as live_matches_router
from app.live_matches.schemas import LiveMatchOverlayReadinessView, LiveMatchStreamEventView
from app.live_matches.service import LiveMatchHub
from app.live_matches.legacy_runtime_access import (
    issue_legacy_match_runtime_access_token,
    issue_legacy_match_runtime_refresh_token,
)
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.broadcast_rights import BroadcastAccessGrant, BroadcastRight, ViewSession
from app.models.competition_match import CompetitionMatch
from app.models.spectator_session import SpectatorSession
from app.models.user import User
from app.realtime.service import RealtimeHub
from backend.tests.match_engine.helpers import build_request
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_app(*, enable_legacy_runtime: bool = True) -> tuple[FastAPI, sessionmaker[Session]]:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    if enable_legacy_runtime:
        os.environ["GTEX_ENABLE_LEGACY_MATCH_RUNTIME"] = "1"
    else:
        os.environ.pop("GTEX_ENABLE_LEGACY_MATCH_RUNTIME", None)
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
            BroadcastRight.__table__,
            BroadcastAccessGrant.__table__,
            ViewSession.__table__,
        ],
    )
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

        token, _ = issue_legacy_match_runtime_access_token(
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

        token, _ = issue_legacy_match_runtime_refresh_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=user.id,
        )
        return token, spectator_session.id


def test_match_live_route_requires_legacy_runtime_access_token() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/match/{replay_payload.match_id}/live")

    assert response.status_code == 401
    assert response.json()["detail"] == "Legacy match runtime access token is required."


def test_match_live_route_quarantined_by_default() -> None:
    app, session_factory = _build_app(enable_legacy_runtime=False)
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/match/{replay_payload.match_id}/live")

    assert response.status_code == 404
    assert response.json()["detail"] == "Legacy match runtime is quarantined. Use the canonical 2D match center."


def test_active_live_matches_route_lists_current_live_matches() -> None:
    app, _session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    hub = LiveMatchHub(step_interval_seconds=0.01)
    app.state.live_match_hub = hub
    hub.start_stream(replay_payload.match_id, replay_payload, target_runtime_seconds=30.0)
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
    assert body["items"][0]["websocket_path"] == f"/api/matches/{replay_payload.match_id}/stream"
    assert body["items"][0]["commentary_websocket_path"] == (
        f"/api/matches/{replay_payload.match_id}/commentary/stream"
    )
    assert "/realtime/" not in body["items"][0]["websocket_path"].lower()


def test_spectate_session_exposes_canonical_2d_realtime_websockets() -> None:
    app, _session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    hub = LiveMatchHub(step_interval_seconds=0.01)
    app.state.live_match_hub = hub
    app.state.session_factory = None
    hub.start_stream(replay_payload.match_id, replay_payload, target_runtime_seconds=30.0)
    app.dependency_overrides[get_current_match_user] = lambda: User(
        id="viewer-user-001",
        email="viewer@example.com",
        username="viewer",
        password_hash="hashed-password",  # pragma: allowlist secret
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.post(f"/api/matches/{replay_payload.match_id}/spectate")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["match_id"] == replay_payload.match_id
    assert body["channel"] == f"match:{replay_payload.match_id}:events"
    assert body["websocket_path"] == (f"/api/matches/{replay_payload.match_id}/stream?session_id={body['id']}")
    assert body["commentary_websocket_path"] == (
        f"/api/matches/{replay_payload.match_id}/commentary/stream?session_id={body['id']}"
    )
    assert body["presence_websocket_path"] == f"/ws/spectate/{replay_payload.match_id}"
    assert body["replay_route"] == f"/api/matches/{replay_payload.match_id}/replay"
    assert "legacy" not in body["websocket_path"].lower()
    assert "/realtime/" not in body["websocket_path"].lower()
    assert "unity" not in body["websocket_path"].lower()
    assert "3d" not in body["websocket_path"].lower()


def test_live_match_snapshot_marks_missing_authoritative_score_clock_as_blocked_degraded() -> None:
    match_id = "missing-score-clock-contract-001"
    hub = LiveMatchHub(step_interval_seconds=0.01)
    hub.start_synthetic_stream(
        match_id=match_id,
        home_team_id="home-missing-score",
        away_team_id="away-missing-score",
        home_team_name="Missing Home",
        away_team_name="Missing Away",
        base_home_possession=50,
        base_away_possession=50,
        events=[
            LiveMatchStreamEventView(
                match_id=match_id,
                event_id="missing-score-clock-event",
                sequence=1,
                sequence_id=1,
                tick=240,
                minute=12,
                event_type="shot",
                team_id="home-missing-score",
                team="Missing Home",
                team_side="home",
                commentary="Backend-authored event without score-clock truth.",
            )
        ],
        target_runtime_seconds=1.0,
    )

    state = hub.get_state(match_id)
    for _ in range(50):
        state = hub.get_state(match_id)
        if state is not None and state.event_count > 0:
            break
        time.sleep(0.02)

    assert state is not None
    assert state.channel == f"match:{match_id}:events"
    assert state.data_status == "blocked"
    assert state.blocked is True
    assert state.degraded is True
    assert state.snapshot.score_authoritative is False
    assert state.snapshot.clock_authoritative is False
    assert state.snapshot.overlay_readiness.scorebug_ready is False
    assert state.snapshot.overlay_readiness.timeline_ready is True
    assert state.snapshot.stats["available"] is False
    assert state.snapshot.stats["derived_available"] is True
    assert state.snapshot.xg["available"] is False
    missing_codes = {item.code for item in state.snapshot.missing_data}
    assert "missing_authoritative_score" in missing_codes
    assert "missing_authoritative_clock" in missing_codes
    events, _cursor = hub.get_events_since(match_id, 0)
    assert events[0].blocked is True
    assert events[0].score_authoritative is False
    assert events[0].clock_authoritative is False


def test_live_match_snapshot_without_authoritative_events_renders_syncing_contract() -> None:
    match_id = "missing-events-contract-001"
    hub = LiveMatchHub(step_interval_seconds=0.01)
    hub.start_synthetic_stream(
        match_id=match_id,
        home_team_id="home-missing-events",
        away_team_id="away-missing-events",
        home_team_name="Missing Events Home",
        away_team_name="Missing Events Away",
        base_home_possession=50,
        base_away_possession=50,
        events=[],
        target_runtime_seconds=1.0,
    )

    state = hub.get_state(match_id)

    assert state is not None
    assert state.snapshot.events_authoritative is False
    assert state.snapshot.overlay_readiness.timeline_ready is False
    assert state.snapshot.overlay_readiness.scorebug_ready is False
    assert state.snapshot.timeline_event_count == 0
    assert "waiting_for_authoritative_events" in {item.code for item in state.snapshot.missing_data}


def test_live_match_snapshot_uses_backend_authored_stats_xg_momentum_and_intelligence() -> None:
    match_id = "authored-advanced-feed-contract-001"
    hub = LiveMatchHub(step_interval_seconds=0.01)
    hub.start_synthetic_stream(
        match_id=match_id,
        home_team_id="home-authored-feed",
        away_team_id="away-authored-feed",
        home_team_name="Authored Home",
        away_team_name="Authored Away",
        base_home_possession=51,
        base_away_possession=49,
        events=[
            LiveMatchStreamEventView(
                match_id=match_id,
                event_id="authored-advanced-feed-event",
                sequence=1,
                sequence_id=1,
                tick=640,
                minute=32,
                event_type="shot",
                team_id="home-authored-feed",
                team="Authored Home",
                team_side="home",
                commentary="Backend authored shot pressure is building.",
                home_score=1,
                away_score=0,
                clock_label="32:08",
                meta={"phase": "attacking_phase"},
                stats={
                    "source": "match_engine_live_feed",
                    "available": True,
                    "home": {"shots": 6, "on_target": 3},
                    "away": {"shots": 2, "on_target": 1},
                },
                xg={
                    "source": "match_engine_live_feed",
                    "available": True,
                    "home": 0.91,
                    "away": 0.24,
                },
                momentum={
                    "source": "match_engine_live_feed",
                    "available": True,
                    "indicator": "home",
                    "pressure": "sustained",
                },
                overlay_readiness=LiveMatchOverlayReadinessView(
                    status="ready",
                    scorebug_ready=True,
                    timeline_ready=True,
                    commentary_ready=True,
                    stats_ready=True,
                    pitch_2d_ready=True,
                ),
                inspector_state={
                    "status": "ready",
                    "source": "match_engine_live_feed",
                    "latest_event_id": "authored-advanced-feed-event",
                },
                intelligence_state={
                    "status": "ready",
                    "source": "match_engine_live_feed",
                    "xg_available": True,
                    "momentum_available": True,
                },
            )
        ],
        target_runtime_seconds=1.0,
    )

    state = hub.get_state(match_id)
    for _ in range(50):
        state = hub.get_state(match_id)
        if state is not None and state.event_count > 0:
            break
        time.sleep(0.02)

    assert state is not None
    assert state.data_status == "ready"
    assert state.degraded is False
    assert state.blocked is False
    assert state.snapshot.missing_data == []
    assert state.snapshot.score_authoritative is True
    assert state.snapshot.clock_authoritative is True
    assert state.snapshot.phase_authoritative is True
    assert state.snapshot.stats["available"] is True
    assert state.snapshot.stats["home"]["shots"] == 6
    assert state.snapshot.xg["home"] == 0.91
    assert state.snapshot.momentum["indicator"] == "home"
    assert state.snapshot.overlay_readiness.status == "ready"
    assert state.snapshot.overlay_readiness.scorebug_ready is True
    assert state.snapshot.inspector_state["status"] == "ready"
    assert state.snapshot.intelligence_state["status"] == "ready"


def test_spectate_stream_emits_backend_score_clock_frame() -> None:
    app, session_factory = _build_app()
    match_id = "backend-score-clock-match-001"
    home_team_id = "home-club-score-clock"
    home_team_name = "Backend Home"
    realtime = RealtimeHub()
    event_publisher = InMemoryEventPublisher()
    event_publisher.subscribe(realtime.handle_event)
    hub = LiveMatchHub(step_interval_seconds=0.01)
    app.state.realtime = realtime
    app.state.live_match_hub = hub
    hub.start_synthetic_stream(
        match_id=match_id,
        home_team_id=home_team_id,
        away_team_id="away-club-score-clock",
        home_team_name=home_team_name,
        away_team_name="Backend Away",
        base_home_possession=52,
        base_away_possession=48,
        events=[
            LiveMatchStreamEventView(
                match_id=match_id,
                event_id="backend-score-clock-kickoff",
                sequence=1,
                sequence_id=1,
                tick=0,
                minute=1,
                event_type="kickoff",
                team_id=home_team_id,
                team=home_team_name,
                team_side="home",
                commentary="Backend stream is live.",
                home_score=0,
                away_score=0,
                clock_label="01:00",
            )
        ],
        target_runtime_seconds=30.0,
    )
    hub.session_factory = session_factory

    with session_factory() as session:
        viewer = User(
            id="viewer-user-001",
            email="viewer@example.com",
            username="viewer",
            password_hash="hashed-password",  # pragma: allowlist secret
            is_active=True,
        )
        session.add(viewer)
        spectator_session = SpectatorSession(match_id=match_id, user_id=viewer.id)
        session.add(spectator_session)
        session.commit()
        session.refresh(spectator_session)
        session_id = spectator_session.id

    with TestClient(app) as client:
        with client.websocket_connect(f"/api/matches/{match_id}/stream?session_id={session_id}") as ws:
            event_publisher.publish(
                DomainEvent(
                    name="match.events",
                    aggregate_id=match_id,
                    aggregate_type="match",
                    producer="live-match-hub",
                    payload={
                        "match_id": match_id,
                        "event_id": "backend-score-clock-001",
                        "minute": 37,
                        "clock": "37:12",
                        "event_type": "goal",
                        "source_event_type": "goal",
                        "home_score": 2,
                        "away_score": 1,
                        "status": "live",
                        "team_id": home_team_id,
                        "team": home_team_name,
                        "player": "Backend Authored Forward",
                        "commentary": "Backend score-clock checkpoint.",
                        "stats": {
                            "source": "match_engine_live_feed",
                            "available": True,
                            "home": {"shots": 7},
                            "away": {"shots": 3},
                        },
                        "xg": {
                            "source": "match_engine_live_feed",
                            "available": True,
                            "home": 1.1,
                            "away": 0.45,
                        },
                        "momentum": {
                            "source": "match_engine_live_feed",
                            "available": True,
                            "indicator": "home",
                        },
                        "overlay_readiness": {
                            "status": "ready",
                            "scorebug_ready": True,
                            "timeline_ready": True,
                            "commentary_ready": True,
                            "stats_ready": True,
                            "pitch_2d_ready": True,
                            "blockers": [],
                        },
                        "inspector_state": {
                            "status": "ready",
                            "source": "match_engine_live_feed",
                        },
                        "intelligence_state": {
                            "status": "ready",
                            "source": "match_engine_live_feed",
                            "xg_available": True,
                            "momentum_available": True,
                        },
                    },
                )
            )
            frame = ws.receive_json()

    assert frame["type"] == "match_update"
    data = frame["data"]
    assert data["match_id"] == match_id
    assert data["event_id"] == "backend-score-clock-001"
    assert data["minute"] == 37
    assert data["clock"] == "37:12"
    assert data["home_score"] == 2
    assert data["away_score"] == 1
    assert data["status"] == "live"
    assert data["commentary"] == "Backend score-clock checkpoint."
    assert data["data_status"] == "ready"
    assert data["degraded"] is False
    assert data["blocked"] is False
    assert data["stats_authoritative"] is True
    assert data["xg_authoritative"] is True
    assert data["momentum_authoritative"] is True
    assert data["overlay_authoritative"] is True
    assert data["inspector_authoritative"] is True
    assert data["intelligence_authoritative"] is True
    assert data["stats"]["home"]["shots"] == 7
    assert data["xg"]["home"] == 1.1
    assert data["momentum"]["indicator"] == "home"
    assert data["overlay_readiness"]["status"] == "ready"
    assert data["inspector_state"]["status"] == "ready"
    assert data["intelligence_state"]["status"] == "ready"


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


def test_legacy_match_runtime_refresh_route_issues_new_live_credentials() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)
    refresh_token, spectator_session_id = _issue_live_refresh_token(session_factory, replay_payload.match_id)

    with TestClient(app) as client:
        response = client.post(
            f"/match/{replay_payload.match_id}/legacy-runtime-access/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == replay_payload.match_id
    assert body["spectator_session_id"] == spectator_session_id
    assert body["access_token"]
    assert body["refresh_token"]


def test_legacy_match_runtime_refresh_route_rejects_invalid_refresh_token() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.post(
            f"/match/{replay_payload.match_id}/legacy-runtime-access/refresh",
            json={"refresh_token": "not-a-real-legacy-runtime-refresh-token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"]


def test_legacy_match_runtime_access_requires_session_backed_rights_for_non_generated_matches() -> None:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["GTEX_ENABLE_LEGACY_MATCH_RUNTIME"] = "1"
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
        response = client.post("/match/restricted-match-001/legacy-runtime-access")

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Legacy match runtime access requires session-backed rights validation for restricted matches."
    )


def test_legacy_match_runtime_refresh_route_revalidates_restricted_match_access() -> None:
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["GTEX_ENABLE_LEGACY_MATCH_RUNTIME"] = "1"
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

        refresh_token, _ = issue_legacy_match_runtime_refresh_token(
            match_id=match_id,
            spectator_session_id=spectator_session.id,
            viewer_user_id=viewer.id,
        )

    with TestClient(app) as client:
        response = client.post(
            f"/match/{match_id}/legacy-runtime-access/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["message"] == "Broadcast rights access is restricted for this match."
    assert body["detail"]["access"]["has_access"] is False
    assert body["detail"]["access"]["requires_payment"] is True
