from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.academy.api.router import router
from backend.app.academy.models import (
    AcademyAwardsLeaders,
    AcademyClubRegistrationRequest,
    AcademyMatchResult,
    AcademySeasonRequest,
)
from backend.app.academy.services import AcademyCompetitionService
from backend.app.config.competition_constants import LEAGUE_GROUP_SIZE
from backend.app.competition_engine import MatchDispatcher
from backend.app.competition_engine.queue_contracts import InMemoryQueuePublisher


def _build_clubs() -> tuple[AcademyClubRegistrationRequest, ...]:
    buy_in_cycle = (1000, 800, 500, 300, 150, 25)
    clubs: list[AcademyClubRegistrationRequest] = []
    for index in range(LEAGUE_GROUP_SIZE):
        clubs.append(
            AcademyClubRegistrationRequest(
                club_id=f"club-{index + 1:02d}",
                club_name=f"Academy Club {index + 1:02d}",
                senior_buy_in_tier=buy_in_cycle[index % len(buy_in_cycle)],
            )
        )
    return tuple(clubs)


def _build_request(*, with_results: bool) -> AcademySeasonRequest:
    service = AcademyCompetitionService()
    clubs = _build_clubs()
    request = AcademySeasonRequest(
        season_id="academy-season-1",
        start_date=date(2026, 1, 1),
        clubs=clubs,
        awards_leaders=AcademyAwardsLeaders(
            top_scorer_club_id="club-01",
            top_assist_club_id="club-02",
        ),
    )
    if not with_results:
        return request
    fixtures = service.build_fixtures(request)
    strengths = {club.club_id: position for position, club in enumerate(clubs, start=1)}
    results = tuple(
        AcademyMatchResult(
            fixture_id=fixture.fixture_id,
            home_goals=3 if strengths[fixture.home_club_id] < strengths[fixture.away_club_id] else 0,
            away_goals=0 if strengths[fixture.home_club_id] < strengths[fixture.away_club_id] else 1,
        )
        for fixture in fixtures
    )
    return AcademySeasonRequest(
        season_id=request.season_id,
        start_date=request.start_date,
        clubs=request.clubs,
        results=results,
        awards_leaders=request.awards_leaders,
    )


def test_academy_buy_in_multiplier_tracks_shared_senior_tiers() -> None:
    service = AcademyCompetitionService()
    registrations = service.build_registration_plan(_build_request(with_results=False))

    buy_ins = {registration.senior_buy_in_tier: registration.academy_buy_in for registration in registrations}

    assert buy_ins[1000] == Decimal("500.00")
    assert buy_ins[25] == Decimal("12.50")


def test_academy_season_integrity_generates_double_round_robin_across_seven_days() -> None:
    service = AcademyCompetitionService()
    request = _build_request(with_results=False)
    fixtures = service.build_fixtures(request)
    standings = service.build_standings(request)

    assert len(fixtures) == 380
    assert {fixture.round_number for fixture in fixtures} == set(range(1, 39))
    assert {fixture.window_number for fixture in fixtures} == {1, 2, 3, 4, 5, 6}
    assert {fixture.match_date for fixture in fixtures} == {date(2026, 1, day) for day in range(1, 8)}
    assert all(not fixture.is_cup_match for fixture in fixtures)
    assert all(not fixture.allow_penalties for fixture in fixtures)

    pair_counts: Counter[tuple[str, str]] = Counter()
    home_away_tracker: defaultdict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    club_matches: Counter[str] = Counter()
    for fixture in fixtures:
        ordered_pair = tuple(sorted((fixture.home_club_id, fixture.away_club_id)))
        pair_counts[ordered_pair] += 1
        home_away_tracker[ordered_pair].add((fixture.home_club_id, fixture.away_club_id))
        club_matches[fixture.home_club_id] += 1
        club_matches[fixture.away_club_id] += 1
        assert fixture.home_club_id != fixture.away_club_id

    assert all(count == 2 for count in pair_counts.values())
    assert all(len(home_away_orders) == 2 for home_away_orders in home_away_tracker.values())
    assert all(match_count == 38 for match_count in club_matches.values())
    assert all(row.played == 0 for row in standings)


def test_academy_qualification_flow_and_knockout_path_follow_scaled_senior_ratios() -> None:
    service = AcademyCompetitionService()
    request = _build_request(with_results=True)
    projection = service.build_season_projection(request)

    assert projection.status.value == "completed"
    assert [entry.club_id for entry in projection.qualification.direct_qualifiers] == [
        "club-01",
        "club-02",
        "club-03",
        "club-04",
    ]
    assert [entry.club_id for entry in projection.qualification.playoff_qualifiers] == [
        "club-05",
        "club-06",
        "club-07",
        "club-08",
    ]
    assert len(projection.champions_league.playoff_ties) == 2
    assert len(projection.champions_league.league_phase_table) == 6
    assert len(projection.champions_league.quarterfinals) == 2
    assert len(projection.champions_league.semifinals) == 2
    assert projection.champions_league.final.allow_penalties is True
    assert projection.champions_league.final.extra_time_allowed is False
    assert projection.champions_league.champion_club_id == "club-01"


def test_academy_remains_active_during_senior_world_super_cup_window() -> None:
    service = AcademyCompetitionService()
    request = _build_request(with_results=False)
    projection = service.build_season_projection(
        AcademySeasonRequest(
            season_id=request.season_id,
            start_date=request.start_date,
            clubs=request.clubs,
            senior_world_super_cup_active=True,
            awards_leaders=request.awards_leaders,
        )
    )

    assert projection.active_during_senior_world_super_cup is True
    assert projection.status.value == "fixtures_published"
    assert len(projection.fixtures) == 380


def test_academy_top_four_rollover_and_awards_preview() -> None:
    service = AcademyCompetitionService()
    projection = service.build_season_projection(_build_request(with_results=True))

    assert [club.club_id for club in projection.rollover_clubs] == [
        "club-01",
        "club-02",
        "club-03",
        "club-04",
    ]
    assert all(club.carry_over_from_previous_season for club in projection.rollover_clubs)
    assert projection.awards.total_pool == Decimal("5062.50")
    assert projection.awards.league_winner_share == Decimal("2531.25")
    assert projection.awards.top_scorer_share == Decimal("506.25")
    assert projection.awards.top_assist_share == Decimal("253.13")
    assert projection.awards.champions_league_fund_share == Decimal("1771.88")


def test_academy_router_exposes_season_summary_api() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    request = _build_request(with_results=True)
    response = client.post(
        "/academy/season-summary",
        json={
            "season_id": request.season_id,
            "start_date": request.start_date.isoformat(),
            "clubs": [
                {
                    "club_id": club.club_id,
                    "club_name": club.club_name,
                    "senior_buy_in_tier": club.senior_buy_in_tier,
                    "carry_over_from_previous_season": club.carry_over_from_previous_season,
                }
                for club in request.clubs
            ],
            "results": [
                {
                    "fixture_id": result.fixture_id,
                    "home_goals": result.home_goals,
                    "away_goals": result.away_goals,
                }
                for result in request.results
            ],
            "senior_world_super_cup_active": True,
            "awards_leaders": {
                "top_scorer_club_id": request.awards_leaders.top_scorer_club_id,
                "top_assist_club_id": request.awards_leaders.top_assist_club_id,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["champion_club_id"] == "club-01"
    assert payload["active_during_senior_world_super_cup"] is True
    assert len(payload["fixtures"]) == 380
    assert payload["awards"]["champions_league_fund_share"] == "1771.88"


def test_academy_dispatch_jobs_preserve_open_window_slot_sequences() -> None:
    service = AcademyCompetitionService()
    request = _build_request(with_results=False)
    publisher = InMemoryQueuePublisher()

    jobs = service.build_match_dispatch_jobs(
        request,
        dispatcher=MatchDispatcher(queue_publisher=publisher),
    )

    assert len(jobs) == 380
    assert jobs[0].payload["window"] == "academy_open"
    assert jobs[0].payload["slot_sequence"] == 1
    assert jobs[5].payload["slot_sequence"] == 1
    assert jobs[10].payload["slot_sequence"] == 2
