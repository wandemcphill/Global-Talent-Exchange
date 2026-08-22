from __future__ import annotations

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.competition_match import CompetitionMatch


def test_replay_payload_is_json_serializable_for_durable_match_storage() -> None:
    """The engine payload must be safe to persist in the existing metadata_json column."""
    from backend.tests.match_engine.helpers import build_request

    payload = MatchSimulationService().build_replay_payload(build_request(seed=31))
    serialized = payload.model_dump(mode="json")

    assert serialized["match_id"]
    assert serialized["timeline"]["events"]
    assert serialized["summary"]["home_score"] >= 0
    assert serialized["summary"]["away_score"] >= 0
    assert "render_sync" in serialized
    assert "post_match_analytics" in serialized


def test_competition_match_can_round_trip_replay_payload_through_metadata_json() -> None:
    """Guard the persistence contract used by the live match viewer/archive path."""
    from backend.tests.match_engine.helpers import build_request

    payload = MatchSimulationService().build_replay_payload(build_request(seed=47))
    metadata = {"replay_payload": payload.model_dump(mode="json")}

    record = CompetitionMatch(
        id=payload.match_id,
        metadata_json=metadata,
    )

    restored = record.metadata_json["replay_payload"]
    assert restored["match_id"] == payload.match_id
    assert len(restored["timeline"]["events"]) == len(payload.timeline.events)
    assert restored["summary"]["home_score"] == payload.summary.home_score
    assert restored["summary"]["away_score"] == payload.summary.away_score
