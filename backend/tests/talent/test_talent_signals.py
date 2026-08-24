"""Talent signal derivation tests.

The central guarantee: no signal fires from a small sample. Each rule is tested
both above and below its minimum sample size, because "we found a clutch
performer" from three appearances is worse than finding nothing.
"""

from __future__ import annotations

from datetime import date

from app.talent.constants import CompetitionLevel, SIGNAL_POLARITY, TalentSignalCode
from app.talent.inputs import AvailabilityWindow, TalentMatchRecord
from app.talent.signals import derive_signals


def _record(
    index: int,
    *,
    rating: float | None = 7.0,
    minutes: int = 90,
    goals: int = 0,
    assists: int = 0,
    clean_sheet: bool = False,
    stage: str | None = None,
    level: str = CompetitionLevel.TIER_1.value,
    yellow_cards: int = 0,
    red_cards: int = 0,
) -> TalentMatchRecord:
    return TalentMatchRecord(
        match_key=f"m-{index:03d}",
        played_on=date.fromordinal(date(2026, 1, 1).toordinal() + index * 7),
        competition_key="comp-a",
        competition_level=level,
        stage=stage,
        minutes=minutes,
        rating=rating,
        goals=goals,
        assists=assists,
        clean_sheet=clean_sheet,
        yellow_cards=yellow_cards,
        red_cards=red_cards,
    )


def _codes(signals) -> set[str]:
    return {signal.code for signal in signals}


def _get(signals, code: TalentSignalCode):
    return next(signal for signal in signals if signal.code == code.value)


# ----------------------------------------------------------------------
# Sample-size floors
# ----------------------------------------------------------------------


def test_a_single_match_produces_no_signals_at_all() -> None:
    assert derive_signals((_record(0, rating=10.0, goals=4),)) == ()


def test_two_perfect_matches_still_produce_no_signals() -> None:
    records = tuple(_record(index, rating=10.0, goals=3) for index in range(2))
    assert derive_signals(records) == ()


def test_five_strong_matches_stay_below_the_form_threshold() -> None:
    records = tuple(_record(index, rating=9.0) for index in range(5))
    assert TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE.value not in _codes(derive_signals(records))


def test_six_strong_matches_clear_the_form_threshold() -> None:
    records = tuple(_record(index, rating=9.0) for index in range(6))
    signals = derive_signals(records)

    assert TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE.value in _codes(signals)
    signal = _get(signals, TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE)
    assert signal.sample_size == 6
    assert 0.0 <= signal.strength <= 1.0
    assert signal.evidence["high_rating_appearances"] == 6


# ----------------------------------------------------------------------
# Determinism and shape
# ----------------------------------------------------------------------


def test_signals_are_returned_in_a_stable_order() -> None:
    records = tuple(_record(index, rating=8.5) for index in range(12))

    first = derive_signals(records)
    second = derive_signals(tuple(reversed(records)))

    assert [signal.code for signal in first] == sorted(signal.code for signal in first)
    assert [signal.as_payload() for signal in first] == [signal.as_payload() for signal in second]


def test_every_signal_declares_polarity_strength_and_evidence() -> None:
    records = tuple(_record(index, rating=8.5, goals=1) for index in range(12))

    for signal in derive_signals(records, position_code="ST"):
        assert signal.polarity == SIGNAL_POLARITY[signal.code]
        assert 0.0 <= signal.strength <= 1.0
        assert signal.sample_size >= 3
        assert signal.explanation
        assert signal.evidence


# ----------------------------------------------------------------------
# Individual rules
# ----------------------------------------------------------------------


def test_clutch_needs_a_comparable_routine_baseline() -> None:
    only_finals = tuple(_record(index, rating=9.0, stage="final") for index in range(6))
    assert TalentSignalCode.CLUTCH_PERFORMANCE.value not in _codes(derive_signals(only_finals))


def test_clutch_fires_when_decisive_ratings_exceed_routine_ratings() -> None:
    routine = [_record(index, rating=6.5) for index in range(6)]
    decisive = [_record(100 + index, rating=8.5, stage="semi_final") for index in range(4)]
    signals = derive_signals(tuple(routine + decisive))

    signal = _get(signals, TalentSignalCode.CLUTCH_PERFORMANCE)
    assert signal.sample_size == 4
    assert signal.evidence["rating_delta"] > 0


def test_consistency_and_volatility_are_mutually_exclusive() -> None:
    steady = derive_signals(tuple(_record(index, rating=7.0) for index in range(10)))
    swings = [3.0, 9.5] * 5
    volatile = derive_signals(tuple(_record(index, rating=swings[index]) for index in range(10)))

    assert TalentSignalCode.CONSISTENT_PERFORMER.value in _codes(steady)
    assert TalentSignalCode.VOLATILE_PERFORMER.value not in _codes(steady)
    assert TalentSignalCode.VOLATILE_PERFORMER.value in _codes(volatile)
    assert TalentSignalCode.CONSISTENT_PERFORMER.value not in _codes(volatile)


def test_positional_excellence_is_normalised_by_position() -> None:
    # Four goals in eight full matches is 0.5 per 90: exactly the forward
    # baseline (unremarkable) but twice the midfielder baseline (excellent).
    records = tuple(_record(index, goals=index % 2, minutes=90) for index in range(8))

    forward = derive_signals(records, position_code="ST")
    midfielder = derive_signals(records, position_code="CM")

    assert TalentSignalCode.POSITIONAL_EXCELLENCE.value in _codes(midfielder)
    assert TalentSignalCode.POSITIONAL_EXCELLENCE.value not in _codes(forward)
    evidence = _get(midfielder, TalentSignalCode.POSITIONAL_EXCELLENCE).evidence
    assert evidence["per_90"] == 0.5
    assert evidence["position_family"] == "midfielder"


def test_positional_excellence_requires_enough_minutes() -> None:
    cameos = tuple(_record(index, goals=1, minutes=10) for index in range(8))
    assert TalentSignalCode.POSITIONAL_EXCELLENCE.value not in _codes(derive_signals(cameos, position_code="CM"))


def test_progression_and_regression_need_both_halves_populated() -> None:
    improving = [5.5] * 4 + [7.5] * 4
    declining = [7.5] * 4 + [5.5] * 4

    progression = derive_signals(tuple(_record(i, rating=improving[i]) for i in range(8)))
    regression = derive_signals(tuple(_record(i, rating=declining[i]) for i in range(8)))
    too_short = derive_signals(tuple(_record(i, rating=improving[i]) for i in range(6)))

    assert TalentSignalCode.PROGRESSION.value in _codes(progression)
    assert TalentSignalCode.REGRESSION.value in _codes(regression)
    assert TalentSignalCode.PROGRESSION.value not in _codes(too_short)
    assert TalentSignalCode.REGRESSION.value not in _codes(too_short)


def test_elite_experience_requires_repeated_top_level_minutes() -> None:
    four = tuple(_record(index, level=CompetitionLevel.ELITE.value) for index in range(4))
    six = tuple(_record(index, level=CompetitionLevel.ELITE.value) for index in range(6))

    assert TalentSignalCode.ELITE_COMPETITION_EXPERIENCE.value not in _codes(derive_signals(four))
    assert TalentSignalCode.ELITE_COMPETITION_EXPERIENCE.value in _codes(derive_signals(six))


def test_disciplinary_concern_needs_a_rate_not_an_incident() -> None:
    one_red = tuple(_record(index, red_cards=1 if index == 0 else 0) for index in range(12))
    persistent = tuple(_record(index, yellow_cards=1, red_cards=1) for index in range(8))

    assert TalentSignalCode.DISCIPLINARY_CONCERN.value not in _codes(derive_signals(one_red))
    signal = _get(derive_signals(persistent), TalentSignalCode.DISCIPLINARY_CONCERN)
    assert signal.polarity == "negative"
    assert signal.evidence["red_cards"] == 8


def test_availability_risk_requires_a_measured_window() -> None:
    records = tuple(_record(index) for index in range(10))

    assert TalentSignalCode.INJURY_AVAILABILITY_RISK.value not in _codes(derive_signals(records, availability=None))
    assert TalentSignalCode.INJURY_AVAILABILITY_RISK.value not in _codes(
        derive_signals(records, availability=AvailabilityWindow(eligible_matches=3, available_matches=1))
    )

    signals = derive_signals(records, availability=AvailabilityWindow(eligible_matches=20, available_matches=8))
    signal = _get(signals, TalentSignalCode.INJURY_AVAILABILITY_RISK)
    assert signal.evidence["availability_ratio"] == 0.4


def test_full_availability_produces_no_risk_signal() -> None:
    records = tuple(_record(index) for index in range(10))
    signals = derive_signals(records, availability=AvailabilityWindow(eligible_matches=20, available_matches=20))
    assert TalentSignalCode.INJURY_AVAILABILITY_RISK.value not in _codes(signals)


def test_unrated_appearances_do_not_fabricate_form_signals() -> None:
    records = tuple(_record(index, rating=None) for index in range(12))
    signals = derive_signals(records)

    assert TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE.value not in _codes(signals)
    assert TalentSignalCode.CONSISTENT_PERFORMER.value not in _codes(signals)
