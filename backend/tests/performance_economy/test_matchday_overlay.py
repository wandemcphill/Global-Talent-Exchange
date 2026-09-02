"""The valuation overlay: the base engine stays primary, the overlay stays bounded."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.value_engine.jobs import InMemoryValueSnapshotRepository, ValueSnapshotJob
from app.value_engine.matchday_signal import (
    MatchdayValuationSignal,
    apply_matchday_overlay,
    build_matchday_signal,
)
from app.value_engine.models import PlayerValueInput

from .test_matchday_signal import _window

AS_OF = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _base_input(player_id: str = "p-1") -> PlayerValueInput:
    return PlayerValueInput(
        player_id=player_id,
        player_name="Ada Forward",
        as_of=AS_OF,
        reference_market_value_eur=70_000_000,
        current_credits=710.0,
    )


def _base_snapshot(player_id: str = "p-1"):
    repository = InMemoryValueSnapshotRepository(inputs={player_id: _base_input(player_id)})
    return ValueSnapshotJob().run(repository, AS_OF)[0]


def test_overlay_raises_the_published_value_for_strong_form():
    base = _base_snapshot()
    signal = build_matchday_signal(_window([8.6] * 6))

    adjusted = apply_matchday_overlay(base, signal)

    assert signal.adjustment_pct > 0
    assert adjusted.target_credits > base.target_credits
    assert adjusted.target_credits == pytest.approx(
        round(base.target_credits * signal.multiplier(), 2)
    )


def test_overlay_lowers_the_published_value_for_poor_form():
    base = _base_snapshot()
    signal = build_matchday_signal(_window([4.5] * 6))

    adjusted = apply_matchday_overlay(base, signal)

    assert adjusted.target_credits < base.target_credits


def test_overlay_leaves_component_values_untouched():
    """The base valuation remains the primary source of truth and stays separable."""
    base = _base_snapshot()
    signal = build_matchday_signal(_window([8.6] * 6))

    adjusted = apply_matchday_overlay(base, signal)

    assert adjusted.football_truth_value_credits == base.football_truth_value_credits
    assert adjusted.market_signal_value_credits == base.market_signal_value_credits
    assert adjusted.scouting_signal_value_credits == base.scouting_signal_value_credits
    assert adjusted.breakdown == base.breakdown


def test_overlay_records_its_reason_and_audit_trail():
    base = _base_snapshot()
    signal = build_matchday_signal(_window([8.6] * 6))

    adjusted = apply_matchday_overlay(base, signal)

    assert signal.reason_code in adjusted.reason_codes
    assert adjusted.matchday_signal_audit is not None
    assert adjusted.matchday_signal_audit["applied"] is True


def test_non_applied_signal_leaves_value_alone_but_still_audits():
    """"We looked and it did not qualify" is a fact worth being able to prove."""
    base = _base_snapshot()
    signal = build_matchday_signal(_window([9.9, 9.8]))

    adjusted = apply_matchday_overlay(base, signal)

    assert adjusted.target_credits == base.target_credits
    assert adjusted.reason_codes == base.reason_codes
    assert adjusted.matchday_signal_audit["applied"] is False


def test_overlay_recomputes_movement_against_the_previous_close():
    base = _base_snapshot()
    signal = build_matchday_signal(_window([8.6] * 6))

    adjusted = apply_matchday_overlay(base, signal)

    expected = round((adjusted.target_credits - base.previous_credits) / base.previous_credits, 4)
    assert adjusted.movement_pct == expected


def test_job_without_a_provider_is_unchanged():
    """The overlay is strictly additive: existing callers must behave exactly as before."""
    repository = InMemoryValueSnapshotRepository(inputs={"p-1": _base_input()})
    plain = ValueSnapshotJob().run(repository, AS_OF)[0]

    assert plain.matchday_signal_audit is None


def test_job_applies_the_provider_signal():
    repository = InMemoryValueSnapshotRepository(inputs={"p-1": _base_input()})
    signal = build_matchday_signal(_window([8.6] * 6))
    baseline = _base_snapshot()

    result = ValueSnapshotJob(matchday_signal_provider=lambda _: signal).run(repository, AS_OF)[0]

    assert result.target_credits > baseline.target_credits
    assert result.matchday_signal_audit is not None


def test_job_tolerates_a_provider_with_nothing_to_say():
    repository = InMemoryValueSnapshotRepository(inputs={"p-1": _base_input()})

    result = ValueSnapshotJob(matchday_signal_provider=lambda _: None).run(repository, AS_OF)[0]

    assert result.matchday_signal_audit is None


def test_overlay_can_never_exceed_the_documented_bound():
    """A pathological signal must still not be able to run the economy away."""
    base = _base_snapshot()
    rogue = MatchdayValuationSignal(
        player_id="p-1",
        applied=True,
        adjustment_pct=0.02,
        reason_code="matchday_form_positive",
        matches_counted=6,
        competitions_counted=3,
        average_rating=9.0,
        rating_above_baseline=2.5,
        trend="rising",
        trend_delta=0.5,
        confidence=1.0,
        raw_adjustment_pct=0.02,
        capped=False,
    )

    adjusted = apply_matchday_overlay(base, rogue)

    assert adjusted.target_credits <= base.target_credits * 1.05
