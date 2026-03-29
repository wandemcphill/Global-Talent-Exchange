from __future__ import annotations

import time

from app.live_matches.service import ensure_live_match_hub
from app.match_engine.services.match_simulation_service import MatchSimulationService
from backend.tests.match_engine.helpers import build_request


def _ensure_live_match(app, *, seed: int = 17) -> str:
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


def test_broadcast_network_join_and_stream_channel(client, app, demo_auth_headers) -> None:
    live_match_id = _ensure_live_match(app, seed=23)

    channels_response = client.get("/api/broadcast/channels", headers=demo_auth_headers)
    assert channels_response.status_code == 200
    channel_ids = {item["channel_id"] for item in channels_response.json()}
    assert {"live", "trending", "ai", "tournament"} <= channel_ids

    join_response = client.post("/api/broadcast/channels/live/join", headers=demo_auth_headers)
    assert join_response.status_code == 200
    payload = join_response.json()
    assert payload["channel"]["channel_id"] == "live"
    assert payload["current_program"]["match_id"] == live_match_id
    assert payload["match_session"]["audio_stem_websocket_path"].endswith("/audio/stems/stream?session_id=" + payload["match_session"]["id"])
    assert payload["watch_reward"]["rewarded"] is False

    session_id = payload["session_id"]
    with client.websocket_connect(f"/api/broadcast/channels/live/stream?session_id={session_id}") as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["kind"] == "channel_snapshot"
        assert snapshot["payload"]["current_program"]["match_id"] == live_match_id
        assert snapshot["payload"]["match_session"]["channel_context"]["channel_id"] == "live"

    with client.websocket_connect(f"/api/broadcast/channels/live/audio/stems/stream?session_id={session_id}") as websocket:
        manifest = websocket.receive_json()
        assert manifest["kind"] == "audio_manifest_update"
        assert manifest["payload"]["match_id"] == live_match_id


def test_discovery_home_includes_broadcast_network(client, app, demo_auth_headers) -> None:
    _ensure_live_match(app, seed=29)

    response = client.get("/discovery/home", headers=demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["broadcast_items"]
    assert payload["match_of_the_moment"] is not None
    assert payload["match_of_the_moment"]["item_type"] == "broadcast_match"
