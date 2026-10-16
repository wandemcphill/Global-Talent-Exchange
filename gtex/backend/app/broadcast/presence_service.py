from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

from app.broadcast.broadcast_models import SpectatorPresenceView


@dataclass(slots=True)
class _LocalPresenceState:
    expires_at_by_connection: dict[str, float] = field(default_factory=dict)
    user_id_by_connection: dict[str, str] = field(default_factory=dict)
    peak_viewers: int = 0


@dataclass(slots=True)
class PresenceService:
    redis_url: str | None = None
    prefix: str = "gtex:broadcast:presence"
    viewer_ttl_seconds: int = 45
    _redis: redis_asyncio.Redis | None = field(init=False, default=None)
    _local_presence: dict[str, _LocalPresenceState] = field(init=False, default_factory=dict)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    async def register_viewer(self, match_id: str, connection_id: str, user_id: str | None = None) -> SpectatorPresenceView:
        return await self._upsert_viewer(match_id=match_id, connection_id=connection_id, user_id=user_id)

    async def heartbeat_viewer(self, match_id: str, connection_id: str, user_id: str | None = None) -> SpectatorPresenceView:
        return await self._upsert_viewer(match_id=match_id, connection_id=connection_id, user_id=user_id)

    async def unregister_viewer(self, match_id: str, connection_id: str) -> SpectatorPresenceView:
        redis = await self._get_redis()
        if redis is None:
            async with self._lock:
                state = self._local_presence.get(match_id)
                if state is not None:
                    state.expires_at_by_connection.pop(connection_id, None)
                    state.user_id_by_connection.pop(connection_id, None)
                return self._local_snapshot(match_id)

        active_key = self._active_key(match_id)
        pipe = redis.pipeline()
        pipe.zrem(active_key, connection_id)
        pipe.delete(self._viewer_key(match_id, connection_id))
        await pipe.execute()
        return await self.get_match_presence(match_id)

    async def get_match_presence(self, match_id: str) -> SpectatorPresenceView:
        redis = await self._get_redis()
        if redis is None:
            async with self._lock:
                return self._local_snapshot(match_id)

        active_connection_ids = await self._active_connection_ids(redis, match_id)
        user_ids = await self._active_user_ids(redis, match_id, active_connection_ids)
        peak_raw = await redis.get(self._peak_key(match_id))
        peak_viewers = int(peak_raw or 0)
        return SpectatorPresenceView(
            match_id=match_id,
            active_viewers=len(active_connection_ids),
            peak_viewers=max(peak_viewers, len(active_connection_ids)),
            active_user_ids=user_ids,
        )

    async def aclose(self) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.aclose()
        except RedisError:
            pass
        finally:
            self._redis = None

    async def _upsert_viewer(
        self,
        *,
        match_id: str,
        connection_id: str,
        user_id: str | None,
    ) -> SpectatorPresenceView:
        redis = await self._get_redis()
        if redis is None:
            async with self._lock:
                state = self._local_presence.setdefault(match_id, _LocalPresenceState())
                self._prune_local_state(state)
                state.expires_at_by_connection[connection_id] = self._expires_at()
                if user_id:
                    state.user_id_by_connection[connection_id] = user_id
                else:
                    state.user_id_by_connection.pop(connection_id, None)
                state.peak_viewers = max(state.peak_viewers, len(state.expires_at_by_connection))
                return self._local_snapshot(match_id)

        active_key = self._active_key(match_id)
        peak_key = self._peak_key(match_id)
        expires_at = self._expires_at()
        await self._prune_remote(redis, match_id)
        pipe = redis.pipeline()
        pipe.zadd(active_key, {connection_id: expires_at})
        if user_id:
            pipe.set(self._viewer_key(match_id, connection_id), user_id, ex=self.viewer_ttl_seconds)
        else:
            pipe.delete(self._viewer_key(match_id, connection_id))
        await pipe.execute()

        active_connection_ids = await self._active_connection_ids(redis, match_id)
        active_viewers = len(active_connection_ids)
        peak_raw = await redis.get(peak_key)
        peak_viewers = max(int(peak_raw or 0), active_viewers)
        if peak_viewers > int(peak_raw or 0):
            await redis.set(peak_key, peak_viewers)
        user_ids = await self._active_user_ids(redis, match_id, active_connection_ids)
        return SpectatorPresenceView(
            match_id=match_id,
            active_viewers=active_viewers,
            peak_viewers=peak_viewers,
            active_user_ids=user_ids,
        )

    async def _get_redis(self) -> redis_asyncio.Redis | None:
        if not self.redis_url:
            return None
        if self._redis is None:
            self._redis = redis_asyncio.Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def _active_connection_ids(self, redis: redis_asyncio.Redis, match_id: str) -> list[str]:
        await self._prune_remote(redis, match_id)
        return [
            str(connection_id)
            for connection_id in await redis.zrangebyscore(self._active_key(match_id), min=self._now(), max="+inf")
        ]

    async def _active_user_ids(
        self,
        redis: redis_asyncio.Redis,
        match_id: str,
        connection_ids: list[str],
    ) -> list[str]:
        if not connection_ids:
            return []
        pipe = redis.pipeline()
        for connection_id in connection_ids:
            pipe.get(self._viewer_key(match_id, connection_id))
        raw_user_ids = await pipe.execute()
        return sorted({str(user_id) for user_id in raw_user_ids if user_id})

    async def _prune_remote(self, redis: redis_asyncio.Redis, match_id: str) -> None:
        await redis.zremrangebyscore(self._active_key(match_id), min="-inf", max=self._now())

    def _local_snapshot(self, match_id: str) -> SpectatorPresenceView:
        state = self._local_presence.setdefault(match_id, _LocalPresenceState())
        self._prune_local_state(state)
        active_user_ids = sorted({user_id for user_id in state.user_id_by_connection.values() if user_id})
        active_viewers = len(state.expires_at_by_connection)
        state.peak_viewers = max(state.peak_viewers, active_viewers)
        return SpectatorPresenceView(
            match_id=match_id,
            active_viewers=active_viewers,
            peak_viewers=state.peak_viewers,
            active_user_ids=active_user_ids,
        )

    def _prune_local_state(self, state: _LocalPresenceState) -> None:
        now = self._now()
        expired_connection_ids = [
            connection_id
            for connection_id, expires_at in state.expires_at_by_connection.items()
            if expires_at <= now
        ]
        for connection_id in expired_connection_ids:
            state.expires_at_by_connection.pop(connection_id, None)
            state.user_id_by_connection.pop(connection_id, None)

    def _active_key(self, match_id: str) -> str:
        return f"{self.prefix}:{match_id}:active"

    def _peak_key(self, match_id: str) -> str:
        return f"{self.prefix}:{match_id}:peak"

    def _viewer_key(self, match_id: str, connection_id: str) -> str:
        return f"{self.prefix}:{match_id}:viewer:{connection_id}"

    def _expires_at(self) -> float:
        return self._now() + float(self.viewer_ttl_seconds)

    @staticmethod
    def _now() -> float:
        return time.time()
