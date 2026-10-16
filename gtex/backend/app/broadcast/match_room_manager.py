from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import json
import logging
from typing import Any
from uuid import uuid4

import redis.asyncio as redis_asyncio
from fastapi import WebSocket
from pydantic import BaseModel
from redis.exceptions import RedisError

from app.core.event_backbone import make_json_safe

logger = logging.getLogger(__name__)


@dataclass(eq=False, slots=True)
class RoomClient:
    connection_id: str
    websocket: WebSocket
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[dict[str, Any]]
    user_id: str | None = None
    display_name: str | None = None

    def __hash__(self) -> int:
        return hash(self.connection_id)


@dataclass(slots=True)
class MatchRoomManager:
    redis_url: str | None = None
    redis_prefix: str = "match"
    delay_seconds: int = 3
    max_queue_size: int = 256
    rooms: dict[str, dict[str, Any]] = field(default_factory=dict)
    instance_id: str = field(default_factory=lambda: uuid4().hex)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    _listener_tasks: dict[str, asyncio.Task[None]] = field(init=False, default_factory=dict)
    _redis: redis_asyncio.Redis | None = field(init=False, default=None)

    def build_client(
        self,
        *,
        websocket: WebSocket,
        user_id: str | None = None,
        display_name: str | None = None,
    ) -> RoomClient:
        return RoomClient(
            connection_id=uuid4().hex,
            websocket=websocket,
            loop=asyncio.get_running_loop(),
            queue=asyncio.Queue(maxsize=self.max_queue_size),
            user_id=user_id,
            display_name=display_name,
        )

    async def join_room(self, match_id: str, client: RoomClient) -> int:
        start_listener = False
        async with self._lock:
            room = self.rooms.setdefault(match_id, {"clients": set(), "viewer_count": 0})
            room["clients"].add(client)
            room["viewer_count"] = len(room["clients"])
            start_listener = self.redis_url is not None and match_id not in self._listener_tasks
        if start_listener:
            self._listener_tasks[match_id] = asyncio.create_task(
                self._run_room_subscription(match_id),
                name=f"broadcast-match-room-{match_id}",
            )
        return await self.room_viewer_count(match_id)

    async def leave_room(self, match_id: str, client: RoomClient) -> int:
        listener: asyncio.Task[None] | None = None
        async with self._lock:
            room = self.rooms.get(match_id)
            if room is None:
                return 0
            room["clients"].discard(client)
            room["viewer_count"] = len(room["clients"])
            if room["viewer_count"] == 0:
                self.rooms.pop(match_id, None)
                listener = self._listener_tasks.pop(match_id, None)
        if listener is not None:
            listener.cancel()
            with suppress(asyncio.CancelledError):
                await listener
        return await self.room_viewer_count(match_id)

    async def broadcast(self, match_id: str, message: dict[str, Any] | BaseModel, *, delay_seconds: float = 0.0) -> int:
        payload = self._normalize_message(message)
        async with self._lock:
            room = self.rooms.get(match_id)
            if room is None:
                return 0
            clients = tuple(room["clients"])
        for client in clients:
            self._schedule_delivery(client, payload, delay_seconds=delay_seconds)
        return len(clients)

    async def publish(
        self,
        match_id: str,
        message: dict[str, Any] | BaseModel,
        *,
        local_echo: bool = True,
        delay_seconds: float | None = None,
    ) -> None:
        payload = self._normalize_message(message)
        resolved_delay = self._resolved_delay(payload) if delay_seconds is None else delay_seconds
        if local_echo:
            await self.broadcast(match_id, payload, delay_seconds=resolved_delay)
        redis = await self._get_redis()
        if redis is None:
            return
        envelope = {"instance_id": self.instance_id, "message": payload}
        try:
            await redis.publish(self.channel_for_match(match_id), json.dumps(make_json_safe(envelope)))
        except RedisError:
            logger.exception("broadcast.match.publish_failed match_id=%s", match_id)

    async def room_viewer_count(self, match_id: str) -> int:
        async with self._lock:
            room = self.rooms.get(match_id)
            if room is None:
                return 0
            return int(room["viewer_count"])

    async def aclose(self) -> None:
        listeners = tuple(self._listener_tasks.values())
        self._listener_tasks.clear()
        for listener in listeners:
            listener.cancel()
        for listener in listeners:
            with suppress(asyncio.CancelledError):
                await listener
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except RedisError:
                logger.exception("broadcast.match.redis_close_failed")
            finally:
                self._redis = None

    def channel_for_match(self, match_id: str) -> str:
        return f"{self.redis_prefix}:{match_id}:events"

    async def _run_room_subscription(self, match_id: str) -> None:
        if not self.redis_url:
            return
        redis = redis_asyncio.Redis.from_url(self.redis_url, decode_responses=True)
        pubsub = redis.pubsub(ignore_subscribe_messages=True)
        channel = self.channel_for_match(match_id)
        try:
            await pubsub.subscribe(channel)
            while True:
                message = await pubsub.get_message(timeout=1.0)
                if not message or message.get("type") != "message":
                    await asyncio.sleep(0.1)
                    continue
                raw_payload = message.get("data")
                if not isinstance(raw_payload, str) or not raw_payload.strip():
                    continue
                try:
                    envelope = json.loads(raw_payload)
                except json.JSONDecodeError:
                    continue
                if str(envelope.get("instance_id") or "") == self.instance_id:
                    continue
                payload = envelope.get("message")
                if not isinstance(payload, dict):
                    continue
                await self.broadcast(match_id, payload, delay_seconds=self._resolved_delay(payload))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("broadcast.match.subscription_failed match_id=%s", match_id)
        finally:
            with suppress(Exception):
                await pubsub.unsubscribe(channel)
            with suppress(Exception):
                await pubsub.aclose()
            with suppress(Exception):
                await redis.aclose()

    async def _get_redis(self) -> redis_asyncio.Redis | None:
        if not self.redis_url:
            return None
        if self._redis is None:
            self._redis = redis_asyncio.Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _schedule_delivery(self, client: RoomClient, payload: dict[str, Any], *, delay_seconds: float) -> None:
        with suppress(RuntimeError):
            client.loop.call_soon_threadsafe(self._enqueue_for_delivery, client.queue, payload, delay_seconds)

    def _enqueue_for_delivery(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        payload: dict[str, Any],
        delay_seconds: float,
    ) -> None:
        loop = asyncio.get_running_loop()
        if delay_seconds > 0:
            loop.call_later(delay_seconds, self._push_nowait, queue, payload)
            return
        self._push_nowait(queue, payload)

    def _push_nowait(self, queue: asyncio.Queue[dict[str, Any]], payload: dict[str, Any]) -> None:
        if queue.full():
            with suppress(asyncio.QueueEmpty):
                queue.get_nowait()
        with suppress(asyncio.QueueFull):
            queue.put_nowait(payload)

    def _normalize_message(self, message: dict[str, Any] | BaseModel) -> dict[str, Any]:
        if isinstance(message, BaseModel):
            return dict(message.model_dump(mode="json"))
        return dict(make_json_safe(message))

    def _resolved_delay(self, payload: dict[str, Any]) -> float:
        message_type = str(payload.get("type") or "").strip().lower()
        if message_type in {"chat_message", "reaction", "viewer_count", "heartbeat"}:
            return 0.0
        return max(float(self.delay_seconds), 0.0)
