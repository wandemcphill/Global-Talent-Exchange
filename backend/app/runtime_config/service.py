from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import time
from typing import Any

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.analytics_event import AnalyticsEvent
from app.runtime_config.schemas import (
    AdFrequencyConfig,
    FeedWeightsConfig,
    RuntimeConfigSnapshot,
    RuntimeConfigUpdateRequest,
    TrustThresholdsConfig,
    ViralWeightsConfig,
)

RUNTIME_CONFIG_EVENT_NAME = "runtime_config.updated"
RUNTIME_CONFIG_CACHE_KEY = "runtime:config:latest"
DEFAULT_RUNTIME_REFRESH_SECONDS = 45


def default_runtime_config_snapshot() -> RuntimeConfigSnapshot:
    return RuntimeConfigSnapshot(
        viral_weights=ViralWeightsConfig(),
        feed_weights=FeedWeightsConfig(),
        trust_thresholds=TrustThresholdsConfig(),
        ad_frequency=AdFrequencyConfig(),
        ab_flags={},
        updated_at=None,
        source="defaults",
    )


@dataclass(slots=True)
class RuntimeConfigService:
    session: Session
    settings: Settings | None = None
    _redis: Redis | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        redis_url = self.settings.redis_url
        if not redis_url:
            return
        try:
            self._redis = Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
        except RedisError:
            self._redis = None

    def load_current(self) -> RuntimeConfigSnapshot:
        cached = self._load_from_cache()
        if cached is not None:
            return cached
        if self._has_analytics_table():
            stored = self._load_from_database()
            if stored is not None:
                self._persist_to_cache(stored)
                return stored
        return default_runtime_config_snapshot()

    def update(self, *, actor_id: str | None, payload: RuntimeConfigUpdateRequest) -> RuntimeConfigSnapshot:
        merged = self._merge_snapshot(self.load_current(), payload)
        if self._has_analytics_table():
            self.session.add(
                AnalyticsEvent(
                    name=RUNTIME_CONFIG_EVENT_NAME,
                    user_id=actor_id,
                    metadata_json={"config": merged.model_dump(mode="json")},
                )
            )
            self.session.flush()
        self._persist_to_cache(merged)
        return merged

    def _load_from_cache(self) -> RuntimeConfigSnapshot | None:
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(RUNTIME_CONFIG_CACHE_KEY)
        except RedisError:
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        try:
            return RuntimeConfigSnapshot.model_validate(payload)
        except Exception:
            return None

    def _load_from_database(self) -> RuntimeConfigSnapshot | None:
        if not self._has_analytics_table():
            return None
        event = self.session.scalar(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.name == RUNTIME_CONFIG_EVENT_NAME)
            .order_by(AnalyticsEvent.created_at.desc())
            .limit(1)
        )
        if event is None:
            return None
        payload = dict(event.metadata_json or {}).get("config")
        if not isinstance(payload, dict):
            return None
        try:
            return RuntimeConfigSnapshot.model_validate(payload)
        except Exception:
            return None

    def _persist_to_cache(self, snapshot: RuntimeConfigSnapshot) -> None:
        if self._redis is None:
            return
        try:
            self._redis.set(
                RUNTIME_CONFIG_CACHE_KEY,
                json.dumps(snapshot.model_dump(mode="json"), default=str),
                ex=DEFAULT_RUNTIME_REFRESH_SECONDS * 4,
            )
        except RedisError:
            return

    def _has_analytics_table(self) -> bool:
        bind = self.session.get_bind()
        if bind is None:
            return False
        try:
            return bool(inspect(bind).has_table(AnalyticsEvent.__tablename__))
        except Exception:
            return False

    @staticmethod
    def _merge_snapshot(
        current: RuntimeConfigSnapshot,
        payload: RuntimeConfigUpdateRequest,
    ) -> RuntimeConfigSnapshot:
        merged = current.model_copy(deep=True)
        update_data = payload.model_dump(exclude_none=True)
        if "viral_weights" in update_data:
            merged.viral_weights = merged.viral_weights.model_copy(
                update=payload.viral_weights.model_dump(exclude_none=True)  # type: ignore[union-attr]
            )
        if "feed_weights" in update_data:
            merged.feed_weights = merged.feed_weights.model_copy(
                update=payload.feed_weights.model_dump(exclude_none=True)  # type: ignore[union-attr]
            )
        if "trust_thresholds" in update_data:
            merged.trust_thresholds = merged.trust_thresholds.model_copy(
                update=payload.trust_thresholds.model_dump(exclude_none=True)  # type: ignore[union-attr]
            )
        if "ad_frequency" in update_data:
            next_ad_frequency = merged.ad_frequency.model_copy(
                update=payload.ad_frequency.model_dump(exclude_none=True)  # type: ignore[union-attr]
            )
            if next_ad_frequency.max_interval < next_ad_frequency.min_interval:
                next_ad_frequency = next_ad_frequency.model_copy(
                    update={"max_interval": next_ad_frequency.min_interval}
                )
            merged.ad_frequency = next_ad_frequency
        if "ab_flags" in update_data:
            merged.ab_flags = dict(payload.ab_flags or {})
        merged.updated_at = datetime.now(UTC)
        merged.source = "db"
        return merged


@dataclass(slots=True)
class RuntimeConfigLoader:
    app: FastAPI
    refresh_interval_seconds: int = DEFAULT_RUNTIME_REFRESH_SECONDS
    _snapshot: RuntimeConfigSnapshot | None = field(default=None, init=False, repr=False)
    _loaded_at_monotonic: float = field(default=0.0, init=False, repr=False)

    def get_snapshot(self, *, force_refresh: bool = False) -> RuntimeConfigSnapshot:
        if not force_refresh and self._snapshot is not None:
            if (time.monotonic() - self._loaded_at_monotonic) < max(self.refresh_interval_seconds, 1):
                return self._snapshot
        self._snapshot = self._load_snapshot()
        self._loaded_at_monotonic = time.monotonic()
        return self._snapshot

    def _load_snapshot(self) -> RuntimeConfigSnapshot:
        session_factory = getattr(self.app.state, "session_factory", None)
        if session_factory is None:
            return default_runtime_config_snapshot()
        with session_factory() as session:
            return RuntimeConfigService(
                session=session,
                settings=getattr(self.app.state, "settings", None),
            ).load_current()


def ensure_runtime_config_loader(
    app: FastAPI,
    *,
    refresh_interval_seconds: int = DEFAULT_RUNTIME_REFRESH_SECONDS,
) -> RuntimeConfigLoader:
    loader = getattr(app.state, "runtime_config_loader", None)
    if loader is None:
        loader = RuntimeConfigLoader(
            app=app,
            refresh_interval_seconds=refresh_interval_seconds,
        )
        app.state.runtime_config_loader = loader
    return loader


def resolve_runtime_config_snapshot(app: FastAPI | None) -> RuntimeConfigSnapshot:
    if app is None:
        return default_runtime_config_snapshot()
    return ensure_runtime_config_loader(app).get_snapshot()


__all__ = [
    "DEFAULT_RUNTIME_REFRESH_SECONDS",
    "RUNTIME_CONFIG_CACHE_KEY",
    "RUNTIME_CONFIG_EVENT_NAME",
    "RuntimeConfigLoader",
    "RuntimeConfigService",
    "default_runtime_config_snapshot",
    "ensure_runtime_config_loader",
    "resolve_runtime_config_snapshot",
]
