from __future__ import annotations

import os

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
    os.environ["GTE_AUTH_SECRET"] = "match-websocket-test-secret"

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
            password_hash="test-password-hash",
        )
        session.add(user)
        session.commit()
        user_id = user.id

    token = create_access_token(user_id)
    client = TestClient(app)
    with client.websocket_connect(f"/realtime/matches/match-42/stream?token={token}") as websocket:
        initial_message = websocket.receive_json()
        assert initial_message["kind"] == "snapshot"
        assert initial_message["payload"]["match_id"] == "match-42"
        assert initial_message["payload"]["latest_cursor"] == 0

        publisher.publish(
            DomainEvent(
                name="orchestrator.command.match.start",
                payload={
                    "match_id": "match-42",
                    "match_status": "queued",
                    "command_name": "StartMatchCommand",
                },
                aggregate_id="match-42",
                aggregate_type="competition_match",
            )
        )

        events_message = websocket.receive_json()
        assert events_message["kind"] == "events"
        assert events_message["payload"][0]["match_id"] == "match-42"
        assert events_message["payload"][0]["event_name"] == "orchestrator.command.match.start"

        snapshot_message = websocket.receive_json()
        assert snapshot_message["kind"] == "snapshot"
        assert snapshot_message["payload"]["latest_cursor"] == 1
