from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any, Protocol

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings

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
    enabled = False

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    def delete_many(self, keys: list[str]) -> None:
        return None

    def ping(self) -> bool:
        return False


class RedisCacheBackend:
    enabled = True

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
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


def build_cache_backend(redis_url: str | None = None, *, settings: Settings | None = None) -> CacheBackend:
    resolved_settings = settings or get_settings()
    resolved_url = redis_url or resolved_settings.redis_url
    if not resolved_url:
        return NullCacheBackend()
    try:
        backend = RedisCacheBackend(resolved_url)
        if backend.ping():
            return backend
    except Exception:
        logger.warning("cache.backend.fallback", extra={"redis_url_present": True})
    return NullCacheBackend()


class JsonCacheNamespace:
    def __init__(self, backend: CacheBackend | None = None):
        self.backend = backend or NullCacheBackend()

    def get_json(self, key: str) -> dict[str, Any] | None:
        value = self.backend.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("cache.decode.failed", extra={"key": key})
            return None

    def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        envelope = {"payload": payload, "cached_at": datetime.now(timezone.utc).isoformat()}
        self.backend.set(key, json.dumps(envelope, default=str), ttl_seconds)
