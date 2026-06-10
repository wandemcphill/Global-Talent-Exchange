from __future__ import annotations

from app.core.events import DomainEvent
from app.realtime.service import RealtimeHub


def test_competition_settlement_completed_dispatches_without_inventing_fields() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="competition.settlement.completed",
            aggregate_id="competition-99",
            aggregate_type="competition",
            payload={
                "competition_id": "competition-99",
                "status": "completed",
                "stage": "completed",
                "participant_count": 8,
            },
        )
    )

    assert len(dispatches) == 1
    update = dispatches[0]
    assert update.type == "competition_update"
    assert update.data["competition_id"] == "competition-99"
    assert update.data["status"] == "completed"
    assert update.data["stage"] == "completed"
    assert update.data["event_name"] == "competition.settlement.completed"
    # Must not invent fields not present in the event payload
    assert "payout_released" not in update.data
    assert "settlement_dispatched" not in update.data
    assert "home_score" not in update.data
    assert "away_score" not in update.data


def test_competition_settlement_completed_with_no_stage_does_not_synthesize_stage() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="competition.settlement.completed",
            aggregate_id="competition-100",
            aggregate_type="competition",
            payload={
                "competition_id": "competition-100",
                "status": "completed",
            },
        )
    )

    assert len(dispatches) == 1
    update = dispatches[0]
    assert update.data["stage"] is None
    assert update.data["status"] == "completed"


def test_competition_finalized_event_passes_stage_through() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="competition.finalized",
            aggregate_id="competition-101",
            aggregate_type="competition",
            payload={
                "competition_id": "competition-101",
                "status": "completed",
                "stage": "completed",
                "participant_count": 4,
            },
        )
    )

    assert len(dispatches) == 1
    update = dispatches[0]
    assert update.type == "competition_update"
    assert update.data["competition_id"] == "competition-101"
    assert update.data["stage"] == "completed"
    assert update.data["status"] == "completed"


def test_competition_match_execution_started_dispatches_match_and_competition_update() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="competition.match.execution.started",
            aggregate_id="match-50",
            aggregate_type="competition_match",
            payload={
                "fixture_id": "match-50",
                "competition_id": "competition-50",
                "status": "queued",
            },
        )
    )

    dispatch_types = {d.type for d in dispatches}
    assert "match_update" in dispatch_types
    assert "competition_update" in dispatch_types

    match_update = next(d for d in dispatches if d.type == "match_update")
    assert match_update.data["match_id"] == "match-50"
    assert match_update.data["competition_id"] == "competition-50"
    assert "home_score" in match_update.data
    assert "away_score" in match_update.data
    # Must not invent scores for an execution-started event
    assert match_update.data["home_score"] is None
    assert match_update.data["away_score"] is None


def test_competition_match_completed_passes_backend_scores_without_inventing() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="competition.match.completed",
            aggregate_id="match-51",
            aggregate_type="competition_match",
            payload={
                "fixture_id": "match-51",
                "competition_id": "competition-51",
                "result_status": "completed",
                "home_score": 2,
                "away_score": 1,
            },
        )
    )

    match_update = next(d for d in dispatches if d.type == "match_update")
    assert match_update.data["home_score"] == 2
    assert match_update.data["away_score"] == 1
    assert match_update.data["status"] == "completed"


def test_competition_match_event_without_scores_does_not_invent_scores() -> None:
    dispatches = RealtimeHub()._map_domain_event(
        DomainEvent(
            name="competition.match.scheduled",
            aggregate_id="match-52",
            aggregate_type="competition_match",
            payload={
                "fixture_id": "match-52",
                "competition_id": "competition-52",
                "status": "scheduled",
            },
        )
    )

    match_update = next(d for d in dispatches if d.type == "match_update")
    assert match_update.data["home_score"] is None
    assert match_update.data["away_score"] is None
