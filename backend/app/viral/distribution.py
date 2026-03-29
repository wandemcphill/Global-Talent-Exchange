from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
import logging
from threading import Lock
from typing import Any, Protocol

from fastapi import FastAPI
from app.core.cache import CacheBackend, NullCacheBackend, RedisCacheBackend, build_cache_backend
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

TEST_STAGE = "test"
EXPAND_STAGE = "expand"
VIRAL_STAGE = "viral"

_STAGE_ORDER = {
    TEST_STAGE: 1,
    EXPAND_STAGE: 2,
    VIRAL_STAGE: 3,
}
_STAGE_CAP_RANGES = {
    TEST_STAGE: (100, 500),
    EXPAND_STAGE: (1_000, 10_000),
    VIRAL_STAGE: (10_000, 1_000_000),
}

DEFAULT_DISTRIBUTION_TTL_SECONDS = 604_800
DEFAULT_EXPAND_THRESHOLD = 75.0
DEFAULT_VIRAL_THRESHOLD = 110.0
DEFAULT_VIRAL_SCORE_CEILING = 180.0
DEFAULT_MIN_IMPRESSIONS_BEFORE_FREEZE = 100
DEFAULT_FREEZE_COMPLETION_FLOOR = 0.42
DEFAULT_FREEZE_SHARE_FLOOR = 0.01
DEFAULT_FREEZE_SKIP_CEILING = 0.55
VIRAL_POOL_KEY = "viral_pool"
VIRAL_POOL_PAYLOAD_KEY = "viral_pool:payloads"
DEFAULT_VIRAL_POOL_TTL_SECONDS = 3_600
DEFAULT_VIRAL_POOL_MAX_ITEMS = 500
DEFAULT_VIRAL_POOL_BOOST_MULTIPLIER = 1.5


def distribution_cache_key(clip_id: str) -> str:
    return f"clip:{clip_id}:distribution"


def distribution_impressions_key(clip_id: str) -> str:
    return f"clip:{clip_id}:impressions_served"


def distribution_cap_key(clip_id: str) -> str:
    return f"clip:{clip_id}:impressions_cap"


def distribution_frozen_key(clip_id: str) -> str:
    return f"clip:{clip_id}:distribution_frozen"


def viral_pool_key() -> str:
    return VIRAL_POOL_KEY


def viral_pool_payload_key() -> str:
    return VIRAL_POOL_PAYLOAD_KEY


@dataclass(frozen=True, slots=True)
class ViralDispatchEnvelope:
    clip_id: str
    score: float
    payload: dict[str, Any]
    inserted_at: datetime
    expires_at: datetime

    @property
    def expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)


class ViralDispatchPoolStore(Protocol):
    def upsert(
        self,
        *,
        clip_id: str,
        score: float,
        payload: Mapping[str, Any] | None = None,
    ) -> ViralDispatchEnvelope:
        ...

    def top(
        self,
        *,
        limit: int,
        excluded_clip_ids: set[str] | None = None,
    ) -> list[ViralDispatchEnvelope]:
        ...

    def boost(
        self,
        clip_id: str,
        *,
        multiplier: float = DEFAULT_VIRAL_POOL_BOOST_MULTIPLIER,
    ) -> ViralDispatchEnvelope | None:
        ...

    def clear(self) -> None:
        ...


@dataclass(slots=True)
class InMemoryViralDispatchPoolStore:
    ttl_seconds: int = DEFAULT_VIRAL_POOL_TTL_SECONDS
    max_items: int = DEFAULT_VIRAL_POOL_MAX_ITEMS
    _entries: dict[str, ViralDispatchEnvelope] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def upsert(
        self,
        *,
        clip_id: str,
        score: float,
        payload: Mapping[str, Any] | None = None,
    ) -> ViralDispatchEnvelope:
        inserted_at = datetime.now(UTC)
        expires_at = inserted_at + timedelta(seconds=max(int(self.ttl_seconds), 1))
        envelope = _build_viral_dispatch_envelope(
            clip_id=clip_id,
            score=score,
            payload=payload,
            inserted_at=inserted_at,
            expires_at=expires_at,
        )
        with self._lock:
            self._prune_locked()
            self._entries[clip_id] = envelope
            self._trim_locked()
        return _clone_dispatch_envelope(envelope)

    def top(
        self,
        *,
        limit: int,
        excluded_clip_ids: set[str] | None = None,
    ) -> list[ViralDispatchEnvelope]:
        if limit <= 0:
            return []
        blocked = excluded_clip_ids or set()
        with self._lock:
            self._prune_locked()
            ranked = sorted(
                (
                    item
                    for item in self._entries.values()
                    if item.clip_id not in blocked
                ),
                key=lambda item: (-item.score, -item.inserted_at.timestamp(), item.clip_id),
            )[: max(int(limit), 0)]
        return [_clone_dispatch_envelope(item) for item in ranked]

    def boost(
        self,
        clip_id: str,
        *,
        multiplier: float = DEFAULT_VIRAL_POOL_BOOST_MULTIPLIER,
    ) -> ViralDispatchEnvelope | None:
        normalized_clip_id = str(clip_id or "").strip()
        if not normalized_clip_id:
            return None
        with self._lock:
            self._prune_locked()
            current = self._entries.get(normalized_clip_id)
            if current is None:
                return None
            expires_at = datetime.now(UTC) + timedelta(seconds=max(int(self.ttl_seconds), 1))
            boosted = _build_viral_dispatch_envelope(
                clip_id=current.clip_id,
                score=float(current.score) * max(float(multiplier), 1.0),
                payload=_pool_payload_seed(current.payload),
                inserted_at=current.inserted_at,
                expires_at=expires_at,
            )
            self._entries[normalized_clip_id] = boosted
            self._trim_locked()
        return _clone_dispatch_envelope(boosted)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune_locked(self) -> None:
        expired_ids = [clip_id for clip_id, entry in self._entries.items() if entry.expired]
        for clip_id in expired_ids:
            self._entries.pop(clip_id, None)

    def _trim_locked(self) -> None:
        if self.max_items <= 0 or len(self._entries) <= self.max_items:
            return
        overflow = sorted(
            self._entries.values(),
            key=lambda item: (-item.score, -item.inserted_at.timestamp(), item.clip_id),
        )[self.max_items :]
        for entry in overflow:
            self._entries.pop(entry.clip_id, None)


@dataclass(slots=True)
class RedisViralDispatchPoolStore:
    backend: RedisCacheBackend
    ttl_seconds: int = DEFAULT_VIRAL_POOL_TTL_SECONDS
    max_items: int = DEFAULT_VIRAL_POOL_MAX_ITEMS
    pool_key: str = VIRAL_POOL_KEY
    payload_key: str = VIRAL_POOL_PAYLOAD_KEY
    _redis_client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._redis_client = self.backend.client

    def upsert(
        self,
        *,
        clip_id: str,
        score: float,
        payload: Mapping[str, Any] | None = None,
    ) -> ViralDispatchEnvelope:
        inserted_at = datetime.now(UTC)
        expires_at = inserted_at + timedelta(seconds=max(int(self.ttl_seconds), 1))
        envelope = _build_viral_dispatch_envelope(
            clip_id=clip_id,
            score=score,
            payload=payload,
            inserted_at=inserted_at,
            expires_at=expires_at,
        )
        try:
            pipeline = self._redis_client.pipeline()
            pipeline.zadd(self.pool_key, {clip_id: float(envelope.score)})
            pipeline.hset(self.payload_key, mapping={clip_id: json.dumps(envelope.payload, default=str)})
            pipeline.expire(self.pool_key, max(int(self.ttl_seconds), 1))
            pipeline.expire(self.payload_key, max(int(self.ttl_seconds), 1))
            pipeline.execute()
            self._prune_expired()
            self._trim_overflow()
        except Exception:
            logger.warning("viral.pool.upsert_failed", extra={"clip_id": clip_id})
        return envelope

    def top(
        self,
        *,
        limit: int,
        excluded_clip_ids: set[str] | None = None,
    ) -> list[ViralDispatchEnvelope]:
        if limit <= 0:
            return []
        blocked = excluded_clip_ids or set()
        self._prune_expired()
        fetch_limit = max(int(limit), int(self.max_items), 1)
        try:
            ranked = self._redis_client.zrevrange(self.pool_key, 0, fetch_limit - 1, withscores=True)
            clip_ids = [clip_id for clip_id, _score in ranked]
            payloads = self._redis_client.hmget(self.payload_key, clip_ids) if clip_ids else []
        except Exception:
            logger.warning("viral.pool.read_failed", extra={"limit": limit})
            return []

        invalid_ids: list[str] = []
        envelopes: list[ViralDispatchEnvelope] = []
        for (clip_id, score), raw_payload in zip(ranked, payloads):
            if clip_id in blocked:
                continue
            payload = _json_payload(raw_payload)
            if payload is None:
                invalid_ids.append(clip_id)
                continue
            envelope = _dispatch_envelope_from_payload(clip_id=clip_id, score=score, payload=payload)
            if envelope.expired:
                invalid_ids.append(clip_id)
                continue
            envelopes.append(envelope)
            if len(envelopes) >= limit:
                break
        if invalid_ids:
            self._remove_clip_ids(invalid_ids)
        return envelopes

    def boost(
        self,
        clip_id: str,
        *,
        multiplier: float = DEFAULT_VIRAL_POOL_BOOST_MULTIPLIER,
    ) -> ViralDispatchEnvelope | None:
        normalized_clip_id = str(clip_id or "").strip()
        if not normalized_clip_id:
            return None
        self._prune_expired()
        try:
            current_score = self._redis_client.zscore(self.pool_key, normalized_clip_id)
            raw_payload = self._redis_client.hget(self.payload_key, normalized_clip_id)
        except Exception:
            logger.warning("viral.pool.boost_failed", extra={"clip_id": normalized_clip_id})
            return None
        if current_score is None:
            return None
        payload = _json_payload(raw_payload)
        if payload is None:
            self._remove_clip_ids([normalized_clip_id])
            return None
        existing = _dispatch_envelope_from_payload(
            clip_id=normalized_clip_id,
            score=current_score,
            payload=payload,
        )
        refreshed = _build_viral_dispatch_envelope(
            clip_id=existing.clip_id,
            score=float(existing.score) * max(float(multiplier), 1.0),
            payload=_pool_payload_seed(existing.payload),
            inserted_at=existing.inserted_at,
            expires_at=datetime.now(UTC) + timedelta(seconds=max(int(self.ttl_seconds), 1)),
        )
        try:
            pipeline = self._redis_client.pipeline()
            pipeline.zadd(self.pool_key, {normalized_clip_id: float(refreshed.score)})
            pipeline.hset(self.payload_key, mapping={normalized_clip_id: json.dumps(refreshed.payload, default=str)})
            pipeline.expire(self.pool_key, max(int(self.ttl_seconds), 1))
            pipeline.expire(self.payload_key, max(int(self.ttl_seconds), 1))
            pipeline.execute()
        except Exception:
            logger.warning("viral.pool.boost_failed", extra={"clip_id": normalized_clip_id})
            return None
        return refreshed

    def clear(self) -> None:
        try:
            self._redis_client.delete(self.pool_key, self.payload_key)
        except Exception:
            logger.warning("viral.pool.clear_failed")

    def _prune_expired(self) -> None:
        try:
            clip_ids = self._redis_client.zrange(self.pool_key, 0, -1)
            payloads = self._redis_client.hmget(self.payload_key, clip_ids) if clip_ids else []
        except Exception:
            logger.warning("viral.pool.prune_failed")
            return
        expired_ids: list[str] = []
        for clip_id, raw_payload in zip(clip_ids, payloads):
            payload = _json_payload(raw_payload)
            if payload is None:
                expired_ids.append(clip_id)
                continue
            envelope = _dispatch_envelope_from_payload(clip_id=clip_id, score=0.0, payload=payload)
            if envelope.expired:
                expired_ids.append(clip_id)
        if expired_ids:
            self._remove_clip_ids(expired_ids)

    def _trim_overflow(self) -> None:
        if self.max_items <= 0:
            return
        try:
            entry_count = int(self._redis_client.zcard(self.pool_key) or 0)
        except Exception:
            logger.warning("viral.pool.trim_failed")
            return
        overflow = entry_count - self.max_items
        if overflow <= 0:
            return
        try:
            clip_ids = self._redis_client.zrange(self.pool_key, 0, overflow - 1)
        except Exception:
            logger.warning("viral.pool.trim_failed")
            return
        if clip_ids:
            self._remove_clip_ids(list(clip_ids))

    def _remove_clip_ids(self, clip_ids: list[str]) -> None:
        if not clip_ids:
            return
        try:
            pipeline = self._redis_client.pipeline()
            pipeline.zrem(self.pool_key, *clip_ids)
            pipeline.hdel(self.payload_key, *clip_ids)
            pipeline.execute()
        except Exception:
            logger.warning("viral.pool.remove_failed", extra={"clip_count": len(clip_ids)})


@dataclass(slots=True)
class ClipDistributionState:
    clip_id: str
    impressions_served: int = 0
    impressions_cap: int = 100
    expansion_stage: str = TEST_STAGE
    frozen: bool = False
    freeze_reason: str | None = None
    last_viral_score: float = 0.0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_impressions(self) -> int:
        return max(int(self.impressions_cap) - int(self.impressions_served), 0)

    @property
    def eligible(self) -> bool:
        return not self.frozen and self.remaining_impressions > 0

    def as_payload(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "impressions_served": int(self.impressions_served),
            "impressions_cap": int(self.impressions_cap),
            "expansion_stage": self.expansion_stage,
            "frozen": bool(self.frozen),
            "freeze_reason": self.freeze_reason,
            "last_viral_score": round(float(self.last_viral_score), 2),
            "updated_at": self.updated_at.astimezone(UTC).isoformat(),
        }

    @classmethod
    def from_payload(cls, clip_id: str, payload: Mapping[str, Any]) -> "ClipDistributionState":
        raw_updated_at = payload.get("updated_at")
        updated_at = datetime.now(UTC)
        if isinstance(raw_updated_at, str):
            try:
                parsed = datetime.fromisoformat(raw_updated_at)
            except ValueError:
                parsed = None
            if parsed is not None:
                updated_at = parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        return cls(
            clip_id=clip_id,
            impressions_served=max(int(payload.get("impressions_served", 0) or 0), 0),
            impressions_cap=max(int(payload.get("impressions_cap", 100) or 100), 1),
            expansion_stage=str(payload.get("expansion_stage", TEST_STAGE) or TEST_STAGE),
            frozen=bool(payload.get("frozen", False)),
            freeze_reason=str(payload.get("freeze_reason")) if payload.get("freeze_reason") is not None else None,
            last_viral_score=float(payload.get("last_viral_score", 0.0) or 0.0),
            updated_at=updated_at,
        )


@dataclass(frozen=True, slots=True)
class ClipDistributionAllocation:
    state: ClipDistributionState
    allocated_count: int = 0

    @property
    def allocated(self) -> bool:
        return self.allocated_count > 0


class ClipDistributionStore(Protocol):
    def load(self, clip_id: str) -> ClipDistributionState | None:
        ...

    def save(self, state: ClipDistributionState) -> ClipDistributionState:
        ...

    def allocate(self, clip_id: str, *, count: int = 1) -> ClipDistributionAllocation:
        ...


@dataclass(slots=True)
class InMemoryClipDistributionStore:
    _entries: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def load(self, clip_id: str) -> ClipDistributionState | None:
        with self._lock:
            payload = self._entries.get(clip_id)
        if payload is None:
            return None
        return ClipDistributionState.from_payload(clip_id, payload)

    def save(self, state: ClipDistributionState) -> ClipDistributionState:
        payload = state.as_payload()
        with self._lock:
            self._entries[state.clip_id] = payload
        return ClipDistributionState.from_payload(state.clip_id, payload)

    def allocate(self, clip_id: str, *, count: int = 1) -> ClipDistributionAllocation:
        if count <= 0:
            state = self.load(clip_id)
            if state is None:
                raise KeyError(f"Distribution state for {clip_id} was not found.")
            return ClipDistributionAllocation(state=state, allocated_count=0)
        with self._lock:
            payload = self._entries.get(clip_id)
            if payload is None:
                raise KeyError(f"Distribution state for {clip_id} was not found.")
            state = ClipDistributionState.from_payload(clip_id, payload)
            if state.frozen or state.impressions_served >= state.impressions_cap:
                return ClipDistributionAllocation(state=state, allocated_count=0)
            allocated_count = min(max(int(count), 0), state.remaining_impressions)
            state.impressions_served += allocated_count
            state.updated_at = datetime.now(UTC)
            self._entries[clip_id] = state.as_payload()
        return ClipDistributionAllocation(state=state, allocated_count=allocated_count)


@dataclass(slots=True)
class CacheClipDistributionStore:
    backend: CacheBackend
    ttl_seconds: int = DEFAULT_DISTRIBUTION_TTL_SECONDS
    _redis_client: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.backend, RedisCacheBackend):
            self._redis_client = self.backend.client

    def load(self, clip_id: str) -> ClipDistributionState | None:
        raw = self.backend.get(distribution_cache_key(clip_id))
        served_raw = self.backend.get(distribution_impressions_key(clip_id))
        cap_raw = self.backend.get(distribution_cap_key(clip_id))
        frozen_raw = self.backend.get(distribution_frozen_key(clip_id))
        if raw is None and served_raw is None and cap_raw is None and frozen_raw is None:
            return None
        payload: dict[str, Any] = {}
        if raw is not None:
            try:
                decoded = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("viral.distribution.decode_failed", extra={"clip_id": clip_id})
                decoded = {}
            if isinstance(decoded, dict):
                payload = decoded
        if served_raw is not None:
            try:
                payload["impressions_served"] = max(int(served_raw), 0)
            except (TypeError, ValueError):
                pass
        if cap_raw is not None:
            try:
                payload["impressions_cap"] = max(int(cap_raw), 1)
            except (TypeError, ValueError):
                pass
        if frozen_raw is not None:
            payload["frozen"] = str(frozen_raw).strip() == "1"
            if payload["frozen"] and payload.get("freeze_reason") is None:
                payload["freeze_reason"] = "distribution_frozen"
        return ClipDistributionState.from_payload(clip_id, payload)

    def save(self, state: ClipDistributionState) -> ClipDistributionState:
        resolved_state = self._save_state(state)
        self._persist_payload_only(resolved_state)
        return resolved_state

    def allocate(self, clip_id: str, *, count: int = 1) -> ClipDistributionAllocation:
        state = self.load(clip_id)
        if state is None:
            raise KeyError(f"Distribution state for {clip_id} was not found.")
        if count <= 0:
            return ClipDistributionAllocation(state=state, allocated_count=0)
        if self._redis_client is None:
            if state.frozen or state.impressions_served >= state.impressions_cap:
                return ClipDistributionAllocation(state=state, allocated_count=0)
            allocated_count = min(max(int(count), 0), state.remaining_impressions)
            state.impressions_served += allocated_count
            state.updated_at = datetime.now(UTC)
            resolved_state = self.save(state)
            return ClipDistributionAllocation(state=resolved_state, allocated_count=allocated_count)
        try:
            result = self._redis_client.eval(
                """
                local served_key = KEYS[1]
                local cap_key = KEYS[2]
                local frozen_key = KEYS[3]
                local ttl = tonumber(ARGV[1])
                local increment = tonumber(ARGV[2])
                local default_cap = tonumber(ARGV[3])
                local served = tonumber(redis.call('GET', served_key) or '0')
                local cap = tonumber(redis.call('GET', cap_key) or tostring(default_cap))
                local frozen = redis.call('GET', frozen_key)
                if increment <= 0 or frozen == '1' or served >= cap then
                    if ttl and ttl > 0 then
                        redis.call('EXPIRE', served_key, ttl)
                        redis.call('EXPIRE', cap_key, ttl)
                        redis.call('EXPIRE', frozen_key, ttl)
                    end
                    return {served, cap, frozen == '1' and 1 or 0, 0}
                end
                local new_served = redis.call('INCRBY', served_key, increment)
                local allocated = increment
                if new_served > cap then
                    local overflow = new_served - cap
                    redis.call('DECRBY', served_key, overflow)
                    new_served = cap
                    allocated = increment - overflow
                end
                if allocated < 0 then
                    allocated = 0
                end
                if ttl and ttl > 0 then
                    redis.call('EXPIRE', served_key, ttl)
                    redis.call('EXPIRE', cap_key, ttl)
                    redis.call('EXPIRE', frozen_key, ttl)
                end
                return {new_served, cap, frozen == '1' and 1 or 0, allocated}
                """,
                3,
                distribution_impressions_key(clip_id),
                distribution_cap_key(clip_id),
                distribution_frozen_key(clip_id),
                self.ttl_seconds,
                int(count),
                int(state.impressions_cap),
            )
        except Exception:
            logger.warning("viral.distribution.allocate_failed", extra={"clip_id": clip_id})
            return ClipDistributionAllocation(state=state, allocated_count=0)
        new_served = _coerce_int(result[0] if isinstance(result, list) and len(result) > 0 else state.impressions_served)
        new_cap = max(_coerce_int(result[1] if isinstance(result, list) and len(result) > 1 else state.impressions_cap), 1)
        is_frozen = _coerce_int(result[2] if isinstance(result, list) and len(result) > 2 else int(state.frozen)) == 1
        allocated_count = max(_coerce_int(result[3] if isinstance(result, list) and len(result) > 3 else 0), 0)
        resolved_state = state.model_copy() if hasattr(state, "model_copy") else ClipDistributionState.from_payload(clip_id, state.as_payload())
        resolved_state.impressions_served = new_served
        resolved_state.impressions_cap = new_cap
        resolved_state.frozen = is_frozen
        resolved_state.updated_at = datetime.now(UTC)
        self._persist_payload_only(resolved_state)
        return ClipDistributionAllocation(state=resolved_state, allocated_count=allocated_count)

    def _save_state(self, state: ClipDistributionState) -> ClipDistributionState:
        if self._redis_client is None:
            payload = state.as_payload()
            self.backend.set(distribution_cache_key(state.clip_id), json.dumps(payload, default=str), self.ttl_seconds)
            self.backend.set(distribution_impressions_key(state.clip_id), str(max(int(state.impressions_served), 0)), self.ttl_seconds)
            self.backend.set(distribution_cap_key(state.clip_id), str(max(int(state.impressions_cap), 1)), self.ttl_seconds)
            self.backend.set(distribution_frozen_key(state.clip_id), "1" if state.frozen else "0", self.ttl_seconds)
            return ClipDistributionState.from_payload(state.clip_id, payload)
        try:
            current_served = self._redis_client.eval(
                """
                local served_key = KEYS[1]
                local cap_key = KEYS[2]
                local frozen_key = KEYS[3]
                local ttl = tonumber(ARGV[1])
                local requested_served = tonumber(ARGV[2])
                local requested_cap = tonumber(ARGV[3])
                local frozen = tonumber(ARGV[4])
                local existing_served = tonumber(redis.call('GET', served_key) or '0')
                local resolved_served = existing_served
                if requested_served > existing_served then
                    resolved_served = requested_served
                end
                redis.call('SET', served_key, resolved_served, 'EX', ttl)
                redis.call('SET', cap_key, requested_cap, 'EX', ttl)
                redis.call('SET', frozen_key, frozen, 'EX', ttl)
                return resolved_served
                """,
                3,
                distribution_impressions_key(state.clip_id),
                distribution_cap_key(state.clip_id),
                distribution_frozen_key(state.clip_id),
                self.ttl_seconds,
                max(int(state.impressions_served), 0),
                max(int(state.impressions_cap), 1),
                1 if state.frozen else 0,
            )
        except Exception:
            logger.warning("viral.distribution.save_failed", extra={"clip_id": state.clip_id})
            payload = state.as_payload()
            self.backend.set(distribution_cache_key(state.clip_id), json.dumps(payload, default=str), self.ttl_seconds)
            return ClipDistributionState.from_payload(state.clip_id, payload)
        resolved = ClipDistributionState.from_payload(state.clip_id, state.as_payload())
        resolved.impressions_served = max(_coerce_int(current_served), 0)
        resolved.impressions_cap = max(int(state.impressions_cap), 1)
        resolved.updated_at = datetime.now(UTC)
        return resolved

    def _persist_payload_only(self, state: ClipDistributionState) -> None:
        self.backend.set(
            distribution_cache_key(state.clip_id),
            json.dumps(state.as_payload(), default=str),
            self.ttl_seconds,
        )


_SHARED_IN_MEMORY_STORE = InMemoryClipDistributionStore()
_SHARED_IN_MEMORY_VIRAL_POOL_STORE = InMemoryViralDispatchPoolStore()


def build_viral_dispatch_pool_store(
    *,
    settings: Settings | None = None,
    backend: CacheBackend | None = None,
    ttl_seconds: int = DEFAULT_VIRAL_POOL_TTL_SECONDS,
    max_items: int = DEFAULT_VIRAL_POOL_MAX_ITEMS,
) -> ViralDispatchPoolStore:
    resolved_backend = backend or build_cache_backend(settings=settings)
    if isinstance(resolved_backend, RedisCacheBackend) and getattr(resolved_backend, "enabled", False):
        return RedisViralDispatchPoolStore(
            backend=resolved_backend,
            ttl_seconds=ttl_seconds,
            max_items=max_items,
        )
    if ttl_seconds != DEFAULT_VIRAL_POOL_TTL_SECONDS or max_items != DEFAULT_VIRAL_POOL_MAX_ITEMS:
        return InMemoryViralDispatchPoolStore(ttl_seconds=ttl_seconds, max_items=max_items)
    return _SHARED_IN_MEMORY_VIRAL_POOL_STORE


def ensure_viral_dispatch_pool_store(
    app: FastAPI,
    *,
    settings: Settings | None = None,
) -> ViralDispatchPoolStore:
    store = getattr(app.state, "viral_dispatch_pool_store", None)
    if store is None:
        store = build_viral_dispatch_pool_store(settings=settings or getattr(app.state, "settings", None))
        app.state.viral_dispatch_pool_store = store
    return store


def inject_into_distribution_pool(
    clip_id: str,
    score: float,
    payload: Mapping[str, Any] | None = None,
    *,
    store: ViralDispatchPoolStore | None = None,
    settings: Settings | None = None,
    backend: CacheBackend | None = None,
) -> ViralDispatchEnvelope:
    normalized_clip_id = str(clip_id or "").strip()
    if not normalized_clip_id:
        raise ValueError("clip_id is required to inject a clip into the viral distribution pool.")
    resolved_store = store or build_viral_dispatch_pool_store(settings=settings, backend=backend)
    return resolved_store.upsert(
        clip_id=normalized_clip_id,
        score=float(score),
        payload=payload,
    )


def read_distribution_pool(
    limit: int,
    excluded_clip_ids: set[str] | None = None,
    *,
    store: ViralDispatchPoolStore | None = None,
    settings: Settings | None = None,
    backend: CacheBackend | None = None,
) -> list[dict[str, Any]]:
    resolved_store = store or build_viral_dispatch_pool_store(settings=settings, backend=backend)
    return [
        dict(entry.payload)
        for entry in resolved_store.top(
            limit=max(int(limit), 0),
            excluded_clip_ids=excluded_clip_ids,
        )
    ]


def boost_distribution(
    clip_id: str,
    multiplier: float = DEFAULT_VIRAL_POOL_BOOST_MULTIPLIER,
    *,
    store: ViralDispatchPoolStore | None = None,
    settings: Settings | None = None,
    backend: CacheBackend | None = None,
) -> ViralDispatchEnvelope | None:
    normalized_clip_id = str(clip_id or "").strip()
    if not normalized_clip_id:
        return None
    resolved_store = store or build_viral_dispatch_pool_store(settings=settings, backend=backend)
    return resolved_store.boost(
        normalized_clip_id,
        multiplier=max(float(multiplier), 1.0),
    )


def build_clip_distribution_store(
    *,
    settings: Settings | None = None,
    backend: CacheBackend | None = None,
    ttl_seconds: int = DEFAULT_DISTRIBUTION_TTL_SECONDS,
) -> ClipDistributionStore:
    resolved_backend = backend or build_cache_backend(settings=settings)
    if isinstance(resolved_backend, NullCacheBackend) or not getattr(resolved_backend, "enabled", False):
        return _SHARED_IN_MEMORY_STORE
    return CacheClipDistributionStore(backend=resolved_backend, ttl_seconds=ttl_seconds)


@dataclass(slots=True)
class ClipDistributionManager:
    store: ClipDistributionStore
    expand_threshold: float = DEFAULT_EXPAND_THRESHOLD
    viral_threshold: float = DEFAULT_VIRAL_THRESHOLD
    viral_score_ceiling: float = DEFAULT_VIRAL_SCORE_CEILING
    min_impressions_before_freeze: int = DEFAULT_MIN_IMPRESSIONS_BEFORE_FREEZE
    freeze_completion_floor: float = DEFAULT_FREEZE_COMPLETION_FLOOR
    freeze_share_floor: float = DEFAULT_FREEZE_SHARE_FLOOR
    freeze_skip_ceiling: float = DEFAULT_FREEZE_SKIP_CEILING

    def refresh_distribution(
        self,
        *,
        clip_id: str,
        viral_score: float,
        analytics: Mapping[str, Any],
        performance_tier: str | None = None,
        clip_source: str | None = None,
        cap_multiplier: int = 1,
        cap_boost: float = 1.0,
        minimum_cap: int = 0,
    ) -> ClipDistributionState:
        state = self.store.load(clip_id) or ClipDistributionState(clip_id=clip_id)
        prior_stage = state.expansion_stage
        target_stage = self._target_stage(viral_score)
        if _STAGE_ORDER[target_stage] > _STAGE_ORDER.get(prior_stage, 0):
            state.expansion_stage = target_stage
        stage_promoted = state.expansion_stage != prior_stage

        target_cap = round(
            self._cap_for_stage(state.expansion_stage, viral_score)
            * max(int(cap_multiplier or 1), 1)
            * max(float(cap_boost or 1.0), 1.0)
        )
        if str(clip_source or "").strip().lower() == "moment":
            target_cap *= 2
        minimum_cap_value = int(max(minimum_cap, 0))
        current_cap = int(state.impressions_cap)
        if current_cap <= 0:
            state.impressions_cap = max(int(target_cap), minimum_cap_value, 1)
        elif (
            stage_promoted
            or int(cap_multiplier or 1) > 1
            or float(cap_boost or 1.0) > 1.0
            or minimum_cap_value > current_cap
        ):
            state.impressions_cap = max(current_cap, int(target_cap), minimum_cap_value)
        else:
            state.impressions_cap = max(current_cap, minimum_cap_value)
        state.last_viral_score = round(float(viral_score), 2)

        if self._viral_score_drop(state=state, viral_score=viral_score):
            state.frozen = True
            state.freeze_reason = "viral_score_drop"
            state.impressions_cap = max(int(state.impressions_served), 1)
        elif self._performance_drop(
            impressions_served=state.impressions_served,
            analytics=analytics,
            performance_tier=performance_tier,
        ):
            state.frozen = True
            state.freeze_reason = "performance_drop"
        elif state.freeze_reason == "viral_score_drop" and state.impressions_cap <= state.impressions_served:
            state.frozen = True
        else:
            state.frozen = False
            state.freeze_reason = None

        state.updated_at = datetime.now(UTC)
        return self.store.save(state)

    def allocate_impressions(self, clip_id: str, *, count: int = 1) -> ClipDistributionAllocation:
        return self.store.allocate(clip_id, count=count)

    @staticmethod
    def distribution_key(clip_id: str) -> str:
        return distribution_cache_key(clip_id)

    @staticmethod
    def is_eligible(state: ClipDistributionState) -> bool:
        return state.eligible

    def _viral_score_drop(self, *, state: ClipDistributionState, viral_score: float) -> bool:
        score = max(float(viral_score), 0.0)
        if state.expansion_stage == VIRAL_STAGE:
            return score < self.viral_threshold
        if state.expansion_stage == EXPAND_STAGE:
            return score < self.expand_threshold
        return False

    def _target_stage(self, viral_score: float) -> str:
        score = max(float(viral_score), 0.0)
        if score >= self.viral_threshold:
            return VIRAL_STAGE
        if score >= self.expand_threshold:
            return EXPAND_STAGE
        return TEST_STAGE

    def _cap_for_stage(self, stage: str, viral_score: float) -> int:
        lower, upper = _STAGE_CAP_RANGES.get(stage, _STAGE_CAP_RANGES[TEST_STAGE])
        if stage == TEST_STAGE:
            progress = self._progress(viral_score, floor=0.0, ceiling=self.expand_threshold)
        elif stage == EXPAND_STAGE:
            progress = self._progress(
                viral_score,
                floor=self.expand_threshold,
                ceiling=self.viral_threshold,
            )
        else:
            progress = self._progress(
                viral_score,
                floor=self.viral_threshold,
                ceiling=max(self.viral_score_ceiling, self.viral_threshold + 1.0),
            )
        return max(lower, min(upper, int(round(lower + ((upper - lower) * progress)))))

    def _progress(self, viral_score: float, *, floor: float, ceiling: float) -> float:
        score = max(float(viral_score), 0.0)
        if ceiling <= floor:
            return 1.0
        return max(0.0, min((score - floor) / (ceiling - floor), 1.0))

    def _performance_drop(
        self,
        *,
        impressions_served: int,
        analytics: Mapping[str, Any],
        performance_tier: str | None,
    ) -> bool:
        if impressions_served < self.min_impressions_before_freeze:
            return False
        if (performance_tier or "").strip().lower() == "retention_risk":
            return True

        completion_rate = self._as_float(analytics.get("completion_rate"), default=0.0)
        share_rate = self._as_float(analytics.get("share_rate"), default=0.0)
        view_count = max(int(self._as_float(analytics.get("view_count"), default=0.0)), 0)
        skips = max(int(self._as_float(analytics.get("skips"), default=0.0)), 0)
        skip_rate = (skips / view_count) if view_count > 0 else 0.0
        return (
            completion_rate <= self.freeze_completion_floor
            and share_rate <= self.freeze_share_floor
            and skip_rate >= self.freeze_skip_ceiling
        )

    @staticmethod
    def _as_float(value: object, *, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


def _build_viral_dispatch_envelope(
    *,
    clip_id: str,
    score: float,
    payload: Mapping[str, Any] | None,
    inserted_at: datetime,
    expires_at: datetime,
) -> ViralDispatchEnvelope:
    normalized_payload = _pool_payload_seed(payload)
    metadata = dict(normalized_payload.get("metadata") or {})
    metadata["viral_pool_inserted_at"] = inserted_at.astimezone(UTC).isoformat()
    metadata["viral_pool_expires_at"] = expires_at.astimezone(UTC).isoformat()
    metadata["viral_pool_score"] = round(float(score), 6)
    normalized_payload["clip_id"] = str(normalized_payload.get("clip_id") or clip_id).strip() or clip_id
    normalized_payload["metadata"] = metadata
    normalized_payload["inserted_at"] = inserted_at.astimezone(UTC).isoformat()
    normalized_payload["expires_at"] = expires_at.astimezone(UTC).isoformat()
    normalized_payload["pool_score"] = round(float(score), 6)
    return ViralDispatchEnvelope(
        clip_id=clip_id,
        score=round(float(score), 6),
        payload=normalized_payload,
        inserted_at=inserted_at.astimezone(UTC),
        expires_at=expires_at.astimezone(UTC),
    )


def _dispatch_envelope_from_payload(
    *,
    clip_id: str,
    score: float,
    payload: Mapping[str, Any],
) -> ViralDispatchEnvelope:
    inserted_at = _coerce_datetime(
        payload.get("inserted_at"),
        default=_coerce_datetime(
            dict(payload.get("metadata") or {}).get("viral_pool_inserted_at"),
            default=datetime.now(UTC),
        ),
    )
    expires_at = _coerce_datetime(
        payload.get("expires_at"),
        default=_coerce_datetime(
            dict(payload.get("metadata") or {}).get("viral_pool_expires_at"),
            default=inserted_at + timedelta(seconds=DEFAULT_VIRAL_POOL_TTL_SECONDS),
        ),
    )
    return ViralDispatchEnvelope(
        clip_id=clip_id,
        score=round(float(score), 6),
        payload=dict(payload),
        inserted_at=inserted_at,
        expires_at=expires_at,
    )


def _clone_dispatch_envelope(envelope: ViralDispatchEnvelope) -> ViralDispatchEnvelope:
    return ViralDispatchEnvelope(
        clip_id=envelope.clip_id,
        score=float(envelope.score),
        payload=dict(envelope.payload),
        inserted_at=envelope.inserted_at,
        expires_at=envelope.expires_at,
    )


def _pool_payload_seed(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = dict(payload or {})
    normalized.pop("inserted_at", None)
    normalized.pop("expires_at", None)
    normalized.pop("pool_score", None)
    metadata = dict(normalized.get("metadata") or {})
    metadata.pop("viral_pool_inserted_at", None)
    metadata.pop("viral_pool_expires_at", None)
    metadata.pop("viral_pool_score", None)
    if metadata:
        normalized["metadata"] = metadata
    elif "metadata" in normalized:
        normalized["metadata"] = {}
    return normalized


def _json_payload(raw_payload: object) -> dict[str, Any] | None:
    if raw_payload is None:
        return None
    if isinstance(raw_payload, dict):
        return dict(raw_payload)
    if not isinstance(raw_payload, str):
        return None
    try:
        decoded = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _coerce_datetime(value: object, *, default: datetime) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return default
        return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return default


def _coerce_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_clip_distribution_manager(
    *,
    settings: Settings | None = None,
    backend: CacheBackend | None = None,
) -> ClipDistributionManager:
    resolved_settings = settings or get_settings()
    return ClipDistributionManager(
        store=build_clip_distribution_store(settings=resolved_settings, backend=backend),
    )


__all__ = [
    "DEFAULT_VIRAL_POOL_BOOST_MULTIPLIER",
    "DEFAULT_VIRAL_POOL_MAX_ITEMS",
    "DEFAULT_VIRAL_POOL_TTL_SECONDS",
    "CacheClipDistributionStore",
    "ClipDistributionAllocation",
    "ClipDistributionManager",
    "ClipDistributionState",
    "EXPAND_STAGE",
    "InMemoryClipDistributionStore",
    "InMemoryViralDispatchPoolStore",
    "RedisViralDispatchPoolStore",
    "TEST_STAGE",
    "VIRAL_STAGE",
    "ViralDispatchEnvelope",
    "ViralDispatchPoolStore",
    "build_clip_distribution_manager",
    "build_clip_distribution_store",
    "build_viral_dispatch_pool_store",
    "boost_distribution",
    "distribution_cap_key",
    "distribution_cache_key",
    "distribution_frozen_key",
    "distribution_impressions_key",
    "ensure_viral_dispatch_pool_store",
    "inject_into_distribution_pool",
    "read_distribution_pool",
    "viral_pool_key",
    "viral_pool_payload_key",
]
