"""The form -> valuation link: bounded, gradual, deterministic, auditable."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.players.form_service import (
    MINIMUM_MATCHES_FOR_SIGNAL,
    FormEntry,
    PlayerFormWindow,
    TREND_FALLING,
    TREND_RISING,
)
from app.value_engine.matchday_signal import (
    EFFECTIVE_MAX_ADJUSTMENT_PCT,
    MAX_TOTAL_ADJUSTMENT_PCT,
    REASON_FORM_NEGATIVE,
    REASON_FORM_POSITIVE,
    REASON_INSUFFICIENT_SAMPLE,
    build_matchday_signal,
)

BASE = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _window(ratings: list[float], *, trend: str = "steady", competitions: int = 3) -> PlayerFormWindow:
    entries = tuple(
        FormEntry(
            match_id=f"m{index}",
            competition_id=f"c{index}",
            occurred_at=BASE - timedelta(days=index),
            rating=rating,
            minutes_played=90,
            goals=0,
            assists=0,
        )
        for index, rating in enumerate(ratings)
    )
    return PlayerFormWindow(
        player_id="p1",
        entries=entries,
        matches_counted=len(entries),
        competitions_counted=competitions,
        average_rating=round(sum(ratings) / len(ratings), 3) if ratings else None,
        trend=trend,
    )


def test_thin_sample_produces_no_influence():
    signal = build_matchday_signal(_window([9.9, 9.8]))

    assert signal.applied is False
    assert signal.adjustment_pct == 0.0
    assert signal.reason_code == REASON_INSUFFICIENT_SAMPLE


def test_minimum_matches_is_the_threshold():
    below = build_matchday_signal(_window([8.0] * (MINIMUM_MATCHES_FOR_SIGNAL - 1)))
    at = build_matchday_signal(_window([8.0] * MINIMUM_MATCHES_FOR_SIGNAL))

    assert below.applied is False
    assert at.applied is True


def test_strong_form_raises_value_and_weak_form_lowers_it():
    strong = build_matchday_signal(_window([8.5, 8.7, 8.3, 8.6, 8.4, 8.5]))
    weak = build_matchday_signal(_window([4.5, 4.3, 4.7, 4.4, 4.6, 4.5]))

    assert strong.adjustment_pct > 0
    assert strong.reason_code == REASON_FORM_POSITIVE
    assert weak.adjustment_pct < 0
    assert weak.reason_code == REASON_FORM_NEGATIVE


def test_baseline_form_moves_nothing():
    signal = build_matchday_signal(_window([6.5] * 6))

    assert signal.adjustment_pct == 0.0


@pytest.mark.parametrize("rating", [10.0, 9.5, 20.0])
def test_signal_is_bounded_above(rating: float):
    signal = build_matchday_signal(_window([rating] * 6, trend=TREND_RISING))

    assert signal.adjustment_pct <= EFFECTIVE_MAX_ADJUSTMENT_PCT
    assert signal.adjustment_pct <= MAX_TOTAL_ADJUSTMENT_PCT


@pytest.mark.parametrize("rating", [0.0, 1.0, -5.0])
def test_signal_is_bounded_below(rating: float):
    signal = build_matchday_signal(_window([rating] * 6, trend=TREND_FALLING))

    assert signal.adjustment_pct >= -EFFECTIVE_MAX_ADJUSTMENT_PCT
    assert signal.adjustment_pct >= -MAX_TOTAL_ADJUSTMENT_PCT


def test_one_spectacular_match_cannot_carry_the_signal():
    """Gradualism: a single 10/10 among ordinary games barely moves the number."""
    ordinary = build_matchday_signal(_window([6.5] * 6))
    with_spike = build_matchday_signal(_window([10.0] + [6.5] * 5))

    assert with_spike.adjustment_pct > ordinary.adjustment_pct
    # The spike is diluted by the window rather than dominating it.
    assert with_spike.adjustment_pct < EFFECTIVE_MAX_ADJUSTMENT_PCT / 2


def test_partial_windows_carry_less_weight_than_full_ones():
    partial = build_matchday_signal(_window([9.0] * 3))
    full = build_matchday_signal(_window([9.0] * 6))

    assert partial.confidence < full.confidence
    assert abs(partial.adjustment_pct) < abs(full.adjustment_pct)


def test_rising_trajectory_adds_a_nudge_over_identical_ratings():
    steady = build_matchday_signal(_window([7.5] * 6))
    rising = build_matchday_signal(_window([7.5] * 6, trend=TREND_RISING))

    assert rising.adjustment_pct > steady.adjustment_pct


def test_signal_is_deterministic():
    window = _window([7.2, 8.1, 6.9, 7.8, 7.1, 8.0])

    assert build_matchday_signal(window) == build_matchday_signal(window)


def test_audit_payload_explains_the_decision():
    signal = build_matchday_signal(_window([8.5] * 6, trend=TREND_RISING))
    payload = signal.as_audit_payload()

    for key in (
        "adjustment_pct",
        "reason_code",
        "matches_counted",
        "average_rating",
        "confidence",
        "trend",
        "baseline_rating",
        "max_total_adjustment_pct",
    ):
        assert key in payload
    assert payload["applied"] is True


def test_multiplier_matches_the_adjustment():
    signal = build_matchday_signal(_window([8.0] * 6))

    assert signal.multiplier() == pytest.approx(1.0 + signal.adjustment_pct)
