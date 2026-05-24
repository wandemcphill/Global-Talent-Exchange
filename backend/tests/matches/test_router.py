from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_session
from app.matches.router import router as matches_router
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.event_backbone import EventOutbox
from app.models.user import User, UserRole


class _Settings:
    kafka_client_id = "test-client"


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(matches_router)
    app.state.settings = _Settings()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CompetitionMatch.__table__,
            EventOutbox.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        with session_factory() as session:
            yield session

    def override_admin() -> User:
        return User(
            id="match-command-admin",
            email="match-command-admin@example.com",
            username="match-command-admin",
            password_hash="test-hash",  # pragma: allowlist secret
            role=UserRole.ADMIN,
        )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = override_admin
    return app, session_factory


def test_start_match_enqueues_orchestrator_command_and_persists_match_state() -> None:
    app, session_factory = _build_app()

    with TestClient(app) as client:
        response = client.post(
            "/matches/start",
            json={
                "match_id": "match-start-1",
                "competition_id": "competition-1",
                "round_id": "round-1",
                "round_number": 2,
                "home_club_id": "home-1",
                "away_club_id": "away-1",
                "stage": "knockout",
                "metadata": {"source": "api-test"},
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["match_id"] == "match-start-1"
    assert body["status"] == "queued"
    assert body["command_name"] == "StartMatchCommand"
    assert body["outbox_event_type"] == "orchestrator.command.match.start"

    with session_factory() as session:
        match = session.get(CompetitionMatch, "match-start-1")
        assert match is not None
        assert match.status == "queued"
        assert match.round_number == 2
        assert match.stage == "knockout"
        assert (match.metadata_json or {})["orchestrator"]["start_request"]["metadata"] == {"source": "api-test"}

        row = session.scalar(select(EventOutbox).where(EventOutbox.event_id == body["outbox_event_id"]))
        assert row is not None
        assert row.status == "pending"
        assert row.event_type == "orchestrator.command.match.start"
        assert row.aggregate_id == "match-start-1"
        assert row.payload_json["match_id"] == "match-start-1"
        assert row.payload_json["command_name"] == "StartMatchCommand"


def test_complete_match_updates_state_and_enqueues_completion_command() -> None:
    app, session_factory = _build_app()
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id="match-complete-1",
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id="home-1",
                away_club_id="away-1",
                status="queued",
                metadata_json={},
            )
        )
        session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/matches/complete",
            json={
                "match_id": "match-complete-1",
                "home_score": 3,
                "away_score": 1,
                "metadata": {"source": "api-test"},
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["match_id"] == "match-complete-1"
    assert body["status"] == "completed"
    assert body["command_name"] == "CompleteMatchCommand"
    assert body["outbox_event_type"] == "orchestrator.command.match.complete"

    with session_factory() as session:
        match = session.get(CompetitionMatch, "match-complete-1")
        assert match is not None
        assert match.status == "completed"
        assert match.home_score == 3
        assert match.away_score == 1
        assert match.winner_club_id == "home-1"
        assert match.completed_at is not None
        assert (match.metadata_json or {})["orchestrator"]["complete_request"]["metadata"] == {"source": "api-test"}

        row = session.scalar(select(EventOutbox).where(EventOutbox.event_id == body["outbox_event_id"]))
        assert row is not None
        assert row.status == "pending"
        assert row.event_type == "orchestrator.command.match.complete"
        assert row.aggregate_id == "match-complete-1"
        assert row.payload_json["match_status"] == "completed"
