from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
from threading import RLock
from time import monotonic, sleep, time
from typing import Iterator
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_LOCK_TTL_SECONDS = 15
DEFAULT_WAIT_TIMEOUT_SECONDS = 5.0
DEFAULT_RETRY_INTERVAL_SECONDS = 0.05


class _InMemoryLockRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._locks: dict[str, tuple[str, float]] = {}

    @contextmanager
    def acquire(
        self,
        key: str,
        *,
        ttl_seconds: int,
        wait_timeout_seconds: float,
        retry_interval_seconds: float,
    ) -> Iterator[bool]:
        token = uuid4().hex
        deadline = monotonic() + max(wait_timeout_seconds, 0.0)
        acquired = False
        while monotonic() <= deadline:
            with self._lock:
                self._purge_expired()
                if key not in self._locks:
                    self._locks[key] = (token, time() + max(ttl_seconds, 1))
                    acquired = True
                    break
            sleep(max(retry_interval_seconds, 0.01))
        try:
            yield acquired
        finally:
            if acquired:
                with self._lock:
                    current = self._locks.get(key)
                    if current is not None and current[0] == token:
                        self._locks.pop(key, None)

    def _purge_expired(self) -> None:
        now = time()
        expired_keys = [key for key, (_token, expires_at) in self._locks.items() if expires_at <= now]
        for key in expired_keys:
            self._locks.pop(key, None)


_MEMORY_LOCKS = _InMemoryLockRegistry()


@dataclass(slots=True)
class DistributedLockService:
    redis_url: str | None = None
    key_prefix: str = "gtex:lock"
    _client: Redis | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.redis_url:
            return
        try:
            self._client = Redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
        except RedisError:
            logger.warning("distributed_lock.redis.unavailable")
            self._client = None

    @contextmanager
    def acquire(
        self,
        key: str,
        *,
        ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
        retry_interval_seconds: float = DEFAULT_RETRY_INTERVAL_SECONDS,
    ) -> Iterator[bool]:
        namespaced_key = self._scoped_key(key)
        if self._client is None:
            with _MEMORY_LOCKS.acquire(
                namespaced_key,
                ttl_seconds=ttl_seconds,
                wait_timeout_seconds=wait_timeout_seconds,
                retry_interval_seconds=retry_interval_seconds,
            ) as acquired:
                yield acquired
            return

        token = uuid4().hex
        deadline = monotonic() + max(wait_timeout_seconds, 0.0)
        acquired = False
        while monotonic() <= deadline:
            try:
                acquired = bool(
                    self._client.set(
                        namespaced_key,
                        token,
                        nx=True,
                        ex=max(int(ttl_seconds), 1),
                    )
                )
            except RedisError:
                logger.warning("distributed_lock.redis.acquire_failed key=%s", namespaced_key)
                acquired = False
            if acquired:
                break
            sleep(max(retry_interval_seconds, 0.01))

        try:
            yield acquired
        finally:
            if acquired:
                assert self._client is not None
                try:
                    pipeline = self._client.pipeline(True)
                    while True:
                        try:
                            pipeline.watch(namespaced_key)
                            current = pipeline.get(namespaced_key)
                            if current == token:
                                pipeline.multi()
                                pipeline.delete(namespaced_key)
                                pipeline.execute()
                            break
                        except RedisError:
                            break
                        finally:
                            pipeline.reset()
                except RedisError:
                    logger.warning("distributed_lock.redis.release_failed key=%s", namespaced_key)

    def tournament_join_lock(
        self,
        tournament_id: str,
        *,
        ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> Iterator[bool]:
        return self.acquire(
            f"tournament:{tournament_id}:join",
            ttl_seconds=ttl_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    def tournament_state_lock(
        self,
        tournament_id: str,
        *,
        ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> Iterator[bool]:
        return self.acquire(
            f"tournament:{tournament_id}:state",
            ttl_seconds=ttl_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    def jackpot_trigger_lock(
        self,
        jackpot_key: str = "default",
        *,
        ttl_seconds: int = 30,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> Iterator[bool]:
        return self.acquire(
            f"jackpot:{jackpot_key}:trigger",
            ttl_seconds=ttl_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    def market_trade_lock(
        self,
        market_key: str,
        *,
        asset_key: str | None = None,
        ttl_seconds: int = 30,
        wait_timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    ) -> Iterator[bool]:
        resolved_asset_key = asset_key or "global"
        return self.acquire(
            f"market:{market_key}:trade:{resolved_asset_key}",
            ttl_seconds=ttl_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    def _scoped_key(self, key: str) -> str:
        prefix = self.key_prefix.strip(":")
        clean_key = key.strip(":")
        return f"{prefix}:{clean_key}" if prefix else clean_key


def build_distributed_lock_service(*, settings: Settings | None = None) -> DistributedLockService:
    resolved_settings = settings
    if resolved_settings is None:
        try:
            resolved_settings = get_settings()
        except Exception:
            resolved_settings = None
    return DistributedLockService(redis_url=(resolved_settings.redis_url if resolved_settings is not None else None))


__all__ = [
    "DistributedLockService",
    "build_distributed_lock_service",
]
