from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.cache import CacheBackend, JsonCacheNamespace, NullCacheBackend


@dataclass(slots=True, frozen=True)
class CommentaryBudget:
    call_allowed: bool
    used_calls: int
    remaining_calls: int
    max_calls: int

    def as_payload(self) -> dict[str, Any]:
        return {
            "call_allowed": self.call_allowed,
            "used_calls": self.used_calls,
            "remaining_calls": self.remaining_calls,
            "max_calls": self.max_calls,
            "exhausted": self.remaining_calls <= 0,
        }


@dataclass(slots=True)
class CommentaryCostGuard:
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    max_calls_per_match: int = 30
    ttl_seconds: int = 21_600
    _local: dict[str, int] = field(default_factory=dict)
    _cache: JsonCacheNamespace = field(init=False)

    def __post_init__(self) -> None:
        self._cache = JsonCacheNamespace(self.cache_backend)

    def configure(
        self,
        *,
        cache_backend: CacheBackend | None = None,
        max_calls_per_match: int | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        if cache_backend is not None:
            self.cache_backend = cache_backend
        if max_calls_per_match is not None:
            self.max_calls_per_match = max(int(max_calls_per_match), 0)
        if ttl_seconds is not None:
            self.ttl_seconds = max(int(ttl_seconds), 60)
        self._cache = JsonCacheNamespace(self.cache_backend)

    def snapshot(self, match_id: str) -> CommentaryBudget:
        used_calls = self._load_count(match_id)
        max_calls = max(self.max_calls_per_match, 0)
        remaining_calls = max(max_calls - used_calls, 0)
        return CommentaryBudget(
            call_allowed=used_calls < max_calls,
            used_calls=used_calls,
            remaining_calls=remaining_calls,
            max_calls=max_calls,
        )

    def reserve_call(self, match_id: str) -> CommentaryBudget:
        budget = self.snapshot(match_id)
        if not budget.call_allowed:
            return budget
        used_calls = budget.used_calls + 1
        self._save_count(match_id, used_calls)
        return CommentaryBudget(
            call_allowed=True,
            used_calls=used_calls,
            remaining_calls=max(self.max_calls_per_match - used_calls, 0),
            max_calls=max(self.max_calls_per_match, 0),
        )

    def reset(self, match_id: str) -> None:
        self._local.pop(match_id, None)
        self.cache_backend.delete_many([self._key(match_id)])

    def _load_count(self, match_id: str) -> int:
        cached = self._local.get(match_id)
        if cached is not None:
            return cached
        envelope = self._cache.get_json(self._key(match_id))
        payload = envelope.get("payload") if isinstance(envelope, dict) else None
        used_calls = int(dict(payload or {}).get("used_calls") or 0)
        self._local[match_id] = used_calls
        return used_calls

    def _save_count(self, match_id: str, used_calls: int) -> None:
        self._local[match_id] = used_calls
        self._cache.set_json(
            self._key(match_id),
            {"used_calls": used_calls},
            ttl_seconds=max(self.ttl_seconds, 60),
        )

    @staticmethod
    def _key(match_id: str) -> str:
        return f"live-commentary:llm-usage:{match_id}"


__all__ = ["CommentaryBudget", "CommentaryCostGuard"]
