from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session as get_auth_session
from app.auth.router import router as auth_router
from app.db import get_session as get_db_session
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models import Base
from app.models.competition_match import CompetitionMatch
from app.viral.router import router as viral_router
from backend.tests.match_engine.helpers import build_request


class _FakeProducer:
    def __init__(self) -> None:
        self.received: list[list[object]] = []

    def enqueue_many(self, events):
        self.received.append(list(events))
        return len(events)


def _build_app() -> tuple[FastAPI, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(viral_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_auth_session] = override_session
    app.dependency_overrides[get_db_session] = override_session
    app.state.clip_event_ingestion_service = _FakeProducer()
    return app, session_factory


def _insert_match(session_factory: sessionmaker[Session], *, seed: int, match_id: str) -> None:
    replay_payload = MatchSimulationService().build_replay_payload(
        build_request(seed=seed, match_id=match_id),
    )
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=replay_payload.match_id,
                competition_id=f"competition-{replay_payload.match_id}",
                round_id=f"round-{replay_payload.match_id}",
                round_number=1,
                home_club_id=replay_payload.summary.home_stats.team_id,
                away_club_id=replay_payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": replay_payload.model_dump(mode="json")},
            )
        )
        session.commit()


def _identity_headers(register_body: dict[str, object]) -> dict[str, str]:
    user = register_body["user"]
    assert isinstance(user, dict)
    user_id = user["id"]
    session_id = register_body["session_id"]
    access_token = register_body["access_token"]
    assert isinstance(user_id, str)
    assert isinstance(session_id, str)
    assert isinstance(access_token, str)
    return {
        "Authorization": f"Bearer {access_token}",
        "X-User-Id": user_id,
        "X-Session-Id": session_id,
        "X-Device-Id": "device-system-feed-refresh-1",
    }


def _event_metadata(clip: dict[str, object]) -> dict[str, object]:
    metadata = {
        "device": "ios",
        "country": "NG",
        "referrer": "viral_feed",
    }
    clip_metadata = clip.get("metadata")
    if isinstance(clip_metadata, dict):
        creator_id = clip_metadata.get("creator_id")
        format_key = clip_metadata.get("format_key")
        if isinstance(creator_id, str) and creator_id.strip():
            metadata["creator_id"] = creator_id
        if isinstance(format_key, str) and format_key.strip():
            metadata["format_key"] = format_key
    clip_event_type = clip.get("event_type")
    if isinstance(clip_event_type, str) and clip_event_type.strip():
        metadata["clip_event_type"] = clip_event_type
    team_name = clip.get("team_name")
    if isinstance(team_name, str) and team_name.strip():
        metadata["team_name"] = team_name
    return metadata


def _build_event(
    *,
    clip: dict[str, object],
    user_id: str,
    session_id: str,
    event_type: str,
    timestamp: datetime,
    watch_time_ms: int,
) -> dict[str, object]:
    clip_id = clip["clip_id"]
    assert isinstance(clip_id, str)
    return {
        "event_id": str(uuid4()),
        "clip_id": clip_id,
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "watch_time_ms": watch_time_ms,
        "video_length_ms": 12000,
        "metadata": _event_metadata(clip),
    }


def test_new_user_signup_feed_refresh_changes_content_after_feedback() -> None:
    app, session_factory = _build_app()
    for seed in (58, 62, 64, 66, 68, 72, 74, 86):
        _insert_match(session_factory, seed=seed, match_id=f"system-feed-{seed}")

    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "email": "system.feed@example.com",
                "username": "system.feed.user",
                "password": "SuperSecret1",
                "full_name": "System Feed User",
                "region_code": "NG",
            },
        )

        assert register_response.status_code == 201, register_response.text
        register_body = register_response.json()
        headers = _identity_headers(register_body)
        initial_feed_response = client.get(
            "/feed/for-you",
            params={"limit": 12, "refresh": True},
            headers=headers,
        )

        assert initial_feed_response.status_code == 200, initial_feed_response.text
        initial_feed = initial_feed_response.json()
        initial_items = initial_feed["items"]
        assert len(initial_items) >= 5
        initial_clip_ids = [item["clip_id"] for item in initial_items]
        assert all(isinstance(clip_id, str) and clip_id for clip_id in initial_clip_ids)

        user = register_body["user"]
        assert isinstance(user, dict)
        user_id = user["id"]
        session_id = register_body["session_id"]
        assert isinstance(user_id, str)
        assert isinstance(session_id, str)

        feedback_events: list[dict[str, object]] = []
        base_timestamp = datetime(2026, 3, 29, 9, 0, tzinfo=UTC)
        for index, clip in enumerate(initial_items[:5]):
            feedback_events.append(
                _build_event(
                    clip=clip,
                    user_id=user_id,
                    session_id=session_id,
                    event_type="view",
                    timestamp=base_timestamp + timedelta(seconds=index),
                    watch_time_ms=12000,
                )
            )
            feedback_events.append(
                _build_event(
                    clip=clip,
                    user_id=user_id,
                    session_id=session_id,
                    event_type="like" if index < 2 else "scroll",
                    timestamp=base_timestamp + timedelta(seconds=index + 10),
                    watch_time_ms=12000 if index < 2 else 400,
                )
            )

        feedback_response = client.post(
            "/events/clip",
            json={"events": feedback_events},
            headers=headers,
        )

        assert feedback_response.status_code == 202, feedback_response.text
        assert feedback_response.json()["accepted_events"] == len(feedback_events)

        refresh_response = client.get(
            "/feed/for-you/refresh",
            params={"cursor": 4, "limit": len(initial_items)},
            headers=headers,
        )

        assert refresh_response.status_code == 200, refresh_response.text
        refresh_payload = refresh_response.json()
        assert refresh_payload["new_items"]
        assert refresh_payload["replace_indices"]
        assert len(refresh_payload["new_items"]) >= 3
        assert all(index > 4 for index in refresh_payload["replace_indices"])

        refreshed_clip_ids = list(initial_clip_ids)
        for replace_index, item in zip(
            refresh_payload["replace_indices"],
            refresh_payload["new_items"],
        ):
            refreshed_clip_ids[replace_index] = item["clip_id"]

        changed_positions = [
            index
            for index, (before, after) in enumerate(
                zip(initial_clip_ids, refreshed_clip_ids),
            )
            if before != after
        ]

        assert changed_positions
        assert len(changed_positions) >= 3
        assert any(clip_id not in initial_clip_ids for clip_id in refreshed_clip_ids)
        assert len(refreshed_clip_ids) == len(initial_clip_ids)
        assert all(isinstance(clip_id, str) and clip_id for clip_id in refreshed_clip_ids)
        assert app.state.clip_event_ingestion_service.received
