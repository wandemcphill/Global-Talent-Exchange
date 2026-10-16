from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.viral.aggregation_worker import clip_trust_metrics_key

LOW_CLIP_TRUST_THRESHOLD = 0.3


@dataclass(frozen=True, slots=True)
class ClipTrustSummary:
    avg_trust_score: float = 1.0
    clip_trust_score: float = 1.0
    event_count: int = 0
    payout_eligible: bool = True
    viral_boost_eligible: bool = True


@dataclass(slots=True)
class ClipTrustMetricsReader:
    redis_url: str | None = None
    _client: Redis | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.redis_url:
            return
        try:
            client = Redis.from_url(self.redis_url, decode_responses=True, health_check_interval=30)
            client.ping()
        except RedisError:
            return
        self._client = client

    def resolve(
        self,
        *,
        clip_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ClipTrustSummary:
        payload = dict(metadata or {})
        explicit_avg = _coerce_score(payload.get("avg_trust_score"))
        explicit_clip = _coerce_score(payload.get("clip_trust_score"))
        user_scores = _user_trust_scores(payload)
        computed_user_average = _average(user_scores)

        redis_avg = None
        redis_event_count = 0
        if clip_id and self._client is not None:
            try:
                trust_payload = self._client.hgetall(clip_trust_metrics_key(clip_id))
            except RedisError:
                trust_payload = {}
            redis_event_count = max(_coerce_int(trust_payload.get("event_count")), 0)
            if redis_event_count > 0:
                redis_avg = _coerce_score(trust_payload.get("trust_weight_sum"), default=0.0) / redis_event_count

        avg_trust_score = explicit_avg
        if avg_trust_score is None:
            avg_trust_score = computed_user_average
        if avg_trust_score is None:
            avg_trust_score = redis_avg
        if avg_trust_score is None:
            avg_trust_score = explicit_clip
        if avg_trust_score is None:
            avg_trust_score = 1.0

        clip_trust_score = explicit_clip
        if clip_trust_score is None:
            clip_trust_score = computed_user_average
        if clip_trust_score is None:
            clip_trust_score = redis_avg
        if clip_trust_score is None:
            clip_trust_score = avg_trust_score

        resolved_avg = _clamp_score(avg_trust_score)
        resolved_clip = _clamp_score(clip_trust_score)
        eligible = resolved_clip >= LOW_CLIP_TRUST_THRESHOLD
        return ClipTrustSummary(
            avg_trust_score=round(resolved_avg, 4),
            clip_trust_score=round(resolved_clip, 4),
            event_count=redis_event_count,
            payout_eligible=eligible,
            viral_boost_eligible=eligible,
        )


def build_clip_trust_metrics_reader(*, settings: Settings | None = None) -> ClipTrustMetricsReader:
    resolved_settings = settings or get_settings()
    return ClipTrustMetricsReader(redis_url=resolved_settings.redis_url)


def _user_trust_scores(payload: Mapping[str, Any]) -> list[float]:
    for key in ("user_trust_scores", "trust_scores"):
        raw = payload.get(key)
        if isinstance(raw, list):
            return [_clamp_score(score) for score in raw if _coerce_score(score) is not None]
        if isinstance(raw, dict):
            scores: list[float] = []
            for score in raw.values():
                coerced = _coerce_score(score)
                if coerced is not None:
                    scores.append(_clamp_score(coerced))
            return scores
    return []


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _clamp_score(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _coerce_score(value: object, *, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "ClipTrustMetricsReader",
    "ClipTrustSummary",
    "LOW_CLIP_TRUST_THRESHOLD",
    "build_clip_trust_metrics_reader",
]
