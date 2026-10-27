from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.models.base import Base
from app.models.world_clock import WorldClockState
from app.services.world_clock_service import DEFAULT_CLOCK_ID
from app.world_simulation.router import router as world_simulation_router


def test_world_clock_read_endpoint_returns_and_persists_authoritative_snapshot() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[WorldClockState.__table__])
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        app = FastAPI()
        app.include_router(world_simulation_router)

        def override_session():
            yield session

        app.dependency_overrides[get_session] = override_session
        client = TestClient(app)

        first_response = client.get("/api/world/clock")
        assert first_response.status_code == 200, first_response.text
        first = first_response.json()
        assert first["clock_id"] == DEFAULT_CLOCK_ID
        assert first["is_paused"] is False
        assert first["progression_rate"] > 0
        assert first["virtual_months_per_season"] >= 1

        world_time = datetime.fromisoformat(first["world_time"])
        assert date.fromisoformat(first["world_date"]) == world_time.date()
        state = session.get(WorldClockState, DEFAULT_CLOCK_ID)
        assert state is not None
        persisted_epoch = state.epoch_real_utc
        persisted_start = state.virtual_start_time

        second_response = client.get("/api/world/clock")
        assert second_response.status_code == 200, second_response.text
        second = second_response.json()
        assert second["clock_id"] == DEFAULT_CLOCK_ID

        session.refresh(state)
        assert state.epoch_real_utc == persisted_epoch
        assert state.virtual_start_time == persisted_start
        assert second["progression_rate"] == first["progression_rate"]

    engine.dispose()
