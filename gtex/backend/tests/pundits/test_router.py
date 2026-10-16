from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.pundits.router import router as pundits_router
from backend.tests.match_engine.helpers import build_request


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(pundits_router)

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
    preview_request = build_request(seed=74, match_id=replay_payload.match_id)
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=replay_payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                stage="final",
                home_club_id=replay_payload.summary.home_stats.team_id,
                away_club_id=replay_payload.summary.away_stats.team_id,
                metadata_json={
                    "preview_request": preview_request.model_dump(mode="json"),
                    "replay_payload": replay_payload.model_dump(mode="json"),
                },
            )
        )
        session.commit()


def test_pundits_router_returns_match_debate() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=74, match_id="pundits-router"))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        response = client.get(f"/api/pundits/matches/{replay_payload.match_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["headline"]
    assert body["lines"]


def test_pundits_router_returns_show_endpoints() -> None:
    app, session_factory = _build_app()
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=75, match_id="pundits-shows"))
    _insert_match(session_factory, replay_payload)

    with TestClient(app) as client:
        pre_response = client.get(f"/shows/pre-match/{replay_payload.match_id}")
        post_response = client.get(f"/shows/post-match/{replay_payload.match_id}")
        debate_response = client.get("/shows/debate", params={"match_id": replay_payload.match_id})

    assert pre_response.status_code == 200, pre_response.text
    assert post_response.status_code == 200, post_response.text
    assert debate_response.status_code == 200, debate_response.text
    assert pre_response.json()["show_type"] == "pre_match"
    assert pre_response.json()["prediction"]["predicted_score"]
    assert post_response.json()["show_type"] == "post_match"
    assert post_response.json()["player_ratings"]
    assert debate_response.json()["show_type"] == "debate"
