from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.fairness.fairness_guard import FairnessGuard
from app.fairness.match_integrity_service import MatchIntegrityService
from app.live_matches.service import ensure_live_match_hub
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.replay_archive.persistence import InMemoryReplayArchiveRepository
from app.replay_archive.policy import SpectatorVisibilityPolicyService
from app.replay_archive.service import ReplayArchiveService
from app.routes.match_viewer import router as match_viewer_router
from app.schemas.match_viewer import MatchMode
from app.services.match_timeline_service import MatchTimelineService
from backend.tests.match_engine.helpers import build_request
from backend.tests.test_match_timeline_service import _build_archive_record
from app.match_engine.services.match_simulation_service import MatchSimulationService


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(match_viewer_router)
    app.include_router(match_viewer_router, prefix="/api")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[CompetitionMatch.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return app, session_factory


def _insert_match(session_factory: sessionmaker[Session], match_id: str, metadata_json: dict[str, object]) -> None:
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id="home",
                away_club_id="away",
                metadata_json=metadata_json,
            )
        )
        session.commit()


def test_match_viewer_route_scales_stored_payload_by_mode() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=27))
    base_view = MatchTimelineService().build_from_replay_payload(replay_payload)
    _insert_match(
        session_factory,
        replay_payload.match_id,
        metadata_json={"match_viewer": base_view.model_dump(mode="json")},
    )

    with TestClient(app) as client:
        quick = client.get(f"/api/match-viewer/{replay_payload.match_id}", params={"mode": MatchMode.QUICK.value})
        standard = client.get(f"/api/match-viewer/{replay_payload.match_id}")

    assert quick.status_code == 200
    assert quick.json()["match_mode"] == MatchMode.QUICK.value
    assert 180 <= quick.json()["duration_seconds"] <= 300
    assert standard.status_code == 200
    assert standard.json()["match_mode"] == MatchMode.STANDARD.value
    assert 420 <= standard.json()["duration_seconds"] <= 600


def test_match_viewer_route_scales_archive_fallback_by_mode() -> None:
    app, _ = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=33))
    archive = ReplayArchiveService(
        spectator_policy=SpectatorVisibilityPolicyService(),
        repository=InMemoryReplayArchiveRepository(),
    )
    app.state.replay_archive = archive
    archive.repository.append_record(_build_archive_record(replay_payload, presentation_duration_minutes=4))

    with TestClient(app) as client:
        cinematic = client.get(
            f"/api/match-viewer/{replay_payload.match_id}",
            params={"mode": MatchMode.CINEMATIC.value},
        )

    assert cinematic.status_code == 200
    assert cinematic.json()["match_mode"] == MatchMode.CINEMATIC.value
    assert 600 <= cinematic.json()["duration_seconds"] <= 900


def test_match_viewer_route_builds_live_hub_fallback_when_no_stored_metadata_exists() -> None:
    app, _ = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    hub = ensure_live_match_hub(app, step_interval_seconds=0.01)
    hub.start_stream(replay_payload.match_id, replay_payload, target_runtime_seconds=0.2)

    with TestClient(app) as client:
        timeline = client.get(f"/api/match-viewer/{replay_payload.match_id}")
        session = client.get(f"/api/match-viewer/{replay_payload.match_id}/session")

    assert timeline.status_code == 200
    timeline_payload = timeline.json()
    assert timeline_payload["match_id"] == replay_payload.match_id
    assert timeline_payload["source"] == "live_match_hub"
    assert timeline_payload["home_team"]["team_name"]
    assert timeline_payload["away_team"]["team_name"]
    assert timeline_payload["frames"]

    assert session.status_code == 200
    session_payload = session.json()
    assert session_payload["match_id"] == replay_payload.match_id
    assert session_payload["source"] == "live_match_hub"
    assert session_payload["timeline_proof"]["status"] == "unverified"


def test_match_viewer_route_locks_fairness_protected_payloads_before_full_playback() -> None:
    app, session_factory = _build_app()
    request = build_request(seed=37)
    replay_payload = MatchSimulationService().build_replay_payload(request)
    base_view = MatchTimelineService().build_from_replay_payload(replay_payload)
    locked_context = FairnessGuard().lock_official_request(request)
    fairness = MatchIntegrityService().build_fairness_envelope(
        locked_context=locked_context,
        view_state=base_view,
        balance_metadata={},
        competition_metadata_json={},
    )
    _insert_match(
        session_factory,
        replay_payload.match_id,
        metadata_json={
            "match_viewer": base_view.model_dump(mode="json"),
            "fairness": fairness,
        },
    )

    with TestClient(app) as client:
        response = client.get(f"/api/match-viewer/{replay_payload.match_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deterministic_seed"] is None
    assert payload["duration_seconds"] < base_view.duration_seconds
    assert all(event["event_type"] != "fulltime" for event in payload["events"])


def test_match_viewer_session_reveals_segments_progressively_without_seed_or_fulltime_leak() -> None:
    app, session_factory = _build_app()
    request = build_request(seed=41)
    replay_payload = MatchSimulationService().build_replay_payload(request)
    base_view = MatchTimelineService().build_from_replay_payload(replay_payload)
    locked_context = FairnessGuard().lock_official_request(request)
    fairness = MatchIntegrityService().build_fairness_envelope(
        locked_context=locked_context,
        view_state=base_view,
        balance_metadata={},
        competition_metadata_json={},
    )
    _insert_match(
        session_factory,
        replay_payload.match_id,
        metadata_json={
            "match_viewer": base_view.model_dump(mode="json"),
            "fairness": fairness,
        },
    )

    with TestClient(app) as client:
        initial = client.get(f"/api/match-viewer/{replay_payload.match_id}/session")

        assert initial.status_code == 200
        initial_payload = initial.json()
        assert initial_payload["score_reveal_locked"] is True
        assert initial_payload["has_more_segments"] is True
        assert initial_payload["deterministic_seed"] is None
        assert initial_payload["duration_seconds"] == initial_payload["segment_end_seconds"]
        assert initial_payload["segment_end_seconds"] < base_view.duration_seconds
        assert all(event["event_type"] != "fulltime" for event in initial_payload["events"])

        continued = client.get(
            f"/api/match-viewer/{replay_payload.match_id}/session",
            params={"token": initial_payload["next_segment_token"]},
        )

    assert continued.status_code == 200
    continued_payload = continued.json()
    assert continued_payload["segment_start_seconds"] == initial_payload["segment_end_seconds"]
    assert continued_payload["segment_end_seconds"] > initial_payload["segment_end_seconds"]
