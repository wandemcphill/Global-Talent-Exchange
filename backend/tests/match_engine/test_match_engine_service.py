from __future__ import annotations

from backend.app.common.enums.match_status import MatchStatus
from backend.app.config.competition_constants import MATCH_PRESENTATION_MAX_MINUTES, MATCH_PRESENTATION_MIN_MINUTES
from backend.app.match_engine.schemas import MatchKitIdentityInput, MatchTeamIdentityInput
from backend.app.match_engine.services.match_simulation_service import MatchSimulationService
from backend.app.match_engine.simulation.models import MatchCompetitionType, MatchEventType, PlayerRole, TacticalStyle
from backend.tests.match_engine.helpers import build_request, build_team


def _find_payload(service: MatchSimulationService, request_builder, predicate, *, seeds=range(1, 220)):
    for seed in seeds:
        payload = service.build_replay_payload(request_builder(seed))
        if predicate(payload):
            return payload
    raise AssertionError("No payload satisfied the requested predicate within the seed range")


def test_match_simulation_is_deterministic_for_same_seed() -> None:
    service = MatchSimulationService()
    request = build_request(seed=17)
    first = service.build_replay_payload(request)
    second = service.build_replay_payload(request)
    assert first.model_dump() == second.model_dump()


def test_replay_payload_contains_valid_key_moments_and_standard_duration() -> None:
    service = MatchSimulationService()
    payload = service.build_replay_payload(build_request(seed=11))

    assert payload.summary.status is MatchStatus.COMPLETED
    assert payload.timeline.events[0].event_type is MatchEventType.KICKOFF
    assert payload.timeline.events[-1].event_type is MatchEventType.FULLTIME
    assert any(event.event_type is MatchEventType.HALFTIME for event in payload.timeline.events)
    assert MATCH_PRESENTATION_MIN_MINUTES * 60 <= payload.timeline.presentation_duration_seconds <= MATCH_PRESENTATION_MAX_MINUTES * 60
    assert [event.sequence for event in payload.timeline.events] == sorted(event.sequence for event in payload.timeline.events)
    assert [event.presentation_second for event in payload.timeline.events] == sorted(
        event.presentation_second for event in payload.timeline.events
    )
    assert len(payload.timeline.events) == len(payload.replay_log)

    player_event_types = {
        MatchEventType.MISSED_CHANCE,
        MatchEventType.SAVE,
        MatchEventType.GOAL,
        MatchEventType.YELLOW_CARD,
        MatchEventType.RED_CARD,
        MatchEventType.INJURY,
        MatchEventType.SUBSTITUTION,
        MatchEventType.PENALTY_GOAL,
        MatchEventType.PENALTY_MISS,
    }
    for event in payload.timeline.events:
        assert event.commentary
        assert event.clock_label
        if event.event_type in player_event_types:
            assert event.primary_player is not None


def test_cup_draws_go_straight_to_penalties_without_extra_time() -> None:
    service = MatchSimulationService()
    balanced_home = build_team("cup-home", "Cup Home", 76)
    balanced_away = build_team("cup-away", "Cup Away", 76)
    payload = _find_payload(
        service,
        lambda seed: build_request(
            seed=seed,
            competition_type=MatchCompetitionType.CUP,
            requires_winner=True,
            home_team=balanced_home,
            away_team=balanced_away,
        ),
        lambda payload: payload.summary.decided_by_penalties,
    )

    regular_events = [
        event for event in payload.timeline.events if event.event_type not in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS}
    ]
    fulltime_index = next(index for index, event in enumerate(payload.timeline.events) if event.event_type is MatchEventType.FULLTIME)

    assert payload.summary.shootout is not None
    assert payload.summary.home_penalty_score != payload.summary.away_penalty_score
    assert max(event.minute for event in regular_events) == 90
    assert all(
        event.event_type in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS}
        for event in payload.timeline.events[fulltime_index + 1 :]
    )


def test_red_card_switches_team_into_fallback_shape() -> None:
    service = MatchSimulationService()
    disciplined_home = build_team("steady-home", "Steady Home", 79)
    volatile_away = build_team(
        "volatile-away",
        "Volatile Away",
        79,
        aggression=100,
        discipline=18,
        red_card_fallback_formation="4-4-1",
        style=TacticalStyle.ATTACKING,
    )
    payload = _find_payload(
        service,
        lambda seed: build_request(seed=seed, home_team=disciplined_home, away_team=volatile_away),
        lambda payload: any(
            event.event_type is MatchEventType.RED_CARD and event.team_id == volatile_away.team_id for event in payload.timeline.events
        ),
    )

    red_event = next(
        event for event in payload.timeline.events if event.event_type is MatchEventType.RED_CARD and event.team_id == volatile_away.team_id
    )
    assert red_event.metadata["fallback_formation"] == "4-4-1"
    assert payload.summary.away_stats.current_formation == "4-4-1"


def test_injury_auto_substitution_reacts_in_same_window() -> None:
    service = MatchSimulationService()
    stable_home = build_team("stable-home", "Stable Home", 80)
    fragile_away = build_team(
        "fragile-away",
        "Fragile Away",
        77,
        tempo=84,
        pressing=81,
        fitness=30,
    )
    payload = _find_payload(
        service,
        lambda seed: build_request(seed=seed, home_team=stable_home, away_team=fragile_away),
        lambda payload: any(
            event.event_type is MatchEventType.SUBSTITUTION
            and event.team_id == fragile_away.team_id
            and event.metadata.get("reason") == "injury"
            for event in payload.timeline.events
        ),
    )

    injury_event = next(
        event for event in payload.timeline.events if event.event_type is MatchEventType.INJURY and event.team_id == fragile_away.team_id
    )
    substitution_event = next(
        event
        for event in payload.timeline.events
        if event.event_type is MatchEventType.SUBSTITUTION
        and event.team_id == fragile_away.team_id
        and event.metadata.get("reason") == "injury"
    )
    assert substitution_event.minute == injury_event.minute


def test_yellow_card_replacement_prefers_configured_roles() -> None:
    service = MatchSimulationService()
    control_home = build_team("control-home", "Control Home", 80)
    managed_away = build_team(
        "managed-away",
        "Managed Away",
        78,
        aggression=84,
        discipline=44,
        substitution_windows=(56, 68, 80),
        yellow_card_substitution_minute=55,
        yellow_card_replacement_roles=(PlayerRole.DEFENDER,),
    )
    payload = _find_payload(
        service,
        lambda seed: build_request(seed=seed, home_team=control_home, away_team=managed_away),
        lambda payload: any(
            event.event_type is MatchEventType.SUBSTITUTION
            and event.team_id == managed_away.team_id
            and event.metadata.get("reason") == "yellow_card_protection"
            for event in payload.timeline.events
        ),
    )

    substitution_event = next(
        event
        for event in payload.timeline.events
        if event.event_type is MatchEventType.SUBSTITUTION
        and event.team_id == managed_away.team_id
        and event.metadata.get("reason") == "yellow_card_protection"
    )
    assert substitution_event.metadata["outgoing_role"] == PlayerRole.DEFENDER.value


def test_stronger_team_has_bias_without_removing_upsets() -> None:
    service = MatchSimulationService()
    strong_home = build_team("strong-home", "Powerhouse", 90, style=TacticalStyle.ATTACKING, pressing=74, tempo=74)
    weak_away = build_team("weak-away", "Underdogs", 62, style=TacticalStyle.BALANCED, pressing=50, tempo=50)

    strong_wins = 0
    weak_wins = 0
    draws = 0
    for seed in range(1, 181):
        summary = service.build_summary(build_request(seed=seed, home_team=strong_home, away_team=weak_away))
        if summary.winner_team_id == strong_home.team_id:
            strong_wins += 1
        elif summary.winner_team_id == weak_away.team_id:
            weak_wins += 1
        else:
            draws += 1

    assert strong_wins > weak_wins * 3
    assert weak_wins > 0
    assert strong_wins + weak_wins + draws == 180


def test_home_strength_has_home_edge_for_even_matchup() -> None:
    service = MatchSimulationService()
    home = build_team("home-edge", "Home Edge", 78)
    away = build_team("away-edge", "Away Edge", 78)

    summary = service.build_summary(build_request(seed=3, home_team=home, away_team=away))

    assert summary.home_stats.strength.overall >= summary.away_stats.strength.overall
    assert summary.home_stats.strength.motivation > summary.away_stats.strength.motivation


def test_manager_profile_boosts_coach_and_tactical_quality() -> None:
    service = MatchSimulationService()
    elite_manager = {
        "display_name": "Elite Manager",
        "mentality": "pressing",
        "tactics": ["high_press_attack", "tiki_taka", "possession_control"],
        "traits": ["great_motivator", "tactical_flexibility", "defensive_organization"],
        "rarity": "legendary",
        "substitution_tendency": "proactive",
    }
    home = build_team("managed-home", "Managed Home", 78).model_copy(update={"manager_profile": elite_manager})
    away = build_team("managed-away", "Managed Away", 78)

    summary = service.build_summary(build_request(seed=5, home_team=home, away_team=away))

    assert summary.home_stats.strength.coach_quality > summary.away_stats.strength.coach_quality
    assert summary.home_stats.strength.tactical_quality >= summary.away_stats.strength.tactical_quality
    assert summary.home_stats.strength.adaptability >= summary.away_stats.strength.adaptability


def test_visual_identity_payload_includes_kits_and_players() -> None:
    service = MatchSimulationService()
    home_identity = MatchTeamIdentityInput(
        club_name="North City",
        short_club_code="NCI",
        badge_url="https://example.com/north-city.svg",
        badge_shape="shield",
        badge_initials="NC",
        badge_primary_color="#112233",
        badge_secondary_color="#ffffff",
        badge_accent_color="#ffcc00",
        home_kit=MatchKitIdentityInput(primary_color="#112233", secondary_color="#ffffff", accent_color="#ffcc00", front_text="NCI"),
        away_kit=MatchKitIdentityInput(
            kit_type="away",
            primary_color="#f1f5f9",
            secondary_color="#1e293b",
            accent_color="#f97316",
            front_text="NCI",
        ),
        goalkeeper_kit=MatchKitIdentityInput(
            kit_type="goalkeeper",
            primary_color="#111827",
            secondary_color="#a7f3d0",
            accent_color="#f9fafb",
            front_text="NCI",
        ),
    )
    away_identity = MatchTeamIdentityInput(
        club_name="South Town",
        short_club_code="STW",
        badge_url="https://example.com/south-town.svg",
        badge_shape="round",
        badge_initials="ST",
        badge_primary_color="#1f2937",
        badge_secondary_color="#e2e8f0",
        badge_accent_color="#38bdf8",
        home_kit=MatchKitIdentityInput(primary_color="#1f2937", secondary_color="#e2e8f0", accent_color="#38bdf8", front_text="STW"),
        away_kit=MatchKitIdentityInput(
            kit_type="away",
            primary_color="#f8fafc",
            secondary_color="#0f172a",
            accent_color="#22c55e",
            front_text="STW",
        ),
        goalkeeper_kit=MatchKitIdentityInput(
            kit_type="goalkeeper",
            primary_color="#0f172a",
            secondary_color="#38bdf8",
            accent_color="#fbbf24",
            front_text="STW",
        ),
    )
    home_team = build_team("north", "North City", 80).model_copy(update={"identity": home_identity})
    away_team = build_team("south", "South Town", 78).model_copy(update={"identity": away_identity})

    payload = service.build_replay_payload(build_request(seed=9, home_team=home_team, away_team=away_team))

    assert payload.visual_identity is not None
    assert payload.visual_identity.home_team.badge.badge_url == "https://example.com/north-city.svg"
    assert payload.visual_identity.home_team.selected_kit.primary_color == "#112233"
    assert payload.visual_identity.home_team.player_visuals
    assert any(player.shirt_number == 1 for player in payload.visual_identity.home_team.player_visuals)
    assert any(player.shirt_name == "N1" for player in payload.visual_identity.home_team.player_visuals)


def test_kit_clash_resolves_to_alternate() -> None:
    service = MatchSimulationService()
    home_identity = MatchTeamIdentityInput(
        club_name="Clash FC",
        short_club_code="CLH",
        home_kit=MatchKitIdentityInput(primary_color="#111111", secondary_color="#444444", accent_color="#888888", front_text="CLH"),
        away_kit=MatchKitIdentityInput(
            kit_type="away",
            primary_color="#f7fafc",
            secondary_color="#111827",
            accent_color="#38bdf8",
            front_text="CLH",
        ),
    )
    away_identity = MatchTeamIdentityInput(
        club_name="Clash Away",
        short_club_code="CLA",
        home_kit=MatchKitIdentityInput(primary_color="#111111", secondary_color="#333333", accent_color="#f97316", front_text="CLA"),
        away_kit=MatchKitIdentityInput(
            kit_type="away",
            primary_color="#f7fafc",
            secondary_color="#111827",
            accent_color="#22c55e",
            front_text="CLA",
        ),
    )
    home_team = build_team("clash-home", "Clash FC", 79).model_copy(update={"identity": home_identity})
    away_team = build_team("clash-away", "Clash Away", 79).model_copy(update={"identity": away_identity})

    payload = service.build_replay_payload(build_request(seed=12, home_team=home_team, away_team=away_team))

    assert payload.visual_identity is not None
    assert payload.visual_identity.clash_resolved
    assert payload.visual_identity.away_team.selected_kit.primary_color == "#f7fafc"


def test_woodwork_and_double_save_events_surface() -> None:
    service = MatchSimulationService()
    payload_woodwork = _find_payload(
        service,
        lambda seed: build_request(seed=seed),
        lambda payload: any(event.event_type is MatchEventType.WOODWORK for event in payload.timeline.events),
        seeds=range(1, 160),
    )
    payload_double_save = _find_payload(
        service,
        lambda seed: build_request(seed=seed),
        lambda payload: any(event.event_type is MatchEventType.DOUBLE_SAVE for event in payload.timeline.events),
        seeds=range(1, 200),
    )

    assert any(event.event_type is MatchEventType.WOODWORK for event in payload_woodwork.timeline.events)
    assert any(event.event_type is MatchEventType.DOUBLE_SAVE for event in payload_double_save.timeline.events)
