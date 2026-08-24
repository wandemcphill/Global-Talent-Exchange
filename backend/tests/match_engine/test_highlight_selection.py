"""Phase B regression tests for highlight package selection.

The clip builder fills a fixed second budget and stops once it is spent. Candidates
used to be fed in purely chronological order, so a busy match spent that budget on
early, low-importance moments and silently dropped decisive ones — a late winner could
be cut while a routine first-half save survived.
"""

from __future__ import annotations

from app.match_engine.services.experience_layers import MatchHighlightBuilder
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType

_DECISIVE = {
    MatchEventType.GOAL,
    MatchEventType.PENALTY_GOAL,
    MatchEventType.PENALTY_SCORED,
    MatchEventType.RED_CARD,
}


def _simulate(seed: int):
    from backend.tests.match_engine.helpers import build_request

    return MatchSimulationService().event_generator.simulate(build_request(seed=seed))


def test_every_decisive_moment_survives_the_highlight_budget() -> None:
    builder = MatchHighlightBuilder()
    for seed in (3, 11, 19, 23, 31, 47, 59, 71):
        result = _simulate(seed)
        decisive = [event for event in result.events if event.event_type in _DECISIVE]
        if not decisive:
            continue

        bundle = builder.build(result)
        clipped_ids = {clip.event_id for clip in bundle.clips if clip.event_id}

        missing = [event.event_id for event in decisive if event.event_id not in clipped_ids]
        assert not missing, f"seed {seed} dropped decisive moments: {missing}"


def test_clips_play_back_in_chronological_order() -> None:
    builder = MatchHighlightBuilder()
    for seed in (5, 13, 29):
        bundle = builder.build(_simulate(seed))
        starts = [clip.start_second for clip in bundle.clips]
        assert starts == sorted(starts), f"seed {seed} produced out-of-order clips"
        for earlier, later in zip(bundle.clips, bundle.clips[1:]):
            assert earlier.end_second <= later.start_second, "clips must not overlap"


def test_highlight_selection_is_deterministic_for_a_fixed_seed() -> None:
    builder = MatchHighlightBuilder()
    result = _simulate(37)

    first = builder.build(result)
    second = builder.build(result)

    assert [clip.event_id for clip in first.clips] == [clip.event_id for clip in second.clips]
    assert first.runtime_seconds == second.runtime_seconds


def test_low_value_moments_never_outrank_a_goal() -> None:
    """A goal must outrank filler even when the filler happens earlier."""
    builder = MatchHighlightBuilder()
    result = _simulate(19)
    goals = [event for event in result.events if event.event_type in _DECISIVE]
    if not goals:
        return

    bundle = builder.build(result)
    clipped = [clip for clip in bundle.clips if clip.event_id]
    clipped_types = {clip.event_type for clip in clipped}

    # If any filler made the cut, every decisive moment must have made it too.
    filler = clipped_types - _DECISIVE - {MatchEventType.KICKOFF, MatchEventType.FULLTIME}
    if filler:
        clipped_ids = {clip.event_id for clip in clipped}
        assert all(event.event_id in clipped_ids for event in goals)


def test_cards_and_substitutions_are_eligible_highlight_content() -> None:
    from app.match_engine.services.experience_layers import _HIGHLIGHT_EVENT_TYPES

    assert MatchEventType.YELLOW_CARD in _HIGHLIGHT_EVENT_TYPES
    assert MatchEventType.SUBSTITUTION in _HIGHLIGHT_EVENT_TYPES
    assert MatchEventType.INJURY in _HIGHLIGHT_EVENT_TYPES
    assert MatchEventType.GOALKEEPER_SAVE in _HIGHLIGHT_EVENT_TYPES
    assert MatchEventType.TACTICAL_SWING in _HIGHLIGHT_EVENT_TYPES
