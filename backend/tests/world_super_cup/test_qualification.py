from __future__ import annotations

from datetime import datetime, timezone

from backend.app.config.competition_constants import (
    WORLD_SUPER_CUP_DIRECT_SLOTS,
    WORLD_SUPER_CUP_MAIN_TEAMS,
    WORLD_SUPER_CUP_PLAYOFF_TEAMS,
    WORLD_SUPER_CUP_PLAYOFF_WINNERS,
)
from backend.app.world_super_cup.models import ClubSeasonPerformance
from backend.app.world_super_cup.services.calendar import WorldSuperCupCalendarService
from backend.app.world_super_cup.services.qualification import QualificationCoefficientService
from backend.app.world_super_cup.services.tournament import WorldSuperCupService


def test_world_super_cup_qualification_pipeline_keeps_32_club_integrity() -> None:
    service = WorldSuperCupService()
    plan = service.build_demo_tournament(datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc))

    qualification = plan.qualification
    assert len(qualification.direct_qualifiers) == WORLD_SUPER_CUP_DIRECT_SLOTS
    assert len(qualification.playoff_qualifiers) == WORLD_SUPER_CUP_PLAYOFF_TEAMS
    assert len(qualification.playoff_winners) == WORLD_SUPER_CUP_PLAYOFF_WINNERS
    assert len(qualification.main_event_clubs) == WORLD_SUPER_CUP_MAIN_TEAMS
    assert len({club.club_id for club in qualification.main_event_clubs}) == WORLD_SUPER_CUP_MAIN_TEAMS
    direct_by_region = {}
    for club in qualification.direct_qualifiers:
        direct_by_region[club.region] = direct_by_region.get(club.region, 0) + 1
    assert all(slot_count == 4 for slot_count in direct_by_region.values())


def test_two_season_coefficient_ranking_ignores_older_history_and_uses_recent_tiebreaker() -> None:
    results = (
        ClubSeasonPerformance(
            club_id="club-a",
            club_name="Club A",
            region="Europe",
            season_year=2025,
            coefficient_points=20,
            continental_finish="winner",
        ),
        ClubSeasonPerformance(
            club_id="club-a",
            club_name="Club A",
            region="Europe",
            season_year=2024,
            coefficient_points=10,
        ),
        ClubSeasonPerformance(
            club_id="club-a",
            club_name="Club A",
            region="Europe",
            season_year=2023,
            coefficient_points=99,
        ),
        ClubSeasonPerformance(
            club_id="club-b",
            club_name="Club B",
            region="Europe",
            season_year=2025,
            coefficient_points=19,
        ),
        ClubSeasonPerformance(
            club_id="club-b",
            club_name="Club B",
            region="Europe",
            season_year=2024,
            coefficient_points=11,
            continental_finish="runner_up",
        ),
        ClubSeasonPerformance(
            club_id="club-c",
            club_name="Club C",
            region="Europe",
            season_year=2025,
            coefficient_points=18,
        ),
        ClubSeasonPerformance(
            club_id="club-c",
            club_name="Club C",
            region="Europe",
            season_year=2024,
            coefficient_points=11,
        ),
    )

    table = QualificationCoefficientService().build_table(results)

    assert [entry.club_id for entry in table] == ["club-a", "club-b", "club-c"]
    assert table[0].total_points == 30
    assert table[1].total_points == 30
    assert table[0].recent_season_points > table[1].recent_season_points


def test_pause_policy_keeps_fast_cup_and_academy_running() -> None:
    pause_policy = WorldSuperCupCalendarService().pause_policy()

    assert pause_policy.cadence_description == "Runs every 2 weeks and every 2 seasons."
    assert pause_policy.paused_competitions == ("senior_regional_leagues", "senior_continental_cups")
    assert pause_policy.active_competitions == ("gtex_fast_cup", "academy_competitions")
