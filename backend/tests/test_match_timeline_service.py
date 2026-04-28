from __future__ import annotations

from datetime import UTC, datetime

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType, TacticalStyle
from app.live_matches.schemas import LiveMatchRenderPointView, LiveMatchStreamEventView
from app.replay_archive.schemas import ReplayArchiveRecord
from app.services.match_timeline_service import MatchTimelineService
from app.schemas.match_viewer import (
    MatchViewerAnimationState,
    MatchViewerEventType,
    MatchViewerPossessionPhase,
    MatchViewerPlayerState,
    MatchViewerSide,
)
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
        discovered.update(
            event.event_type for event in timeline_service.build_from_replay_payload(replay_payload).events
        )
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


def test_match_timeline_service_enriches_frames_with_player_motion_pressure_and_tags() -> None:
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=33))

    view_state = MatchTimelineService().build_from_replay_payload(replay_payload)

    assert all(0.0 <= frame.pressure_index <= 1.0 for frame in view_state.frames)
    assert all(0.0 <= frame.compactness_home <= 1.0 for frame in view_state.frames)
    assert all(0.0 <= frame.compactness_away <= 1.0 for frame in view_state.frames)
    assert all(frame.danger_zone for frame in view_state.frames)
    assert any(frame.frame_tags for frame in view_state.frames)
    assert any(
        frame.possession_phase
        in {
            MatchViewerPossessionPhase.TRANSITION,
            MatchViewerPossessionPhase.FINAL_THIRD,
            MatchViewerPossessionPhase.BOX_ATTACK,
        }
        for frame in view_state.frames
    )
    assert any(player.has_possession for frame in view_state.frames for player in frame.players)
    assert any(
        player.animation_state is not MatchViewerAnimationState.IDLE
        for frame in view_state.frames
        for player in frame.players
    )
    for frame in view_state.frames:
        for player in frame.players:
            assert 0.0 <= player.speed_ratio <= 1.0
            assert 0.0 <= player.blend_factor <= 1.0
            assert 0.0 <= player.stamina_pct <= 100.0
            assert -1.0 <= player.facing.x <= 1.0
            assert -1.0 <= player.facing.y <= 1.0


def test_match_timeline_service_builds_archive_fallback() -> None:
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=27))
    record = _build_archive_record(replay_payload, presentation_duration_minutes=4)

    view_state = MatchTimelineService().build_from_archive_record(record)

    assert view_state.source == "replay_archive"
    assert view_state.home_team.team_name == replay_payload.visual_identity.home_team.team_name
    assert view_state.away_team.team_name == replay_payload.visual_identity.away_team.team_name
    assert view_state.frames[-1].home_score == replay_payload.summary.home_score
    assert view_state.frames[-1].away_score == replay_payload.summary.away_score


def test_match_timeline_service_handles_stress_profiles_back_to_back() -> None:
    simulation_service = MatchSimulationService()
    timeline_service = MatchTimelineService()

    requests = [
        build_request(
            seed=81,
            home_team=build_team(
                "home",
                "North City",
                86,
                formation="4-3-3",
                style=TacticalStyle.ATTACKING,
                pressing=90,
                aggression=95,
                discipline=16,
            ),
            away_team=build_team(
                "away",
                "South Town",
                84,
                formation="3-5-2",
                style=TacticalStyle.ATTACKING,
                pressing=88,
                aggression=93,
                discipline=18,
            ),
        ),
        build_request(
            seed=82,
            home_team=build_team(
                "home",
                "North City",
                80,
                formation="4-4-2",
                style=TacticalStyle.BALANCED,
                pressing=38,
                aggression=22,
                discipline=92,
            ),
            away_team=build_team(
                "away",
                "South Town",
                79,
                formation="4-2-3-1",
                style=TacticalStyle.BALANCED,
                pressing=35,
                aggression=24,
                discipline=94,
            ),
        ),
        *[build_request(seed=seed) for seed in range(83, 89)],
    ]

    for request in requests:
        replay_payload = simulation_service.build_replay_payload(request)
        view_state = timeline_service.build_from_replay_payload(replay_payload)

        assert view_state.frames
        assert view_state.events
        assert view_state.frames[-1].home_score == replay_payload.summary.home_score
        assert view_state.frames[-1].away_score == replay_payload.summary.away_score
        assert all(frame.possession_side in {MatchViewerSide.HOME, MatchViewerSide.AWAY} for frame in view_state.frames)
        assert max(len(frame.players) for frame in view_state.frames) <= 22


def test_match_timeline_service_builds_long_archive_replay() -> None:
    replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=91))
    record = _build_archive_record(
        replay_payload,
        presentation_duration_minutes=8,
        is_final=True,
    )

    view_state = MatchTimelineService().build_from_archive_record(record)

    assert view_state.duration_seconds == 480
    assert view_state.frames[-1].time_seconds >= 480
    assert all(frame.possession_side in {MatchViewerSide.HOME, MatchViewerSide.AWAY} for frame in view_state.frames)


def test_match_timeline_service_maps_infinite_league_chance_and_save_events_to_action_frames() -> None:
    service = MatchTimelineService()
    view_state = service.build_from_live_stream(
        match_id="match-live-001",
        source="infinite_league_runtime",
        home_team_id="home-team",
        home_team_name="North City",
        away_team_id="away-team",
        away_team_name="South Town",
        events=[
            LiveMatchStreamEventView(
                match_id="match-live-001",
                event_id="match-live-001:chance",
                sequence=1,
                tick=120,
                minute=2,
                event_type="chance",
                team_id="home-team",
                team="North City",
                player_id="north-city-9",
                player="North City 9",
                secondary_player_id="north-city-10",
                secondary_player="North City 10",
                commentary="North City miss a big chance.",
                position=LiveMatchRenderPointView(x=62.0, y=48.0),
                target_position=LiveMatchRenderPointView(x=87.0, y=44.0),
                metadata={"raw_event_type": "chance", "team_side": "home"},
            ),
            LiveMatchStreamEventView(
                match_id="match-live-001",
                event_id="match-live-001:save",
                sequence=2,
                tick=185,
                minute=3,
                event_type="save",
                team_id="away-team",
                team="South Town",
                player_id="south-town-gk",
                player="South Town GK",
                secondary_player_id="north-city-9",
                secondary_player="North City 9",
                commentary="The keeper makes the save.",
                position=LiveMatchRenderPointView(x=14.0, y=50.0),
                target_position=LiveMatchRenderPointView(x=9.0, y=51.0),
                metadata={"raw_event_type": "save", "team_side": "away"},
            ),
        ],
    )

    event_types = {event.event_type for event in view_state.events}
    assert MatchViewerEventType.MISS in event_types
    assert MatchViewerEventType.SAVE in event_types

    moving_frames = [
        frame
        for frame in view_state.frames
        if frame.active_event_id in {"match-live-001:chance", "match-live-001:save"}
    ]
    assert moving_frames
    assert any(frame.ball.position.x != 50.0 or frame.ball.position.y != 50.0 for frame in moving_frames)
    assert any(
        sum(
            1
            for player in frame.players
            if player.state in {MatchViewerPlayerState.ATTACKING, MatchViewerPlayerState.PRESSING}
        )
        >= 3
        for frame in moving_frames
    )


def test_match_timeline_service_maps_live_pass_events_to_2d_contract() -> None:
    service = MatchTimelineService()

    view_state = service.build_from_live_stream(
        match_id="match-live-pass-001",
        source="infinite_league_runtime",
        home_team_id="home-team",
        home_team_name="North City",
        away_team_id="away-team",
        away_team_name="South Town",
        events=[
            LiveMatchStreamEventView(
                match_id="match-live-pass-001",
                event_id="match-live-pass-001:pass",
                sequence=1,
                tick=11,
                minute=0,
                event_type="pass",
                team_id="home-team",
                team="North City",
                team_side="home",
                player_id="north-city-6",
                player="Zakaria",
                secondary_player_id="north-city-8",
                secondary_player="Schingienne",
                commentary="Zakaria lays it back to Schingienne",
                position=LiveMatchRenderPointView(x=44.0, y=52.0),
                target_position=LiveMatchRenderPointView(x=52.0, y=48.0),
                meta={
                    "duration_ms": 650,
                    "positions": [
                        {
                            "player_id": "north-city-6",
                            "player_name": "Zakaria",
                            "team_id": "home-team",
                            "side": "home",
                            "shirt_number": 6,
                            "role": "midfielder",
                            "line": "midfield",
                            "position": {"x": 44.0, "y": 52.0},
                        },
                        {
                            "player_id": "north-city-8",
                            "player_name": "Schingienne",
                            "team_id": "home-team",
                            "side": "home",
                            "shirt_number": 8,
                            "role": "midfielder",
                            "line": "midfield",
                            "position": {"x": 52.0, "y": 48.0},
                        },
                    ],
                    "ball": {
                        "position": {"x": 52.0, "y": 48.0},
                        "owner_player_id": "north-city-8",
                        "state": "pass",
                    },
                },
            ),
        ],
    )

    event = next(event for event in view_state.events if event.event_id == "match-live-pass-001:pass")
    assert event.event_type is MatchViewerEventType.PASS
    assert event.commentary == "Zakaria lays it back to Schingienne"
    assert event.duration_ms == 650
    assert event.positions[0].position.x == 44.0
    assert event.positions[1].position.y == 48.0
    assert event.ball is not None
    assert event.ball.owner_player_id == "north-city-8"
    assert all(0.0 <= frame.ball.position.x <= 100.0 for frame in view_state.frames)
    assert all(0.0 <= player.position.y <= 100.0 for frame in view_state.frames for player in frame.players)


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


def _build_archive_record(
    replay_payload,
    *,
    presentation_duration_minutes: int,
    is_final: bool = False,
) -> ReplayArchiveRecord:
    return ReplayArchiveRecord.model_validate(
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
            "home_club": {
                "club_id": replay_payload.visual_identity.home_team.team_id,
                "club_name": replay_payload.visual_identity.home_team.team_name,
            },
            "away_club": {
                "club_id": replay_payload.visual_identity.away_team.team_id,
                "club_name": replay_payload.visual_identity.away_team.team_name,
            },
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
                    "secondary_player_id": (
                        event.secondary_player.player_id if event.secondary_player is not None else None
                    ),
                    "secondary_player_name": (
                        event.secondary_player.player_name if event.secondary_player is not None else None
                    ),
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
                "is_final": is_final,
                "is_cup_match": False,
                "competition_allows_public": True,
                "allow_early_round_public": False,
                "presentation_duration_minutes": presentation_duration_minutes,
                "replay_visibility": "competition",
                "resolved_visibility": "competition",
                "public_metadata_visible": True,
                "featured_public": False,
            },
        }
    )
