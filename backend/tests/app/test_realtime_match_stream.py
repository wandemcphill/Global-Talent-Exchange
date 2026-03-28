from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.core.events import InMemoryEventPublisher
from app.main import create_app
from app.realtime.commentary_engine import CommentaryEngine
from app.realtime.match_stream_service import MatchStreamService, match_event_channel
from app.realtime.websocket_gateway import MatchStreamWebSocketGateway


@pytest.fixture()
def realtime_app():
    temp_root = Path(__file__).resolve().parents[2] / ".tmp_testdbs"
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = temp_root / f"gte_realtime_test_{uuid4().hex}.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        yield create_app(engine=engine, run_migration_check=True)
    finally:
        engine.dispose()
        with suppress(FileNotFoundError, PermissionError):
            database_path.unlink()


def test_commentary_engine_generates_multiple_styles() -> None:
    engine = CommentaryEngine()

    variations = engine.render_variations(
        {"type": "goal", "player": "Player A", "minute": 67},
        match_id="match-1",
    )

    assert set(variations) == {"broadcast", "hype", "analyst"}
    assert "Player A" in variations["broadcast"]
    assert "67th" in variations["broadcast"]


def test_match_stream_service_builds_envelope_without_redis() -> None:
    service = MatchStreamService(redis_url=None, commentary_engine=CommentaryEngine())

    payload = service.publish_event(
        "match-42",
        {
            "type": "goal",
            "player": "Player A",
            "minute": 67,
            "home_score": 2,
            "away_score": 1,
        },
    )

    assert payload["match_id"] == "match-42"
    assert payload["channel"] == match_event_channel("match-42")
    assert payload["event_type"] == "goal"
    assert payload["home_score"] == 2
    assert payload["away_score"] == 1
    assert payload["commentary_styles"]["broadcast"]


def test_match_stream_service_publishes_match_events_to_domain_bus() -> None:
    publisher = InMemoryEventPublisher()
    service = MatchStreamService(
        redis_url=None,
        commentary_engine=CommentaryEngine(),
        event_publisher=publisher,
    )

    payload = service.publish_event(
        "match-77",
        {
            "type": "penalty_scored",
            "player": "Player B",
            "minute": 88,
            "home_score": 2,
            "away_score": 1,
        },
    )

    assert payload["source_event_type"] == "penalty_scored"
    assert len(publisher.published_events) == 1
    event = publisher.published_events[0]
    assert event.name == "match.events"
    assert event.aggregate_id == "match-77"
    assert event.payload["match_id"] == "match-77"
    assert event.payload["source_event_type"] == "penalty_scored"


def test_match_stream_websocket_gateway_broadcasts_messages() -> None:
    class StubSubscriber:
        def __init__(self) -> None:
            self.subscribed: list[str] = []
            self.unsubscribed: list[str] = []
            self.shutdown_called = False

        async def subscribe(self, match_id: str) -> None:
            self.subscribed.append(match_id)

        async def unsubscribe(self, match_id: str) -> None:
            self.unsubscribed.append(match_id)

        async def shutdown(self) -> None:
            self.shutdown_called = True

    class StubWebSocket:
        def __init__(self) -> None:
            self.accepted = False
            self.messages: list[dict[str, object]] = []

        async def accept(self) -> None:
            self.accepted = True

        async def send_json(self, payload: dict[str, object]) -> None:
            self.messages.append(payload)

    async def _exercise() -> None:
        subscriber = StubSubscriber()
        gateway = MatchStreamWebSocketGateway(redis_url=None, subscriber=subscriber)
        websocket_a = StubWebSocket()
        websocket_b = StubWebSocket()

        subscription_a = await gateway.connect(websocket_a, "match-99")
        subscription_b = await gateway.connect(websocket_b, "match-99")
        delivered = await gateway.broadcast("match-99", {"event_type": "goal", "player": "Player A"})
        await gateway.disconnect(websocket_a, "match-99")
        await gateway.disconnect(websocket_b, "match-99")
        await gateway.shutdown()

        assert subscription_a["channel"] == match_event_channel("match-99")
        assert subscription_b["channel"] == match_event_channel("match-99")
        assert delivered == 2
        assert websocket_a.messages == [{"event_type": "goal", "player": "Player A"}]
        assert websocket_b.messages == [{"event_type": "goal", "player": "Player A"}]
        assert subscriber.subscribed == ["match-99"]
        assert subscriber.unsubscribed == ["match-99"]
        assert subscriber.shutdown_called is True

    asyncio.run(_exercise())


def test_match_stream_websocket_endpoint_accepts_connections(realtime_app) -> None:
    with TestClient(realtime_app) as client:
        with client.websocket_connect("/ws/match/match-123") as websocket:
            payload = websocket.receive_json()

    assert payload == {
        "type": "subscribed",
        "match_id": "match-123",
        "channel": "match:match-123:events",
    }
