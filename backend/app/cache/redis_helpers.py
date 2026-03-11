from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Protocol

from redis import Redis
from redis.exceptions import RedisError

from backend.app.ingestion.cache_keys import (
    CACHE_TTLS,
    club_cache_keys,
    club_roster_snapshot_key,
    competition_cache_keys,
    competition_table_key,
    player_cache_keys,
    player_profile_summary_key,
    top_prospects_key,
    trending_players_key,
)
from backend.app.ingestion.constants import ENV_REDIS_URL

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        ...

    def delete_many(self, keys: list[str]) -> None:
        ...

    def ping(self) -> bool:
        ...


class NullCacheBackend:
    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    def delete_many(self, keys: list[str]) -> None:
        return None

    def ping(self) -> bool:
        return False


class RedisCacheBackend:
    def __init__(self, redis_url: str):
        self.client = Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> str | None:
        try:
            return self.client.get(key)
        except RedisError:
            logger.warning("cache.get.failed", extra={"key": key})
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self.client.set(name=key, value=value, ex=ttl_seconds)
        except RedisError:
            logger.warning("cache.set.failed", extra={"key": key, "ttl_seconds": ttl_seconds})

    def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return
        try:
            self.client.delete(*keys)
        except RedisError:
            logger.warning("cache.delete.failed", extra={"key_count": len(keys)})

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisError:
            logger.warning("cache.ping.failed")
            return False


def build_cache_backend(redis_url: str | None = None) -> CacheBackend:
    resolved_url = redis_url or os.getenv(ENV_REDIS_URL)
    if not resolved_url:
        return NullCacheBackend()
    try:
        backend = RedisCacheBackend(resolved_url)
        if backend.ping():
            return backend
        return NullCacheBackend()
    except Exception:
        logger.warning("cache.backend.fallback", extra={"redis_url_present": True})
        return NullCacheBackend()


class HotReadCache:
    def __init__(self, backend: CacheBackend | None = None):
        self.backend = backend or NullCacheBackend()

    def get_top_prospects(self, scope: str = "global") -> dict[str, Any] | None:
        return self._get_json(top_prospects_key(scope))

    def set_top_prospects(self, payload: dict[str, Any], scope: str = "global") -> None:
        self._set_json(top_prospects_key(scope), payload, CACHE_TTLS["top_prospects"])

    def get_player_profile_summary(self, player_id: str) -> dict[str, Any] | None:
        return self._get_json(player_profile_summary_key(player_id))

    def set_player_profile_summary(self, player_id: str, payload: dict[str, Any]) -> None:
        self._set_json(player_profile_summary_key(player_id), payload, CACHE_TTLS["player_profile_summary"])

    def get_trending_players(self, scope: str = "global") -> dict[str, Any] | None:
        return self._get_json(trending_players_key(scope))

    def set_trending_players(self, payload: dict[str, Any], scope: str = "global") -> None:
        self._set_json(trending_players_key(scope), payload, CACHE_TTLS["trending_players"])

    def get_competition_table(self, competition_id: str, season_id: str | None = None) -> dict[str, Any] | None:
        return self._get_json(competition_table_key(competition_id, season_id))

    def set_competition_table(self, competition_id: str, payload: dict[str, Any], season_id: str | None = None) -> None:
        self._set_json(
            competition_table_key(competition_id, season_id),
            payload,
            CACHE_TTLS["competition_table"],
        )

    def get_club_roster_snapshot(self, club_id: str, season_id: str | None = None) -> dict[str, Any] | None:
        return self._get_json(club_roster_snapshot_key(club_id, season_id))

    def set_club_roster_snapshot(self, club_id: str, payload: dict[str, Any], season_id: str | None = None) -> None:
        self._set_json(
            club_roster_snapshot_key(club_id, season_id),
            payload,
            CACHE_TTLS["club_roster_snapshot"],
        )

    def invalidate(
        self,
        *,
        competition_ids: set[str] | None = None,
        club_ids: set[str] | None = None,
        player_ids: set[str] | None = None,
        season_id: str | None = None,
    ) -> None:
        keys: list[str] = []
        for competition_id in sorted(competition_ids or set()):
            keys.extend(competition_cache_keys(competition_id, season_id))
        for club_id in sorted(club_ids or set()):
            keys.extend(club_cache_keys(club_id, season_id))
        for player_id in sorted(player_ids or set()):
            keys.extend(player_cache_keys(player_id))
        self.backend.delete_many(keys)

    def _get_json(self, key: str) -> dict[str, Any] | None:
        value = self.backend.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("cache.decode.failed", extra={"key": key})
            return None

    def _set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        envelope = {"payload": payload, "cached_at": datetime.now(timezone.utc).isoformat()}
        self.backend.set(key, json.dumps(envelope, default=str), ttl_seconds)
