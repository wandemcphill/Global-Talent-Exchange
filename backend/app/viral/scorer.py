from __future__ import annotations

from dataclasses import dataclass
from math import exp


_BASE_EVENT_SCORES: dict[str, int] = {
    "goal": 50,
    "penalty_goal": 46,
    "penalty_scored": 46,
    "penalty_missed": 34,
    "penalty_miss": 34,
    "red_card": 36,
    "double_save": 32,
    "goalkeeper_save": 26,
    "save": 24,
    "woodwork": 24,
    "missed_big_chance": 22,
    "shot_on_target": 18,
    "tactical_swing": 14,
    "substitution": 10,
}


@dataclass(slots=True)
class ViralScoreContext:
    event_type: str
    minute: int
    xg: float = 0.0
    importance: int = 1
    late_drama: bool = False
    comeback: bool = False
    go_ahead: bool = False
    equalizer: bool = False
    rivalry: bool = False
    upset: bool = False
    is_final: bool = False
    decided_by_penalties: bool = False
    crowd_spike: bool = False
    total_goals: int = 0


@dataclass(slots=True)
class ViralScoreBreakdown:
    base_event: int = 0
    xg_bonus: int = 0
    late_drama_bonus: int = 0
    comeback_bonus: int = 0
    go_ahead_bonus: int = 0
    equalizer_bonus: int = 0
    rivalry_bonus: int = 0
    upset_bonus: int = 0
    stage_bonus: int = 0
    crowd_bonus: int = 0
    importance_bonus: int = 0
    chaos_bonus: int = 0
    total: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "base_event": self.base_event,
            "xg_bonus": self.xg_bonus,
            "late_drama_bonus": self.late_drama_bonus,
            "comeback_bonus": self.comeback_bonus,
            "go_ahead_bonus": self.go_ahead_bonus,
            "equalizer_bonus": self.equalizer_bonus,
            "rivalry_bonus": self.rivalry_bonus,
            "upset_bonus": self.upset_bonus,
            "stage_bonus": self.stage_bonus,
            "crowd_bonus": self.crowd_bonus,
            "importance_bonus": self.importance_bonus,
            "chaos_bonus": self.chaos_bonus,
            "total": self.total,
        }


def score_clip(context: ViralScoreContext) -> ViralScoreBreakdown:
    breakdown = ViralScoreBreakdown()
    normalized_event = context.event_type.strip().lower()

    breakdown.base_event = _BASE_EVENT_SCORES.get(normalized_event, 12)
    breakdown.importance_bonus = max(0, min(context.importance, 5) - 1) * 6

    if context.xg >= 0.50:
        breakdown.xg_bonus = 20
    elif context.xg >= 0.30:
        breakdown.xg_bonus = 10

    if context.minute >= 85:
        breakdown.late_drama_bonus = 30
    elif context.minute >= 75:
        breakdown.late_drama_bonus = 14

    if context.comeback:
        breakdown.comeback_bonus = 28
    if context.go_ahead:
        breakdown.go_ahead_bonus = 18
    if context.equalizer:
        breakdown.equalizer_bonus = 14
    if context.rivalry:
        breakdown.rivalry_bonus = 16
    if context.upset:
        breakdown.upset_bonus = 20
    if context.is_final:
        breakdown.stage_bonus += 18
    if context.decided_by_penalties:
        breakdown.stage_bonus += 10
    if context.crowd_spike:
        breakdown.crowd_bonus = 8
    if context.total_goals >= 4:
        breakdown.chaos_bonus = 8

    breakdown.total = sum(
        (
            breakdown.base_event,
            breakdown.xg_bonus,
            breakdown.late_drama_bonus,
            breakdown.comeback_bonus,
            breakdown.go_ahead_bonus,
            breakdown.equalizer_bonus,
            breakdown.rivalry_bonus,
            breakdown.upset_bonus,
            breakdown.stage_bonus,
            breakdown.crowd_bonus,
            breakdown.importance_bonus,
            breakdown.chaos_bonus,
        )
    )
    return breakdown


@dataclass(slots=True)
class ViralRankingInput:
    clip_id: str
    views: int
    completions: int
    total_watch_time: float
    loops: float
    shares: int
    comments: int
    skips: int
    views_last_10min: int
    views_last_60min: int
    age_hours: float
    duration_seconds: float | None = None


@dataclass(slots=True)
class ViralRankingMetrics:
    completion_rate: float = 0.0
    avg_watch_time: float = 0.0
    avg_watch_time_normalized: float = 0.0
    loop_rate: float = 0.0
    share_rate: float = 0.0
    comment_rate: float = 0.0
    skip_rate: float = 0.0
    velocity: float = 0.0
    views_last_10min: int = 0
    views_last_60min: int = 0
    velocity_boost_applied: bool = False
    decay_multiplier: float = 1.0

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "completion_rate": self.completion_rate,
            "avg_watch_time": self.avg_watch_time,
            "avg_watch_time_normalized": self.avg_watch_time_normalized,
            "loop_rate": self.loop_rate,
            "share_rate": self.share_rate,
            "comment_rate": self.comment_rate,
            "skip_rate": self.skip_rate,
            "velocity": self.velocity,
            "views_last_10min": self.views_last_10min,
            "views_last_60min": self.views_last_60min,
            "velocity_boost_applied": self.velocity_boost_applied,
            "decay_multiplier": self.decay_multiplier,
        }


@dataclass(slots=True)
class ViralRankingResult:
    clip_id: str
    score: float
    metrics: ViralRankingMetrics


@dataclass(frozen=True, slots=True)
class TrendingScoreWeights:
    completion_rate: float = 0.35
    loop_rate: float = 0.20
    share_rate: float = 0.20
    comment_rate: float = 0.10
    avg_watch_time: float = 0.10
    skip_penalty: float = 0.15
    velocity_multiplier: float = 1.20


def compute_ranking_metrics(payload: ViralRankingInput) -> ViralRankingMetrics:
    views = max(int(payload.views), 0)
    completions = max(0, min(int(payload.completions), views)) if views > 0 else 0
    total_watch_time = max(float(payload.total_watch_time), 0.0)
    loops = max(float(payload.loops), 0.0)
    shares = max(int(payload.shares), 0)
    comments = max(int(payload.comments), 0)
    skips = max(int(payload.skips), 0)
    views_last_10min = max(int(payload.views_last_10min), 0)
    views_last_60min = max(int(payload.views_last_60min), 0)

    completion_rate = _safe_divide(completions, views)
    avg_watch_time = _safe_divide(total_watch_time, views)
    avg_watch_time_normalized = _normalize_watch_time(
        avg_watch_time=avg_watch_time,
        duration_seconds=payload.duration_seconds,
    )
    loop_rate = _safe_divide(loops, views)
    share_rate = _safe_divide(shares, views)
    comment_rate = _safe_divide(comments, views)
    skip_rate = _safe_divide(skips, views)
    velocity = _safe_divide(views_last_10min, views_last_60min)

    return ViralRankingMetrics(
        completion_rate=round(completion_rate, 4),
        avg_watch_time=round(avg_watch_time, 4),
        avg_watch_time_normalized=round(avg_watch_time_normalized, 4),
        loop_rate=round(loop_rate, 4),
        share_rate=round(share_rate, 4),
        comment_rate=round(comment_rate, 4),
        skip_rate=round(skip_rate, 4),
        velocity=round(velocity, 4),
        views_last_10min=views_last_10min,
        views_last_60min=views_last_60min,
    )


def score_trending_clip(
    payload: ViralRankingInput,
    *,
    velocity_threshold: float = 0.3,
    weights: TrendingScoreWeights | None = None,
) -> ViralRankingResult:
    resolved_weights = weights or TrendingScoreWeights()
    metrics = compute_ranking_metrics(payload)
    score = (
        (resolved_weights.completion_rate * metrics.completion_rate)
        + (resolved_weights.loop_rate * metrics.loop_rate)
        + (resolved_weights.share_rate * metrics.share_rate)
        + (resolved_weights.comment_rate * metrics.comment_rate)
        + (resolved_weights.avg_watch_time * metrics.avg_watch_time_normalized)
        - (resolved_weights.skip_penalty * metrics.skip_rate)
    )
    if metrics.velocity > velocity_threshold:
        score *= resolved_weights.velocity_multiplier
        metrics.velocity_boost_applied = True
    score = max(score, 0.0)
    metrics.decay_multiplier = round(exp(-max(float(payload.age_hours), 0.0) / 24.0), 6)
    score *= metrics.decay_multiplier
    return ViralRankingResult(
        clip_id=payload.clip_id,
        score=round(max(score, 0.0), 6),
        metrics=metrics,
    )


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(float(numerator), 0.0) / float(denominator)


def _normalize_watch_time(*, avg_watch_time: float, duration_seconds: float | None) -> float:
    normalized_duration = float(duration_seconds or 0.0)
    if normalized_duration > 0:
        return max(0.0, min(avg_watch_time / normalized_duration, 1.0))
    if avg_watch_time <= 0.0:
        return 0.0
    return 1.0


__all__ = [
    "TrendingScoreWeights",
    "ViralRankingInput",
    "ViralRankingMetrics",
    "ViralRankingResult",
    "compute_ranking_metrics",
    "score_clip",
    "score_trending_clip",
]
