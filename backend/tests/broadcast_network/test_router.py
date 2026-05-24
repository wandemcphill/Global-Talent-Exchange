from __future__ import annotations

from dataclasses import replace
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
    assert payload["current_program"]["watch_route"] == f"/matches/broadcast/{live_match_id}"
    assert payload["current_program"]["replay_route"] == f"/api/matches/{live_match_id}/replay"
    assert payload["match_session"]["audio_stem_websocket_path"].endswith(
        "/audio/stems/stream?session_id=" + payload["match_session"]["id"]
    )
    assert payload["match_session"]["replay_route"] == f"/api/matches/{live_match_id}/replay"
    assert payload["watch_reward"]["rewarded"] is False

    session_id = payload["session_id"]
    with client.websocket_connect(f"/api/broadcast/channels/live/stream?session_id={session_id}") as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["kind"] == "channel_snapshot"
        assert snapshot["payload"]["current_program"]["match_id"] == live_match_id
        assert snapshot["payload"]["match_session"]["channel_context"]["channel_id"] == "live"

    with client.websocket_connect(
        f"/api/broadcast/channels/live/audio/stems/stream?session_id={session_id}"
    ) as websocket:
        manifest = websocket.receive_json()
        assert manifest["kind"] == "audio_manifest_update"
        assert manifest["payload"]["match_id"] == live_match_id


def test_discovery_home_includes_broadcast_network(client, app, demo_auth_headers) -> None:
    _ensure_live_match(app, seed=29)

    response = client.get("/api/discovery/home", headers=demo_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["broadcast_items"]
    assert payload["match_of_the_moment"] is not None
    assert payload["match_of_the_moment"]["item_type"] == "broadcast_match"
    assert payload["match_of_the_moment"]["metadata"]["watch_route"].startswith("/matches/broadcast/")
    assert payload["match_of_the_moment"]["metadata"]["replay_route"].startswith("/api/matches/")


def test_authenticated_broadcast_home_current_match_resolves_match_viewer_endpoints(
    client, app, demo_auth_headers
) -> None:
    _ensure_live_match(app, seed=31)

    home_response = client.get("/api/broadcast/home", headers=demo_auth_headers)

    assert home_response.status_code == 200
    home_payload = home_response.json()
    current_program = home_payload["match_of_the_moment"]
    assert current_program is not None
    match_key = current_program["match_id"]
    assert match_key
    assert current_program["watch_route"] == f"/matches/broadcast/{match_key}"
    assert current_program["replay_route"] == f"/api/matches/{match_key}/replay"

    timeline_response = client.get(f"/api/match-viewer/{match_key}")
    session_response = client.get(f"/api/match-viewer/{match_key}/session")

    assert timeline_response.status_code == 200
    assert session_response.status_code == 200
    assert timeline_response.json()["match_id"] == match_key
    assert session_response.json()["match_id"] == match_key


def test_public_broadcast_home_works_without_auth(client, app) -> None:
    _ensure_live_match(app, seed=33)

    response = client.get("/api/broadcast/home")

    assert response.status_code == 200
    payload = response.json()
    assert payload["channels"]
    assert payload["featured_channel"] is not None


def test_broadcast_home_does_not_emit_replay_fallbacks_in_protected_runtime(client, app) -> None:
    app.state.settings = replace(app.state.settings, app_env="production")
    hub = ensure_live_match_hub(app)
    with hub._lock:
        known_match_ids = list(hub._matches.keys())
        hub._matches.clear()
        for match_id in known_match_ids:
            hub._halted_matches.pop(match_id, None)
    for match_id in known_match_ids:
        hub._hot_cache.clear_match_state(match_id)
        hub._hot_cache.clear_match_events(match_id)

    response = client.get("/api/broadcast/home")

    assert response.status_code == 200
    payload = response.json()
    live_channel = next(item for item in payload["channels"] if item["channel_id"] == "live")
    ai_channel = next(item for item in payload["channels"] if item["channel_id"] == "ai")
    assert live_channel["current_program"] is None
    assert live_channel["metadata"]["strict_live_blocked_reason"] == "no_persisted_live_programs"
    assert ai_channel["current_program"] is None
    assert ai_channel["metadata"]["strict_live_blocked_reason"] == "generated_broadcast_programs_disabled"


def test_broadcast_network_refreshes_cached_fallback_slots_when_live_match_starts(
    client, app, demo_auth_headers
) -> None:
    hub = ensure_live_match_hub(app)
    with hub._lock:
        known_match_ids = list(hub._matches.keys())
        hub._matches.clear()
        for match_id in known_match_ids:
            hub._halted_matches.pop(match_id, None)
    for match_id in known_match_ids:
        hub._hot_cache.clear_match_state(match_id)
        hub._hot_cache.clear_match_events(match_id)

    warm_response = client.get("/api/broadcast/home", headers=demo_auth_headers)
    assert warm_response.status_code == 200
    warm_payload = warm_response.json()
    live_channel_before = next(item for item in warm_payload["channels"] if item["channel_id"] == "live")
    assert live_channel_before["current_program"]["match_id"] is None
    assert live_channel_before["current_program"]["watch_route"] is None
    assert live_channel_before["current_program"]["replay_route"] is None

    live_match_id = _ensure_live_match(app, seed=37)

    join_response = client.post("/api/broadcast/channels/live/join", headers=demo_auth_headers)
    assert join_response.status_code == 200
    assert join_response.json()["current_program"]["match_id"] == live_match_id

    refreshed_home = client.get("/api/broadcast/home", headers=demo_auth_headers)
    assert refreshed_home.status_code == 200
    live_channel_after = next(item for item in refreshed_home.json()["channels"] if item["channel_id"] == "live")
    assert live_channel_after["current_program"]["match_id"] == live_match_id
