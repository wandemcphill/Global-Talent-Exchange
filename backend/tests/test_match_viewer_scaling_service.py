from __future__ import annotations

from functools import lru_cache

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.schemas.match_viewer import MatchMode
from app.services.match_timeline_service import MatchTimelineService
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from backend.tests.match_engine.helpers import build_request


@lru_cache(maxsize=1)
def _scaled_views():
    simulation_service = MatchSimulationService()
    timeline_service = MatchTimelineService()
    scaling_service = MatchViewerScalingService()

    for seed in range(1, 80):
        replay_payload = simulation_service.build_replay_payload(build_request(seed=seed))
        base_view = timeline_service.build_from_replay_payload(replay_payload)
        quick = scaling_service.transform(base_view, MatchMode.QUICK)
        standard = scaling_service.transform(base_view, MatchMode.STANDARD)
        cinematic = scaling_service.transform(base_view, MatchMode.CINEMATIC)
        if any("presentation_only" in event.flags for event in cinematic.events):
            return base_view, quick, standard, cinematic
    raise AssertionError("Unable to find a replay that produces cinematic presentation beats.")


def _authoritative_event_ids(view_state) -> list[str]:
    return [event.event_id for event in view_state.events if "presentation_only" not in event.flags]


def test_match_viewer_scaling_preserves_authoritative_match_flow() -> None:
    base_view, quick, standard, cinematic = _scaled_views()

    assert 180 <= quick.duration_seconds <= 300
    assert 420 <= standard.duration_seconds <= 600
    assert 600 <= cinematic.duration_seconds <= 900
    assert quick.duration_seconds < standard.duration_seconds < cinematic.duration_seconds

    authoritative_ids = _authoritative_event_ids(base_view)
    for view_state in (quick, standard, cinematic):
        assert view_state.deterministic_seed == base_view.deterministic_seed
        assert _authoritative_event_ids(view_state) == authoritative_ids
        assert view_state.frames[-1].home_score == base_view.frames[-1].home_score
        assert view_state.frames[-1].away_score == base_view.frames[-1].away_score


def test_match_viewer_scaling_adjusts_density_by_mode() -> None:
    _, quick, standard, cinematic = _scaled_views()

    assert len(quick.frames) < len(standard.frames)
    assert len(cinematic.frames) > len(standard.frames)
    assert not any("presentation_only" in event.flags for event in quick.events)
    assert any("presentation_only" in event.flags for event in cinematic.events)

