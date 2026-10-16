from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.calendar_engine.router import router as calendar_router
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.calendar_engine import GlobalEvent
from app.models.competition_match import CompetitionMatch
from backend.tests.match_engine.helpers import build_request


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(calendar_router)
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[CompetitionMatch.__table__, GlobalEvent.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    request = build_request(seed=12, match_id="calendar-match", is_final=True)
    replay = MatchSimulationService().build_replay_payload(request)
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id="calendar-match",
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                stage="final",
                home_club_id=request.home_team.team_id,
                away_club_id=request.away_team.team_id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
                status="scheduled",
                metadata_json={
                    "preview_request": request.model_dump(mode="json"),
                    "replay_payload": replay.model_dump(mode="json"),
                },
            )
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return app, session_factory


def test_calendar_engine_exposes_today_and_upcoming_global_events() -> None:
    app, _session_factory = _build_app()

    with TestClient(app) as client:
        today_response = client.get("/events/today")
        upcoming_response = client.get("/events/upcoming")

    assert today_response.status_code == 200, today_response.text
    assert upcoming_response.status_code == 200, upcoming_response.text
    today_body = today_response.json()
    upcoming_body = upcoming_response.json()
    assert today_body["events"]
    assert any(item["engagement"]["pre_match_show_route"] == "/shows/pre-match/calendar-match" for item in upcoming_body["events"] if item["match_id"] == "calendar-match")
