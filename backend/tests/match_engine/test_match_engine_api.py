from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings, reset_settings_cache
from app.db import get_session
from app.match_engine.api.router import router as match_engine_router
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from backend.tests.match_engine.helpers import build_request


def _artifact_root(name: str) -> Path:
    root = Path(__file__).resolve().parents[3] / ".codex_tmp" / f"{name}_{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_app(storage_root: Path | None = None) -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(match_engine_router)
    if storage_root is not None:
        reset_settings_cache()
        settings = get_settings()
        app.state.settings = replace(
            settings,
            media_storage=replace(settings.media_storage, storage_root=storage_root),
        )

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


def _build_payload_with_manifestable_highlights() -> object:
    service = MatchSimulationService()
    for seed in range(1, 120):
        replay_payload = service.build_replay_payload(build_request(seed=seed, match_id=f"match-{seed:03d}"))
        if any(clip.event_id is not None for clip in replay_payload.summary.highlight_package):
            return replay_payload
    raise AssertionError("Expected a replay payload with event-backed highlight clips.")


def test_match_engine_routes_expose_render_sync_and_post_match_analytics() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=58))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        render_sync = client.get(f"/api/match-engine/render-sync/{replay_payload.match_id}")
        analytics = client.get(f"/api/match-engine/analytics/{replay_payload.match_id}")

    assert render_sync.status_code == 200
    assert analytics.status_code == 200

    render_body = render_sync.json()
    analytics_body = analytics.json()

    assert render_body["match_id"] == replay_payload.match_id
    assert render_body["seed"] == replay_payload.seed
    assert render_body["events"]
    assert analytics_body["match_id"] == replay_payload.match_id
    assert analytics_body["score"] == f"{replay_payload.summary.home_score}-{replay_payload.summary.away_score}"
    assert analytics_body["shot_map"]
    assert analytics_body["team_heatmaps"]


def test_match_engine_simulate_route_returns_unity_ready_contract() -> None:
    app, _ = _build_app()
    request_payload = build_request(seed=58, match_id="unity-ready-match")

    with TestClient(app) as client:
        response = client.post("/api/match-engine/simulate", json=request_payload.model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["match_id"] == "unity-ready-match"
    assert body["score"]["home"] >= 0
    assert body["score"]["away"] >= 0
    assert body["stats"]["home"]["team_id"] == request_payload.home_team.team_id
    assert body["stats"]["away"]["team_id"] == request_payload.away_team.team_id
    assert body["timeline_events"]
    first_event = body["timeline_events"][0]
    assert {"minute", "type", "player", "team", "position_x", "position_y"} <= set(first_event)
    assert 0.0 <= float(first_event["position_x"]) <= 100.0
    assert 0.0 <= float(first_event["position_y"]) <= 100.0


def test_match_engine_highlights_route_exposes_clip_manifests() -> None:
    app, session_factory = _build_app(_artifact_root("match_engine_highlight_manifest"))
    replay_payload = _build_payload_with_manifestable_highlights()
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/api/match-engine/highlights/{replay_payload.match_id}")

    assert response.status_code == 200

    body = response.json()
    assert body["match_id"] == replay_payload.match_id
    assert body["highlight_profile"] == replay_payload.summary.highlight_profile.value
    assert body["pipeline"]["worker_profile"] == "ffmpeg_gpu_preferred"
    assert body["reel"]["runtime_seconds"] == replay_payload.summary.highlight_runtime_seconds
    assert body["reel"]["render_status"] == "queued"
    assert body["highlights"]

    first_clip = body["highlights"][0]
    assert first_clip["duration_seconds"] > 0
    assert first_clip["camera_sequence"]
    assert first_clip["storage_key"].startswith("media/highlights/")
    assert first_clip["render_status"] == "queued"
    assert first_clip["metadata"]["queue_job_id"].startswith("highlight_")
    assert first_clip["metadata"]["queue_status"] == "queued"
