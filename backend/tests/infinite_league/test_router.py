from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_match_user, get_current_social_user
from app.db import get_session
from app.live_matches.service import ensure_live_match_hub
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.highlight_event import HighlightEvent
from app.models.manager_duel import ManagerDuel
from app.models.spectator_session import SpectatorSession
from app.models.story_feed import StoryFeedItem
from app.models.user import User, UserRole
from app.replay_archive.persistence import ReplayArchiveRecordRow
from app.infinite_league.router import router as infinite_league_router
from app.live_matches.router import router as live_matches_router
from app.pundits.router import router as pundits_router
from app.viral.router import router as viral_router


def _build_app() -> TestClient:
    app = FastAPI()
    app.include_router(infinite_league_router)
    app.include_router(live_matches_router)
    app.include_router(viral_router)
    app.include_router(pundits_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CompetitionMatch.__table__,
            HighlightEvent.__table__,
            ManagerDuel.__table__,
            ReplayArchiveRecordRow.__table__,
            SpectatorSession.__table__,
            StoryFeedItem.__table__,
            User.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory
    app.state.live_match_hub = ensure_live_match_hub(app, step_interval_seconds=0.01)

    with session_factory() as session:
        spectator = User(
            email="spectator@example.com",
            username="spectator",
            password_hash="not-used",
            role=UserRole.USER,
            is_active=True,
        )
        session.add(spectator)
        session.commit()
        session.refresh(spectator)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_match_user] = lambda: spectator
    app.dependency_overrides[get_current_social_user] = lambda: spectator
    return TestClient(app)


def test_infinite_league_generates_matches_and_feeds_existing_surfaces() -> None:
    with _build_app() as client:
        tick_response = client.post("/infinite-league/tick", params={"count": 1})

        assert tick_response.status_code == 200
        tick_body = tick_response.json()
        assert tick_body["matches"]
        match_id = tick_body["matches"][0]["match_id"]

        status_response = client.get("/infinite-league/status")
        highlights_response = client.get(f"/api/matches/{match_id}/highlights")
        match_viral_response = client.get(f"/api/viral/matches/{match_id}/clips")
        feed_response = client.get("/api/viral/feed", params={"match_ids": match_id})
        pundits_response = client.get(f"/api/pundits/matches/{match_id}")
        livestream_response = client.get("/infinite-league/livestream")
        economy_response = client.get("/infinite-league/economy")
        spectate_response = client.post(f"/api/matches/{match_id}/spectate")

        assert status_response.status_code == 200
        assert status_response.json()["completed_matches"] >= 1

        assert highlights_response.status_code == 200
        assert highlights_response.json()["highlights"]

        assert match_viral_response.status_code == 200
        assert match_viral_response.json()["clips"]
        assert match_viral_response.json()["clips"][0]["match_id"] == match_id

        assert feed_response.status_code == 200
        assert feed_response.json()["clips"]
        assert feed_response.json()["clips"][0]["match_id"] == match_id

        assert pundits_response.status_code == 200
        assert pundits_response.json()["match_id"] == match_id
        assert pundits_response.json()["lines"]

        assert livestream_response.status_code == 200
        assert livestream_response.json()["segments"]
        assert livestream_response.json()["ffmpeg_command"][0] == "ffmpeg"

        assert economy_response.status_code == 200
        assert economy_response.json()["wallets"]

        assert spectate_response.status_code == 200
        spectate_payload = spectate_response.json()
        assert spectate_payload["match_id"] == match_id
        assert spectate_payload["access_source"] == "infinite_league"
        assert spectate_payload["premium_features"]["generated_commentary"] is True

        live_hub = ensure_live_match_hub(client.app, step_interval_seconds=0.01)
        with live_hub._lock:
            live_hub._matches.clear()

        with client.websocket_connect(spectate_payload["websocket_path"]) as websocket:
            first_message = websocket.receive_json()
            assert first_message["kind"] == "snapshot"
            saw_events = False
            for _ in range(20):
                message = websocket.receive_json()
                if message["kind"] == "events":
                    assert message["payload"]
                    assert message["payload"][0]["metadata"]["commentary_provider"] == "infinite_league"
                    assert message["payload"][0]["experience"]["commentary"]["tts_ready"] is True
                    saw_events = True
                    break
            assert saw_events is True

        with live_hub._lock:
            live_hub._matches.clear()

        with client.websocket_connect(spectate_payload["commentary_websocket_path"]) as commentary_socket:
            first_commentary = commentary_socket.receive_json()
            assert first_commentary["kind"] == "commentary_snapshot"
            saw_commentary = False
            for _ in range(20):
                message = commentary_socket.receive_json()
                if message["kind"] == "commentary":
                    assert message["payload"]
                    assert message["payload"][0]["line"]
                    assert message["payload"][0]["context"]["source"] == "infinite_league"
                    assert message["payload"][0]["cue"]["tts_ready"] is True
                    saw_commentary = True
                    break
            assert saw_commentary is True
