"""The bounded valuation signal derived from GTEX competition performance.

This module is the contract between football and money. It is deliberately small,
pure and free of database access so that its behaviour can be reasoned about and
tested exhaustively.

Design constraints, all of which are enforced below and covered by tests:

* **Bounded.** A player's whole matchday history can move his value by at most
  ``MAX_TOTAL_ADJUSTMENT_PCT`` in either direction. It can never run away.
* **Gradual.** The signal is the *mean* over a rolling window, so a single
  spectacular or catastrophic match is diluted, never decisive. On top of that each
  match's own contribution is capped before it is averaged.
* **Deterministic.** Same window in, same number out. No randomness, no clock, no
  ordering ambiguity.
* **Auditable.** The result carries every intermediate quantity that produced it,
  so "why did his value move?" is answerable from stored data.
* **Secondary.** This is an overlay applied on top of the existing valuation, which
  remains the primary source of truth. It adjusts; it does not replace.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from app.players.form_service import (
    BASELINE_RATING,
    FORM_WINDOW_SIZE,
    MINIMUM_MATCHES_FOR_SIGNAL,
    TREND_FALLING,
    TREND_RISING,
    PlayerFormWindow,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from app.value_engine.models import ValueSnapshot

#: Value movement per rating point above/below the 6.5 baseline, per match.
PER_MATCH_SENSITIVITY = 0.012

#: Hard cap on what any single match may contribute before averaging. A 10/10 and a
#: 9/10 are worth the same to the signal, which removes the incentive to chase one
#: freak scoreline.
PER_MATCH_CAP_PCT = 0.02

#: Absolute backstop on the whole signal.
#:
#: Note that in practice this is *not* the binding constraint and is not expected to
#: be reached: because the signal is the mean of per-match contributions that are
#: each already capped at ``PER_MATCH_CAP_PCT``, the mean can never exceed that cap.
#: The true effective bound is therefore
#: ``PER_MATCH_CAP_PCT + TREND_NUDGE_PCT`` = 2.4%, which is asserted by the tests.
#: This constant is retained as defence in depth so that a future change to the
#: per-match maths cannot silently unbound the economy.
MAX_TOTAL_ADJUSTMENT_PCT = 0.05

#: A rising or falling trajectory is worth a small nudge on top of the level of
#: performance, because a holder is buying the direction as much as the standard.
TREND_NUDGE_PCT = 0.004

#: The bound that actually binds, exposed so callers and UI can state it truthfully.
EFFECTIVE_MAX_ADJUSTMENT_PCT = PER_MATCH_CAP_PCT + TREND_NUDGE_PCT

REASON_INSUFFICIENT_SAMPLE = "matchday_form_insufficient_sample"
REASON_FORM_POSITIVE = "matchday_form_positive"
REASON_FORM_NEGATIVE = "matchday_form_negative"
REASON_FORM_NEUTRAL = "matchday_form_neutral"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True, slots=True)
class MatchdayValuationSignal:
    """A bounded, auditable valuation adjustment derived from competition form."""

    player_id: str
    applied: bool
    adjustment_pct: float
    reason_code: str
    matches_counted: int
    competitions_counted: int
    average_rating: float | None
    rating_above_baseline: float
    trend: str
    trend_delta: float
    confidence: float
    raw_adjustment_pct: float
    capped: bool

    def multiplier(self) -> float:
        """The factor to apply to an existing valuation."""
        return 1.0 + self.adjustment_pct

    def as_audit_payload(self) -> dict[str, object]:
        """Everything needed to reconstruct this decision after the fact."""
        return {
            "player_id": self.player_id,
            "applied": self.applied,
            "adjustment_pct": round(self.adjustment_pct, 6),
            "reason_code": self.reason_code,
            "matches_counted": self.matches_counted,
            "competitions_counted": self.competitions_counted,
            "average_rating": self.average_rating,
            "rating_above_baseline": round(self.rating_above_baseline, 4),
            "trend": self.trend,
            "trend_delta": self.trend_delta,
            "confidence": round(self.confidence, 4),
            "raw_adjustment_pct": round(self.raw_adjustment_pct, 6),
            "capped": self.capped,
            "baseline_rating": BASELINE_RATING,
            "max_total_adjustment_pct": MAX_TOTAL_ADJUSTMENT_PCT,
            "minimum_matches_for_signal": MINIMUM_MATCHES_FOR_SIGNAL,
        }


def build_matchday_signal(window: PlayerFormWindow) -> MatchdayValuationSignal:
    """Turn a form window into a bounded valuation adjustment.

    Returns a non-applied, zero-adjustment signal when the sample is too thin. A
    player with one good game is not a player whose value should move.
    """
    if not window.is_signal_eligible:
        return MatchdayValuationSignal(
            player_id=window.player_id,
            applied=False,
            adjustment_pct=0.0,
            reason_code=REASON_INSUFFICIENT_SAMPLE,
            matches_counted=window.matches_counted,
            competitions_counted=window.competitions_counted,
            average_rating=window.average_rating,
            rating_above_baseline=window.rating_above_baseline,
            trend=window.trend,
            trend_delta=window.trend_delta,
            confidence=0.0,
            raw_adjustment_pct=0.0,
            capped=False,
        )

    # Each match contributes independently, and is capped on its own before being
    # averaged. This is what stops one match from carrying the signal.
    per_match = [
        _clamp(
            (entry.rating - BASELINE_RATING) * PER_MATCH_SENSITIVITY,
            -PER_MATCH_CAP_PCT,
            PER_MATCH_CAP_PCT,
        )
        for entry in window.entries
    ]
    mean_contribution = sum(per_match) / len(per_match)

    trend_nudge = 0.0
    if window.trend == TREND_RISING:
        trend_nudge = TREND_NUDGE_PCT
    elif window.trend == TREND_FALLING:
        trend_nudge = -TREND_NUDGE_PCT

    # A partially filled window is a weaker claim than a full one, so its influence
    # ramps in rather than arriving at full strength the moment it becomes eligible.
    confidence = _clamp(window.matches_counted / FORM_WINDOW_SIZE, 0.0, 1.0)

    raw = (mean_contribution + trend_nudge) * confidence
    adjustment = _clamp(raw, -MAX_TOTAL_ADJUSTMENT_PCT, MAX_TOTAL_ADJUSTMENT_PCT)

    if adjustment > 0:
        reason = REASON_FORM_POSITIVE
    elif adjustment < 0:
        reason = REASON_FORM_NEGATIVE
    else:
        reason = REASON_FORM_NEUTRAL

    return MatchdayValuationSignal(
        player_id=window.player_id,
        applied=True,
        adjustment_pct=round(adjustment, 6),
        reason_code=reason,
        matches_counted=window.matches_counted,
        competitions_counted=window.competitions_counted,
        average_rating=window.average_rating,
        rating_above_baseline=window.rating_above_baseline,
        trend=window.trend,
        trend_delta=window.trend_delta,
        confidence=confidence,
        raw_adjustment_pct=round(raw, 6),
        capped=abs(raw) > MAX_TOTAL_ADJUSTMENT_PCT,
    )


__all__ = [
    "EFFECTIVE_MAX_ADJUSTMENT_PCT",
    "MAX_TOTAL_ADJUSTMENT_PCT",
    "PER_MATCH_CAP_PCT",
    "PER_MATCH_SENSITIVITY",
    "TREND_NUDGE_PCT",
    "REASON_FORM_NEGATIVE",
    "REASON_FORM_NEUTRAL",
    "REASON_FORM_POSITIVE",
    "REASON_INSUFFICIENT_SAMPLE",
    "MatchdayValuationSignal",
    "build_matchday_signal",
    "apply_matchday_overlay",
]


def apply_matchday_overlay(snapshot: "ValueSnapshot", signal: MatchdayValuationSignal) -> "ValueSnapshot":
    """Return a copy of ``snapshot`` with the bounded matchday overlay applied.

    The base snapshot produced by :class:`~app.value_engine.scoring.ValueEngine`
    remains the primary source of truth. This adjusts the published figure and
    records exactly why, leaving every underlying component value untouched so the
    two contributions stay separable forever.
    """
    if not signal.applied or signal.adjustment_pct == 0.0:
        # Still attach the audit payload: "we looked and it did not qualify" is
        # itself a fact worth being able to prove later.
        return replace(snapshot, matchday_signal_audit=signal.as_audit_payload())

    adjusted_target = round(snapshot.target_credits * signal.multiplier(), 2)

    previous = snapshot.previous_credits
    movement_pct = (
        round((adjusted_target - previous) / previous, 4) if previous else snapshot.movement_pct
    )

    reason_codes = tuple(snapshot.reason_codes) + (signal.reason_code,)

    return replace(
        snapshot,
        target_credits=adjusted_target,
        movement_pct=movement_pct,
        reason_codes=reason_codes,
        matchday_signal_audit=signal.as_audit_payload(),
    )
