"""Deterministic, explainable talent ranking.

There is deliberately no single "overall rating" input here. A composite score
is assembled from eight independently computed components, each of which
reports its own score, weight, sample size, confidence and a human-readable
explanation. Two properties are load-bearing:

1. **Determinism.** The pipeline is a pure function of `TalentRankingInput`.
   No clock, no database, no randomness. `as_of` is supplied by the caller.
   Inputs are canonicalised (sorted, deduplicated, clamped) before scoring, so
   the same facts in a different order produce a byte-identical result, and the
   returned `inputs_digest` proves which facts produced a given score.

2. **Small samples cannot move a ranking far.** Every evidence-derived
   component is shrunk toward a neutral 50 in proportion to its sample size,
   and signal-derived adjustments are individually and collectively clamped.
   One extraordinary match is worth a fraction of a point.

The pipeline does not read, and cannot read, identity, KYC, wallet or payment
state — see `TalentRankingInput`.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import pstdev
from typing import Any, Final, Mapping, Sequence

from app.talent.constants import (
    COMPETITION_LEVEL_SCORE,
    CompetitionLevel,
    NEUTRAL_COMPONENT_SCORE,
    POSITION_FAMILY,
    POSITION_OUTPUT_BASELINE_PER_90,
    TALENT_RANKING_CONFIG_VERSION,
    TACTICAL_ATTRIBUTES,
    PHYSICAL_ATTRIBUTES,
    VERIFICATION_TIER_SCORE,
    TalentSignalCode,
    technical_attribute_keys,
)
from app.talent.inputs import TalentMatchRecord, TalentRankingInput
from app.talent.signals import TalentSignal, derive_signals

# Component identifiers, in the fixed order used for scoring and display.
COMPONENT_TECHNICAL: Final[str] = "technical_ability"
COMPONENT_TACTICAL: Final[str] = "tactical_intelligence"
COMPONENT_PHYSICAL: Final[str] = "physical_profile"
COMPONENT_MATCH_PERFORMANCE: Final[str] = "match_performance"
COMPONENT_CONSISTENCY: Final[str] = "consistency"
COMPONENT_COMPETITION_LEVEL: Final[str] = "competition_level"
COMPONENT_RECENT_FORM: Final[str] = "recent_form"
COMPONENT_CREDENTIALS: Final[str] = "verified_credentials"

COMPONENT_ORDER: Final[tuple[str, ...]] = (
    COMPONENT_TECHNICAL,
    COMPONENT_TACTICAL,
    COMPONENT_PHYSICAL,
    COMPONENT_MATCH_PERFORMANCE,
    COMPONENT_CONSISTENCY,
    COMPONENT_COMPETITION_LEVEL,
    COMPONENT_RECENT_FORM,
    COMPONENT_CREDENTIALS,
)

COMPONENT_WEIGHTS: Final[Mapping[str, float]] = {
    COMPONENT_TECHNICAL: 0.18,
    COMPONENT_TACTICAL: 0.14,
    COMPONENT_PHYSICAL: 0.10,
    COMPONENT_MATCH_PERFORMANCE: 0.20,
    COMPONENT_CONSISTENCY: 0.12,
    COMPONENT_COMPETITION_LEVEL: 0.12,
    COMPONENT_RECENT_FORM: 0.10,
    COMPONENT_CREDENTIALS: 0.04,
}

COMPONENT_LABELS: Final[Mapping[str, str]] = {
    COMPONENT_TECHNICAL: "Technical ability",
    COMPONENT_TACTICAL: "Tactical intelligence",
    COMPONENT_PHYSICAL: "Physical profile",
    COMPONENT_MATCH_PERFORMANCE: "Match performance",
    COMPONENT_CONSISTENCY: "Consistency",
    COMPONENT_COMPETITION_LEVEL: "Competition level",
    COMPONENT_RECENT_FORM: "Recent form",
    COMPONENT_CREDENTIALS: "Verified credentials",
}

# Shrinkage constants: `score = 50 + (raw - 50) * n / (n + K)`.
MATCH_PERFORMANCE_SHRINKAGE_K: Final[float] = 6.0
CONSISTENCY_SHRINKAGE_K: Final[float] = 4.0
COMPETITION_LEVEL_SHRINKAGE_K: Final[float] = 6.0
RECENT_FORM_SHRINKAGE_K: Final[float] = 4.0
MIN_RATED_FOR_CONSISTENCY: Final[int] = 3

# Attribute coverage below this fraction is shrunk toward neutral so a profile
# with one filled-in attribute cannot claim an elite technical score.
ATTRIBUTE_FULL_CREDIT_COVERAGE: Final[float] = 0.60

RECENT_FORM_WINDOW: Final[int] = 6
RECENT_FORM_HALF_LIFE_MATCHES: Final[float] = 3.0
OUTPUT_DELTA_CAP: Final[float] = 12.0
OUTPUT_DELTA_GAIN: Final[float] = 8.0
CONSISTENCY_SD_FULL_PENALTY: Final[float] = 2.0

# Signal-driven adjustments. Only signals whose evidence is *not* already
# carried by a component appear here; otherwise the same fact would be counted
# twice. Sustained performance, positional output, consistency/volatility and
# elite experience are all already inside components and are therefore absent.
SIGNAL_ADJUSTMENT_WEIGHTS: Final[Mapping[str, float]] = {
    TalentSignalCode.CLUTCH_PERFORMANCE.value: 2.5,
    TalentSignalCode.PROGRESSION.value: 2.5,
    TalentSignalCode.REGRESSION.value: -2.5,
    TalentSignalCode.DISCIPLINARY_CONCERN.value: -4.0,
    TalentSignalCode.INJURY_AVAILABILITY_RISK.value: -4.0,
}
ADJUSTMENT_TOTAL_CAP: Final[float] = 8.0


@dataclass(frozen=True, slots=True)
class RankingComponent:
    code: str
    label: str
    score: float
    weight: float
    weighted_contribution: float
    sample_size: int
    confidence: float
    explanation: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "score": self.score,
            "weight": self.weight,
            "weighted_contribution": self.weighted_contribution,
            "sample_size": self.sample_size,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class RankingAdjustment:
    code: str
    label: str
    delta: float
    reason: str

    def as_payload(self) -> dict[str, Any]:
        return {"code": self.code, "label": self.label, "delta": self.delta, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class TalentRankingResult:
    player_id: str
    as_of: str
    config_version: str
    composite_score: float
    base_score: float
    adjustments_total: float
    confidence: float
    sample_size: int
    components: tuple[RankingComponent, ...]
    adjustments: tuple[RankingAdjustment, ...]
    signals: tuple[TalentSignal, ...]
    inputs_digest: str

    @property
    def form_score(self) -> float:
        return self.component_score(COMPONENT_RECENT_FORM)

    @property
    def consistency_score(self) -> float:
        return self.component_score(COMPONENT_CONSISTENCY)

    @property
    def competition_level_score(self) -> float:
        return self.component_score(COMPONENT_COMPETITION_LEVEL)

    def component_score(self, code: str) -> float:
        for component in self.components:
            if component.code == code:
                return component.score
        return NEUTRAL_COMPONENT_SCORE

    def sort_key(self) -> tuple[float, str]:
        """Total order for ranked listings.

        Negated score first so ascending sort yields descending rank, then
        `player_id` so equal scores never reorder between requests.
        """

        return (-self.composite_score, self.player_id)

    def as_payload(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "as_of": self.as_of,
            "config_version": self.config_version,
            "composite_score": self.composite_score,
            "base_score": self.base_score,
            "adjustments_total": self.adjustments_total,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "components": [component.as_payload() for component in self.components],
            "adjustments": [adjustment.as_payload() for adjustment in self.adjustments],
            "signals": [signal.as_payload() for signal in self.signals],
            "inputs_digest": self.inputs_digest,
        }


def compute_inputs_digest(ranking_input: TalentRankingInput) -> str:
    """Stable fingerprint of the exact facts a score was computed from."""

    payload = ranking_input.canonical().as_digest_payload()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _shrink(raw_score: float, weight: float, shrinkage_k: float) -> float:
    if weight <= 0:
        return NEUTRAL_COMPONENT_SCORE
    factor = weight / (weight + shrinkage_k)
    return NEUTRAL_COMPONENT_SCORE + (raw_score - NEUTRAL_COMPONENT_SCORE) * factor


def _confidence(weight: float, shrinkage_k: float) -> float:
    if weight <= 0:
        return 0.0
    return round(weight / (weight + shrinkage_k), 4)


def _appearance_weight(record: TalentMatchRecord) -> float:
    """Minutes-based weight capped at one full match."""

    return min(1.0, record.clamped_minutes / 90.0)


def _build_component(
    code: str,
    *,
    score: float,
    sample_size: int,
    confidence: float,
    explanation: str,
) -> RankingComponent:
    weight = COMPONENT_WEIGHTS[code]
    clamped = _clamp_score(score)
    return RankingComponent(
        code=code,
        label=COMPONENT_LABELS[code],
        score=clamped,
        weight=weight,
        weighted_contribution=round(clamped * weight, 4),
        sample_size=max(0, int(sample_size)),
        confidence=round(max(0.0, min(1.0, confidence)), 4),
        explanation=explanation,
    )


def _attribute_component(
    code: str,
    attributes: Mapping[str, float],
    expected_keys: Sequence[str],
    *,
    group_label: str,
) -> RankingComponent:
    present = [attributes[key] for key in expected_keys if key in attributes]
    if not present:
        return _build_component(
            code,
            score=NEUTRAL_COMPONENT_SCORE,
            sample_size=0,
            confidence=0.0,
            explanation=f"No {group_label} attributes recorded; scored neutral.",
        )
    coverage = len(present) / len(expected_keys)
    raw_mean = sum(present) / len(present)
    credit = min(1.0, coverage / ATTRIBUTE_FULL_CREDIT_COVERAGE)
    score = NEUTRAL_COMPONENT_SCORE + (raw_mean - NEUTRAL_COMPONENT_SCORE) * credit
    explanation = (
        f"Mean of {len(present)} of {len(expected_keys)} {group_label} attributes "
        f"({raw_mean:.1f}), credited at {credit * 100:.0f}% for coverage."
    )
    return _build_component(
        code,
        score=score,
        sample_size=len(present),
        confidence=round(coverage, 4),
        explanation=explanation,
    )


def _weighted_mean_rating(records: Sequence[TalentMatchRecord]) -> tuple[float | None, float]:
    total_weight = 0.0
    accumulator = 0.0
    for record in records:
        rating = record.clamped_rating
        if rating is None:
            continue
        weight = _appearance_weight(record)
        if weight <= 0:
            continue
        accumulator += rating * weight
        total_weight += weight
    if total_weight <= 0:
        return None, 0.0
    return accumulator / total_weight, total_weight


def _match_performance_component(records: Sequence[TalentMatchRecord], position_code: str | None) -> RankingComponent:
    mean_rating, rating_weight = _weighted_mean_rating(records)
    appearances = [record for record in records if record.clamped_minutes > 0]
    if mean_rating is None or not appearances:
        return _build_component(
            COMPONENT_MATCH_PERFORMANCE,
            score=NEUTRAL_COMPONENT_SCORE,
            sample_size=len(appearances),
            confidence=0.0,
            explanation="No rated appearances on record; scored neutral.",
        )

    family = POSITION_FAMILY.get((position_code or "").upper(), "midfielder")
    baseline = POSITION_OUTPUT_BASELINE_PER_90[family]
    total_minutes = sum(record.clamped_minutes for record in appearances)
    if family == "goalkeeper":
        events = sum(1 for record in appearances if record.clean_sheet)
        baseline = 0.30
        metric = "clean sheets"
    else:
        events = sum(record.goals + record.assists for record in appearances)
        metric = "goal contributions"
    per_90 = events / (total_minutes / 90.0) if total_minutes > 0 else 0.0
    ratio = per_90 / baseline if baseline > 0 else 1.0
    output_delta = max(-OUTPUT_DELTA_CAP, min(OUTPUT_DELTA_CAP, (ratio - 1.0) * OUTPUT_DELTA_GAIN))

    raw = max(0.0, min(100.0, mean_rating * 10.0 + output_delta))
    score = _shrink(raw, rating_weight, MATCH_PERFORMANCE_SHRINKAGE_K)
    explanation = (
        f"Minutes-weighted rating {mean_rating:.2f}/10 with {per_90:.2f} {metric} per 90 "
        f"({ratio:.2f}x the {family} baseline), shrunk toward neutral on "
        f"{rating_weight:.1f} full-match equivalents."
    )
    return _build_component(
        COMPONENT_MATCH_PERFORMANCE,
        score=score,
        sample_size=len(appearances),
        confidence=_confidence(rating_weight, MATCH_PERFORMANCE_SHRINKAGE_K),
        explanation=explanation,
    )


def _consistency_component(records: Sequence[TalentMatchRecord]) -> RankingComponent:
    ratings = [record.clamped_rating for record in records if record.clamped_rating is not None]
    if len(ratings) < MIN_RATED_FOR_CONSISTENCY:
        return _build_component(
            COMPONENT_CONSISTENCY,
            score=NEUTRAL_COMPONENT_SCORE,
            sample_size=len(ratings),
            confidence=0.0,
            explanation=(
                f"Fewer than {MIN_RATED_FOR_CONSISTENCY} rated appearances; "
                "consistency cannot be assessed and is scored neutral."
            ),
        )
    deviation = pstdev([float(rating) for rating in ratings])
    raw = max(0.0, min(100.0, 100.0 - (deviation / CONSISTENCY_SD_FULL_PENALTY) * 100.0))
    score = _shrink(raw, float(len(ratings)), CONSISTENCY_SHRINKAGE_K)
    return _build_component(
        COMPONENT_CONSISTENCY,
        score=score,
        sample_size=len(ratings),
        confidence=_confidence(float(len(ratings)), CONSISTENCY_SHRINKAGE_K),
        explanation=(f"Rating standard deviation {deviation:.2f} across {len(ratings)} rated appearances."),
    )


def _competition_level_component(records: Sequence[TalentMatchRecord]) -> RankingComponent:
    total_weight = 0.0
    accumulator = 0.0
    for record in records:
        weight = _appearance_weight(record)
        if weight <= 0:
            continue
        accumulator += COMPETITION_LEVEL_SCORE.get(record.competition_level, 0.0) * weight
        total_weight += weight
    if total_weight <= 0:
        return _build_component(
            COMPONENT_COMPETITION_LEVEL,
            score=COMPETITION_LEVEL_SCORE[CompetitionLevel.UNKNOWN.value],
            sample_size=0,
            confidence=0.0,
            explanation="No competition minutes on record; scored at the unknown-level baseline.",
        )
    raw = accumulator / total_weight
    score = _shrink(raw, total_weight, COMPETITION_LEVEL_SHRINKAGE_K)
    levels = sorted({record.competition_level for record in records if _appearance_weight(record) > 0})
    return _build_component(
        COMPONENT_COMPETITION_LEVEL,
        score=score,
        sample_size=len(levels),
        confidence=_confidence(total_weight, COMPETITION_LEVEL_SHRINKAGE_K),
        explanation=(f"Minutes-weighted competition level {raw:.1f}/100 across levels: {', '.join(levels)}."),
    )


def _recent_form_component(records: Sequence[TalentMatchRecord]) -> RankingComponent:
    """Form is a *delta* against the talent's own baseline, centred on 50.

    Scoring form in absolute terms would double-count match performance. What a
    scout wants from this component is "is this player currently above or below
    their own level", which is what a centred delta expresses.
    """

    rated = [record for record in records if record.clamped_rating is not None]
    baseline, baseline_weight = _weighted_mean_rating(records)
    if baseline is None or len(rated) < 2:
        return _build_component(
            COMPONENT_RECENT_FORM,
            score=NEUTRAL_COMPONENT_SCORE,
            sample_size=len(rated),
            confidence=0.0,
            explanation="Not enough rated appearances to establish a form trend; scored neutral.",
        )

    window = list(reversed(rated))[:RECENT_FORM_WINDOW]
    weighted_total = 0.0
    weight_total = 0.0
    for index, record in enumerate(window):
        decay = 0.5 ** (index / RECENT_FORM_HALF_LIFE_MATCHES)
        weighted_total += float(record.clamped_rating or 0.0) * decay
        weight_total += decay
    recent_mean = weighted_total / weight_total if weight_total > 0 else baseline

    raw = max(0.0, min(100.0, NEUTRAL_COMPONENT_SCORE + (recent_mean - baseline) * 10.0))
    score = _shrink(raw, float(len(window)), RECENT_FORM_SHRINKAGE_K)
    direction = "above" if recent_mean >= baseline else "below"
    return _build_component(
        COMPONENT_RECENT_FORM,
        score=score,
        sample_size=len(window),
        confidence=_confidence(float(len(window)), RECENT_FORM_SHRINKAGE_K),
        explanation=(
            f"Last {len(window)} appearances average {recent_mean:.2f}, {direction} the "
            f"career baseline of {baseline:.2f} ({baseline_weight:.1f} full-match equivalents)."
        ),
    )


def _credentials_component(verification_tier: str) -> RankingComponent:
    score = VERIFICATION_TIER_SCORE.get(verification_tier, 0.0)
    readable = verification_tier.replace("_", " ")
    return _build_component(
        COMPONENT_CREDENTIALS,
        score=score,
        sample_size=1,
        confidence=1.0,
        explanation=f"Verification tier: {readable}.",
    )


def _adjustments_from_signals(signals: Sequence[TalentSignal]) -> tuple[RankingAdjustment, ...]:
    adjustments: list[RankingAdjustment] = []
    for signal in sorted(signals, key=lambda item: item.code):
        weight = SIGNAL_ADJUSTMENT_WEIGHTS.get(signal.code)
        if weight is None:
            continue
        delta = round(weight * signal.strength, 2)
        if delta == 0.0:
            continue
        adjustments.append(
            RankingAdjustment(
                code=signal.code,
                label=signal.label,
                delta=delta,
                reason=signal.explanation,
            )
        )
    return tuple(adjustments)


def compute_ranking(ranking_input: TalentRankingInput) -> TalentRankingResult:
    """Score one talent. Pure, deterministic, and fully explainable."""

    normalised = ranking_input.canonical()
    records = normalised.match_records
    position_code = normalised.position_code

    components = (
        _attribute_component(
            COMPONENT_TECHNICAL,
            normalised.technical_attributes,
            technical_attribute_keys(position_code),
            group_label="technical",
        ),
        _attribute_component(
            COMPONENT_TACTICAL,
            normalised.tactical_attributes,
            TACTICAL_ATTRIBUTES,
            group_label="tactical",
        ),
        _attribute_component(
            COMPONENT_PHYSICAL,
            normalised.physical_attributes,
            PHYSICAL_ATTRIBUTES,
            group_label="physical",
        ),
        _match_performance_component(records, position_code),
        _consistency_component(records),
        _competition_level_component(records),
        _recent_form_component(records),
        _credentials_component(normalised.verification_tier),
    )
    # Fixed display/scoring order regardless of construction order above.
    ordered = tuple(component for code in COMPONENT_ORDER for component in components if component.code == code)

    signals = derive_signals(
        records,
        position_code=position_code,
        availability=normalised.availability,
    )
    adjustments = _adjustments_from_signals(signals)

    base_score = round(sum(component.weighted_contribution for component in ordered), 2)
    raw_adjustment_total = round(sum(adjustment.delta for adjustment in adjustments), 2)
    adjustments_total = round(max(-ADJUSTMENT_TOTAL_CAP, min(ADJUSTMENT_TOTAL_CAP, raw_adjustment_total)), 2)
    composite = _clamp_score(base_score + adjustments_total)
    confidence = round(sum(component.confidence * component.weight for component in ordered), 4)

    return TalentRankingResult(
        player_id=normalised.player_id,
        as_of=normalised.as_of.isoformat(),
        config_version=TALENT_RANKING_CONFIG_VERSION,
        composite_score=composite,
        base_score=base_score,
        adjustments_total=adjustments_total,
        confidence=confidence,
        sample_size=len(records),
        components=ordered,
        adjustments=adjustments,
        signals=signals,
        inputs_digest=compute_inputs_digest(normalised),
    )


def rank_talents(inputs: Sequence[TalentRankingInput]) -> tuple[TalentRankingResult, ...]:
    """Score a batch and return it in stable ranked order."""

    return tuple(sorted((compute_ranking(item) for item in inputs), key=lambda result: result.sort_key()))


__all__ = [
    "ADJUSTMENT_TOTAL_CAP",
    "COMPONENT_COMPETITION_LEVEL",
    "COMPONENT_CONSISTENCY",
    "COMPONENT_CREDENTIALS",
    "COMPONENT_MATCH_PERFORMANCE",
    "COMPONENT_ORDER",
    "COMPONENT_PHYSICAL",
    "COMPONENT_RECENT_FORM",
    "COMPONENT_TACTICAL",
    "COMPONENT_TECHNICAL",
    "COMPONENT_WEIGHTS",
    "RankingAdjustment",
    "RankingComponent",
    "TALENT_RANKING_CONFIG_VERSION",
    "TalentRankingResult",
    "compute_inputs_digest",
    "compute_ranking",
    "rank_talents",
]
