from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.realtime.match_stream_service import match_event_channel

logger = logging.getLogger(__name__)


class RedisMatchSubscriber:
    def __init__(
        self,
        *,
        redis_url: str | None,
        on_message: Callable[[str, dict[str, Any]], Awaitable[int | None]],
        reconnect_delay_seconds: float = 1.0,
    ) -> None:
        self._redis_url = redis_url
        self._on_message = on_message
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, match_id: str) -> None:
        if not self._redis_url:
            return
        async with self._lock:
            task = self._tasks.get(match_id)
            if task is not None and not task.done():
                return
            self._tasks[match_id] = asyncio.create_task(
                self._run_subscription(match_id),
                name=f"gtex-match-stream-{match_id}",
            )

    async def unsubscribe(self, match_id: str) -> None:
        async with self._lock:
            task = self._tasks.pop(match_id, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def shutdown(self) -> None:
        async with self._lock:
            tasks = list(self._tasks.values())
            self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_subscription(self, match_id: str) -> None:
        assert self._redis_url is not None
        channel = match_event_channel(match_id)
        while True:
            redis: Redis | None = None
            pubsub = None
            try:
                redis = Redis.from_url(self._redis_url, decode_responses=True)
                pubsub = redis.pubsub()
                await pubsub.subscribe(channel)
                logger.info("realtime.redis.subscribe channel=%s", channel)
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message is None:
                        await asyncio.sleep(0.05)
                        continue
                    raw = message.get("data")
                    if not isinstance(raw, str) or not raw.strip():
                        continue
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("realtime.redis.invalid_json channel=%s", channel)
                        continue
                    if not isinstance(payload, dict):
                        continue
                    await self._on_message(match_id, payload)
            except asyncio.CancelledError:
                raise
            except RedisError:
                logger.exception("realtime.redis.subscription_failed channel=%s", channel)
                await asyncio.sleep(self._reconnect_delay_seconds)
            finally:
                if pubsub is not None:
                    await _close_async(pubsub)
                if redis is not None:
                    await _close_async(redis)


async def _close_async(resource: Any) -> None:
    close = getattr(resource, "aclose", None)
    if callable(close):
        await close()
        return
    close = getattr(resource, "close", None)
    if callable(close):
        result = close()
        if asyncio.iscoroutine(result):
            await result


__all__ = ["RedisMatchSubscriber"]
