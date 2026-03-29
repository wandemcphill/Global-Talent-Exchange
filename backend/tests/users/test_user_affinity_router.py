from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import get_current_user, get_session
from app.auth.security import create_access_token
from app.auth.service import AuthService
from app.models.creator_profile import CreatorProfile
from app.models.follow import Follow
from app.models.user_affinity_profile import UserAffinityProfile
from app.models.user import User
from app.users.router import get_follow_graph_service, router as users_router


def _identity_headers(*, token: str, user_id: str, session_id: str, device_id: str = "device-test-1") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-User-Id": user_id,
        "X-Session-Id": session_id,
        "X-Device-Id": device_id,
    }


def _create_user_headers(app_session_factory, *, email: str, username: str) -> dict[str, str]:
    with app_session_factory() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is None:
            user = AuthService().register_user(
                session,
                email=email,
                username=username,
                password="SuperSecret1",
            )
        else:
            user = session.get(User, existing.id)
        session_id = f"session-{username}"
        token = create_access_token(user.id, claims={"sid": session_id})
        session.commit()
        return _identity_headers(token=token, user_id=user.id, session_id=session_id)


def test_user_affinity_profile_defaults(client, app_session_factory) -> None:
    headers = _create_user_headers(
        app_session_factory,
        email="affinity-defaults@example.com",
        username="affinitydefaults",
    )

    response = client.get("/users/me/profile", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profile_key"].startswith("user:")
    assert payload["favorite_formats"] == {}
    assert payload["favorite_creators"] == {}
    assert payload["avg_watch_time"] == 0.0
    assert payload["skip_rate"] == 0.0
    assert payload["session_duration"] == 0.0
    assert payload["engagement_score"] == 0.0
    assert payload["affinity_vector"] == {}
    assert payload["affinity"] is None


def test_clip_events_update_user_affinity_profile(client, app_session_factory) -> None:
    headers = _create_user_headers(
        app_session_factory,
        email="affinity-events@example.com",
        username="affinityevents",
    )
    events = [
        {
            "name": "clip.view",
            "metadata": {
                "format": "debate",
                "creator_id": "creator_xyz",
                "watch_time": 36,
                "session_id": "session-1",
                "session_duration": 240,
            },
        },
        {
            "name": "clip.complete",
            "metadata": {
                "format": "debate",
                "creator_id": "creator_xyz",
                "watch_time": 52,
                "session_id": "session-1",
                "session_duration": 240,
            },
        },
        {
            "name": "clip.like",
            "metadata": {
                "format": "debate",
                "creator_id": "creator_xyz",
                "session_id": "session-1",
                "session_duration": 240,
            },
        },
        {
            "name": "clip.share",
            "metadata": {
                "format": "debate",
                "creator_id": "creator_xyz",
                "session_id": "session-1",
                "session_duration": 240,
            },
        },
        {
            "name": "clip.view",
            "metadata": {
                "format": "meme",
                "creator_id": "creator_zzz",
                "watch_time": 4,
                "session_id": "session-1",
                "session_duration": 240,
            },
        },
        {
            "name": "clip.scroll",
            "metadata": {
                "format": "meme",
                "creator_id": "creator_zzz",
                "session_id": "session-1",
                "session_duration": 240,
            },
        },
    ]

    for payload in events:
        response = client.post("/api/analytics/events", headers=headers, json=payload)
        assert response.status_code == 201, response.text

    profile_response = client.get(
        "/users/me/profile",
        headers=headers,
        params={"format": "debate", "creator_id": "creator_xyz"},
    )

    assert profile_response.status_code == 200, profile_response.text
    payload = profile_response.json()
    assert payload["favorite_formats"]["debate"] == pytest.approx(1.0)
    assert payload["favorite_creators"]["creator_xyz"] == pytest.approx(1.0)
    assert "meme" not in payload["favorite_formats"]
    assert "creator_zzz" not in payload["favorite_creators"]
    assert payload["avg_watch_time"] == pytest.approx(30.6667, rel=1e-4)
    assert payload["skip_rate"] == pytest.approx(0.5)
    assert payload["session_duration"] == pytest.approx(240.0)
    assert 0.5 < payload["engagement_score"] < 0.6
    assert payload["affinity_vector"]["format:debate"] == pytest.approx(1.0)
    assert payload["affinity_vector"]["creator:creator_xyz"] == pytest.approx(1.0)
    assert payload["affinity"]["format"] == "debate"
    assert payload["affinity"]["creator_id"] == "creator_xyz"
    assert payload["affinity"]["format_match"] == pytest.approx(1.0)
    assert payload["affinity"]["creator_match"] == pytest.approx(1.0)
    assert payload["affinity"]["engagement_history"] > 0.5
    assert payload["affinity"]["score"] > 0.87


def test_follow_route_rejects_missing_identity_context(app_session_factory, client) -> None:
    app = FastAPI()
    app.include_router(users_router)
    current_user = User(
        id="follow-missing-current",
        email="follow-missing-current@example.com",
        username="followmissingcurrent",
        password_hash="hashed",
    )

    class _UnreachableFollowService:
        def follow(self, *, actor, following_id):
            raise AssertionError("follow service should not run without identity")

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[get_follow_graph_service] = lambda: _UnreachableFollowService()

    authorization = f"Bearer {create_access_token(current_user.id, claims={'sid': 'session-missing'})}"

    with TestClient(app) as test_client:
        response = test_client.post(
            "/follow/follow-missing-target",
            headers={"Authorization": authorization},
        )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Missing identity context"


def test_follow_routes_and_suggestions_surface_social_graph(app_session_factory, client) -> None:
    current_user_id, headers = _create_user(app_session_factory, email="follow-current@example.com", username="followcurrent")
    target_user_id, _target_headers = _create_user(app_session_factory, email="follow-target@example.com", username="followtarget")
    suggested_user_id, _suggested_headers = _create_user(
        app_session_factory,
        email="follow-suggested@example.com",
        username="followsuggested",
    )
    booster_a_id, _ = _create_user(app_session_factory, email="follow-booster-a@example.com", username="followboostera")
    booster_b_id, _ = _create_user(app_session_factory, email="follow-booster-b@example.com", username="followboosterb")

    with app_session_factory() as session:
        session.add_all(
            [
                CreatorProfile(user_id=target_user_id, handle="target-creator", display_name="Target Creator"),
                CreatorProfile(user_id=suggested_user_id, handle="suggested-creator", display_name="Suggested Creator"),
            ]
        )
        session.add(
            UserAffinityProfile(
                user_id=current_user_id,
                favorite_formats_json={"instant_clip": 1.0},
                favorite_creators_json={suggested_user_id: 1.0},
                affinity_vector_json={
                    "format:instant_clip": 1.0,
                    f"creator:{suggested_user_id}": 0.9,
                },
                state_json={},
            )
        )
        session.add(
            UserAffinityProfile(
                user_id=suggested_user_id,
                favorite_formats_json={"instant_clip": 0.9},
                favorite_creators_json={suggested_user_id: 1.0},
                affinity_vector_json={
                    "format:instant_clip": 0.95,
                    f"creator:{suggested_user_id}": 1.0,
                },
                state_json={},
            )
        )
        session.add_all(
            [
                Follow(follower_id=booster_a_id, following_id=suggested_user_id),
                Follow(follower_id=booster_b_id, following_id=suggested_user_id),
            ]
        )
        session.commit()

    follow_response = client.post(f"/follow/{target_user_id}", headers=headers)

    assert follow_response.status_code == 200, follow_response.text
    follow_payload = follow_response.json()
    assert follow_payload["following"] is True
    assert follow_payload["following_id"] == target_user_id
    assert follow_payload["target_followers_count"] == 1

    followers_response = client.get(f"/users/{target_user_id}/followers")
    assert followers_response.status_code == 200, followers_response.text
    followers_payload = followers_response.json()
    assert followers_payload["total"] == 1
    assert followers_payload["users"][0]["id"] == current_user_id

    following_response = client.get(f"/users/{current_user_id}/following")
    assert following_response.status_code == 200, following_response.text
    following_payload = following_response.json()
    assert following_payload["total"] == 1
    assert following_payload["users"][0]["id"] == target_user_id
    assert following_payload["users"][0]["creator_handle"] == "target-creator"

    suggestions_response = client.get("/users/suggestions", headers=headers)
    assert suggestions_response.status_code == 200, suggestions_response.text
    suggestions_payload = suggestions_response.json()
    suggested_ids = [item["id"] for item in suggestions_payload["suggestions"]]
    assert target_user_id not in suggested_ids
    assert suggested_ids[0] == suggested_user_id
    assert suggestions_payload["suggestions"][0]["reason"] in {
        "Shared engagement patterns",
        "Similar affinity profile",
    }
    assert suggestions_payload["suggestions"][0]["followers_count"] == 2


def _create_user(app_session_factory, *, email: str, username: str) -> tuple[str, dict[str, str]]:
    with app_session_factory() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is None:
            user = AuthService().register_user(
                session,
                email=email,
                username=username,
                password="SuperSecret1",
            )
        else:
            user = session.get(User, existing.id)
        session_id = f"session-{username}"
        token = create_access_token(user.id, claims={"sid": session_id})
        session.commit()
        return user.id, _identity_headers(token=token, user_id=user.id, session_id=session_id)
