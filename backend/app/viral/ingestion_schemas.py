from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, TypeAdapter

from app.common.schemas.base import CommonSchema


class ClipEventType(str, Enum):
    VIEW = "view"
    WATCH_TIME = "watch_time"
    COMPLETE = "complete"
    LOOP = "loop"
    SHARE = "share"
    COMMENT = "comment"
    LIKE = "like"
    SCROLL = "scroll"

    @property
    def topic_name(self) -> str:
        return f"clip.{self.value}"

    @property
    def metric_field(self) -> str | None:
        if self is ClipEventType.VIEW:
            return "views"
        if self is ClipEventType.COMPLETE:
            return "completions"
        if self is ClipEventType.LOOP:
            return "loops"
        if self is ClipEventType.SHARE:
            return "shares"
        if self is ClipEventType.COMMENT:
            return "comments"
        if self is ClipEventType.LIKE:
            return "likes"
        if self is ClipEventType.SCROLL:
            return "skips"
        return None


CLIP_EVENT_TOPICS: tuple[str, ...] = tuple(event_type.topic_name for event_type in ClipEventType)
CLIP_METRIC_FIELDS: tuple[str, ...] = (
    "views",
    "total_watch_time",
    "completions",
    "loops",
    "shares",
    "comments",
    "likes",
    "skips",
)


class ClipEventMetadata(CommonSchema):
    device: str = Field(min_length=1)
    country: str = Field(min_length=1)
    referrer: str = Field(min_length=1)
    content_type: str | None = Field(default=None, min_length=1)
    format_key: str | None = Field(default=None, min_length=1)
    clip_event_type: str | None = Field(default=None, min_length=1)
    team_name: str | None = Field(default=None, min_length=1)
    tags: list[str] = Field(default_factory=list)


class ClipEventTrustFactors(CommonSchema):
    account_age: float = Field(default=1.0, ge=0.0, le=1.0)
    session_consistency: float = Field(default=1.0, ge=0.0, le=1.0)
    device_fingerprint_stability: float = Field(default=1.0, ge=0.0, le=1.0)
    engagement_authenticity: float = Field(default=1.0, ge=0.0, le=1.0)
    anomaly_detection: float = Field(default=1.0, ge=0.0, le=1.0)


class ClipEventTrust(CommonSchema):
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0)
    weighted_event_value: float = Field(default=1.0, ge=0.0)
    velocity_weight: float = Field(default=1.0, ge=0.0)
    loop_discount_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    shadow_banned: bool = False
    monetization_eligible: bool = True
    ranking_eligible: bool = True
    device_fingerprint: str | None = None
    device_fingerprint_sources: list[str] = Field(default_factory=list)
    ip_hash: str | None = None
    pattern_signature: str | None = None
    suspicious_flags: list[str] = Field(default_factory=list)
    factors: ClipEventTrustFactors = Field(default_factory=ClipEventTrustFactors)


class ClipEvent(CommonSchema):
    event_id: UUID
    clip_id: str = Field(min_length=1)
    user_id: str | None = None
    session_id: str = Field(min_length=1)
    timestamp: datetime
    event_type: ClipEventType
    watch_time_ms: int | None = Field(default=None, ge=0)
    video_length_ms: int | None = Field(default=None, ge=0)
    metadata: ClipEventMetadata
    trust: ClipEventTrust = Field(default_factory=ClipEventTrust)

    def to_kafka_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @property
    def kafka_topic(self) -> str:
        return self.event_type.topic_name

    @property
    def redis_metric_deltas(self) -> dict[str, int]:
        deltas: dict[str, int] = {}
        if self.watch_time_ms is not None:
            deltas["total_watch_time"] = int(self.watch_time_ms)
        metric_field = self.event_type.metric_field
        if metric_field is not None:
            deltas[metric_field] = deltas.get(metric_field, 0) + 1
        return deltas

    @property
    def weighted_redis_metric_deltas(self) -> dict[str, float]:
        if self.trust.shadow_banned:
            return {}
        deltas: dict[str, float] = {}
        base_weight = max(float(self.trust.weighted_event_value), 0.0)
        if self.watch_time_ms is not None and base_weight > 0.0:
            deltas["total_watch_time"] = round(float(self.watch_time_ms) * base_weight, 6)
        metric_field = self.event_type.metric_field
        if metric_field is not None and base_weight > 0.0:
            metric_weight = base_weight
            if self.event_type is ClipEventType.LOOP:
                metric_weight *= max(float(self.trust.loop_discount_factor), 0.0)
            deltas[metric_field] = round(deltas.get(metric_field, 0.0) + metric_weight, 6)
        return deltas


class ClipEventBatchWrite(CommonSchema):
    events: list[ClipEvent] = Field(min_length=1, max_length=1000)


class ClipEventIngestionAccepted(CommonSchema):
    status: str = "queued"
    accepted_events: int = Field(ge=0)
    queue_depth: int = Field(ge=0)
    topics: list[str] = Field(default_factory=list)


_clip_event_request_adapter = TypeAdapter(ClipEvent | list[ClipEvent] | ClipEventBatchWrite)


def parse_clip_events(payload: Any) -> list[ClipEvent]:
    parsed = _clip_event_request_adapter.validate_python(payload)
    if isinstance(parsed, ClipEvent):
        return [parsed]
    if isinstance(parsed, ClipEventBatchWrite):
        return list(parsed.events)
    if isinstance(parsed, Sequence):
        return list(parsed)
    raise TypeError("Unsupported clip event payload.")
