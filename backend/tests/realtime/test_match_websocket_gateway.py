from __future__ import annotations

import os

from backend.tests.support.secrets import (
    MATCH_WEBSOCKET_AUTH_SECRET,
    MEDIA_SIGNING_TEST_SECRET,
    TEST_PASSWORD_HASH,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token
from app.core.events import DomainEvent, InMemoryEventPublisher
from app.models.base import Base
from app.models.user import User
from app.realtime.match_stream_service import MatchStreamService, match_event_channel
from app.realtime.router import router as realtime_router
from app.realtime.service import RealtimeHub, commentary_topic, match_topic


def test_legacy_match_realtime_gateway_is_hidden_from_openapi_and_points_to_canonical_stream() -> None:
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["GTE_AUTH_SECRET"] = MATCH_WEBSOCKET_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.include_router(realtime_router)
    app.state.session_factory = session_factory
    app.state.realtime = RealtimeHub()

    with session_factory() as session:
        user = User(
            email="match-gateway@example.com",
            username="match_gateway",
            password_hash=TEST_PASSWORD_HASH,
        )
        session.add(user)
        session.commit()
        user_id = user.id

    app.dependency_overrides[get_current_user] = lambda: User(
        id=user_id,
        email="match-gateway@example.com",
        username="match_gateway",
        password_hash=TEST_PASSWORD_HASH,
    )
    client = TestClient(app)

    openapi = client.get("/openapi.json").json()
    assert "/realtime/matches/{match_id}/gateway" not in openapi["paths"]

    response = client.get("/realtime/matches/match-42/gateway")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["channel"] == "match:match-42:events"
    assert body["websocket_path"] == "/api/matches/match-42/stream"

    engine.dispose()


def test_legacy_match_websocket_gateway_streams_match_events() -> None:
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["GTE_AUTH_SECRET"] = MATCH_WEBSOCKET_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    publisher = InMemoryEventPublisher()
    realtime = RealtimeHub()
    publisher.subscribe(realtime.handle_event)

    app = FastAPI()
    app.include_router(realtime_router)
    app.state.session_factory = session_factory
    app.state.realtime = realtime

    with session_factory() as session:
        user = User(
            email="match-websocket@example.com",
            username="match_websocket",
            password_hash=TEST_PASSWORD_HASH,
        )
        session.add(user)
        session.commit()
        user_id = user.id

    token = create_access_token(user_id)
    client = TestClient(app)
    with client.websocket_connect(f"/realtime/matches/match-42/stream?token={token}") as websocket:
        initial_message = websocket.receive_json()
        assert initial_message == {
            "type": "subscription_ack",
            "data": {"topics": ["match:match-42:events", "commentary:match-42"]},
        }

        publisher.publish(
            DomainEvent(
                name="competition.match.execution.started",
                payload={
                    "fixture_id": "match-42",
                    "competition_id": "competition-42",
                    "status": "queued",
                },
                aggregate_id="match-42",
                aggregate_type="competition_match",
            )
        )

        events_message = websocket.receive_json()
        assert events_message["type"] == "match_update"
        assert events_message["data"]["match_id"] == "match-42"
        assert events_message["data"]["event_name"] == "competition.match.execution.started"


def test_match_event_dispatch_does_not_invent_score_clock_status() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="match.events",
            aggregate_id="match-42",
            aggregate_type="match",
            payload={
                "match_id": "match-42",
                "event_id": "event-commentary-only",
                "event_type": "incident",
                "minute": 12,
                "commentary": "Backend-authored event without score-clock truth.",
            },
        )
    )

    match_update = next(item for item in dispatches if item.type == "match_update")
    match_event = next(item for item in dispatches if item.type == "match_event")
    commentary = next(item for item in dispatches if item.type == "commentary")

    assert match_update.topics == (match_topic("match-42"),)
    assert match_event.topics == (match_topic("match-42"),)
    assert commentary.topics == (commentary_topic("match-42"),)
    assert match_update.data["status"] is None
    assert match_update.data["home_score"] is None
    assert match_update.data["away_score"] is None
    assert match_update.data["minute"] == 12
    assert match_update.data["commentary"] == "Backend-authored event without score-clock truth."
    assert match_update.data["data_status"] == "blocked"
    assert match_update.data["blocked"] is True
    assert match_update.data["degraded"] is True
    assert match_update.data["score_authoritative"] is False
    assert match_update.data["clock_authoritative"] is False
    assert match_update.data["minute_authoritative"] is True
    missing_codes = {item["code"] for item in match_update.data["missing_data"]}
    assert "missing_authoritative_score" in missing_codes
    assert "missing_authoritative_clock" in missing_codes


def test_match_event_dispatch_missing_fields_override_ready_claim() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="match.events",
            aggregate_id="match-42",
            aggregate_type="match",
            payload={
                "match_id": "match-42",
                "event_id": "event-incomplete-ready-claim",
                "event_type": "incident",
                "data_status": "ready",
                "score_authoritative": True,
                "clock_authoritative": True,
                "minute_authoritative": True,
            },
        )
    )

    match_update = next(item for item in dispatches if item.type == "match_update")

    assert match_update.data["data_status"] == "blocked"
    assert match_update.data["score_authoritative"] is False
    assert match_update.data["clock_authoritative"] is False
    assert match_update.data["minute_authoritative"] is False
    assert match_update.data["blocked"] is True


def test_match_event_dispatch_preserves_backend_score_clock_but_degrades_missing_advanced_feed() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="match.events",
            aggregate_id="match-42",
            aggregate_type="match",
            payload={
                "match_id": "match-42",
                "event_id": "event-score-clock",
                "event_type": "goal",
                "minute": 64,
                "clock": "64:22",
                "home_score": 2,
                "away_score": 1,
                "status": "live",
                "commentary": "Backend score-clock checkpoint.",
            },
        )
    )

    match_update = next(item for item in dispatches if item.type == "match_update")

    assert match_update.data["status"] == "live"
    assert match_update.data["home_score"] == 2
    assert match_update.data["away_score"] == 1
    assert match_update.data["minute"] == 64
    assert match_update.data["clock"] == "64:22"
    assert match_update.data["channel"] == match_topic("match-42")
    assert match_update.data["data_status"] == "degraded"
    assert match_update.data["score_authoritative"] is True
    assert match_update.data["clock_authoritative"] is True
    assert match_update.data["stats_authoritative"] is False
    assert match_update.data["xg_authoritative"] is False
    missing_codes = {item["code"] for item in match_update.data["missing_data"]}
    assert "missing_authoritative_stats" in missing_codes
    assert "missing_authoritative_xg" in missing_codes


def test_match_event_dispatch_accepts_nested_score_and_clock_aliases_without_inventing_truth() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="match.events",
            aggregate_id="match-42",
            aggregate_type="match",
            payload={
                "match_id": "match-42",
                "event_id": "event-nested-truth",
                "event_type": "incident",
                "score": {"home": 2, "away": 1},
                "clock_label": "64:22",
                "clock_minute": 64,
                "current_minute": 64,
                "status": "live",
                "commentary": "Backend-authored nested score update.",
            },
        )
    )

    match_update = next(item for item in dispatches if item.type == "match_update")
    missing_codes = {item["code"] for item in match_update.data["missing_data"]}

    assert match_update.data["status"] == "live"
    assert match_update.data["home_score"] == 2
    assert match_update.data["away_score"] == 1
    assert match_update.data["minute"] == 64
    assert match_update.data["clock"] == "64:22"
    assert match_update.data["data_status"] == "degraded"
    assert match_update.data["score_authoritative"] is True
    assert match_update.data["clock_authoritative"] is True
    assert match_update.data["minute_authoritative"] is True
    assert "missing_authoritative_score" not in missing_codes
    assert "missing_authoritative_minute" not in missing_codes
    assert "missing_authoritative_clock" not in missing_codes


def test_match_event_dispatch_preserves_backend_authored_advanced_feed_status() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="match.events",
            aggregate_id="match-42",
            aggregate_type="match",
            payload={
                "match_id": "match-42",
                "event_id": "event-authored-advanced-feed",
                "event_type": "shot",
                "minute": 72,
                "clock": "72:03",
                "home_score": 2,
                "away_score": 1,
                "status": "live",
                "commentary": "Backend authored pressure is now visible.",
                "stats": {
                    "source": "match_engine_live_feed",
                    "available": True,
                    "home": {"shots": 8},
                    "away": {"shots": 4},
                },
                "xg": {
                    "source": "match_engine_live_feed",
                    "available": True,
                    "home": 1.4,
                    "away": 0.7,
                },
                "momentum": {
                    "source": "match_engine_live_feed",
                    "available": True,
                    "indicator": "home",
                },
                "overlay_readiness": {
                    "status": "ready",
                    "scorebug_ready": True,
                    "timeline_ready": True,
                    "commentary_ready": True,
                    "stats_ready": True,
                    "pitch_2d_ready": True,
                    "blockers": [],
                },
                "inspector_state": {
                    "status": "ready",
                    "source": "match_engine_live_feed",
                },
                "intelligence_state": {
                    "status": "ready",
                    "source": "match_engine_live_feed",
                    "xg_available": True,
                    "momentum_available": True,
                },
            },
        )
    )

    match_update = next(item for item in dispatches if item.type == "match_update")

    assert match_update.data["data_status"] == "ready"
    assert match_update.data["missing_data"] == []
    assert match_update.data["blocked"] is False
    assert match_update.data["degraded"] is False
    assert match_update.data["score_authoritative"] is True
    assert match_update.data["clock_authoritative"] is True
    assert match_update.data["minute_authoritative"] is True
    assert match_update.data["commentary_authoritative"] is True
    assert match_update.data["stats_authoritative"] is True
    assert match_update.data["xg_authoritative"] is True
    assert match_update.data["momentum_authoritative"] is True
    assert match_update.data["overlay_authoritative"] is True
    assert match_update.data["inspector_authoritative"] is True
    assert match_update.data["intelligence_authoritative"] is True
    assert match_update.data["stats"]["home"]["shots"] == 8
    assert match_update.data["xg"]["home"] == 1.4
    assert match_update.data["momentum"]["indicator"] == "home"
    assert match_update.data["overlay_readiness"]["status"] == "ready"


def test_match_stream_service_does_not_default_missing_score_clock_minute() -> None:
    payload = MatchStreamService(redis_url=None).build_stream_message(
        "match-42",
        {
            "event_id": "missing-authority-event",
            "event_type": "incident",
            "commentary": "Backend-authored incomplete event.",
        },
    )

    assert payload["channel"] == match_event_channel("match-42")
    assert payload["home_score"] is None
    assert payload["away_score"] is None
    assert payload["minute"] is None
    assert payload["clock"] is None
    assert payload["data_status"] == "blocked"
    assert payload["score_authoritative"] is False
    assert payload["clock_authoritative"] is False
    assert payload["minute_authoritative"] is False
    missing_codes = {item["code"] for item in payload["missing_data"]}
    assert "missing_authoritative_score" in missing_codes
    assert "missing_authoritative_minute" in missing_codes


def test_match_stream_service_preserves_authored_advanced_feed_payload() -> None:
    payload = MatchStreamService(redis_url=None).build_stream_message(
        "match-42",
        {
            "event_id": "authored-stream-feed-event",
            "event_type": "shot",
            "minute": 45,
            "clock": "45:00",
            "home_score": 1,
            "away_score": 1,
            "commentary": "Backend-authored stream payload includes the full live feed.",
            "stats": {
                "source": "match_engine_live_feed",
                "available": True,
                "home": {"shots": 5},
                "away": {"shots": 5},
            },
            "xg": {
                "source": "match_engine_live_feed",
                "available": True,
                "home": 0.8,
                "away": 0.8,
            },
            "momentum": {
                "source": "match_engine_live_feed",
                "available": True,
                "indicator": "balanced",
            },
            "overlay_readiness": {
                "status": "ready",
                "scorebug_ready": True,
                "timeline_ready": True,
                "commentary_ready": True,
                "stats_ready": True,
                "pitch_2d_ready": True,
                "blockers": [],
            },
            "inspector_state": {
                "status": "ready",
                "source": "match_engine_live_feed",
            },
            "intelligence_state": {
                "status": "ready",
                "source": "match_engine_live_feed",
                "xg_available": True,
                "momentum_available": True,
            },
        },
    )

    assert payload["data_status"] == "ready"
    assert payload["missing_data"] == []
    assert payload["degraded"] is False
    assert payload["blocked"] is False
    assert payload["stats_authoritative"] is True
    assert payload["xg_authoritative"] is True
    assert payload["momentum_authoritative"] is True
    assert payload["overlay_authoritative"] is True
    assert payload["inspector_authoritative"] is True
    assert payload["intelligence_authoritative"] is True
    assert payload["stats"]["home"]["shots"] == 5
    assert payload["xg"]["away"] == 0.8
    assert payload["momentum"]["indicator"] == "balanced"


def test_match_stream_service_does_not_invent_missing_commentary_line() -> None:
    payload = MatchStreamService(redis_url=None).build_stream_message(
        "match-42",
        {
            "event_id": "no-commentary-feed-event",
            "event_type": "shot",
            "minute": 52,
            "clock": "52:10",
            "home_score": 1,
            "away_score": 1,
            "stats": {
                "source": "match_engine_live_feed",
                "available": True,
            },
            "xg": {
                "source": "match_engine_live_feed",
                "available": True,
                "home": 0.9,
                "away": 0.7,
            },
            "momentum": {
                "source": "match_engine_live_feed",
                "available": True,
                "indicator": "away",
            },
            "overlay_readiness": {
                "status": "ready",
                "scorebug_ready": True,
                "timeline_ready": True,
                "commentary_ready": False,
                "stats_ready": True,
                "pitch_2d_ready": True,
                "blockers": [],
            },
            "inspector_state": {
                "status": "ready",
                "source": "match_engine_live_feed",
            },
            "intelligence_state": {
                "status": "ready",
                "source": "match_engine_live_feed",
                "xg_available": True,
                "momentum_available": True,
            },
        },
    )

    assert payload["commentary"] is None
    assert payload["source_commentary"] is None
    assert payload["commentary_authoritative"] is False
    assert payload["data_status"] == "degraded"
    missing_codes = {item["code"] for item in payload["missing_data"]}
    assert "missing_authoritative_commentary" in missing_codes
