from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.live_matches.router import router as live_matches_router
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from backend.tests.match_engine.helpers import build_request


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(live_matches_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[CompetitionMatch.__table__])
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


def test_match_live_route_returns_frames_from_db_when_live_cache_is_empty() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=35))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/match/{replay_payload.match_id}/live")

    assert response.status_code == 200
    body = response.json()
    assert body["matchId"] == replay_payload.match_id
    assert body["status"] == "completed"
    assert body["isLive"] is False
    assert body["frames"]
    assert body["timelineEvents"]
    assert body["viewer"]["match_id"] == replay_payload.match_id
    assert body["score"]["home"] == replay_payload.summary.home_score
    assert body["score"]["away"] == replay_payload.summary.away_score
