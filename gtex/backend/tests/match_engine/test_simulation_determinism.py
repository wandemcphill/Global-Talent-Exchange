"""Phase B determinism guards for the match engine.

Replay integrity depends on the simulation being a pure function of its request: the
same fixture re-simulated after a retry, on another worker, or when a replay is rebuilt
from an archived request must produce byte-identical output. These tests pin that
contract so a stray ``datetime.now()``/``uuid4()``/unseeded ``Random`` cannot creep back
into the event, timeline or replay path.
"""

from __future__ import annotations

import pytest

from app.match_engine.services.match_simulation_service import MatchSimulationService


def _request(**kwargs):
    from backend.tests.match_engine.helpers import build_request

    return build_request(**kwargs)


@pytest.mark.parametrize("seed", [1, 17, 404, 9973])
def test_replay_payload_is_byte_identical_for_a_repeated_seed(seed: int) -> None:
    service = MatchSimulationService()

    first = service.build_replay_payload(_request(seed=seed)).model_dump(mode="json")
    second = service.build_replay_payload(_request(seed=seed)).model_dump(mode="json")

    assert first == second


def test_independent_service_instances_agree() -> None:
    """A retry handled by a different worker process must reproduce the same match."""
    first = MatchSimulationService().build_replay_payload(_request(seed=8123)).model_dump(mode="json")
    second = MatchSimulationService().build_replay_payload(_request(seed=8123)).model_dump(mode="json")

    assert first == second


def test_distinct_seeds_produce_distinct_matches() -> None:
    service = MatchSimulationService()

    a = service.build_replay_payload(_request(seed=101))
    b = service.build_replay_payload(_request(seed=102))

    assert [event.event_id for event in a.timeline.events] != [event.event_id for event in b.timeline.events] or (
        a.summary.home_score,
        a.summary.away_score,
    ) != (b.summary.home_score, b.summary.away_score)


def test_omitted_seed_is_derived_from_the_request_not_the_clock() -> None:
    """An unseeded request must still be reproducible from its own identity."""
    service = MatchSimulationService()

    first = service.build_replay_payload(_request(seed=None, match_id="derived-seed-match"))
    second = service.build_replay_payload(_request(seed=None, match_id="derived-seed-match"))

    assert first.seed == second.seed
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_derived_seed_differs_per_match_identity() -> None:
    service = MatchSimulationService()

    a = service.build_replay_payload(_request(seed=None, match_id="derived-a"))
    b = service.build_replay_payload(_request(seed=None, match_id="derived-b"))

    assert a.seed != b.seed


def test_summary_and_timeline_helpers_agree_with_the_full_replay() -> None:
    """The three entry points each re-simulate; they must not diverge."""
    service = MatchSimulationService()

    replay = service.build_replay_payload(_request(seed=555))
    summary = service.build_summary(_request(seed=555))
    timeline = service.build_timeline(_request(seed=555))

    assert (summary.home_score, summary.away_score) == (
        replay.summary.home_score,
        replay.summary.away_score,
    )
    assert summary.winner_team_id == replay.summary.winner_team_id
    assert [event.event_id for event in timeline.events] == [event.event_id for event in replay.timeline.events]


@pytest.mark.parametrize("seed", [7, 88, 1234])
def test_event_sequence_is_strictly_monotonic_and_minute_ordered(seed: int) -> None:
    replay = MatchSimulationService().build_replay_payload(_request(seed=seed))

    sequences = [entry.sequence for entry in replay.replay_log]
    assert sequences == sorted(sequences), "replay log must be sequence-ordered"
    assert len(set(sequences)) == len(sequences), "sequences must be unique"

    event_ids = [event.event_id for event in replay.timeline.events]
    assert len(set(event_ids)) == len(event_ids), "event ids must be unique within a match"

    minutes = [event.minute for event in replay.timeline.events]
    assert minutes == sorted(minutes), "timeline must be minute-ordered"
