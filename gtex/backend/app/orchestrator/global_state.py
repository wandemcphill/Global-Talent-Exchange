from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
from threading import Lock
from typing import Any, Protocol

from redis.exceptions import RedisError
from sqlalchemy import inspect
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, RedisCacheBackend, build_cache_backend
from app.core.config import Settings, get_settings
from app.core.database import (
    create_database_engine,
    create_read_database_engine,
    create_read_session_factory,
    create_session_factory,
    run_read_with_primary_fallback,
)
from app.models.scale_backbone import OrchestratorClipStateRecord, OrchestratorConfigRecord

logger = logging.getLogger(__name__)

TEST_STAGE = "test"
EXPAND_STAGE = "expand"
VIRAL_STAGE = "viral"
DECAY_STAGE = "decay"

GLOBAL_STATE_TTL_SECONDS = 604_800
GLOBAL_CLIP_INDEX_KEY = "orchestrator:clips"
GLOBAL_CONFIG_KEY = "orchestrator:config"

DEFAULT_TEST_IMPRESSIONS_CAP = 1_000
DEFAULT_EXPAND_MULTIPLIER = 3.0
DEFAULT_VIRAL_BASE_CAP = 9_000
DEFAULT_VIRAL_VELOCITY_CAP_MULTIPLIER = 6_000.0
DEFAULT_NEW_CLIP_MINIMUM_IMPRESSIONS = 200
DEFAULT_NEW_CLIP_AGE_HOURS = 12.0
DEFAULT_MOMENT_BOOST = 1.5
DEFAULT_EXPAND_THRESHOLD = 0.8
DEFAULT_VIRAL_THRESHOLD = 1.35
DEFAULT_DECAY_THRESHOLD = 0.2
DEFAULT_WINNER_SHARE = 0.70
DEFAULT_EXPLORATION_SHARE = 0.30
DEFAULT_MAX_AGENT_FEED_RATIO = 0.40
DEFAULT_MIN_HUMAN_EXPOSURE_GUARANTEE = 0.60


def clip_global_state_key(clip_id: str) -> str:
    return f"clip:{clip_id}:global"


def clip_global_consumed_key(clip_id: str) -> str:
    return f"clip:{clip_id}:global:consumed"


def clip_global_allocated_key(clip_id: str) -> str:
    return f"clip:{clip_id}:global:allocated"


@dataclass(frozen=True, slots=True)
class AttentionOrchestratorConfig:
    test_impressions_cap: int = DEFAULT_TEST_IMPRESSIONS_CAP
    expand_multiplier: float = DEFAULT_EXPAND_MULTIPLIER
    viral_base_cap: int = DEFAULT_VIRAL_BASE_CAP
    viral_velocity_cap_multiplier: float = DEFAULT_VIRAL_VELOCITY_CAP_MULTIPLIER
    new_clip_minimum_impressions: int = DEFAULT_NEW_CLIP_MINIMUM_IMPRESSIONS
    new_clip_age_hours: float = DEFAULT_NEW_CLIP_AGE_HOURS
    moment_boost: float = DEFAULT_MOMENT_BOOST
    expand_threshold: float = DEFAULT_EXPAND_THRESHOLD
    viral_threshold: float = DEFAULT_VIRAL_THRESHOLD
    decay_threshold: float = DEFAULT_DECAY_THRESHOLD
    winner_share: float = DEFAULT_WINNER_SHARE
    exploration_share: float = DEFAULT_EXPLORATION_SHARE
    max_agent_feed_ratio: float = DEFAULT_MAX_AGENT_FEED_RATIO
    min_human_exposure_guarantee: float = DEFAULT_MIN_HUMAN_EXPOSURE_GUARANTEE

    def as_payload(self) -> dict[str, Any]:
        return {
            "test_impressions_cap": max(int(self.test_impressions_cap), 1),
            "expand_multiplier": round(max(float(self.expand_multiplier), 1.0), 4),
            "viral_base_cap": max(int(self.viral_base_cap), 1),
            "viral_velocity_cap_multiplier": round(max(float(self.viral_velocity_cap_multiplier), 0.0), 4),
            "new_clip_minimum_impressions": max(int(self.new_clip_minimum_impressions), 0),
            "new_clip_age_hours": round(max(float(self.new_clip_age_hours), 0.0), 4),
            "moment_boost": round(max(float(self.moment_boost), 1.0), 4),
            "expand_threshold": round(max(float(self.expand_threshold), 0.0), 4),
            "viral_threshold": round(max(float(self.viral_threshold), 0.0), 4),
            "decay_threshold": round(max(float(self.decay_threshold), 0.0), 4),
            "winner_share": round(min(max(float(self.winner_share), 0.0), 1.0), 4),
            "exploration_share": round(min(max(float(self.exploration_share), 0.0), 1.0), 4),
            "max_agent_feed_ratio": round(min(max(float(self.max_agent_feed_ratio), 0.0), 1.0), 4),
            "min_human_exposure_guarantee": round(min(max(float(self.min_human_exposure_guarantee), 0.0), 1.0), 4),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "AttentionOrchestratorConfig":
        source = dict(payload or {})
        return cls(
            test_impressions_cap=max(_as_int(source.get("test_impressions_cap"), DEFAULT_TEST_IMPRESSIONS_CAP), 1),
            expand_multiplier=max(_as_float(source.get("expand_multiplier"), DEFAULT_EXPAND_MULTIPLIER), 1.0),
            viral_base_cap=max(_as_int(source.get("viral_base_cap"), DEFAULT_VIRAL_BASE_CAP), 1),
            viral_velocity_cap_multiplier=max(
                _as_float(source.get("viral_velocity_cap_multiplier"), DEFAULT_VIRAL_VELOCITY_CAP_MULTIPLIER),
                0.0,
            ),
            new_clip_minimum_impressions=max(
                _as_int(source.get("new_clip_minimum_impressions"), DEFAULT_NEW_CLIP_MINIMUM_IMPRESSIONS),
                0,
            ),
            new_clip_age_hours=max(_as_float(source.get("new_clip_age_hours"), DEFAULT_NEW_CLIP_AGE_HOURS), 0.0),
            moment_boost=max(_as_float(source.get("moment_boost"), DEFAULT_MOMENT_BOOST), 1.0),
            expand_threshold=max(_as_float(source.get("expand_threshold"), DEFAULT_EXPAND_THRESHOLD), 0.0),
            viral_threshold=max(_as_float(source.get("viral_threshold"), DEFAULT_VIRAL_THRESHOLD), 0.0),
            decay_threshold=max(_as_float(source.get("decay_threshold"), DEFAULT_DECAY_THRESHOLD), 0.0),
            winner_share=min(max(_as_float(source.get("winner_share"), DEFAULT_WINNER_SHARE), 0.0), 1.0),
            exploration_share=min(
                max(_as_float(source.get("exploration_share"), DEFAULT_EXPLORATION_SHARE), 0.0),
                1.0,
            ),
            max_agent_feed_ratio=min(
                max(_as_float(source.get("max_agent_feed_ratio"), DEFAULT_MAX_AGENT_FEED_RATIO), 0.0),
                1.0,
            ),
            min_human_exposure_guarantee=min(
                max(_as_float(source.get("min_human_exposure_guarantee"), DEFAULT_MIN_HUMAN_EXPOSURE_GUARANTEE), 0.0),
                1.0,
            ),
        )


@dataclass(slots=True)
class ClipGlobalState:
    clip_id: str
    stage: str = TEST_STAGE
    allocated_impressions: int = DEFAULT_TEST_IMPRESSIONS_CAP
    consumed_impressions: int = 0
    velocity_score: float = 1.0
    quality_score: float = 0.5
    trust_score: float = 1.0
    is_ad: bool = False
    is_moment: bool = False
    bid_weight: float = 1.0
    age_hours: float = 0.0
    base_clip_id: str | None = None
    winner_variant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_impressions(self) -> int:
        return max(int(self.allocated_impressions) - int(self.consumed_impressions), 0)

    @property
    def available(self) -> bool:
        return self.remaining_impressions > 0 and self.stage != DECAY_STAGE

    def as_payload(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "stage": self.stage,
            "allocated_impressions": max(int(self.allocated_impressions), 0),
            "consumed_impressions": max(int(self.consumed_impressions), 0),
            "velocity_score": round(max(float(self.velocity_score), 0.0), 6),
            "quality_score": round(min(max(float(self.quality_score), 0.0), 1.0), 6),
            "trust_score": round(min(max(float(self.trust_score), 0.0), 1.0), 6),
            "is_ad": bool(self.is_ad),
            "is_moment": bool(self.is_moment),
            "bid_weight": round(max(float(self.bid_weight), 0.0), 6),
            "age_hours": round(max(float(self.age_hours), 0.0), 6),
            "base_clip_id": self.base_clip_id,
            "winner_variant_id": self.winner_variant_id,
            "metadata": dict(self.metadata),
            "updated_at": self.updated_at.astimezone(UTC).isoformat(),
        }

    @classmethod
    def from_payload(cls, clip_id: str, payload: Mapping[str, Any]) -> "ClipGlobalState":
        raw_updated_at = payload.get("updated_at")
        updated_at = datetime.now(UTC)
        if isinstance(raw_updated_at, str):
            try:
                parsed = datetime.fromisoformat(raw_updated_at)
            except ValueError:
                parsed = None
            if parsed is not None:
                updated_at = parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        stage = str(payload.get("stage", TEST_STAGE) or TEST_STAGE).strip().lower()
        if stage not in {TEST_STAGE, EXPAND_STAGE, VIRAL_STAGE, DECAY_STAGE}:
            stage = TEST_STAGE
        metadata = payload.get("metadata")
        return cls(
            clip_id=clip_id,
            stage=stage,
            allocated_impressions=max(_as_int(payload.get("allocated_impressions"), DEFAULT_TEST_IMPRESSIONS_CAP), 0),
            consumed_impressions=max(_as_int(payload.get("consumed_impressions"), 0), 0),
            velocity_score=max(_as_float(payload.get("velocity_score"), 1.0), 0.0),
            quality_score=min(max(_as_float(payload.get("quality_score"), 0.5), 0.0), 1.0),
            trust_score=min(max(_as_float(payload.get("trust_score"), 1.0), 0.0), 1.0),
            is_ad=bool(payload.get("is_ad", False)),
            is_moment=bool(payload.get("is_moment", False)),
            bid_weight=max(_as_float(payload.get("bid_weight"), 1.0), 0.0),
            age_hours=max(_as_float(payload.get("age_hours"), 0.0), 0.0),
            base_clip_id=_as_optional_text(payload.get("base_clip_id")),
            winner_variant_id=_as_optional_text(payload.get("winner_variant_id")),
            metadata=dict(metadata) if isinstance(metadata, Mapping) else {},
            updated_at=updated_at,
        )


@dataclass(frozen=True, slots=True)
class ClipGlobalAllocation:
    state: ClipGlobalState
    allocated_count: int = 0

    @property
    def allocated(self) -> bool:
        return self.allocated_count > 0


class GlobalFeedStateStore(Protocol):
    def load_clip(self, clip_id: str) -> ClipGlobalState | None:
        ...

    def save_clip(self, state: ClipGlobalState) -> ClipGlobalState:
        ...

    def allocate_clip(self, clip_id: str, *, count: int = 1) -> ClipGlobalAllocation:
        ...

    def list_clips(self, *, limit: int | None = None) -> list[ClipGlobalState]:
        ...

    def load_config(self) -> AttentionOrchestratorConfig:
        ...

    def save_config(self, config: AttentionOrchestratorConfig) -> AttentionOrchestratorConfig:
        ...


@dataclass(slots=True)
class InMemoryGlobalFeedStateStore:
    _clips: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _config: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def load_clip(self, clip_id: str) -> ClipGlobalState | None:
        with self._lock:
            payload = self._clips.get(clip_id)
        if payload is None:
            return None
        return ClipGlobalState.from_payload(clip_id, payload)

    def save_clip(self, state: ClipGlobalState) -> ClipGlobalState:
        payload = state.as_payload()
        with self._lock:
            self._clips[state.clip_id] = payload
        return ClipGlobalState.from_payload(state.clip_id, payload)

    def allocate_clip(self, clip_id: str, *, count: int = 1) -> ClipGlobalAllocation:
        with self._lock:
            payload = self._clips.get(clip_id)
            if payload is None:
                raise KeyError(f"Global state for {clip_id} was not found.")
            state = ClipGlobalState.from_payload(clip_id, payload)
            if count <= 0 or state.consumed_impressions >= state.allocated_impressions or state.stage == DECAY_STAGE:
                return ClipGlobalAllocation(state=state, allocated_count=0)
            allocated_count = min(max(int(count), 0), state.remaining_impressions)
            state.consumed_impressions += allocated_count
            state.updated_at = datetime.now(UTC)
            self._clips[clip_id] = state.as_payload()
        return ClipGlobalAllocation(state=state, allocated_count=allocated_count)

    def list_clips(self, *, limit: int | None = None) -> list[ClipGlobalState]:
        with self._lock:
            values = list(self._clips.items())
        states = [ClipGlobalState.from_payload(clip_id, payload) for clip_id, payload in values]
        states.sort(key=lambda item: item.updated_at, reverse=True)
        if limit is None:
            return states
        return states[: max(int(limit), 0)]

    def load_config(self) -> AttentionOrchestratorConfig:
        with self._lock:
            payload = dict(self._config)
        return AttentionOrchestratorConfig.from_payload(payload)

    def save_config(self, config: AttentionOrchestratorConfig) -> AttentionOrchestratorConfig:
        payload = config.as_payload()
        with self._lock:
            self._config = payload
        return AttentionOrchestratorConfig.from_payload(payload)


@dataclass(slots=True)
class CacheGlobalFeedStateStore:
    backend: CacheBackend
    ttl_seconds: int = GLOBAL_STATE_TTL_SECONDS
    _redis_client: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.backend, RedisCacheBackend):
            self._redis_client = self.backend.client

    def load_clip(self, clip_id: str) -> ClipGlobalState | None:
        raw = self.backend.get(clip_global_state_key(clip_id))
        consumed_raw = self.backend.get(clip_global_consumed_key(clip_id))
        allocated_raw = self.backend.get(clip_global_allocated_key(clip_id))
        if raw is None and consumed_raw is None and allocated_raw is None:
            return None
        payload: dict[str, Any] = {}
        if raw is not None:
            try:
                decoded = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("orchestrator.global_state.decode_failed clip_id=%s", clip_id)
                decoded = {}
            if isinstance(decoded, dict):
                payload = decoded
        if consumed_raw is not None:
            payload["consumed_impressions"] = max(_as_int(consumed_raw, 0), 0)
        if allocated_raw is not None:
            payload["allocated_impressions"] = max(_as_int(allocated_raw, DEFAULT_TEST_IMPRESSIONS_CAP), 0)
        return ClipGlobalState.from_payload(clip_id, payload)

    def save_clip(self, state: ClipGlobalState) -> ClipGlobalState:
        payload = state.as_payload()
        serialized = json.dumps(payload, default=str)
        self.backend.set(clip_global_state_key(state.clip_id), serialized, self.ttl_seconds)
        self.backend.set(
            clip_global_consumed_key(state.clip_id),
            str(max(int(state.consumed_impressions), 0)),
            self.ttl_seconds,
        )
        self.backend.set(
            clip_global_allocated_key(state.clip_id),
            str(max(int(state.allocated_impressions), 0)),
            self.ttl_seconds,
        )
        if self._redis_client is not None:
            try:
                self._redis_client.sadd(GLOBAL_CLIP_INDEX_KEY, state.clip_id)
                self._redis_client.expire(GLOBAL_CLIP_INDEX_KEY, self.ttl_seconds)
            except RedisError:
                logger.warning("orchestrator.global_state.index_failed clip_id=%s", state.clip_id)
        return ClipGlobalState.from_payload(state.clip_id, payload)

    def allocate_clip(self, clip_id: str, *, count: int = 1) -> ClipGlobalAllocation:
        state = self.load_clip(clip_id)
        if state is None:
            raise KeyError(f"Global state for {clip_id} was not found.")
        if count <= 0:
            return ClipGlobalAllocation(state=state, allocated_count=0)
        if self._redis_client is None:
            if state.consumed_impressions >= state.allocated_impressions or state.stage == DECAY_STAGE:
                return ClipGlobalAllocation(state=state, allocated_count=0)
            allocated_count = min(max(int(count), 0), state.remaining_impressions)
            state.consumed_impressions += allocated_count
            state.updated_at = datetime.now(UTC)
            resolved = self.save_clip(state)
            return ClipGlobalAllocation(state=resolved, allocated_count=allocated_count)
        try:
            result = self._redis_client.eval(
                """
                local consumed_key = KEYS[1]
                local allocated_key = KEYS[2]
                local ttl = tonumber(ARGV[1])
                local increment = tonumber(ARGV[2])
                local current = tonumber(redis.call('GET', consumed_key) or '0')
                local cap = tonumber(redis.call('GET', allocated_key) or '0')
                if increment <= 0 or cap <= 0 or current >= cap then
                    if ttl and ttl > 0 then
                        redis.call('EXPIRE', consumed_key, ttl)
                        redis.call('EXPIRE', allocated_key, ttl)
                    end
                    return {current, cap, 0}
                end
                local new_value = redis.call('INCRBY', consumed_key, increment)
                local granted = increment
                if new_value > cap then
                    local overflow = new_value - cap
                    redis.call('DECRBY', consumed_key, overflow)
                    new_value = cap
                    granted = increment - overflow
                end
                if ttl and ttl > 0 then
                    redis.call('EXPIRE', consumed_key, ttl)
                    redis.call('EXPIRE', allocated_key, ttl)
                end
                return {new_value, cap, granted}
                """,
                2,
                clip_global_consumed_key(clip_id),
                clip_global_allocated_key(clip_id),
                self.ttl_seconds,
                int(count),
            )
        except RedisError:
            logger.warning("orchestrator.global_state.allocate_failed clip_id=%s", clip_id)
            return ClipGlobalAllocation(state=state, allocated_count=0)
        state.consumed_impressions = max(_as_int(result[0] if isinstance(result, list) and result else 0, 0), 0)
        state.allocated_impressions = max(
            _as_int(result[1] if isinstance(result, list) and len(result) > 1 else state.allocated_impressions, state.allocated_impressions),
            0,
        )
        state.updated_at = datetime.now(UTC)
        resolved = self.save_clip(state)
        allocated_count = max(
            _as_int(result[2] if isinstance(result, list) and len(result) > 2 else 0, 0),
            0,
        )
        return ClipGlobalAllocation(state=resolved, allocated_count=allocated_count)

    def list_clips(self, *, limit: int | None = None) -> list[ClipGlobalState]:
        if self._redis_client is None:
            return []
        clip_ids: list[str] = []
        try:
            for raw_clip_id in self._redis_client.sscan_iter(GLOBAL_CLIP_INDEX_KEY):
                clip_ids.append(str(raw_clip_id))
                if limit is not None and len(clip_ids) >= max(int(limit), 0):
                    break
        except RedisError:
            logger.warning("orchestrator.global_state.list_failed")
            return []
        states = [state for clip_id in clip_ids if (state := self.load_clip(clip_id)) is not None]
        states.sort(key=lambda item: item.updated_at, reverse=True)
        return states

    def load_config(self) -> AttentionOrchestratorConfig:
        raw = self.backend.get(GLOBAL_CONFIG_KEY)
        if raw is None:
            return AttentionOrchestratorConfig()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("orchestrator.config.decode_failed")
            payload = {}
        return AttentionOrchestratorConfig.from_payload(payload if isinstance(payload, dict) else {})

    def save_config(self, config: AttentionOrchestratorConfig) -> AttentionOrchestratorConfig:
        payload = config.as_payload()
        self.backend.set(GLOBAL_CONFIG_KEY, json.dumps(payload, default=str), self.ttl_seconds)
        return AttentionOrchestratorConfig.from_payload(payload)


@dataclass(slots=True)
class PersistentGlobalFeedStateStore:
    session_factory: sessionmaker[Session]
    read_session_factory: sessionmaker[Session] | None = None
    cache_store: CacheGlobalFeedStateStore | None = None

    def __post_init__(self) -> None:
        if self.read_session_factory is None:
            self.read_session_factory = self.session_factory

    def load_clip(self, clip_id: str) -> ClipGlobalState | None:
        if self.cache_store is not None:
            cached = self.cache_store.load_clip(clip_id)
            if cached is not None:
                return cached
        assert self.read_session_factory is not None
        state = run_read_with_primary_fallback(
            read_session_factory=self.read_session_factory,
            primary_session_factory=self.session_factory,
            operation_name="orchestrator.load_clip",
            fn=lambda session: self._load_clip_from_session(session, clip_id=clip_id),
        )
        if state is None:
            return None
        self._sync_cache(state)
        return state

    def save_clip(self, state: ClipGlobalState) -> ClipGlobalState:
        with self.session_factory() as session:
            record = session.get(OrchestratorClipStateRecord, state.clip_id)
            if record is None:
                record = OrchestratorClipStateRecord(clip_id=state.clip_id)
                session.add(record)
            self._apply_state(record, state)
            session.commit()
            session.refresh(record)
            resolved = self._state_from_record(record)
        self._sync_cache(resolved)
        return resolved

    def allocate_clip(self, clip_id: str, *, count: int = 1) -> ClipGlobalAllocation:
        with self.session_factory() as session:
            record = session.scalar(
                select(OrchestratorClipStateRecord)
                .where(OrchestratorClipStateRecord.clip_id == clip_id)
                .with_for_update()
            )
            if record is None:
                raise KeyError(f"Global state for {clip_id} was not found.")
            state = self._state_from_record(record)
            if count <= 0 or state.consumed_impressions >= state.allocated_impressions or state.stage == DECAY_STAGE:
                allocated_count = 0
            else:
                allocated_count = min(max(int(count), 0), state.remaining_impressions)
                state.consumed_impressions += allocated_count
                state.updated_at = datetime.now(UTC)
                self._apply_state(record, state)
            session.commit()
            session.refresh(record)
            resolved = self._state_from_record(record)
        self._sync_cache(resolved)
        return ClipGlobalAllocation(state=resolved, allocated_count=allocated_count)

    def list_clips(self, *, limit: int | None = None) -> list[ClipGlobalState]:
        assert self.read_session_factory is not None
        records = run_read_with_primary_fallback(
            read_session_factory=self.read_session_factory,
            primary_session_factory=self.session_factory,
            operation_name="orchestrator.list_clips",
            fn=lambda session: self._list_records(session, limit=limit),
        )
        states = [self._state_from_record(record) for record in records]
        for state in states:
            self._sync_cache(state)
        return states

    def load_config(self) -> AttentionOrchestratorConfig:
        assert self.read_session_factory is not None
        config = run_read_with_primary_fallback(
            read_session_factory=self.read_session_factory,
            primary_session_factory=self.session_factory,
            operation_name="orchestrator.load_config",
            fn=lambda session: self._load_config_from_session(session),
        )
        if self.cache_store is not None:
            self.cache_store.save_config(config)
        return config

    def save_config(self, config: AttentionOrchestratorConfig) -> AttentionOrchestratorConfig:
        payload = config.as_payload()
        with self.session_factory() as session:
            record = session.get(OrchestratorConfigRecord, GLOBAL_CONFIG_KEY)
            if record is None:
                record = OrchestratorConfigRecord(config_key=GLOBAL_CONFIG_KEY)
                session.add(record)
            record.payload_json = payload
            session.commit()
        resolved = AttentionOrchestratorConfig.from_payload(payload)
        if self.cache_store is not None:
            self.cache_store.save_config(resolved)
        return resolved

    def _sync_cache(self, state: ClipGlobalState) -> None:
        if self.cache_store is not None:
            self.cache_store.save_clip(state)

    @staticmethod
    def _state_from_record(record: OrchestratorClipStateRecord) -> ClipGlobalState:
        return ClipGlobalState(
            clip_id=record.clip_id,
            stage=str(record.stage or TEST_STAGE),
            allocated_impressions=max(int(record.allocated_impressions or 0), 0),
            consumed_impressions=max(int(record.consumed_impressions or 0), 0),
            velocity_score=max(float(record.velocity_score or 0.0), 0.0),
            quality_score=min(max(float(record.quality_score or 0.0), 0.0), 1.0),
            trust_score=min(max(float(record.trust_score or 0.0), 0.0), 1.0),
            is_ad=bool(record.is_ad),
            is_moment=bool(record.is_moment),
            bid_weight=max(float(record.bid_weight or 0.0), 0.0),
            age_hours=max(float(record.age_hours or 0.0), 0.0),
            base_clip_id=_as_optional_text(record.base_clip_id),
            winner_variant_id=_as_optional_text(record.winner_variant_id),
            metadata=dict(record.metadata_json or {}),
            updated_at=record.updated_at.astimezone(UTC) if record.updated_at.tzinfo is not None else record.updated_at.replace(tzinfo=UTC),
        )

    @staticmethod
    def _apply_state(record: OrchestratorClipStateRecord, state: ClipGlobalState) -> None:
        record.stage = str(state.stage or TEST_STAGE)
        record.allocated_impressions = max(int(state.allocated_impressions), 0)
        record.consumed_impressions = max(int(state.consumed_impressions), 0)
        record.velocity_score = max(float(state.velocity_score), 0.0)
        record.quality_score = min(max(float(state.quality_score), 0.0), 1.0)
        record.trust_score = min(max(float(state.trust_score), 0.0), 1.0)
        record.is_ad = bool(state.is_ad)
        record.is_moment = bool(state.is_moment)
        record.bid_weight = max(float(state.bid_weight), 0.0)
        record.age_hours = max(float(state.age_hours), 0.0)
        record.base_clip_id = _as_optional_text(state.base_clip_id)
        record.winner_variant_id = _as_optional_text(state.winner_variant_id)
        record.metadata_json = dict(state.metadata or {})
        record.updated_at = state.updated_at.astimezone(UTC)

    def _load_clip_from_session(self, session: Session, *, clip_id: str) -> ClipGlobalState | None:
        record = session.get(OrchestratorClipStateRecord, clip_id)
        if record is None:
            return None
        return self._state_from_record(record)

    def _list_records(self, session: Session, *, limit: int | None) -> list[OrchestratorClipStateRecord]:
        stmt = select(OrchestratorClipStateRecord).order_by(OrchestratorClipStateRecord.updated_at.desc())
        if limit is not None:
            stmt = stmt.limit(max(int(limit), 0))
        return list(session.scalars(stmt).all())

    @staticmethod
    def _load_config_from_session(session: Session) -> AttentionOrchestratorConfig:
        record = session.get(OrchestratorConfigRecord, GLOBAL_CONFIG_KEY)
        if record is None:
            return AttentionOrchestratorConfig()
        return AttentionOrchestratorConfig.from_payload(record.payload_json)


def build_global_feed_state_store(
    *,
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
    read_session_factory: sessionmaker[Session] | None = None,
    backend: CacheBackend | None = None,
) -> GlobalFeedStateStore:
    resolved_settings = settings or get_settings()
    resolved_session_factory = session_factory or create_session_factory(
        create_database_engine(resolved_settings.database_url)
    )
    resolved_read_session_factory = read_session_factory or create_read_session_factory(
        create_read_database_engine(resolved_settings.database_read_url)
    )
    resolved_backend = backend or build_cache_backend(settings=resolved_settings)
    bind = resolved_session_factory.kw.get("bind") if hasattr(resolved_session_factory, "kw") else None
    if bind is None or not _orchestrator_tables_available(bind):
        logger.warning("orchestrator.global_state.persistence_unavailable_falling_back_to_memory")
        return InMemoryGlobalFeedStateStore()
    return PersistentGlobalFeedStateStore(
        session_factory=resolved_session_factory,
        read_session_factory=resolved_read_session_factory,
        cache_store=CacheGlobalFeedStateStore(backend=resolved_backend),
    )


def _orchestrator_tables_available(bind: Any) -> bool:
    try:
        inspector = inspect(bind)
        return all(
            inspector.has_table(table_name)
            for table_name in (
                OrchestratorClipStateRecord.__tablename__,
                OrchestratorConfigRecord.__tablename__,
            )
        )
    except Exception:
        return False


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _as_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _as_optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


__all__ = [
    "AttentionOrchestratorConfig",
    "CacheGlobalFeedStateStore",
    "ClipGlobalAllocation",
    "ClipGlobalState",
    "DECAY_STAGE",
    "EXPAND_STAGE",
    "GLOBAL_STATE_TTL_SECONDS",
    "GlobalFeedStateStore",
    "InMemoryGlobalFeedStateStore",
    "TEST_STAGE",
    "VIRAL_STAGE",
    "build_global_feed_state_store",
    "clip_global_state_key",
]
