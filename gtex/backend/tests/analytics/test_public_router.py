from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.router import public_router
from app.auth.dependencies import get_current_admin, get_optional_current_user, get_session
from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.user import User, UserRole


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, AnalyticsEvent.__table__])
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_public_analytics_router_exposes_clip_and_dashboard_views() -> None:
    session_factory = _build_session_factory()
    admin = User(
        id="admin-analytics",
        email="admin.analytics@example.com",
        username="admin.analytics",
        password_hash="hashed",
        role=UserRole.ADMIN,
        is_active=True,
    )
    with session_factory() as session:
        session.add(admin)
        session.add_all(
            [
                AnalyticsEvent(
                    name="campaign_clip.created",
                    user_id=admin.id,
                    metadata_json={
                        "clip_id": "clip-1",
                        "clip": {
                            "clip_id": "clip-1",
                            "title": "Clip One",
                            "analytics": {
                                "view_count": 4,
                                "completions": 3,
                                "watch_time": 8.5,
                                "total_watch_time": 34.0,
                                "shares": 1,
                                "comments": 1,
                                "completion_rate": 0.75,
                                "drop_off_point_seconds": 7.5,
                            },
                        },
                    },
                ),
                AnalyticsEvent(name="clip.generated", user_id=admin.id, metadata_json={"clip_id": "clip-1", "title": "Clip One"}),
                AnalyticsEvent(name="clip.view", user_id=admin.id, metadata_json={"clip_id": "clip-1"}),
                AnalyticsEvent(name="clip.view", user_id=admin.id, metadata_json={"clip_id": "clip-1"}),
                AnalyticsEvent(name="clip.complete", user_id=admin.id, metadata_json={"clip_id": "clip-1", "watch_time_seconds": 9.0}),
                AnalyticsEvent(name="clip.share", user_id=admin.id, metadata_json={"clip_id": "clip-1"}),
                AnalyticsEvent(
                    name="campaign_clip.created",
                    user_id=admin.id,
                    metadata_json={
                        "clip_id": "clip-2",
                        "clip": {
                            "clip_id": "clip-2",
                            "title": "Clip Two",
                            "analytics": {
                                "view_count": 2,
                                "completions": 1,
                                "watch_time": 6.0,
                                "total_watch_time": 12.0,
                                "shares": 0,
                                "comments": 0,
                                "completion_rate": 0.5,
                                "drop_off_point_seconds": 4.0,
                            },
                        },
                    },
                ),
                AnalyticsEvent(name="clip.generated", user_id=admin.id, metadata_json={"clip_id": "clip-2", "title": "Clip Two"}),
                AnalyticsEvent(name="clip.view", user_id=admin.id, metadata_json={"clip_id": "clip-2"}),
            ]
        )
        session.commit()

    app = FastAPI()
    app.include_router(public_router)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin

    with TestClient(app) as client:
        clip_response = client.get("/analytics/clip/clip-1")
        assert clip_response.status_code == 200
        clip_payload = clip_response.json()
        assert clip_payload["clip_id"] == "clip-1"
        assert clip_payload["impressions"] == 4
        assert clip_payload["views"] == 4
        assert clip_payload["completions"] == 3
        assert clip_payload["shares"] == 1
        assert clip_payload["revenue"] == "0.0000"
        assert [stage["stage"] for stage in clip_payload["funnel"]] == [
            "generated",
            "viewed",
            "completed",
            "shared",
            "monetized",
        ]

        top_clips_response = client.get("/analytics/dashboard/top-clips")
        assert top_clips_response.status_code == 200
        top_items = top_clips_response.json()["items"]
        assert top_items[0]["clip_id"] == "clip-1"
        assert top_items[0]["views"] == 4

        drop_off_response = client.get("/analytics/dashboard/drop-off")
        assert drop_off_response.status_code == 200
        drop_off_items = drop_off_response.json()["items"]
        assert {item["clip_id"] for item in drop_off_items[:2]} == {"clip-1", "clip-2"}


def test_public_frontend_analytics_route_tracks_authenticated_and_anonymous_events() -> None:
    session_factory = _build_session_factory()
    user = User(
        id="viewer-analytics",
        email="viewer.analytics@example.com",
        username="viewer.analytics",
        password_hash="hashed",
        role=UserRole.USER,
        is_active=True,
    )
    with session_factory() as session:
        session.add(user)
        session.commit()

    app = FastAPI()
    app.include_router(public_router)
    current_actor: dict[str, User | None] = {"user": user}

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_optional_current_user] = lambda: current_actor["user"]

    with TestClient(app) as client:
        authenticated_response = client.post(
            "/analytics/frontend",
            headers={
                "X-Device-Id": "frontend-audit-device",
                "User-Agent": "frontend-audit-test",
            },
            json={
                "name": "follow_tap",
                "category": "button_click",
                "screen": "profile",
                "flow": "follow_system",
                "target": "follow_button",
                "success": True,
                "latency_ms": 18,
                "metadata": {"creator_id": "creator-1"},
            },
        )

        assert authenticated_response.status_code == 201, authenticated_response.text
        authenticated_payload = authenticated_response.json()
        assert authenticated_payload["name"] == "frontend.button_click.follow_tap"
        assert authenticated_payload["user_id"] == user.id
        assert authenticated_payload["metadata_json"]["flow"] == "follow_system"
        assert authenticated_payload["metadata_json"]["target"] == "follow_button"
        assert authenticated_payload["metadata_json"]["latency_ms"] == 18
        assert authenticated_payload["metadata_json"]["creator_id"] == "creator-1"
        assert authenticated_payload["metadata_json"]["device_fingerprint"]
        assert "x-device-id" in authenticated_payload["metadata_json"]["device_signal_sources"]

        current_actor["user"] = None
        anonymous_response = client.post(
            "/analytics/frontend",
            json={
                "name": "feed_empty",
                "category": "drop_off",
                "screen": "viral_feed",
                "flow": "feed_load",
                "stage": "empty_state",
                "success": False,
                "metadata": {"clip_count": 0},
            },
        )

        assert anonymous_response.status_code == 201, anonymous_response.text
        anonymous_payload = anonymous_response.json()
        assert anonymous_payload["name"] == "frontend.drop_off.feed_empty"
        assert anonymous_payload["user_id"] is None
        assert anonymous_payload["metadata_json"]["stage"] == "empty_state"
        assert anonymous_payload["metadata_json"]["clip_count"] == 0
