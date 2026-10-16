"""Defence in depth: the overlay enforces the bound itself.

``build_matchday_signal`` already produces a bounded signal. These tests cover the
case where a signal reaches ``apply_matchday_overlay`` from somewhere else - a
future caller, a replayed audit payload, an upstream bug, a test double - and
prove the overlay refuses to publish an out-of-range adjustment regardless.

Two independent checks must both fail before the economy can be unbounded.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.value_engine.jobs import InMemoryValueSnapshotRepository, ValueSnapshotJob
from app.value_engine.matchday_signal import (
    EFFECTIVE_MAX_ADJUSTMENT_PCT,
    REASON_OVERLAY_CLAMPED,
    MatchdayValuationSignal,
    apply_matchday_overlay,
)
from app.value_engine.models import PlayerValueInput

AS_OF = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _base_snapshot():
    repository = InMemoryValueSnapshotRepository(
        inputs={
            "p-1": PlayerValueInput(
                player_id="p-1",
                player_name="Ada Forward",
                as_of=AS_OF,
                reference_market_value_eur=70_000_000,
                current_credits=710.0,
            )
        }
    )
    return ValueSnapshotJob().run(repository, AS_OF)[0]


def _signal(adjustment_pct: float) -> MatchdayValuationSignal:
    """A signal with an arbitrary adjustment, bypassing the builder's own clamp."""
    return MatchdayValuationSignal(
        player_id="p-1",
        applied=True,
        adjustment_pct=adjustment_pct,
        reason_code="matchday_form_positive" if adjustment_pct >= 0 else "matchday_form_negative",
        matches_counted=6,
        competitions_counted=3,
        average_rating=8.0,
        rating_above_baseline=1.5,
        trend="rising",
        trend_delta=0.3,
        confidence=1.0,
        raw_adjustment_pct=adjustment_pct,
        capped=False,
    )


# --- rogue signals: must be clamped -----------------------------------------


def test_rogue_positive_signal_is_clamped():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(0.10))

    ceiling = round(base.target_credits * (1.0 + EFFECTIVE_MAX_ADJUSTMENT_PCT), 2)
    assert adjusted.target_credits == ceiling
    assert adjusted.target_credits < base.target_credits * 1.10
    assert adjusted.matchday_signal_audit["overlay_clamped"] is True
    assert adjusted.matchday_signal_audit["requested_adjustment_pct"] == 0.10
    assert adjusted.matchday_signal_audit["applied_adjustment_pct"] == EFFECTIVE_MAX_ADJUSTMENT_PCT
    assert REASON_OVERLAY_CLAMPED in adjusted.reason_codes


def test_rogue_negative_signal_is_clamped():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(-0.10))

    floor = round(base.target_credits * (1.0 - EFFECTIVE_MAX_ADJUSTMENT_PCT), 2)
    assert adjusted.target_credits == floor
    assert adjusted.target_credits > base.target_credits * 0.90
    assert adjusted.matchday_signal_audit["overlay_clamped"] is True
    assert adjusted.matchday_signal_audit["applied_adjustment_pct"] == -EFFECTIVE_MAX_ADJUSTMENT_PCT
    assert REASON_OVERLAY_CLAMPED in adjusted.reason_codes


# --- valid edges: must pass through untouched -------------------------------


def test_valid_upper_edge_is_applied_in_full():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(EFFECTIVE_MAX_ADJUSTMENT_PCT))

    assert adjusted.target_credits == round(
        base.target_credits * (1.0 + EFFECTIVE_MAX_ADJUSTMENT_PCT), 2
    )
    assert adjusted.matchday_signal_audit["overlay_clamped"] is False
    assert REASON_OVERLAY_CLAMPED not in adjusted.reason_codes


def test_valid_lower_edge_is_applied_in_full():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(-EFFECTIVE_MAX_ADJUSTMENT_PCT))

    assert adjusted.target_credits == round(
        base.target_credits * (1.0 - EFFECTIVE_MAX_ADJUSTMENT_PCT), 2
    )
    assert adjusted.matchday_signal_audit["overlay_clamped"] is False
    assert REASON_OVERLAY_CLAMPED not in adjusted.reason_codes


# --- normal signals: unaffected by the guard --------------------------------


def test_normal_positive_signal_passes_through():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(0.0121))

    assert adjusted.target_credits == round(base.target_credits * 1.0121, 2)
    assert adjusted.target_credits > base.target_credits
    assert adjusted.matchday_signal_audit["overlay_clamped"] is False


def test_normal_negative_signal_passes_through():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(-0.0090))

    assert adjusted.target_credits == round(base.target_credits * 0.9910, 2)
    assert adjusted.target_credits < base.target_credits
    assert adjusted.matchday_signal_audit["overlay_clamped"] is False


# --- the invariant, stated directly -----------------------------------------


@pytest.mark.parametrize(
    "rogue_pct",
    [0.10, -0.10, 1.0, -1.0, 5.0, -0.99, 0.025, -0.025],
)
def test_published_target_can_never_exceed_the_bound(rogue_pct: float):
    """No input to the overlay may move the published number beyond the bound."""
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(rogue_pct))

    ceiling = base.target_credits * (1.0 + EFFECTIVE_MAX_ADJUSTMENT_PCT)
    floor = base.target_credits * (1.0 - EFFECTIVE_MAX_ADJUSTMENT_PCT)
    # Rounding to two decimals can land a hair outside the raw product.
    assert floor - 0.01 <= adjusted.target_credits <= ceiling + 0.01


def test_clamped_overlay_still_leaves_component_values_untouched():
    base = _base_snapshot()

    adjusted = apply_matchday_overlay(base, _signal(0.10))

    assert adjusted.football_truth_value_credits == base.football_truth_value_credits
    assert adjusted.market_signal_value_credits == base.market_signal_value_credits
    assert adjusted.breakdown == base.breakdown
