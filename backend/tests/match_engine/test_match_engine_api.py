from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.match_engine.api.router import router as match_engine_router
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from backend.tests.match_engine.helpers import build_request


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(match_engine_router)

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
