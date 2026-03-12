from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.fast_cups.models.domain import (
    ClubCompetitionWindow,
    FastCupDivision,
    FastCupStateError,
    FastCupValidationError,
)


def test_recurring_creation_runs_every_15_minutes(ecosystem, base_now) -> None:
    cups = ecosystem.list_upcoming_cups(now=base_now, horizon_intervals=3)
    senior_32 = [cup for cup in cups if cup.division is FastCupDivision.SENIOR and cup.size == 32]

    assert len(cups) == 24
    assert [cup.slot.kickoff_at for cup in senior_32] == [
        datetime(2026, 7, 1, 12, 15, tzinfo=UTC),
        datetime(2026, 7, 1, 12, 30, tzinfo=UTC),
        datetime(2026, 7, 1, 12, 45, tzinfo=UTC),
    ]

    repeated = ecosystem.list_upcoming_cups(now=base_now, horizon_intervals=3)
    assert len(repeated) == len(cups)


def test_bracket_generation_pairs_top_seed_with_bottom_seed(ecosystem, base_now, select_cup, fill_cup) -> None:
    cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=32)
    filled = fill_cup(ecosystem, cup)

    bracket = ecosystem.get_bracket(cup_id=filled.cup_id)

    assert bracket.total_rounds == 5
    assert [len(round_entry.matches) for round_entry in bracket.rounds] == [16, 8, 4, 2, 1]
    assert bracket.rounds[0].matches[0].home.club_id == "senior-club-001"
    assert bracket.rounds[0].matches[0].away.club_id == "senior-club-032"
    assert bracket.rounds[1].matches[0].home_source_tie_id == bracket.rounds[0].matches[0].tie_id


def test_join_rejects_overlapping_senior_window(ecosystem, base_now, select_cup, build_entrant) -> None:
    cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=32)
    join_at = cup.slot.registration_opens_at + timedelta(minutes=2)

    with pytest.raises(FastCupStateError, match="already committed"):
        ecosystem.join_cup(
            cup_id=cup.cup_id,
            entrant=build_entrant(1, division=FastCupDivision.SENIOR, registered_at=join_at),
            existing_windows=(
                ClubCompetitionWindow(
                    club_id="senior-club-001",
                    competition_id="league-alpha",
                    competition_type=CompetitionType.LEAGUE,
                    starts_at=cup.slot.kickoff_at + timedelta(minutes=5),
                    ends_at=cup.slot.kickoff_at + timedelta(minutes=25),
                    window=FixtureWindow.SENIOR_2,
                ),
            ),
            now=join_at,
        )


def test_academy_and_senior_fast_cups_stay_separate(ecosystem, base_now, select_cup, build_entrant) -> None:
    senior_cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=64)
    academy_cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.ACADEMY, size=64)
    join_at = senior_cup.slot.registration_opens_at + timedelta(minutes=1)

    assert academy_cup.buy_in < senior_cup.buy_in

    with pytest.raises(FastCupValidationError, match="division does not match"):
        ecosystem.join_cup(
            cup_id=senior_cup.cup_id,
            entrant=build_entrant(1, division=FastCupDivision.ACADEMY, registered_at=join_at),
            now=join_at,
        )

    joined = ecosystem.join_cup(
        cup_id=academy_cup.cup_id,
        entrant=build_entrant(2, division=FastCupDivision.ACADEMY, registered_at=join_at),
        now=join_at,
    )
    assert len(joined.entrants) == 1
    assert joined.entrants[0].division is FastCupDivision.ACADEMY


def test_academy_window_does_not_block_fast_cup_registration(ecosystem, base_now, select_cup, build_entrant) -> None:
    cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=32)
    join_at = cup.slot.registration_opens_at + timedelta(minutes=2)

    joined = ecosystem.join_cup(
        cup_id=cup.cup_id,
        entrant=build_entrant(1, division=FastCupDivision.SENIOR, registered_at=join_at),
        existing_windows=(
            ClubCompetitionWindow(
                club_id="senior-club-001",
                competition_id="academy-alpha",
                competition_type=CompetitionType.ACADEMY,
                starts_at=cup.slot.kickoff_at + timedelta(minutes=5),
                ends_at=cup.slot.kickoff_at + timedelta(minutes=25),
                window=FixtureWindow.ACADEMY_OPEN,
            ),
        ),
        now=join_at,
    )

    assert len(joined.entrants) == 1


def test_completion_timing_stays_under_one_hour_and_settles_rewards(
    ecosystem,
    base_now,
    select_cup,
    fill_cup,
) -> None:
    cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=256)

    assert (cup.slot.expected_completion_at - cup.slot.kickoff_at) <= timedelta(hours=1)
    assert (cup.slot.expected_completion_at - cup.slot.kickoff_at) == timedelta(minutes=45)

    senior_32 = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=32)
    filled = fill_cup(ecosystem, senior_32)
    summary = ecosystem.get_result_summary(
        cup_id=filled.cup_id,
        now=filled.slot.expected_completion_at,
    )

    assert summary.expected_duration_minutes == 30
    assert summary.total_matches == 31
    assert summary.champion.club_id == "senior-club-001"
    assert [event.event_type for event in summary.events] == [
        "fast_cup.prize_pool_funded",
        "fast_cup.champion_paid",
        "fast_cup.runner_up_paid",
        "fast_cup.semifinal_paid",
        "fast_cup.semifinal_paid",
        "fast_cup.platform_fee_reserved",
    ]
