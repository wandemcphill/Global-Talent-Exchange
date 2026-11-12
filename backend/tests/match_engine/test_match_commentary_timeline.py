from __future__ import annotations

from types import SimpleNamespace

from app.match_engine.commentary.timeline import MatchCommentaryTimelineGenerator
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEvent, MatchEventType
from backend.tests.match_engine.helpers import build_request


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        home_team_id="home",
        away_team_id="away",
        home_team_name="North City",
        away_team_name="South Town",
    )


def _event(**overrides) -> MatchEvent:
    payload = {
        "event_id": "chance-1",
        "sequence": 4,
        "event_type": MatchEventType.GOAL,
        "minute": 23,
        "added_time": 0,
        "home_score": 1,
        "away_score": 0,
        "team_id": "home",
        "team_name": "North City",
        "primary_player_id": "kane",
        "primary_player_name": "Kane",
        "secondary_player_id": None,
        "secondary_player_name": None,
        "metadata": {},
    }
    payload.update(overrides)
    return MatchEvent(**payload)


def test_goal_commentary_names_the_pass_and_the_lane() -> None:
    event = _event(
        metadata={
            "possession_route": "central_combine",
            "decision_action": "pass",
            "creator_player_name": "Silva",
            "chance_family": "cutback",
            "assisted": True,
        }
    )

    line = MatchCommentaryTimelineGenerator()._commentary_for_event(event, _result())

    assert line.startswith("Goal for North City.")
    assert "Silva finds Kane through the middle" in line
    assert "The score is 1-0." in line
    assert "cutback" in line


def test_goal_commentary_does_not_invent_a_pass() -> None:
    event = _event(metadata={"decision_action": "shoot", "chance_family": "long_range_effort"})

    line = MatchCommentaryTimelineGenerator()._commentary_for_event(event, _result())

    assert "finds Kane" not in line
    assert "Kane" in line
    assert "from range" in line
    assert "The score is 1-0." in line


def test_open_play_commentary_follows_the_block() -> None:
    event = _event(
        event_id="swing-1",
        event_type=MatchEventType.DANGEROUS_ATTACK,
        primary_player_name=None,
        metadata={"possession_route": "wide_overlap"},
    )

    line = MatchCommentaryTimelineGenerator()._commentary_for_event(event, _result())
    note = MatchCommentaryTimelineGenerator()._analyst_commentary_for_event(event, _result())

    assert "down the overlap" in line
    assert "final third" in line
    assert "defending line" in note


def test_save_commentary_names_the_keeper_and_the_shot() -> None:
    event = _event(
        event_id="save-1",
        event_type=MatchEventType.SAVE,
        primary_player_name="Costa",
        secondary_player_name="Kane",
        metadata={
            "possession_route": "press_break",
            "decision_action": "pass",
            "creator_player_name": "Silva",
            "chance_family": "near_post_finish",
        },
    )

    line = MatchCommentaryTimelineGenerator()._commentary_for_event(event, _result())

    assert line.startswith("Silva finds Kane through the press.")
    assert "Costa keeps out Kane" in line
    assert "near post" in line


def test_replay_commentary_calls_every_goal_with_the_score() -> None:
    replay = MatchSimulationService().build_replay_payload(build_request(seed=33))
    goals = [event for event in replay.timeline.events if event.event_type is MatchEventType.GOAL]

    assert goals
    for event in goals:
        assert event.commentary.startswith("Goal for ")
        assert f"The score is {event.home_score}-{event.away_score}." in event.commentary
        assert event.commentary.strip().endswith(".") or event.commentary.strip().endswith("!")
    assert all(event.commentary.strip() for event in replay.timeline.events)
