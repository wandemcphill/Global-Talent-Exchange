from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.events import DomainEvent, InMemoryEventPublisher
from app.highlights.queue import FileHighlightRenderQueue
from app.highlights.service import HighlightGenerationService
from app.moments.router import router
from app.moments.service import ensure_moments_engine
from app.storage import LocalObjectStorage
from app.viral.ranking_service import InMemoryViralLeaderboardStore


def _build_app(tmp_path) -> FastAPI:
    app = FastAPI()
    app.state.settings = get_settings()
    app.state.event_publisher = InMemoryEventPublisher()
    app.state.highlight_generation_service = HighlightGenerationService(
        settings=app.state.settings,
        queue=FileHighlightRenderQueue(tmp_path),
        storage=LocalObjectStorage(tmp_path),
    )
    app.state.viral_leaderboard_store = InMemoryViralLeaderboardStore()
    app.include_router(router)
    return app


def test_live_moments_endpoint_returns_detected_moment(tmp_path) -> None:
    app = _build_app(tmp_path)
    ensure_moments_engine(app)

    with TestClient(app) as client:
        client.app.state.event_publisher.publish(
            DomainEvent(
                name="match.events",
                payload={
                    "match_id": "match-api",
                    "event_id": "evt-api",
                    "event_type": "red_card",
                    "source_event_type": "red_card",
                    "minute": 63,
                    "clock": "63'",
                    "team": "Home FC",
                    "player": "Captain",
                    "home_score": 1,
                    "away_score": 1,
                    "metadata": {},
                },
            )
        )

        response = client.get("/moments/live")
        api_response = client.get("/api/moments/live", params={"match_id": "match-api"})

    assert response.status_code == 200
    assert api_response.status_code == 200
    payload = api_response.json()
    assert payload["total"] == 1
    moment = payload["moments"][0]
    assert moment["match_id"] == "match-api"
    assert moment["event_type"] == "red_card"
    assert moment["detected_events"] == ["red_card"]
    assert moment["destinations"]["websocket_broadcast"] == "broadcast"
