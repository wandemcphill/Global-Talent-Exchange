"""Phase B regression tests for live match stream event identity and ordering.

The stream envelope previously carried no sequence number, so a reconnecting client
could not order events that shared a minute, detect a gap, or resume from a cursor.
It also minted a fresh ``uuid4`` whenever an event arrived without an ``event_id``,
which meant the *same* event republished after a retry arrived with a new identity and
defeated consumer-side de-duplication.
"""

from __future__ import annotations

from app.realtime.commentary_engine import CommentaryEngine
from app.realtime.match_stream_service import MatchStreamService


def _service() -> MatchStreamService:
    return MatchStreamService(redis_url=None, commentary_engine=CommentaryEngine())


def test_envelope_carries_the_publisher_sequence() -> None:
    envelope = _service().build_stream_message(
        "match-seq-1",
        {"event_id": "match-seq-1:007", "sequence": 7, "type": "goal", "minute": 61},
    )

    assert envelope["sequence"] == 7
    assert envelope["event_id"] == "match-seq-1:007"


def test_sequence_is_none_when_the_publisher_does_not_supply_one() -> None:
    envelope = _service().build_stream_message(
        "match-seq-2",
        {"event_id": "match-seq-2:001", "type": "goal", "minute": 12},
    )

    assert envelope["sequence"] is None


def test_malformed_sequence_degrades_instead_of_raising() -> None:
    envelope = _service().build_stream_message(
        "match-seq-3",
        {"event_id": "e1", "sequence": "not-a-number", "type": "goal", "minute": 5},
    )

    assert envelope["sequence"] is None
    assert envelope["event_id"] == "e1"


def test_missing_event_id_is_stable_across_redeliveries() -> None:
    """The same event republished must keep the same key so consumers can dedupe."""
    service = _service()
    event = {"sequence": 12, "type": "goal", "minute": 33}

    first = service.build_stream_message("match-seq-4", dict(event))
    second = service.build_stream_message("match-seq-4", dict(event))

    assert first["event_id"] == second["event_id"]
    assert first["event_id"] == "match-seq-4:00012"


def test_missing_event_id_and_sequence_falls_back_to_event_content() -> None:
    service = _service()
    event = {"event_type": "yellow_card", "minute": 77}

    first = service.build_stream_message("match-seq-5", dict(event))
    second = service.build_stream_message("match-seq-5", dict(event))

    assert first["event_id"] == second["event_id"] == "match-seq-5:077:yellow_card"


def test_distinct_events_do_not_collide_on_the_derived_key() -> None:
    service = _service()

    goal = service.build_stream_message("match-seq-6", {"event_type": "goal", "minute": 20})
    card = service.build_stream_message("match-seq-6", {"event_type": "yellow_card", "minute": 20})
    later = service.build_stream_message("match-seq-6", {"event_type": "goal", "minute": 21})

    assert len({goal["event_id"], card["event_id"], later["event_id"]}) == 3


def test_replay_timeline_publishes_a_dense_monotonic_sequence() -> None:
    from backend.tests.match_engine.helpers import build_request
    from app.match_engine.services.match_simulation_service import MatchSimulationService

    replay = MatchSimulationService().build_replay_payload(build_request(seed=19))
    published = _service().publish_replay_timeline(
        match_id="match-seq-7",
        replay_payload=replay,
        home_team_name="North City",
        away_team_name="South Town",
    )

    assert published, "replay timeline must publish at least one event"
    assert [item["sequence"] for item in published] == list(range(1, len(published) + 1))
    assert len({item["event_id"] for item in published}) == len(published)
