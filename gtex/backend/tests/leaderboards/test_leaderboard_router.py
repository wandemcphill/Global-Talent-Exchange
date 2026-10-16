from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.leaderboards.models import LeaderboardPlayerRating, LeaderboardSeason, SeasonStatus
from app.leaderboards.router import router
from app.models.base import Base


@pytest.fixture()
def leaderboard_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            LeaderboardSeason.__table__,
            LeaderboardPlayerRating.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def leaderboard_client(leaderboard_session: Session) -> Iterator[TestClient]:
    SessionLocal = sessionmaker(bind=leaderboard_session.bind, autoflush=False, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)
    app.state.settings = SimpleNamespace(redis_url=None)
    app.state.session_factory = SessionLocal

    def _override_session() -> Iterator[Session]:
        yield leaderboard_session

    app.dependency_overrides[get_session] = _override_session

    with TestClient(app) as client:
        yield client


def test_leaderboard_routes_return_current_history_and_global_views(
    leaderboard_client: TestClient,
    leaderboard_session: Session,
) -> None:
    now = datetime.now(UTC)
    current = LeaderboardSeason(
        start_date=now - timedelta(days=2),
        end_date=now + timedelta(days=5),
        status=SeasonStatus.ACTIVE,
        metadata_json={"duration_days": 7},
    )
    previous = LeaderboardSeason(
        start_date=now - timedelta(days=20),
        end_date=now - timedelta(days=10),
        status=SeasonStatus.ENDED,
        ended_at=now - timedelta(days=10),
        rewards_distributed_at=now - timedelta(days=10),
        metadata_json={"duration_days": 10},
    )
    leaderboard_session.add_all([previous, current])
    leaderboard_session.flush()
    leaderboard_session.add(
        LeaderboardPlayerRating(
            season_id=current.id,
            player_id="player-1",
            display_name="Player One",
            region="ng",
            division="gold",
            rating=1325,
            points=18,
            matches_played=8,
            wins=6,
            losses=1,
            draws=1,
            highest_rating=1325,
            last_rating_delta=14,
            metadata_json={},
        )
    )
    leaderboard_session.commit()

    global_response = leaderboard_client.get("/leaderboard/global", params={"limit": 12})
    current_response = leaderboard_client.get("/season/current")
    history_response = leaderboard_client.get("/season/history", params={"limit": 4})

    assert global_response.status_code == 200, global_response.text
    assert current_response.status_code == 200, current_response.text
    assert history_response.status_code == 200, history_response.text

    global_payload = global_response.json()
    current_payload = current_response.json()
    history_payload = history_response.json()

    assert global_payload["season_id"] == current.id
    assert global_payload["entries"][0]["player_id"] == "player-1"
    assert global_payload["entries"][0]["display_name"] == "Player One"
    assert current_payload["id"] == current.id
    assert current_payload["status"] == "active"
    assert [season["id"] for season in history_payload["seasons"]] == [current.id, previous.id]
    assert history_payload["seasons"][1]["status"] == "ended"
