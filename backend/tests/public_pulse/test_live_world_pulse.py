from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import app.models  # noqa: F401
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_optional_current_user, get_session
from app.models.analytics_event import AnalyticsEvent
from app.models.auth_session import AuthSession
from app.models.base import Base, utcnow
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import User
from app.public_pulse.router import router as public_pulse_router
from app.public_pulse.service import PUBLIC_PAGE_VIEW_EVENT, PublicPulseService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def test_live_world_pulse_counts_active_sessions_and_unique_daily_visitors(session) -> None:
    now = utcnow()
    active = User(
        email="online@gtex.test",
        username="online_user",
        password_hash="x",
        last_login_at=now - timedelta(days=2),
    )
    stale = User(
        email="stale@gtex.test",
        username="stale_user",
        password_hash="x",
        last_login_at=now,
    )
    session.add_all([active, stale])
    session.flush()
    session.add_all(
        [
            AuthSession(
                user_id=active.id,
                refresh_token_hash="active-hash",
                expires_at=now + timedelta(hours=1),
                last_used_at=now,
            ),
            AuthSession(
                user_id=stale.id,
                refresh_token_hash="stale-hash",
                expires_at=now + timedelta(hours=1),
                last_used_at=now - timedelta(minutes=30),
            ),
        ]
    )
    session.add(
        ClubProfile(
            owner_user_id=active.id,
            club_name="Pulse FC",
            short_name="PFC",
            slug="pulse-fc",
            country_code="NG",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            primary_color="#111111",
            secondary_color="#222222",
            accent_color="#333333",
        )
    )
    session.add_all(
        [
            AnalyticsEvent(
                name=PUBLIC_PAGE_VIEW_EVENT,
                user_id=None,
                metadata_json={"visitor_key": "visitor-a", "path": "/"},
            ),
            AnalyticsEvent(
                name=PUBLIC_PAGE_VIEW_EVENT,
                user_id=active.id,
                metadata_json={"visitor_key": "visitor-a", "path": "/market"},
            ),
            AnalyticsEvent(
                name=PUBLIC_PAGE_VIEW_EVENT,
                user_id=None,
                metadata_json={"visitor_key": "visitor-b", "path": "/"},
            ),
        ]
    )
    session.commit()

    pulse = PublicPulseService(session).live_world_pulse()
    assert pulse.clubs_on_gtex == 1
    # Recent login alone must not count; only a recently active, valid session does.
    assert pulse.users_online == 1
    assert pulse.registered_users == 2
    assert pulse.visitors_today == 2
    assert pulse.page_views_today == 3
    assert pulse.players_online == 0
    assert pulse.labels["visitors_today"] == "Unique visitors today"


def test_anonymous_heartbeat_records_private_visitor_hash_and_safe_path(session) -> None:
    app = FastAPI()
    app.include_router(public_pulse_router)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_optional_current_user] = lambda: None

    visitor_id = str(uuid4())
    with TestClient(app) as client:
        response = client.post(
            "/public/traffic/heartbeat",
            json={
                "visitor_id": visitor_id,
                "path": "/market?access_token=must-not-be-stored",
                "page_view": True,
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["accepted"] is True
    assert response.json()["recorded_page_view"] is True
    event = session.scalar(select(AnalyticsEvent).where(AnalyticsEvent.name == PUBLIC_PAGE_VIEW_EVENT))
    assert event is not None
    assert event.user_id is None
    assert event.metadata_json["path"] == "/market"
    assert event.metadata_json["visitor_key"] != visitor_id
    assert "access_token" not in str(event.metadata_json)


def test_heartbeat_without_page_view_does_not_create_visit_event(session) -> None:
    app = FastAPI()
    app.include_router(public_pulse_router)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_optional_current_user] = lambda: None

    with TestClient(app) as client:
        response = client.post(
            "/public/traffic/heartbeat",
            json={"visitor_id": str(uuid4()), "path": "/", "page_view": False},
        )

    assert response.status_code == 200
    assert response.json()["recorded_page_view"] is False
    assert session.scalar(select(AnalyticsEvent.id).where(AnalyticsEvent.name == PUBLIC_PAGE_VIEW_EVENT)) is None


def test_authenticated_heartbeat_refreshes_login_presence(session) -> None:
    now = utcnow()
    user = User(
        email="heartbeat@gtex.test",
        username="heartbeat_user",
        password_hash="x",
        is_active=True,
    )
    session.add(user)
    session.flush()
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash="heartbeat-hash",
        expires_at=now + timedelta(hours=1),
        last_used_at=now - timedelta(minutes=10),
    )
    session.add(auth_session)
    session.commit()

    app = FastAPI()
    app.include_router(public_pulse_router)

    def override_session():
        yield session

    @app.middleware("http")
    async def attach_test_auth_session(request, call_next):
        request.state.auth_session = auth_session
        return await call_next(request)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_optional_current_user] = lambda: user

    with TestClient(app) as client:
        response = client.post(
            "/public/traffic/heartbeat",
            json={"visitor_id": str(uuid4()), "path": "/app/community", "page_view": False},
        )

    assert response.status_code == 200, response.text
    assert auth_session.last_used_at is not None
    assert (utcnow() - auth_session.last_used_at).total_seconds() < 5
    assert PublicPulseService(session).live_world_pulse().users_online == 1
