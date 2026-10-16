from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_session
from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.user import User, UserRole
from app.runtime_config.router import router as runtime_config_router
from app.runtime_config.service import ensure_runtime_config_loader


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, AnalyticsEvent.__table__])
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_runtime_config_router_updates_snapshot_and_loader_cache() -> None:
    session_factory = _build_session_factory()
    admin = User(
        id="admin-1",
        email="admin@example.com",
        username="admin",
        password_hash="hashed",
        role=UserRole.ADMIN,
        is_active=True,
    )
    with session_factory() as session:
        session.add(admin)
        session.commit()

    app = FastAPI()
    app.include_router(runtime_config_router)
    app.state.session_factory = session_factory
    app.state.settings = SimpleNamespace(redis_url=None)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin

    with TestClient(app) as client:
        update_response = client.post(
            "/config/update",
            json={
                "viral_weights": {
                    "share_rate": 0.33,
                    "comment_rate": 0.14,
                    "sponsored_boost": 0.15,
                },
                "feed_weights": {
                    "viral_score": 0.5,
                    "following_boost": 0.2,
                },
                "ab_flags": {
                    "cold_start_v2": "enabled",
                },
            },
        )
        assert update_response.status_code == 200
        updated_payload = update_response.json()
        assert updated_payload["viral_weights"]["share_rate"] == 0.33
        assert updated_payload["viral_weights"]["sponsored_boost"] == 0.15
        assert updated_payload["feed_weights"]["viral_score"] == 0.5
        assert updated_payload["ab_flags"] == {"cold_start_v2": "enabled"}

        current_response = client.get("/config/current")
        assert current_response.status_code == 200
        current_payload = current_response.json()
        assert current_payload["viral_weights"]["comment_rate"] == 0.14
        assert current_payload["feed_weights"]["following_boost"] == 0.2
        assert current_payload["ab_flags"] == {"cold_start_v2": "enabled"}

    loader_snapshot = ensure_runtime_config_loader(app).get_snapshot(force_refresh=True)
    assert loader_snapshot.viral_weights.sponsored_boost == 0.15
    assert loader_snapshot.ab_flags == {"cold_start_v2": "enabled"}

    with session_factory() as session:
        events = session.scalars(select(AnalyticsEvent).where(AnalyticsEvent.name == "runtime_config.updated")).all()
        assert len(events) == 1
