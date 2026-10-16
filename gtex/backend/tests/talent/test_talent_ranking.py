"""Ranking pipeline tests.

The properties under test are the ones the ranking has to defend in public:
it is reproducible, it is explainable component by component, and it cannot be
swung by a tiny sample.
"""

from __future__ import annotations

from datetime import date
import random

import pytest

from app.talent.constants import (
    COMPETITION_LEVEL_SCORE,
    CompetitionLevel,
    NEUTRAL_COMPONENT_SCORE,
    VerificationTier,
)
from app.talent.inputs import AvailabilityWindow, TalentMatchRecord, TalentRankingInput
from app.talent.ranking import (
    ADJUSTMENT_TOTAL_CAP,
    COMPONENT_COMPETITION_LEVEL,
    COMPONENT_CONSISTENCY,
    COMPONENT_CREDENTIALS,
    COMPONENT_MATCH_PERFORMANCE,
    COMPONENT_ORDER,
    COMPONENT_PHYSICAL,
    COMPONENT_RECENT_FORM,
    COMPONENT_TACTICAL,
    COMPONENT_TECHNICAL,
    COMPONENT_WEIGHTS,
    compute_ranking,
    rank_talents,
)

AS_OF = date(2026, 8, 1)


def _record(
    index: int,
    *,
    rating: float | None = 7.0,
    minutes: int = 90,
    goals: int = 0,
    assists: int = 0,
    level: str = CompetitionLevel.TIER_1.value,
    stage: str | None = None,
    yellow_cards: int = 0,
    red_cards: int = 0,
    competition_key: str = "comp-a",
) -> TalentMatchRecord:
    return TalentMatchRecord(
        match_key=f"match-{index:03d}",
        played_on=date(2026, 1, 1),
        competition_key=competition_key,
        competition_level=level,
        stage=stage,
        minutes=minutes,
        rating=rating,
        goals=goals,
        assists=assists,
        yellow_cards=yellow_cards,
        red_cards=red_cards,
    )


def _dated_record(index: int, **kwargs) -> TalentMatchRecord:
    """Same as `_record` but with distinct, increasing match dates."""

    base = _record(index, **kwargs)
    day = date(2026, 1, 1).toordinal() + index * 7
    return TalentMatchRecord(
        match_key=base.match_key,
        played_on=date.fromordinal(day),
        competition_key=base.competition_key,
        competition_level=base.competition_level,
        stage=base.stage,
        minutes=base.minutes,
        rating=base.rating,
        goals=base.goals,
        assists=base.assists,
        yellow_cards=base.yellow_cards,
        red_cards=base.red_cards,
    )


def _input(player_id: str = "player-1", **kwargs) -> TalentRankingInput:
    payload = {
        "player_id": player_id,
        "as_of": AS_OF,
        "position_code": "CM",
        "age_years": 22,
    }
    payload.update(kwargs)
    return TalentRankingInput(**payload)


# ----------------------------------------------------------------------
# Structure
# ----------------------------------------------------------------------


def test_component_weights_sum_to_one() -> None:
    assert round(sum(COMPONENT_WEIGHTS.values()), 10) == 1.0
    assert set(COMPONENT_WEIGHTS) == set(COMPONENT_ORDER)


def test_ranking_exposes_every_component_in_a_fixed_order() -> None:
    result = compute_ranking(_input())

    assert tuple(component.code for component in result.components) == COMPONENT_ORDER
    for component in result.components:
        assert 0.0 <= component.score <= 100.0
        assert component.weight == COMPONENT_WEIGHTS[component.code]
        assert component.explanation, f"{component.code} must explain itself"


def test_ranking_is_not_a_single_overall_rating() -> None:
    """No single component may dominate the composite."""

    assert max(COMPONENT_WEIGHTS.values()) <= 0.25


# ----------------------------------------------------------------------
# Determinism
# ----------------------------------------------------------------------


def test_repeated_computation_is_byte_identical() -> None:
    records = tuple(_dated_record(index, rating=6.0 + (index % 4) * 0.5) for index in range(12))
    ranking_input = _input(match_records=records)

    first = compute_ranking(ranking_input)
    second = compute_ranking(ranking_input)

    assert first.composite_score == second.composite_score
    assert first.inputs_digest == second.inputs_digest
    assert first.as_payload() == second.as_payload()


def test_input_order_does_not_change_the_result() -> None:
    records = [_dated_record(index, rating=5.5 + (index % 5) * 0.4) for index in range(15)]
    ordered = compute_ranking(_input(match_records=tuple(records)))

    shuffled = list(records)
    random.Random(20260823).shuffle(shuffled)
    reordered = compute_ranking(_input(match_records=tuple(shuffled)))

    assert reordered.composite_score == ordered.composite_score
    assert reordered.inputs_digest == ordered.inputs_digest


def test_duplicate_appearances_are_deduplicated() -> None:
    records = [_dated_record(index) for index in range(8)]
    with_duplicates = records + records[:4]

    clean = compute_ranking(_input(match_records=tuple(records)))
    dirty = compute_ranking(_input(match_records=tuple(with_duplicates)))

    assert dirty.sample_size == clean.sample_size == 8
    assert dirty.composite_score == clean.composite_score
    assert dirty.inputs_digest == clean.inputs_digest


def test_different_inputs_produce_different_digests() -> None:
    baseline = compute_ranking(_input(match_records=(_dated_record(0, rating=6.0),)))
    changed = compute_ranking(_input(match_records=(_dated_record(0, rating=8.0),)))

    assert baseline.inputs_digest != changed.inputs_digest


def test_ranked_batch_ordering_is_stable_on_ties() -> None:
    """Equal scores must not reorder between calls."""

    inputs = [_input(player_id=f"player-{index}") for index in ("c", "a", "b")]

    first = rank_talents(inputs)
    second = rank_talents(list(reversed(inputs)))

    assert [item.player_id for item in first] == ["player-a", "player-b", "player-c"]
    assert [item.player_id for item in second] == [item.player_id for item in first]
    assert len({item.composite_score for item in first}) == 1


# ----------------------------------------------------------------------
# Neutral / missing evidence
# ----------------------------------------------------------------------


def test_empty_profile_scores_neutral_with_no_confidence() -> None:
    result = compute_ranking(_input())

    expected_base = round(
        NEUTRAL_COMPONENT_SCORE
        * (1.0 - COMPONENT_WEIGHTS[COMPONENT_COMPETITION_LEVEL] - COMPONENT_WEIGHTS[COMPONENT_CREDENTIALS])
        + COMPETITION_LEVEL_SCORE[CompetitionLevel.UNKNOWN.value] * COMPONENT_WEIGHTS[COMPONENT_COMPETITION_LEVEL],
        2,
    )
    assert result.base_score == expected_base
    assert result.composite_score == expected_base
    assert result.sample_size == 0
    # Only the (known) verification tier carries any confidence.
    assert result.confidence == COMPONENT_WEIGHTS[COMPONENT_CREDENTIALS]
    for component in result.components:
        if component.code != COMPONENT_CREDENTIALS:
            assert component.confidence == 0.0


def test_missing_attributes_are_scored_neutral_not_guessed() -> None:
    result = compute_ranking(_input())

    for code in (COMPONENT_TECHNICAL, COMPONENT_TACTICAL, COMPONENT_PHYSICAL):
        component = next(item for item in result.components if item.code == code)
        assert component.score == NEUTRAL_COMPONENT_SCORE
        assert component.sample_size == 0
        assert "No" in component.explanation


def test_sparse_attribute_coverage_is_shrunk_toward_neutral() -> None:
    sparse = compute_ranking(_input(technical_attributes={"passing": 100.0}))
    full = compute_ranking(
        _input(
            technical_attributes={
                key: 100.0
                for key in (
                    "first_touch",
                    "ball_control",
                    "passing",
                    "dribbling",
                    "finishing",
                    "crossing",
                    "heading",
                    "long_shots",
                    "set_pieces",
                    "tackling",
                )
            }
        )
    )

    sparse_component = next(item for item in sparse.components if item.code == COMPONENT_TECHNICAL)
    full_component = next(item for item in full.components if item.code == COMPONENT_TECHNICAL)

    assert sparse_component.score < full_component.score
    assert full_component.score == 100.0
    assert sparse_component.confidence < full_component.confidence


def test_unknown_attribute_keys_are_ignored() -> None:
    with_junk = compute_ranking(_input(technical_attributes={"passing": 60.0, "vibes": 100.0}))
    clean = compute_ranking(_input(technical_attributes={"passing": 60.0}))

    assert with_junk.composite_score == clean.composite_score


# ----------------------------------------------------------------------
# Small-sample protection
# ----------------------------------------------------------------------


def test_one_outstanding_match_barely_moves_the_composite() -> None:
    perfect = compute_ranking(_input(match_records=(_dated_record(0, rating=10.0),)))
    average = compute_ranking(_input(match_records=(_dated_record(0, rating=5.0),)))

    assert perfect.composite_score > average.composite_score
    assert perfect.composite_score - average.composite_score < 2.5


def test_evidence_accumulates_with_sample_size() -> None:
    few = compute_ranking(_input(match_records=tuple(_dated_record(i, rating=9.0) for i in range(2))))
    many = compute_ranking(_input(match_records=tuple(_dated_record(i, rating=9.0) for i in range(30))))

    assert many.composite_score > few.composite_score
    few_component = next(item for item in few.components if item.code == COMPONENT_MATCH_PERFORMANCE)
    many_component = next(item for item in many.components if item.code == COMPONENT_MATCH_PERFORMANCE)
    assert many_component.confidence > few_component.confidence


def test_consistency_requires_a_minimum_rated_sample() -> None:
    two_matches = compute_ranking(_input(match_records=tuple(_dated_record(i, rating=7.0) for i in range(2))))
    component = next(item for item in two_matches.components if item.code == COMPONENT_CONSISTENCY)

    assert component.score == NEUTRAL_COMPONENT_SCORE
    assert component.confidence == 0.0


def test_steady_ratings_beat_volatile_ratings_on_consistency() -> None:
    steady = compute_ranking(_input(match_records=tuple(_dated_record(i, rating=7.0) for i in range(10))))
    volatile_ratings = [4.0, 10.0] * 5
    volatile = compute_ranking(
        _input(match_records=tuple(_dated_record(i, rating=volatile_ratings[i]) for i in range(10)))
    )

    steady_component = next(item for item in steady.components if item.code == COMPONENT_CONSISTENCY)
    volatile_component = next(item for item in volatile.components if item.code == COMPONENT_CONSISTENCY)
    assert steady_component.score > volatile_component.score


# ----------------------------------------------------------------------
# Component behaviour
# ----------------------------------------------------------------------


def test_competition_level_reflects_where_the_minutes_were_played() -> None:
    elite = compute_ranking(
        _input(match_records=tuple(_dated_record(i, level=CompetitionLevel.ELITE.value) for i in range(10)))
    )
    amateur = compute_ranking(
        _input(match_records=tuple(_dated_record(i, level=CompetitionLevel.AMATEUR.value) for i in range(10)))
    )

    elite_component = next(item for item in elite.components if item.code == COMPONENT_COMPETITION_LEVEL)
    amateur_component = next(item for item in amateur.components if item.code == COMPONENT_COMPETITION_LEVEL)
    assert elite_component.score > amateur_component.score
    assert elite.composite_score > amateur.composite_score


def test_recent_form_is_measured_against_the_player_own_baseline() -> None:
    flat = compute_ranking(_input(match_records=tuple(_dated_record(i, rating=7.0) for i in range(12))))
    flat_component = next(item for item in flat.components if item.code == COMPONENT_RECENT_FORM)
    assert flat_component.score == pytest.approx(NEUTRAL_COMPONENT_SCORE, abs=0.01)

    improving_ratings = [5.0] * 6 + [9.0] * 6
    improving = compute_ranking(
        _input(match_records=tuple(_dated_record(i, rating=improving_ratings[i]) for i in range(12)))
    )
    improving_component = next(item for item in improving.components if item.code == COMPONENT_RECENT_FORM)
    assert improving_component.score > NEUTRAL_COMPONENT_SCORE


def test_verification_tier_lifts_the_credentials_component_only() -> None:
    unverified = compute_ranking(_input(verification_tier=VerificationTier.UNVERIFIED.value))
    staff = compute_ranking(_input(verification_tier=VerificationTier.STAFF_VERIFIED.value))

    unverified_credentials = next(item for item in unverified.components if item.code == COMPONENT_CREDENTIALS)
    staff_credentials = next(item for item in staff.components if item.code == COMPONENT_CREDENTIALS)

    assert unverified_credentials.score == 0.0
    assert staff_credentials.score == 100.0
    # Every other component is untouched by verification status.
    for code in COMPONENT_ORDER:
        if code == COMPONENT_CREDENTIALS:
            continue
        assert unverified.component_score(code) == staff.component_score(code)
    assert staff.composite_score - unverified.composite_score == pytest.approx(
        100.0 * COMPONENT_WEIGHTS[COMPONENT_CREDENTIALS], abs=0.01
    )


def test_goalkeeper_uses_its_own_attribute_vocabulary() -> None:
    keeper = compute_ranking(_input(position_code="GK", technical_attributes={"handling": 90.0, "reflexes": 90.0}))
    keeper_component = next(item for item in keeper.components if item.code == COMPONENT_TECHNICAL)

    assert keeper_component.sample_size == 2
    assert keeper_component.score > NEUTRAL_COMPONENT_SCORE


# ----------------------------------------------------------------------
# Adjustments
# ----------------------------------------------------------------------


def test_signal_adjustments_are_clamped_in_aggregate() -> None:
    declining = [8.5] * 5 + [4.5] * 5
    records = tuple(_dated_record(index, rating=declining[index], yellow_cards=1, red_cards=1) for index in range(10))
    result = compute_ranking(
        _input(
            match_records=records,
            availability=AvailabilityWindow(eligible_matches=10, available_matches=2),
        )
    )

    raw_total = sum(adjustment.delta for adjustment in result.adjustments)
    assert raw_total < -ADJUSTMENT_TOTAL_CAP
    assert result.adjustments_total == -ADJUSTMENT_TOTAL_CAP
    assert result.composite_score == round(result.base_score - ADJUSTMENT_TOTAL_CAP, 2)


def test_adjustments_never_double_count_a_component() -> None:
    """Signals already represented by a component must not also adjust."""

    records = tuple(_dated_record(index, rating=8.5) for index in range(12))
    result = compute_ranking(_input(match_records=records))

    signal_codes = {signal.code for signal in result.signals}
    adjustment_codes = {adjustment.code for adjustment in result.adjustments}

    assert "sustained_high_performance" in signal_codes
    assert "sustained_high_performance" not in adjustment_codes
    assert "consistent_performer" not in adjustment_codes


def test_composite_stays_inside_zero_to_one_hundred() -> None:
    elite_attributes = {
        key: 100.0
        for key in (
            "positioning",
            "decision_making",
            "anticipation",
            "off_the_ball",
            "vision",
            "composure",
            "team_work",
            "concentration",
            "pressing_intelligence",
        )
    }
    result = compute_ranking(
        _input(
            verification_tier=VerificationTier.STAFF_VERIFIED.value,
            tactical_attributes=elite_attributes,
            match_records=tuple(
                _dated_record(index, rating=10.0, goals=3, level=CompetitionLevel.ELITE.value) for index in range(40)
            ),
        )
    )

    assert 0.0 <= result.composite_score <= 100.0
