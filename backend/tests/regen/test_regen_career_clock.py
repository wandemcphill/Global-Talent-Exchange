from __future__ import annotations

import pytest

from app.regen_career.clock import (
    RegenCareerClock,
    RegenRetirementInputs,
    RetirementPressureBand,
)


def test_virtual_age_uses_gtx_season_timeline_not_wall_clock() -> None:
    clock = RegenCareerClock()
    months = clock.virtual_age_months_from_seasons(
        generation_season_number=3,
        current_season_number=8,
        season_virtual_month_index={3: 72, 8: 156},
    )
    assert months == 84


def test_missing_virtual_age_mapping_is_explicitly_rejected() -> None:
    with pytest.raises(ValueError, match="virtual-age mapping"):
        RegenCareerClock().virtual_age_months_from_seasons(
            generation_season_number=3,
            current_season_number=8,
            season_virtual_month_index={3: 72},
        )


def test_goalkeeper_receives_longevity_credit() -> None:
    clock = RegenCareerClock()
    goalkeeper = clock.assess(
        RegenRetirementInputs(
            virtual_age_months=360,
            position="goalkeeper",
            injury_burden=0.25,
            playing_time=0.8,
            performance_trajectory=0.75,
            contract_security=0.7,
            market_demand=0.7,
            salary_burden=0.3,
            willingness_to_continue=0.9,
            ambition=0.6,
            resilience=0.8,
            loyalty=0.7,
            achievements=0.8,
            club_opportunity=0.8,
        )
    )
    striker = clock.assess(
        RegenRetirementInputs(
            virtual_age_months=360,
            position="striker",
            injury_burden=0.25,
            playing_time=0.8,
            performance_trajectory=0.75,
            contract_security=0.7,
            market_demand=0.7,
            salary_burden=0.3,
            willingness_to_continue=0.9,
            ambition=0.6,
            resilience=0.8,
            loyalty=0.7,
            achievements=0.8,
            club_opportunity=0.8,
        )
    )
    assert goalkeeper.retirement_pressure < striker.retirement_pressure


def test_injury_and_low_playing_time_raise_pressure() -> None:
    clock = RegenCareerClock()
    healthy_regular = clock.assess(
        RegenRetirementInputs(
            virtual_age_months=340,
            position="midfielder",
            injury_burden=0.1,
            playing_time=0.85,
            performance_trajectory=0.8,
            contract_security=0.75,
            market_demand=0.75,
            salary_burden=0.3,
            willingness_to_continue=0.9,
            ambition=0.7,
            resilience=0.8,
            loyalty=0.7,
            achievements=0.5,
            club_opportunity=0.8,
        )
    )
    injured_fringe = clock.assess(
        RegenRetirementInputs(
            virtual_age_months=340,
            position="midfielder",
            injury_burden=0.85,
            playing_time=0.2,
            performance_trajectory=0.35,
            contract_security=0.25,
            market_demand=0.25,
            salary_burden=0.75,
            willingness_to_continue=0.45,
            ambition=0.4,
            resilience=0.4,
            loyalty=0.6,
            achievements=0.2,
            club_opportunity=0.2,
        )
    )
    assert injured_fringe.retirement_pressure > healthy_regular.retirement_pressure
    assert injured_fringe.pressure_band in {
        RetirementPressureBand.WATCH,
        RetirementPressureBand.HIGH,
        RetirementPressureBand.DECISION,
    }


def test_high_pressure_does_not_force_decision_without_virtual_age() -> None:
    assessment = RegenCareerClock().assess(
        RegenRetirementInputs(
            virtual_age_months=None,
            position="striker",
            injury_burden=1.0,
            playing_time=0.0,
            performance_trajectory=0.0,
            contract_security=0.0,
            market_demand=0.0,
            salary_burden=1.0,
            willingness_to_continue=0.0,
            ambition=0.0,
            resilience=0.0,
            loyalty=0.0,
            achievements=0.0,
            club_opportunity=0.0,
        )
    )
    assert assessment.eligible_for_retirement_decision is False
    assert assessment.virtual_age_months is None
