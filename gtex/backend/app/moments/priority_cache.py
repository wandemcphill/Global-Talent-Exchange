from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any


DEFAULT_MOMENT_PRIORITY_TTL_SECONDS = 45
DEFAULT_MOMENT_PRIORITY_LIMIT = 50


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class MomentPriorityEnvelope:
    clip_id: str
    score: float
    payload: dict[str, Any]
    inserted_at: datetime = field(default_factory=_utcnow)
    expires_at: datetime = field(default_factory=lambda: _utcnow() + timedelta(seconds=DEFAULT_MOMENT_PRIORITY_TTL_SECONDS))

    @property
    def expired(self) -> bool:
        return self.expires_at <= _utcnow()


@dataclass(slots=True)
class InMemoryMomentPriorityCache:
    ttl_seconds: int = DEFAULT_MOMENT_PRIORITY_TTL_SECONDS
    max_items: int = DEFAULT_MOMENT_PRIORITY_LIMIT
    _entries: dict[str, MomentPriorityEnvelope] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def put(self, *, clip_id: str, score: float, payload: dict[str, Any]) -> None:
        expires_at = _utcnow() + timedelta(seconds=max(int(self.ttl_seconds), 1))
        envelope = MomentPriorityEnvelope(
            clip_id=clip_id,
            score=float(score),
            payload=dict(payload),
            expires_at=expires_at,
        )
        with self._lock:
            self._prune_locked()
            self._entries[clip_id] = envelope
            if len(self._entries) > self.max_items:
                overflow = sorted(
                    self._entries.values(),
                    key=lambda item: (-item.score, -item.inserted_at.timestamp(), item.clip_id),
                )[self.max_items :]
                for item in overflow:
                    self._entries.pop(item.clip_id, None)

    def top(self, *, limit: int, excluded_clip_ids: set[str] | None = None) -> list[dict[str, Any]]:
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
            return [dict(item.payload) for item in ranked]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune_locked(self) -> None:
        expired_ids = [clip_id for clip_id, entry in self._entries.items() if entry.expired]
        for clip_id in expired_ids:
            self._entries.pop(clip_id, None)


def ensure_moment_priority_cache(app, *, ttl_seconds: int = DEFAULT_MOMENT_PRIORITY_TTL_SECONDS) -> InMemoryMomentPriorityCache:  # noqa: ANN001
    cache = getattr(app.state, "moment_priority_cache", None)
    if isinstance(cache, InMemoryMomentPriorityCache):
        return cache
    cache = InMemoryMomentPriorityCache(ttl_seconds=ttl_seconds)
    app.state.moment_priority_cache = cache
    return cache


__all__ = [
    "DEFAULT_MOMENT_PRIORITY_LIMIT",
    "DEFAULT_MOMENT_PRIORITY_TTL_SECONDS",
    "InMemoryMomentPriorityCache",
    "MomentPriorityEnvelope",
    "ensure_moment_priority_cache",
]
