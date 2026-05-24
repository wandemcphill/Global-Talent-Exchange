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

from app.auth.security import create_access_token
from app.core.events import DomainEvent, InMemoryEventPublisher
from app.models.base import Base
from app.models.user import User
from app.realtime.router import router as realtime_router
from app.realtime.service import RealtimeHub


def test_match_websocket_gateway_streams_match_events() -> None:
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
            "data": {"topics": ["match:match-42", "commentary:match-42"]},
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
        assert events_message["source_of_truth"] == "persisted_backend_authority"
        assert events_message["source_tag"] == "gtex_realtime_hub"
        assert events_message["topics"] == ["match:match-42"]
        assert events_message["published_at"]
        assert events_message["data"]["match_id"] == "match-42"
        assert events_message["data"]["event_name"] == "competition.match.execution.started"
        assert events_message["data"]["source_of_truth"] == "persisted_backend_authority"
        assert events_message["data"]["source_tag"] == "gtex_realtime_hub"
