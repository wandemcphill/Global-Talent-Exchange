from __future__ import annotations

import json
import time

from app.live_matches.service import LiveMatchHub
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType
from backend.tests.match_engine.helpers import build_request


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


def _find_payload(service: MatchSimulationService, *, seeds=range(1, 200)):
    for seed in seeds:
        payload = service.build_replay_payload(build_request(seed=seed))
        if any(
            event.event_type in {MatchEventType.GOAL, MatchEventType.SHOT, MatchEventType.MISSED_BIG_CHANCE}
            for event in payload.timeline.events
        ):
            return payload
    raise AssertionError("No payload satisfied the requested predicate within the seed range")


def test_live_match_hub_caches_state_events_and_active_matches() -> None:
    cache_backend = FakeCacheBackend()
    replay_payload = _find_payload(MatchSimulationService())
    hub = LiveMatchHub(cache_backend=cache_backend, step_interval_seconds=0.01)

    hub.start_stream(replay_payload.match_id, replay_payload)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        state = hub.get_state(replay_payload.match_id)
        cached_events = cache_backend.get(f"match:{replay_payload.match_id}:events")
        if state is not None and state.event_count > 0 and cached_events is not None:
            break
        time.sleep(0.02)

    assert replay_payload.match_id in hub.list_active_matches()
    cached_state = json.loads(cache_backend.values[f"match:{replay_payload.match_id}:state"])
    cached_events = json.loads(cache_backend.values[f"match:{replay_payload.match_id}:events"])
    assert cached_state["match_id"] == replay_payload.match_id
    assert cached_state["is_live"] is True
    assert cached_events

    hub.halt_match(replay_payload.match_id, reason="test")
    time.sleep(0.05)
    with hub._lock:
        hub._matches.pop(replay_payload.match_id, None)

    restored_state = hub.get_state(replay_payload.match_id)
    restored_events, cursor = hub.get_events_since(replay_payload.match_id, 0)

    assert restored_state is not None
    assert restored_state.snapshot.status == "halted"
    assert restored_events
    assert cursor >= len(restored_events)
    assert replay_payload.match_id not in hub.list_active_matches()
