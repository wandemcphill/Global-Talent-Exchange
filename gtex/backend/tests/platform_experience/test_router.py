from __future__ import annotations

import time

from app.auth.security import create_access_token
from app.live_matches.service import ensure_live_match_hub
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.user import User
from backend.tests.match_engine.helpers import build_request


def _ensure_live_match(app, *, seed: int = 41) -> str:
    service = MatchSimulationService()
    payload = service.build_replay_payload(build_request(seed=seed))
    hub = ensure_live_match_hub(app, step_interval_seconds=0.01)
    hub.start_stream(payload.match_id, payload, target_runtime_seconds=5.0)
    deadline = time.time() + 2.0
    while time.time() < deadline:
        state = hub.get_state(payload.match_id)
        if state is not None:
            return payload.match_id
        time.sleep(0.02)
    raise AssertionError("Live match did not become available in time.")


def _auth_headers(app_session_factory) -> dict[str, str]:
    with app_session_factory() as session:
        user = session.get(User, "platform-user")
        if user is None:
            user = User(
                id="platform-user",
                email="platform-user@example.com",
                username="platform-user",
                password_hash="hashed",
                full_name="Platform User",
            )
            session.add(user)
            session.commit()
    return {"Authorization": f"Bearer {create_access_token('platform-user')}"}


def test_platform_mode_switch_syncs_resume_state_across_devices(client, app, app_session_factory) -> None:
    live_match_id = _ensure_live_match(app, seed=43)
    auth_headers = _auth_headers(app_session_factory)

    anonymous_response = client.get("/platform/mode")
    living_room_response = client.post(
        "/platform/switch",
        headers=auth_headers,
        json={
            "mode": "tv",
            "device_id": "living-room-tv",
            "device_name": "Living Room",
            "current_match_id": live_match_id,
            "current_channel_id": "live",
            "resume_position_seconds": 27.5,
            "commentary_cursor": 12,
            "metadata": {"surface": "tv_mode"},
        },
    )
    phone_response = client.post(
        "/platform/switch",
        headers=auth_headers,
        json={
            "mode": "mobile",
            "device_id": "phone-app",
            "device_name": "Phone",
            "current_match_id": live_match_id,
            "current_channel_id": "trending",
            "resume_position_seconds": 4.0,
            "commentary_cursor": 3,
            "metadata": {"surface": "mobile_feed"},
        },
    )
    synced_response = client.get(
        "/platform/mode",
        headers=auth_headers,
        params={"device_id": "phone-app"},
    )

    assert anonymous_response.status_code == 200
    assert anonymous_response.json()["metadata"]["authenticated"] is False

    assert living_room_response.status_code == 200
    assert living_room_response.json()["mode"] == "tv"
    assert living_room_response.json()["features"]["full_screen_broadcast"] is True

    assert phone_response.status_code == 200
    assert synced_response.status_code == 200

    synced_payload = synced_response.json()
    assert synced_payload["mode"] == "mobile"
    assert synced_payload["sync_state"]["source_device_id"] == "living-room-tv"
    assert synced_payload["sync_state"]["resume_match_id"] == live_match_id
    assert synced_payload["sync_state"]["commentary_cursor"] == 12
    assert synced_payload["sync_state"]["watch_history"]


def test_platform_broadcast_channels_expose_live_now_and_highlight_reels(client, app, app_session_factory) -> None:
    _ensure_live_match(app, seed=47)
    auth_headers = _auth_headers(app_session_factory)

    response = client.get("/broadcast/channels", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["featured_channel"] is not None
    assert payload["channels"]
    assert payload["auto_switch_policy"]["switch_on_match_end"] is True
    assert payload["auto_switch_policy"]["highlight_reels_between_matches"] is True
    assert payload["highlight_reels"]
