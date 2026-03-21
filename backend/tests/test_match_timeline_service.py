from __future__ import annotations

from datetime import UTC, datetime

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType, TacticalStyle
from app.replay_archive.schemas import ReplayArchiveRecord
from app.services.match_timeline_service import MatchTimelineService
from app.schemas.match_viewer import MatchViewerEventType
from backend.tests.match_engine.helpers import build_request, build_team


def test_match_timeline_service_builds_deterministic_view_state() -> None:
    replay_payload = MatchSimulationService().build_replay_payload(
        build_request(
            seed=33,
            home_team=build_team(
                "home",
                "North City",
                84,
                formation="4-2-3-1",
                style=TacticalStyle.ATTACKING,
                pressing=82,
                aggression=74,
            ),
            away_team=build_team(
                "away",
                "South Town",
                81,
                formation="4-4-2",
                style=TacticalStyle.BALANCED,
                pressing=68,
                aggression=71,
            ),
        )
    )
    service = MatchTimelineService()

    view_a = service.build_from_replay_payload(replay_payload)
    view_b = service.build_from_replay_payload(replay_payload)

    assert view_a.model_dump(mode="json") == view_b.model_dump(mode="json")
    assert view_a.frames[0].ball.position.x == 50.0
    assert view_a.frames[0].ball.position.y == 50.0
    assert view_a.frames[-1].home_score == replay_payload.summary.home_score
    assert view_a.frames[-1].away_score == replay_payload.summary.away_score
    assert any(frame.home_attacks_right for frame in view_a.frames if frame.clock_minute < 45)
    assert any(not frame.home_attacks_right for frame in view_a.frames if frame.clock_minute >= 45)
    assert any(event.event_type is MatchViewerEventType.GOAL for event in view_a.events)
    for frame in view_a.frames:
        assert 0.0 <= frame.ball.position.x <= 100.0
        assert 0.0 <= frame.ball.position.y <= 100.0
        for player in frame.players:
            assert 0.0 <= player.position.x <= 100.0
            assert 0.0 <= player.position.y <= 100.0


def test_match_timeline_service_surfaces_major_event_types_across_replays() -> None:
    simulation_service = MatchSimulationService()
    timeline_service = MatchTimelineService()
    discovered: set[MatchViewerEventType] = set()

    for seed in range(1, 60):
        replay_payload = simulation_service.build_replay_payload(
            build_request(
                seed=seed,
                home_team=build_team(
                    "home",
                    "North City",
                    83,
                    formation="4-3-3",
                    style=TacticalStyle.ATTACKING,
                    pressing=86,
                    aggression=94,
                    discipline=18,
                ),
                away_team=build_team(
                    "away",
                    "South Town",
                    82,
                    formation="3-5-2",
                    style=TacticalStyle.ATTACKING,
                    pressing=84,
                    aggression=92,
                    discipline=20,
                ),
            )
        )
        discovered.update(event.event_type for event in timeline_service.build_from_replay_payload(replay_payload).events)
        if {
            MatchViewerEventType.GOAL,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.RED_CARD,
        }.issubset(discovered):
            break

    assert MatchViewerEventType.GOAL in discovered
    assert MatchViewerEventType.SAVE in discovered
    assert MatchViewerEventType.MISS in discovered
    assert MatchViewerEventType.RED_CARD in discovered


def test_match_timeline_service_builds_archive_fallback() -> None:
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=27))
    record = ReplayArchiveRecord.model_validate(
        {
            "replay_id": "replay:match-001",
            "version": 1,
            "fixture_id": replay_payload.match_id,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "scheduled_start": datetime.now(UTC),
            "started_at": datetime.now(UTC),
            "final_whistle_at": datetime.now(UTC),
            "live": False,
            "home_club": {"club_id": replay_payload.visual_identity.home_team.team_id, "club_name": replay_payload.visual_identity.home_team.team_name},
            "away_club": {"club_id": replay_payload.visual_identity.away_team.team_id, "club_name": replay_payload.visual_identity.away_team.team_name},
            "scoreline": {
                "home_goals": replay_payload.summary.home_score,
                "away_goals": replay_payload.summary.away_score,
            },
            "visual_identity": replay_payload.visual_identity.model_dump(mode="json"),
            "timeline": [
                {
                    "event_id": event.event_id,
                    "minute": event.minute,
                    "event_type": _archive_event_type(event.event_type),
                    "club_id": event.team_id,
                    "club_name": event.team_name,
                    "player_id": event.primary_player.player_id if event.primary_player is not None else None,
                    "player_name": event.primary_player.player_name if event.primary_player is not None else None,
                    "secondary_player_id": event.secondary_player.player_id if event.secondary_player is not None else None,
                    "secondary_player_name": event.secondary_player.player_name if event.secondary_player is not None else None,
                    "description": event.commentary,
                    "home_score": event.home_score,
                    "away_score": event.away_score,
                    "is_penalty": event.event_type in {MatchEventType.PENALTY_SCORED, MatchEventType.PENALTY_MISSED},
                }
                for event in replay_payload.timeline.events
                if _archive_event_type(event.event_type) is not None
            ],
            "participant_user_ids": [],
            "competition_context": {
                "competition_id": "comp-001",
                "competition_type": "league",
                "competition_name": "GTEX League",
                "season_id": "season-001",
                "stage_name": "Regular",
                "round_number": 1,
                "is_final": False,
                "is_cup_match": False,
                "competition_allows_public": True,
                "allow_early_round_public": False,
                "presentation_duration_minutes": 4,
                "replay_visibility": "competition",
                "resolved_visibility": "competition",
                "public_metadata_visible": True,
                "featured_public": False,
            },
        }
    )

    view_state = MatchTimelineService().build_from_archive_record(record)

    assert view_state.source == "replay_archive"
    assert view_state.home_team.team_name == replay_payload.visual_identity.home_team.team_name
    assert view_state.away_team.team_name == replay_payload.visual_identity.away_team.team_name
    assert view_state.frames[-1].home_score == replay_payload.summary.home_score
    assert view_state.frames[-1].away_score == replay_payload.summary.away_score


def _archive_event_type(event_type: MatchEventType) -> str | None:
    mapping = {
        MatchEventType.GOAL: "goals",
        MatchEventType.PENALTY_SCORED: "penalties",
        MatchEventType.GOALKEEPER_SAVE: "missed_chances",
        MatchEventType.DOUBLE_SAVE: "missed_chances",
        MatchEventType.MISSED_CHANCE: "missed_chances",
        MatchEventType.MISSED_BIG_CHANCE: "missed_chances",
        MatchEventType.WOODWORK: "missed_chances",
        MatchEventType.PENALTY_MISSED: "penalties",
        MatchEventType.RED_CARD: "red_cards",
        MatchEventType.YELLOW_CARD: "yellow_cards",
        MatchEventType.SUBSTITUTION: "substitutions",
        MatchEventType.INJURY: "injuries",
    }
    return mapping.get(event_type)

