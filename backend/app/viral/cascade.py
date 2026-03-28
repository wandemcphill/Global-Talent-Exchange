from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from threading import Lock
from typing import Any, Mapping, Protocol

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings

CASCADE_FLAG_KEY_PATTERN = "clip:{clip_id}:cascade"
CASCADE_STATE_KEY_PATTERN = "clip:{clip_id}:cascade:state"
CASCADE_INDEX_KEY = "viral:cascades:index"

DEFAULT_ACTIVE_WINDOW = timedelta(minutes=15)
DEFAULT_COOLDOWN_WINDOW = timedelta(hours=1)
DEFAULT_DISTRIBUTION_CAP_MULTIPLIER = 3
DEFAULT_FEED_INJECTION_BONUS = 30.0
DEFAULT_VELOCITY_THRESHOLD = 2.5
DEFAULT_COMPLETION_RATE_THRESHOLD = 0.7
DEFAULT_SHARE_RATE_THRESHOLD = 0.1
DEFAULT_RETRIGGER_VELOCITY_DELTA = 0.25
DEFAULT_RETRIGGER_GROWTH_FACTOR = 1.25
DEFAULT_HISTORY_RETENTION = timedelta(hours=24)


def cascade_flag_key(clip_id: str) -> str:
    return CASCADE_FLAG_KEY_PATTERN.format(clip_id=clip_id)


def cascade_state_key(clip_id: str) -> str:
    return CASCADE_STATE_KEY_PATTERN.format(clip_id=clip_id)


@dataclass(frozen=True, slots=True)
class CascadeMetricsSnapshot:
    velocity: float
    completion_rate: float
    share_rate: float
    views_last_10min: int
    views_last_60min: int
    view_count: int
    source: str = "clip_analytics"

    def as_dict(self) -> dict[str, Any]:
        return {
            "velocity": round(float(self.velocity), 4),
            "completion_rate": round(float(self.completion_rate), 4),
            "share_rate": round(float(self.share_rate), 4),
            "views_last_10min": int(self.views_last_10min),
            "views_last_60min": int(self.views_last_60min),
            "view_count": int(self.view_count),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CascadeMetricsSnapshot":
        return cls(
            velocity=float(payload.get("velocity", 0.0) or 0.0),
            completion_rate=float(payload.get("completion_rate", 0.0) or 0.0),
            share_rate=float(payload.get("share_rate", 0.0) or 0.0),
            views_last_10min=int(payload.get("views_last_10min", 0) or 0),
            views_last_60min=int(payload.get("views_last_60min", 0) or 0),
            view_count=int(payload.get("view_count", 0) or 0),
            source=str(payload.get("source") or "clip_analytics"),
        )


@dataclass(frozen=True, slots=True)
class ViralCascadeCandidate:
    clip_id: str
    analytics: Mapping[str, Any]
    match_id: str | None = None
    highlight_id: str | None = None
    title: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ViralCascadeRecord:
    clip_id: str
    triggered_at: datetime
    active_until: datetime
    cooldown_until: datetime
    metrics: CascadeMetricsSnapshot
    trigger_count: int = 1
    distribution_cap_multiplier: int = DEFAULT_DISTRIBUTION_CAP_MULTIPLIER
    feed_injection_targets: tuple[str, ...] = ("for_you_feed", "following_feed", "discover_feed")
    pinned_in_trending: bool = True
    match_id: str | None = None
    highlight_id: str | None = None
    title: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)

    def status(self, *, now: datetime) -> str:
        if self.active_until > now:
            return "active"
        if self.cooldown_until > now:
            return "cooldown"
        return "expired"

    def as_dict(self, *, now: datetime) -> dict[str, Any]:
        status = self.status(now=now)
        return {
            "clip_id": self.clip_id,
            "match_id": self.match_id,
            "highlight_id": self.highlight_id,
            "title": self.title,
            "cascade": status == "active",
            "status": status,
            "triggered_at": self.triggered_at,
            "active_until": self.active_until,
            "cooldown_until": self.cooldown_until,
            "trigger_count": self.trigger_count,
            "actions": {
                "distribution_cap_multiplier": int(self.distribution_cap_multiplier),
                "feed_injection_targets": list(self.feed_injection_targets),
                "pinned_in_trending": bool(self.pinned_in_trending),
            },
            "metrics": self.metrics.as_dict(),
            "metadata": dict(self.metadata_json),
        }

    def to_json(self) -> str:
        payload = {
            "clip_id": self.clip_id,
            "triggered_at": self.triggered_at.isoformat(),
            "active_until": self.active_until.isoformat(),
            "cooldown_until": self.cooldown_until.isoformat(),
            "metrics": self.metrics.as_dict(),
            "trigger_count": self.trigger_count,
            "distribution_cap_multiplier": self.distribution_cap_multiplier,
            "feed_injection_targets": list(self.feed_injection_targets),
            "pinned_in_trending": self.pinned_in_trending,
            "match_id": self.match_id,
            "highlight_id": self.highlight_id,
            "title": self.title,
            "metadata": dict(self.metadata_json),
        }
        return json.dumps(payload, default=str)

    @classmethod
    def from_json(cls, payload: str) -> "ViralCascadeRecord" | None:
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError:
            return None
        try:
            return cls(
                clip_id=str(raw["clip_id"]),
                triggered_at=_parse_datetime(raw["triggered_at"]),
                active_until=_parse_datetime(raw["active_until"]),
                cooldown_until=_parse_datetime(raw["cooldown_until"]),
                metrics=CascadeMetricsSnapshot.from_dict(raw.get("metrics", {})),
                trigger_count=int(raw.get("trigger_count", 1) or 1),
                distribution_cap_multiplier=int(
                    raw.get("distribution_cap_multiplier", DEFAULT_DISTRIBUTION_CAP_MULTIPLIER)
                    or DEFAULT_DISTRIBUTION_CAP_MULTIPLIER
                ),
                feed_injection_targets=tuple(raw.get("feed_injection_targets", ()) or ()),
                pinned_in_trending=bool(raw.get("pinned_in_trending", True)),
                match_id=raw.get("match_id"),
                highlight_id=raw.get("highlight_id"),
                title=raw.get("title"),
                metadata_json=dict(raw.get("metadata", {}) or {}),
            )
        except (KeyError, TypeError, ValueError):
            return None


@dataclass(frozen=True, slots=True)
class ViralCascadeEvaluation:
    status: str
    metrics: CascadeMetricsSnapshot
    record: ViralCascadeRecord | None = None
    triggered: bool = False

    @property
    def active(self) -> bool:
        return self.status == "active" and self.record is not None


class ViralCascadeStore(Protocol):
    def get(self, clip_id: str) -> ViralCascadeRecord | None:
        ...

    def upsert(self, record: ViralCascadeRecord) -> None:
        ...

    def list(self) -> list[ViralCascadeRecord]:
        ...


@dataclass(slots=True)
class InMemoryViralCascadeStore:
    _records: dict[str, ViralCascadeRecord] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def get(self, clip_id: str) -> ViralCascadeRecord | None:
        with self._lock:
            return self._records.get(clip_id)

    def upsert(self, record: ViralCascadeRecord) -> None:
        with self._lock:
            self._records[record.clip_id] = record

    def list(self) -> list[ViralCascadeRecord]:
        with self._lock:
            return list(self._records.values())


@dataclass(slots=True)
class RedisViralCascadeStore:
    redis_url: str
    index_key: str = CASCADE_INDEX_KEY
    history_retention: timedelta = DEFAULT_HISTORY_RETENTION
    _client: Redis = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False

    def get(self, clip_id: str) -> ViralCascadeRecord | None:
        try:
            payload = self._client.get(cascade_state_key(clip_id))
        except RedisError:
            return None
        if payload is None:
            return None
        return ViralCascadeRecord.from_json(payload)

    def upsert(self, record: ViralCascadeRecord) -> None:
        now = _utcnow()
        active_ttl_seconds = max(1, int((record.active_until - now).total_seconds()))
        history_ttl_seconds = max(1, int((record.cooldown_until - now + self.history_retention).total_seconds()))
        try:
            pipeline = self._client.pipeline()
            pipeline.set(name=cascade_flag_key(record.clip_id), value="true", ex=active_ttl_seconds)
            pipeline.set(name=cascade_state_key(record.clip_id), value=record.to_json(), ex=history_ttl_seconds)
            pipeline.sadd(self.index_key, record.clip_id)
            pipeline.execute()
        except RedisError:
            return None

    def list(self) -> list[ViralCascadeRecord]:
        try:
            clip_ids = list(self._client.smembers(self.index_key))
        except RedisError:
            return []
        records: list[ViralCascadeRecord] = []
        stale_ids: list[str] = []
        for clip_id in clip_ids:
            record = self.get(clip_id)
            if record is None:
                stale_ids.append(clip_id)
                continue
            records.append(record)
        if stale_ids:
            try:
                self._client.srem(self.index_key, *stale_ids)
            except RedisError:
                pass
        return records


@dataclass(slots=True)
class ViralCascadeEngine:
    store: ViralCascadeStore
    active_window: timedelta = DEFAULT_ACTIVE_WINDOW
    cooldown_window: timedelta = DEFAULT_COOLDOWN_WINDOW
    distribution_cap_multiplier: int = DEFAULT_DISTRIBUTION_CAP_MULTIPLIER
    feed_injection_bonus: float = DEFAULT_FEED_INJECTION_BONUS
    velocity_threshold: float = DEFAULT_VELOCITY_THRESHOLD
    completion_rate_threshold: float = DEFAULT_COMPLETION_RATE_THRESHOLD
    share_rate_threshold: float = DEFAULT_SHARE_RATE_THRESHOLD
    retrigger_velocity_delta: float = DEFAULT_RETRIGGER_VELOCITY_DELTA
    retrigger_growth_factor: float = DEFAULT_RETRIGGER_GROWTH_FACTOR

    def evaluate_candidate(
        self,
        candidate: ViralCascadeCandidate,
        *,
        now: datetime | None = None,
    ) -> ViralCascadeEvaluation:
        resolved_now = _normalize_datetime(now)
        metrics = self._metrics_snapshot(candidate.analytics)
        existing = self.store.get(candidate.clip_id)

        if existing is not None:
            existing_status = existing.status(now=resolved_now)
            if existing_status == "active":
                return ViralCascadeEvaluation(status="active", metrics=metrics, record=existing)
            if existing_status == "cooldown":
                return ViralCascadeEvaluation(status="cooldown", metrics=metrics, record=existing)

        if not self._thresholds_met(metrics):
            return ViralCascadeEvaluation(status="inactive", metrics=metrics)

        if existing is not None and not self._allow_retrigger(existing=existing, metrics=metrics):
            return ViralCascadeEvaluation(status="inactive", metrics=metrics, record=existing)

        record = ViralCascadeRecord(
            clip_id=candidate.clip_id,
            match_id=candidate.match_id,
            highlight_id=candidate.highlight_id,
            title=candidate.title,
            triggered_at=resolved_now,
            active_until=resolved_now + self.active_window,
            cooldown_until=resolved_now + self.cooldown_window,
            metrics=metrics,
            trigger_count=(existing.trigger_count + 1) if existing is not None else 1,
            distribution_cap_multiplier=self.distribution_cap_multiplier,
            feed_injection_targets=("for_you_feed", "following_feed", "discover_feed"),
            pinned_in_trending=True,
            metadata_json=dict(candidate.metadata),
        )
        self.store.upsert(record)
        return ViralCascadeEvaluation(
            status="active",
            metrics=metrics,
            record=record,
            triggered=True,
        )

    def apply_to_clip(
        self,
        clip,
        *,
        now: datetime | None = None,
    ):
        evaluation = self.evaluate_candidate(
            ViralCascadeCandidate(
                clip_id=str(clip.clip_id),
                match_id=getattr(clip, "match_id", None),
                highlight_id=getattr(clip, "highlight_id", None),
                title=getattr(clip, "title", None),
                analytics=clip.analytics.model_dump(),
                metadata=dict(getattr(clip, "metadata", {}) or {}),
            ),
            now=now,
        )
        metadata = dict(getattr(clip, "metadata", {}) or {})
        if evaluation.record is not None:
            cascade_payload = evaluation.record.as_dict(now=_normalize_datetime(now))
            cascade_payload["triggered"] = evaluation.triggered
            cascade_payload["feed_injection_bonus"] = round(self.feed_injection_bonus, 2)
            if evaluation.active:
                cascade_payload["base_ranking_score"] = round(float(getattr(clip, "ranking_score", 0.0) or 0.0), 2)
            metadata["cascade"] = cascade_payload
        if not evaluation.active:
            return clip.model_copy(update={"metadata": metadata})

        ranking_score = round(float(getattr(clip, "ranking_score", 0.0) or 0.0) + self.feed_injection_bonus, 2)
        tags = list(dict.fromkeys([*list(getattr(clip, "tags", []) or []), "cascade"]))
        return clip.model_copy(
            update={
                "ranking_score": ranking_score,
                "tags": tags,
                "metadata": metadata,
            }
        )

    def list_cascades(
        self,
        *,
        limit: int = 50,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        resolved_now = _normalize_datetime(now)
        records = [
            record
            for record in self.store.list()
            if record.status(now=resolved_now) in {"active", "cooldown"}
        ]
        records.sort(
            key=lambda item: (
                0 if item.status(now=resolved_now) == "active" else 1,
                -item.triggered_at.timestamp(),
                item.clip_id,
            )
        )
        return [record.as_dict(now=resolved_now) for record in records[: max(1, int(limit))]]

    def _thresholds_met(self, metrics: CascadeMetricsSnapshot) -> bool:
        return (
            metrics.velocity > self.velocity_threshold
            and metrics.completion_rate > self.completion_rate_threshold
            and metrics.share_rate > self.share_rate_threshold
        )

    def _allow_retrigger(self, *, existing: ViralCascadeRecord, metrics: CascadeMetricsSnapshot) -> bool:
        velocity_growth = metrics.velocity >= (existing.metrics.velocity + self.retrigger_velocity_delta)
        view_growth = (
            metrics.views_last_10min >= max(
                int(round(existing.metrics.views_last_10min * self.retrigger_growth_factor)),
                existing.metrics.views_last_10min + 10,
            )
            or metrics.views_last_60min >= max(
                int(round(existing.metrics.views_last_60min * self.retrigger_growth_factor)),
                existing.metrics.views_last_60min + 25,
            )
        )
        return velocity_growth or view_growth

    def _metrics_snapshot(self, analytics: Mapping[str, Any]) -> CascadeMetricsSnapshot:
        view_count = max(_as_int(analytics.get("view_count", analytics.get("views", 0))), 0)
        views_last_10min = max(_as_int(analytics.get("views_last_10min", 0)), 0)
        views_last_60min = max(_as_int(analytics.get("views_last_60min", 0)), 0)
        completion_rate = _bounded_ratio(
            analytics.get(
                "completion_rate",
                _safe_divide(_as_float(analytics.get("completions", 0.0)), max(view_count, 1)),
            )
        )
        share_rate = _bounded_ratio(
            analytics.get(
                "share_rate",
                _safe_divide(_as_float(analytics.get("shares", 0.0)), max(view_count, 1)),
            )
        )
        velocity = _safe_divide(float(views_last_10min), float(views_last_60min))
        return CascadeMetricsSnapshot(
            velocity=round(velocity, 4),
            completion_rate=completion_rate,
            share_rate=share_rate,
            views_last_10min=views_last_10min,
            views_last_60min=views_last_60min,
            view_count=view_count,
        )


def build_viral_cascade_store(*, settings: Settings | None = None) -> ViralCascadeStore:
    resolved_settings = settings or get_settings()
    if resolved_settings.redis_url:
        store = RedisViralCascadeStore(resolved_settings.redis_url)
        if store.ping():
            return store
    return InMemoryViralCascadeStore()


def ensure_viral_cascade_store(app: FastAPI, *, settings: Settings | None = None) -> ViralCascadeStore:
    store = getattr(app.state, "viral_cascade_store", None)
    if store is None:
        store = build_viral_cascade_store(settings=settings or getattr(app.state, "settings", None))
        app.state.viral_cascade_store = store
    return store


def ensure_viral_cascade_engine(app: FastAPI, *, settings: Settings | None = None) -> ViralCascadeEngine:
    engine = getattr(app.state, "viral_cascade_engine", None)
    if engine is None:
        engine = ViralCascadeEngine(
            store=ensure_viral_cascade_store(app, settings=settings or getattr(app.state, "settings", None))
        )
        app.state.viral_cascade_engine = engine
    return engine


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return _normalize_datetime(value)
    if not isinstance(value, str):
        raise ValueError("Expected ISO datetime string.")
    return _normalize_datetime(datetime.fromisoformat(value))


def _normalize_datetime(value: datetime | None) -> datetime:
    resolved = value or _utcnow()
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=UTC)
    return resolved.astimezone(UTC)


def _as_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(float(numerator), 0.0) / float(denominator)


def _bounded_ratio(value: object) -> float:
    numeric = _as_float(value)
    if 1.0 < numeric <= 100.0:
        numeric = numeric / 100.0
    return round(max(0.0, min(numeric, 1.0)), 4)


__all__ = [
    "CascadeMetricsSnapshot",
    "InMemoryViralCascadeStore",
    "RedisViralCascadeStore",
    "ViralCascadeCandidate",
    "ViralCascadeEngine",
    "ViralCascadeEvaluation",
    "ViralCascadeRecord",
    "ViralCascadeStore",
    "build_viral_cascade_store",
    "cascade_flag_key",
    "cascade_state_key",
    "ensure_viral_cascade_engine",
    "ensure_viral_cascade_store",
]
