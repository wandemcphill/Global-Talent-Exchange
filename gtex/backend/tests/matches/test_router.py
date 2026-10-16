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


def _seed_match(session_factory, *, match_id: str, status: str, **overrides) -> None:
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id="home-1",
                away_club_id="away-1",
                status=status,
                metadata_json={},
                **overrides,
            )
        )
        session.commit()


def test_start_match_cannot_reset_a_completed_match() -> None:
    """A duplicate StartMatchCommand must not wipe a settled result.

    Regression: ``_prepare_existing_match_for_start`` unconditionally reset status,
    scores, winner and ``completed_at``, so a replayed start command destroyed the
    persisted result while the standings kept the points already applied to it.
    """
    app, session_factory = _build_app()
    _seed_match(
        session_factory,
        match_id="match-settled-1",
        status="completed",
        home_score=2,
        away_score=1,
        winner_club_id="home-1",
        stats_applied=True,
    )

    with TestClient(app) as client:
        response = client.post(
            "/matches/start",
            json={
                "match_id": "match-settled-1",
                "competition_id": "competition-1",
                "round_id": "round-1",
                "home_club_id": "home-1",
                "away_club_id": "away-1",
            },
        )

    assert response.status_code == 409
    assert "completed" in response.json()["detail"]

    with session_factory() as session:
        match = session.get(CompetitionMatch, "match-settled-1")
        assert match is not None
        assert match.status == "completed"
        assert (match.home_score, match.away_score) == (2, 1)
        assert match.winner_club_id == "home-1"
        # No orchestrator command may be enqueued for a rejected transition.
        assert session.scalars(select(EventOutbox)).all() == []


def test_start_match_cannot_restart_a_cancelled_match() -> None:
    app, session_factory = _build_app()
    _seed_match(session_factory, match_id="match-cancelled-1", status="cancelled")

    with TestClient(app) as client:
        response = client.post(
            "/matches/start",
            json={
                "match_id": "match-cancelled-1",
                "competition_id": "competition-1",
                "round_id": "round-1",
                "home_club_id": "home-1",
                "away_club_id": "away-1",
            },
        )

    assert response.status_code == 409
    with session_factory() as session:
        assert session.get(CompetitionMatch, "match-cancelled-1").status == "cancelled"


def test_complete_match_is_idempotent_for_an_identical_replay() -> None:
    """Replaying the same completion command must not re-settle the match."""
    app, session_factory = _build_app()
    _seed_match(session_factory, match_id="match-idem-1", status="queued")

    body = {"match_id": "match-idem-1", "home_score": 3, "away_score": 1}
    with TestClient(app) as client:
        first = client.post("/matches/complete", json=body)
        second = client.post("/matches/complete", json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["status"] == "completed"

    with session_factory() as session:
        match = session.get(CompetitionMatch, "match-idem-1")
        assert (match.home_score, match.away_score) == (3, 1)
        # The second call must not enqueue a second settlement command.
        outbox = session.scalars(select(EventOutbox).where(EventOutbox.aggregate_id == "match-idem-1")).all()
        assert len(outbox) == 1


def test_complete_match_rejects_a_conflicting_rescore() -> None:
    app, session_factory = _build_app()
    _seed_match(session_factory, match_id="match-conflict-1", status="queued")

    with TestClient(app) as client:
        first = client.post(
            "/matches/complete",
            json={"match_id": "match-conflict-1", "home_score": 3, "away_score": 1},
        )
        second = client.post(
            "/matches/complete",
            json={"match_id": "match-conflict-1", "home_score": 0, "away_score": 5},
        )

    assert first.status_code == 202
    assert second.status_code == 409

    with session_factory() as session:
        match = session.get(CompetitionMatch, "match-conflict-1")
        assert (match.home_score, match.away_score) == (3, 1)


def test_complete_match_rejects_an_abandoned_match() -> None:
    """An abandoned match must never settle, even if a worker reports a scoreline."""
    app, session_factory = _build_app()
    _seed_match(session_factory, match_id="match-abandoned-1", status="abandoned")

    with TestClient(app) as client:
        response = client.post(
            "/matches/complete",
            json={"match_id": "match-abandoned-1", "home_score": 1, "away_score": 0},
        )

    assert response.status_code == 409
    with session_factory() as session:
        match = session.get(CompetitionMatch, "match-abandoned-1")
        assert match.status == "abandoned"
        assert (match.home_score, match.away_score) == (0, 0)
        assert match.completed_at is None
