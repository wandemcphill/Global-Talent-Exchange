from __future__ import annotations

from decimal import Decimal

from backend.app.common.enums.qualification_status import QualificationStatus as SharedQualificationStatus
from backend.app.champions_league.models.domain import QualificationStatus
from backend.app.champions_league.services.tournament import ChampionsLeagueService, LeaguePhaseTableService


def test_48_to_36_pathway(build_candidates) -> None:
    service = ChampionsLeagueService()

    qualification = service.build_qualification_map(build_candidates())
    playoff = service.build_playoff_bracket(build_candidates())

    assert len(qualification.direct_qualifiers) == 24
    assert len(qualification.playoff_qualifiers) == 24
    assert len([entry for entry in qualification.entries if entry.status is QualificationStatus.ELIMINATED]) == 12
    assert len(playoff.ties) == 12
    assert len(playoff.advancing_clubs) == 36
    assert len({club.club_id for club in playoff.advancing_clubs}) == 36


def test_standings_tie_breakers_prioritize_goal_difference_then_goals_for(build_league_clubs) -> None:
    seeded_clubs = build_league_clubs(4)
    table = LeaguePhaseTableService().build_table(
        clubs=seeded_clubs,
        matches=[
            _match("m1", seeded_clubs[0].club_id, seeded_clubs[3].club_id, 2, 0),
            _match("m2", seeded_clubs[1].club_id, seeded_clubs[2].club_id, 3, 1),
            _match("m3", seeded_clubs[0].club_id, seeded_clubs[1].club_id, 1, 1),
            _match("m4", seeded_clubs[2].club_id, seeded_clubs[3].club_id, 0, 0),
            _match("m5", seeded_clubs[0].club_id, seeded_clubs[2].club_id, 0, 0),
            _match("m6", seeded_clubs[1].club_id, seeded_clubs[3].club_id, 0, 0),
        ],
    )

    assert [row.club_id for row in table.rows[:2]] == [seeded_clubs[1].club_id, seeded_clubs[0].club_id]
    assert table.rows[0].points == table.rows[1].points
    assert table.rows[0].goal_difference == table.rows[1].goal_difference
    assert table.rows[0].goals_for > table.rows[1].goals_for


def test_ranks_9_through_24_enter_knockout_playoff(build_standings_rows) -> None:
    service = ChampionsLeagueService()

    bracket = service.build_knockout_bracket(build_standings_rows())

    assert len(bracket.knockout_playoff) == 8
    assert bracket.knockout_playoff[0].home_club.seed == 9
    assert bracket.knockout_playoff[0].away_club.seed == 24
    assert bracket.knockout_playoff[-1].home_club.seed == 16
    assert bracket.knockout_playoff[-1].away_club.seed == 17
    assert bracket.champion.seed == 1


def test_champion_settlement_preview_uses_append_only_event_hooks() -> None:
    preview = ChampionsLeagueService().build_prize_pool_preview(
        season_id="ucl-2026",
        league_leftover_allocation=Decimal("1000"),
        champion_club_id="club-01",
        champion_club_name="Club 01",
        currency="credit",
    )

    assert preview.funded_pool == Decimal("350.0000")
    assert preview.champion_share == Decimal("245.0000")
    assert preview.platform_share == Decimal("105.0000")
    assert [event.event_type for event in preview.events] == [
        "champions_league.prize_pool_funded",
        "champions_league.champion_awarded",
        "champions_league.platform_awarded",
    ]


def test_qualification_color_and_status_mapping(build_candidates) -> None:
    qualification = ChampionsLeagueService().build_qualification_map(build_candidates())

    assert qualification.direct_qualifiers[0].status is QualificationStatus.DIRECT
    assert qualification.direct_qualifiers[0].display_color == "emerald"
    assert qualification.playoff_qualifiers[0].status is QualificationStatus.PLAYOFF
    assert qualification.playoff_qualifiers[0].display_color == "amber"
    assert qualification.entries[-1].status is QualificationStatus.ELIMINATED
    assert qualification.entries[-1].display_color == "slate"


def test_champions_league_reuses_shared_qualification_status_enum() -> None:
    assert QualificationStatus is SharedQualificationStatus


def _match(match_id: str, home_club_id: str, away_club_id: str, home_goals: int, away_goals: int):
    from backend.app.champions_league.models.domain import LeagueMatchResult

    return LeagueMatchResult(
        match_id=match_id,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
        home_goals=home_goals,
        away_goals=away_goals,
    )
