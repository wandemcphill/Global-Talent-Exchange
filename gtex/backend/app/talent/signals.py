"""Deterministic derivation of talent signals from a competition record.

Design rule that governs this whole module: **no signal may be produced from a
small sample.** Every rule below carries an explicit minimum sample size, and a
signal's strength is bounded to [0, 1]. A single outstanding (or disastrous)
match therefore produces no signal at all, and a run of good matches produces a
bounded one. `app.talent.ranking` then converts signals into clamped
adjustments, so the worst a hot streak can do to a composite score is move it
by a few points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import pstdev
from typing import Any, Final, Sequence

from app.talent.constants import (
    COMPETITION_LEVEL_SCORE,
    POSITION_FAMILY,
    POSITION_OUTPUT_BASELINE_PER_90,
    SIGNAL_POLARITY,
    TALENT_SIGNAL_CONFIG_VERSION,
    TalentSignalCode,
)
from app.talent.inputs import AvailabilityWindow, TalentMatchRecord

# --- Sample-size floors -------------------------------------------------
MIN_RATED_MATCHES_FOR_FORM: Final[int] = 6
MIN_DECISIVE_MATCHES: Final[int] = 3
MIN_APPEARANCES_FOR_OUTPUT: Final[int] = 6
MIN_MINUTES_FOR_OUTPUT: Final[int] = 270
MIN_MATCHES_PER_PROGRESSION_HALF: Final[int] = 4
MIN_APPEARANCES_FOR_DISCIPLINE: Final[int] = 6
MIN_ELIGIBLE_FOR_AVAILABILITY: Final[int] = 6
MIN_ELITE_APPEARANCES: Final[int] = 5

# --- Thresholds ---------------------------------------------------------
HIGH_RATING_THRESHOLD: Final[float] = 7.0
HIGH_RATING_SHARE_FLOOR: Final[float] = 0.50
HIGH_RATING_SHARE_FULL: Final[float] = 0.90
CLUTCH_DELTA_FLOOR: Final[float] = 0.30
CLUTCH_DELTA_FULL: Final[float] = 1.50
CONSISTENCY_SD_LOW: Final[float] = 0.60
CONSISTENCY_SD_HIGH: Final[float] = 1.20
CONSISTENCY_SD_CEILING: Final[float] = 2.20
OUTPUT_EXCELLENCE_MULTIPLIER: Final[float] = 1.50
OUTPUT_EXCELLENCE_FULL_MULTIPLIER: Final[float] = 3.00
PROGRESSION_DELTA_FLOOR: Final[float] = 0.40
PROGRESSION_DELTA_FULL: Final[float] = 1.50
DISCIPLINE_INDEX_FLOOR: Final[float] = 0.50
DISCIPLINE_INDEX_FULL: Final[float] = 1.20
RED_CARD_WEIGHT: Final[float] = 3.0
AVAILABILITY_RISK_RATIO: Final[float] = 0.70
AVAILABILITY_CRITICAL_RATIO: Final[float] = 0.30
ELITE_LEVEL_SCORE_FLOOR: Final[float] = 88.0
ELITE_APPEARANCES_FULL: Final[int] = 25

SIGNAL_LABELS: Final[dict[str, str]] = {
    TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE.value: "Sustained high performance",
    TalentSignalCode.CLUTCH_PERFORMANCE.value: "Raises level in decisive matches",
    TalentSignalCode.CONSISTENT_PERFORMER.value: "Consistent performer",
    TalentSignalCode.VOLATILE_PERFORMER.value: "Volatile match-to-match output",
    TalentSignalCode.POSITIONAL_EXCELLENCE.value: "Output above positional baseline",
    TalentSignalCode.PROGRESSION.value: "Improving trajectory",
    TalentSignalCode.REGRESSION.value: "Declining trajectory",
    TalentSignalCode.ELITE_COMPETITION_EXPERIENCE.value: "Elite competition experience",
    TalentSignalCode.DISCIPLINARY_CONCERN.value: "Disciplinary concern",
    TalentSignalCode.INJURY_AVAILABILITY_RISK.value: "Availability risk",
}


@dataclass(frozen=True, slots=True)
class TalentSignal:
    code: str
    label: str
    polarity: str
    strength: float
    sample_size: int
    explanation: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "polarity": self.polarity,
            "strength": self.strength,
            "sample_size": self.sample_size,
            "explanation": self.explanation,
            "evidence": dict(sorted(self.evidence.items())),
        }


def _clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _ramp(value: float, floor: float, full: float) -> float:
    """Linear 0->1 ramp between `floor` and `full`, clamped at both ends."""

    if full <= floor:
        return 1.0 if value >= full else 0.0
    return _clamp01((value - floor) / (full - floor))


def _signal(
    code: TalentSignalCode,
    *,
    strength: float,
    sample_size: int,
    explanation: str,
    evidence: dict[str, Any],
) -> TalentSignal:
    return TalentSignal(
        code=code.value,
        label=SIGNAL_LABELS[code.value],
        polarity=SIGNAL_POLARITY[code.value],
        strength=_clamp01(strength),
        sample_size=max(0, int(sample_size)),
        explanation=explanation,
        evidence=evidence,
    )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def derive_signals(
    match_records: Sequence[TalentMatchRecord],
    *,
    position_code: str | None = None,
    availability: AvailabilityWindow | None = None,
) -> tuple[TalentSignal, ...]:
    """Derive every applicable signal from an already-canonicalised record set.

    Callers should pass `TalentRankingInput.canonical().match_records` so the
    ordering and deduplication guarantees hold; this function additionally
    sorts defensively so it is safe to call directly.
    """

    records = tuple(
        sorted((record.canonical() for record in match_records), key=lambda item: (item.played_on, item.match_key))
    )
    signals: list[TalentSignal] = []

    rated = tuple(record for record in records if record.clamped_rating is not None)
    ratings = tuple(float(record.clamped_rating or 0.0) for record in rated)

    signals.extend(_form_signals(rated, ratings))
    signals.extend(_clutch_signals(rated))
    signals.extend(_output_signals(records, position_code))
    signals.extend(_trajectory_signals(rated, ratings))
    signals.extend(_competition_level_signals(records))
    signals.extend(_discipline_signals(records))
    signals.extend(_availability_signals(availability))

    return tuple(sorted(signals, key=lambda item: item.code))


def _form_signals(rated: Sequence[TalentMatchRecord], ratings: Sequence[float]) -> list[TalentSignal]:
    if len(rated) < MIN_RATED_MATCHES_FOR_FORM:
        return []

    signals: list[TalentSignal] = []
    high_count = sum(1 for rating in ratings if rating >= HIGH_RATING_THRESHOLD)
    share = high_count / len(ratings)
    if share >= HIGH_RATING_SHARE_FLOOR:
        signals.append(
            _signal(
                TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE,
                strength=_ramp(share, HIGH_RATING_SHARE_FLOOR, HIGH_RATING_SHARE_FULL),
                sample_size=len(rated),
                explanation=(
                    f"Rated {HIGH_RATING_THRESHOLD:.1f}+ in {high_count} of {len(ratings)} rated appearances."
                ),
                evidence={
                    "rated_appearances": len(ratings),
                    "high_rating_appearances": high_count,
                    "high_rating_share": round(share, 4),
                    "rating_threshold": HIGH_RATING_THRESHOLD,
                },
            )
        )

    deviation = pstdev(ratings) if len(ratings) > 1 else 0.0
    if deviation <= CONSISTENCY_SD_LOW:
        signals.append(
            _signal(
                TalentSignalCode.CONSISTENT_PERFORMER,
                strength=1.0 - _ramp(deviation, 0.0, CONSISTENCY_SD_LOW),
                sample_size=len(rated),
                explanation=(f"Match rating spread of {deviation:.2f} across {len(ratings)} rated appearances."),
                evidence={
                    "rated_appearances": len(ratings),
                    "rating_std_dev": round(deviation, 4),
                    "mean_rating": round(_mean(ratings), 4),
                },
            )
        )
    elif deviation >= CONSISTENCY_SD_HIGH:
        signals.append(
            _signal(
                TalentSignalCode.VOLATILE_PERFORMER,
                strength=_ramp(deviation, CONSISTENCY_SD_HIGH, CONSISTENCY_SD_CEILING),
                sample_size=len(rated),
                explanation=(f"Match rating spread of {deviation:.2f} across {len(ratings)} rated appearances."),
                evidence={
                    "rated_appearances": len(ratings),
                    "rating_std_dev": round(deviation, 4),
                    "mean_rating": round(_mean(ratings), 4),
                },
            )
        )
    return signals


def _clutch_signals(rated: Sequence[TalentMatchRecord]) -> list[TalentSignal]:
    decisive = tuple(record for record in rated if record.is_decisive)
    routine = tuple(record for record in rated if not record.is_decisive)
    if len(decisive) < MIN_DECISIVE_MATCHES or len(routine) < MIN_DECISIVE_MATCHES:
        # Without a routine baseline of comparable size there is nothing to
        # compare against; "played three finals" is not evidence of clutch.
        return []

    decisive_mean = _mean([float(record.clamped_rating or 0.0) for record in decisive])
    routine_mean = _mean([float(record.clamped_rating or 0.0) for record in routine])
    delta = decisive_mean - routine_mean
    if delta < CLUTCH_DELTA_FLOOR:
        return []
    return [
        _signal(
            TalentSignalCode.CLUTCH_PERFORMANCE,
            strength=_ramp(delta, CLUTCH_DELTA_FLOOR, CLUTCH_DELTA_FULL),
            sample_size=len(decisive),
            explanation=(
                f"Averages {decisive_mean:.2f} in {len(decisive)} decisive matches "
                f"versus {routine_mean:.2f} in {len(routine)} routine matches."
            ),
            evidence={
                "decisive_appearances": len(decisive),
                "routine_appearances": len(routine),
                "decisive_mean_rating": round(decisive_mean, 4),
                "routine_mean_rating": round(routine_mean, 4),
                "rating_delta": round(delta, 4),
            },
        )
    ]


def _output_signals(records: Sequence[TalentMatchRecord], position_code: str | None) -> list[TalentSignal]:
    appearances = tuple(record for record in records if record.clamped_minutes > 0)
    total_minutes = sum(record.clamped_minutes for record in appearances)
    if len(appearances) < MIN_APPEARANCES_FOR_OUTPUT or total_minutes < MIN_MINUTES_FOR_OUTPUT:
        return []

    family = POSITION_FAMILY.get((position_code or "").upper(), "midfielder")
    baseline = POSITION_OUTPUT_BASELINE_PER_90[family]
    if family == "goalkeeper":
        # Goalkeeper "output" is clean sheets, not goal contributions.
        events = sum(1 for record in appearances if record.clean_sheet)
        metric_name = "clean_sheets"
        baseline = 0.30
    else:
        events = sum(record.goals + record.assists for record in appearances)
        metric_name = "goal_contributions"

    per_90 = events / (total_minutes / 90.0)
    ratio = per_90 / baseline if baseline > 0 else 0.0
    if ratio < OUTPUT_EXCELLENCE_MULTIPLIER:
        return []
    return [
        _signal(
            TalentSignalCode.POSITIONAL_EXCELLENCE,
            strength=_ramp(ratio, OUTPUT_EXCELLENCE_MULTIPLIER, OUTPUT_EXCELLENCE_FULL_MULTIPLIER),
            sample_size=len(appearances),
            explanation=(
                f"{per_90:.2f} {metric_name.replace('_', ' ')} per 90 against a "
                f"{family} baseline of {baseline:.2f}."
            ),
            evidence={
                "appearances": len(appearances),
                "minutes": total_minutes,
                "metric": metric_name,
                "events": events,
                "per_90": round(per_90, 4),
                "position_family": family,
                "baseline_per_90": baseline,
                "baseline_ratio": round(ratio, 4),
            },
        )
    ]


def _trajectory_signals(rated: Sequence[TalentMatchRecord], ratings: Sequence[float]) -> list[TalentSignal]:
    if len(rated) < MIN_MATCHES_PER_PROGRESSION_HALF * 2:
        return []

    midpoint = len(ratings) // 2
    earlier = ratings[:midpoint]
    recent = ratings[midpoint:]
    if len(earlier) < MIN_MATCHES_PER_PROGRESSION_HALF or len(recent) < MIN_MATCHES_PER_PROGRESSION_HALF:
        return []

    earlier_mean = _mean(earlier)
    recent_mean = _mean(recent)
    delta = recent_mean - earlier_mean
    evidence = {
        "earlier_appearances": len(earlier),
        "recent_appearances": len(recent),
        "earlier_mean_rating": round(earlier_mean, 4),
        "recent_mean_rating": round(recent_mean, 4),
        "rating_delta": round(delta, 4),
    }
    if delta >= PROGRESSION_DELTA_FLOOR:
        return [
            _signal(
                TalentSignalCode.PROGRESSION,
                strength=_ramp(delta, PROGRESSION_DELTA_FLOOR, PROGRESSION_DELTA_FULL),
                sample_size=len(recent),
                explanation=(f"Recent half averages {recent_mean:.2f} against {earlier_mean:.2f} earlier."),
                evidence=evidence,
            )
        ]
    if delta <= -PROGRESSION_DELTA_FLOOR:
        return [
            _signal(
                TalentSignalCode.REGRESSION,
                strength=_ramp(-delta, PROGRESSION_DELTA_FLOOR, PROGRESSION_DELTA_FULL),
                sample_size=len(recent),
                explanation=(f"Recent half averages {recent_mean:.2f} against {earlier_mean:.2f} earlier."),
                evidence=evidence,
            )
        ]
    return []


def _competition_level_signals(records: Sequence[TalentMatchRecord]) -> list[TalentSignal]:
    elite = tuple(
        record
        for record in records
        if COMPETITION_LEVEL_SCORE.get(record.competition_level, 0.0) >= ELITE_LEVEL_SCORE_FLOOR
        and record.clamped_minutes > 0
    )
    if len(elite) < MIN_ELITE_APPEARANCES:
        return []
    competitions = sorted({record.competition_key for record in elite})
    return [
        _signal(
            TalentSignalCode.ELITE_COMPETITION_EXPERIENCE,
            strength=_ramp(float(len(elite)), float(MIN_ELITE_APPEARANCES), float(ELITE_APPEARANCES_FULL)),
            sample_size=len(elite),
            explanation=(f"{len(elite)} appearances across {len(competitions)} top-level competitions."),
            evidence={
                "elite_appearances": len(elite),
                "elite_competition_count": len(competitions),
                "minutes": sum(record.clamped_minutes for record in elite),
            },
        )
    ]


def _discipline_signals(records: Sequence[TalentMatchRecord]) -> list[TalentSignal]:
    appearances = tuple(record for record in records if record.clamped_minutes > 0)
    if len(appearances) < MIN_APPEARANCES_FOR_DISCIPLINE:
        return []
    yellows = sum(record.yellow_cards for record in appearances)
    reds = sum(record.red_cards for record in appearances)
    index = (yellows + RED_CARD_WEIGHT * reds) / len(appearances)
    if index < DISCIPLINE_INDEX_FLOOR:
        return []
    return [
        _signal(
            TalentSignalCode.DISCIPLINARY_CONCERN,
            strength=_ramp(index, DISCIPLINE_INDEX_FLOOR, DISCIPLINE_INDEX_FULL),
            sample_size=len(appearances),
            explanation=(f"{yellows} yellow and {reds} red cards across {len(appearances)} appearances."),
            evidence={
                "appearances": len(appearances),
                "yellow_cards": yellows,
                "red_cards": reds,
                "discipline_index": round(index, 4),
            },
        )
    ]


def _availability_signals(availability: AvailabilityWindow | None) -> list[TalentSignal]:
    if availability is None:
        return []
    if availability.eligible_matches < MIN_ELIGIBLE_FOR_AVAILABILITY:
        return []
    ratio = availability.availability_ratio
    if ratio is None or ratio > AVAILABILITY_RISK_RATIO:
        return []
    return [
        _signal(
            TalentSignalCode.INJURY_AVAILABILITY_RISK,
            strength=_ramp(
                AVAILABILITY_RISK_RATIO - ratio,
                0.0,
                AVAILABILITY_RISK_RATIO - AVAILABILITY_CRITICAL_RATIO,
            ),
            sample_size=availability.eligible_matches,
            explanation=(
                f"Available for {availability.available_matches} of "
                f"{availability.eligible_matches} eligible matches."
            ),
            evidence={
                "eligible_matches": availability.eligible_matches,
                "available_matches": availability.available_matches,
                "availability_ratio": round(ratio, 4),
                "days_unavailable": availability.days_unavailable,
                "window_days": availability.window_days,
            },
        )
    ]


__all__ = [
    "TALENT_SIGNAL_CONFIG_VERSION",
    "TalentSignal",
    "derive_signals",
]
