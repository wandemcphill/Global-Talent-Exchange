from __future__ import annotations

import time

from app.live_matches.service import LiveMatchHub
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType
from backend.tests.match_engine.helpers import build_request


def _find_payload(service: MatchSimulationService, *, seeds=range(1, 200)):
    for seed in seeds:
        payload = service.build_replay_payload(build_request(seed=seed))
        if any(
            event.event_type in {MatchEventType.GOAL, MatchEventType.SHOT, MatchEventType.MISSED_BIG_CHANCE}
            for event in payload.timeline.events
        ):
            return payload
    raise AssertionError("No payload satisfied the requested predicate within the seed range")


def test_live_match_hub_projects_experience_layers_into_events_and_state() -> None:
    service = MatchSimulationService()
    replay_payload = _find_payload(service)
    hub = LiveMatchHub(step_interval_seconds=0.01)

    batches = hub._build_batches(replay_payload)
    streamed_events = [event for batch in batches for event in batch.events]

    assert streamed_events
    event = next(item for item in streamed_events if item.experience is not None)
    assert event.experience is not None
    assert event.experience.motion is not None
    assert event.experience.motion.model_key == "gtex_motion_blend_v1"
    assert event.experience.commentary is not None
    assert event.experience.commentary.tts_ready is True
    assert event.experience.crowd is not None
    assert event.experience.spectator_sync is not None
    assert event.experience.spectator_sync.room_id == f"match_{replay_payload.match_id}"

    hub.start_stream(replay_payload.match_id, replay_payload)

    deadline = time.time() + 1.0
    state = None
    while time.time() < deadline:
        state = hub.get_state(replay_payload.match_id)
        if state is not None and state.event_count > 0:
            break
        time.sleep(0.02)

    assert state is not None
    assert state.event_count > 0
    assert state.crowd_state is not None
    assert state.crowd_state.profile
    assert state.spectator_sync is not None
    assert state.spectator_sync.sync_strategy == "deterministic_playback"
    assert state.snapshot.win_probability is not None
    assert state.snapshot.market_pulse is not None
    total_probability = (
        state.snapshot.win_probability.home
        + state.snapshot.win_probability.draw
        + state.snapshot.win_probability.away
    )
    assert 0.99 <= total_probability <= 1.01
    assert state.snapshot.market_pulse.home_line > 0
    assert state.snapshot.market_pulse.draw_line > 0
    assert state.snapshot.market_pulse.away_line > 0
