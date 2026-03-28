from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol


class VariantMetricsLike(Protocol):
    variant_id: str
    view_count: int
    watch_time: float
    loop_rate: float
    shares: int
    comments: int
    completion_rate: float
    share_rate: float
    comment_rate: float


@dataclass(slots=True)
class VariantScoreBreakdown:
    view_score: float = 0.0
    retention_score: float = 0.0
    loop_score: float = 0.0
    share_score: float = 0.0
    comment_score: float = 0.0
    watch_time_score: float = 0.0
    total: float = 0.0


@dataclass(slots=True)
class ViralVariantScoringComparator:
    def score_variant(self, variant: VariantMetricsLike | Mapping[str, Any]) -> VariantScoreBreakdown:
        view_count = float(self._value(variant, "view_count"))
        completion_rate = self._bounded_ratio(self._value(variant, "completion_rate"))
        loop_rate = self._bounded_ratio(self._value(variant, "loop_rate"))
        share_rate = self._bounded_ratio(self._value(variant, "share_rate"))
        comment_rate = self._bounded_ratio(self._value(variant, "comment_rate"))
        watch_time = max(float(self._value(variant, "watch_time")), 0.0)

        breakdown = VariantScoreBreakdown(
            view_score=round(min(view_count / 1000.0, 1.2) * 18.0, 2),
            retention_score=round(completion_rate * 32.0, 2),
            loop_score=round(loop_rate * 18.0, 2),
            share_score=round(share_rate * 300.0, 2),
            comment_score=round(comment_rate * 200.0, 2),
            watch_time_score=round(min(watch_time / 18.0, 1.0) * 10.0, 2),
        )
        breakdown.total = round(
            breakdown.view_score
            + breakdown.retention_score
            + breakdown.loop_score
            + breakdown.share_score
            + breakdown.comment_score
            + breakdown.watch_time_score,
            2,
        )
        return breakdown

    def best_variant(self, variants: Iterable[VariantMetricsLike]) -> VariantMetricsLike:
        return max(
            variants,
            key=lambda variant: (
                self.score_variant(variant).total,
                int(self._value(variant, "view_count")),
                int(self._value(variant, "shares")),
                str(self._value(variant, "variant_id")),
            ),
        )

    def _value(self, variant: VariantMetricsLike | Mapping[str, Any], field_name: str) -> Any:
        if isinstance(variant, Mapping):
            return variant.get(field_name, 0)
        return getattr(variant, field_name, 0)

    def _bounded_ratio(self, value: object) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return max(0.0, min(numeric, 1.0))


__all__ = ["VariantScoreBreakdown", "ViralVariantScoringComparator"]
