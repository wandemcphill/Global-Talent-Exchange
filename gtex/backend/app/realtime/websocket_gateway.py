from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
import logging
from threading import RLock
from typing import Any, Callable

from fastapi import FastAPI, WebSocket

from app.core.events import DomainEvent
from app.realtime.match_stream_service import match_event_channel
from app.realtime.redis_subscriber import RedisMatchSubscriber

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WalletGatewayEnvelope:
    sequence: int
    event_id: str
    event_name: str
    occurred_at: datetime
    payload: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class WalletGatewayMetrics:
    active_connections: int
    tracked_streams: int
    delivered_messages: int


@dataclass(frozen=True, slots=True)
class MatchGatewayEnvelope:
    sequence: int
    event_id: str
    event_name: str
    occurred_at: datetime
    match_id: str
    payload: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
            "match_id": self.match_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class MatchGatewayMetrics:
    active_connections: int
    tracked_streams: int
    delivered_messages: int


@dataclass(slots=True)
class WalletWebsocketGateway:
    max_events_per_user: int = 256
    _events_by_user: dict[str, deque[WalletGatewayEnvelope]] = field(
        default_factory=lambda: defaultdict(deque)
    )
    _next_sequence_by_user: dict[str, int] = field(default_factory=dict)
    _active_connections: int = 0
    _delivered_messages: int = 0
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        user_ids = self._resolve_user_ids(event)
        if not user_ids:
            return
        with self._lock:
            for user_id in user_ids:
                next_sequence = self._next_sequence_by_user.get(user_id, 0) + 1
                self._next_sequence_by_user[user_id] = next_sequence
                stream = self._events_by_user[user_id]
                stream.append(
                    WalletGatewayEnvelope(
                        sequence=next_sequence,
                        event_id=event.event_id,
                        event_name=event.name,
                        occurred_at=event.occurred_at,
                        payload=dict(event.payload),
                    )
                )
                while len(stream) > self.max_events_per_user:
                    stream.popleft()

    def latest_cursor(self, user_id: str) -> int:
        with self._lock:
            stream = self._events_by_user.get(user_id)
            if not stream:
                return 0
            return stream[-1].sequence

    def events_since(self, user_id: str, cursor: int) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            stream = self._events_by_user.get(user_id)
            if not stream:
                return [], cursor
            if cursor < stream[0].sequence - 1:
                events = [item.as_payload() for item in stream]
                return events, stream[-1].sequence
            events = [item.as_payload() for item in stream if item.sequence > cursor]
            if not events:
                return [], cursor
            return events, stream[-1].sequence

    def register_connection(self) -> None:
        with self._lock:
            self._active_connections += 1

    def unregister_connection(self) -> None:
        with self._lock:
            self._active_connections = max(self._active_connections - 1, 0)

    def record_delivery(self, message_count: int = 1) -> None:
        if message_count <= 0:
            return
        with self._lock:
            self._delivered_messages += message_count

    def metrics(self) -> WalletGatewayMetrics:
        with self._lock:
            return WalletGatewayMetrics(
                active_connections=self._active_connections,
                tracked_streams=len(self._events_by_user),
                delivered_messages=self._delivered_messages,
            )

    @staticmethod
    def channel_for_user(user_id: str) -> str:
        return f"wallet:{user_id}"

    @staticmethod
    def _resolve_user_ids(event: DomainEvent) -> tuple[str, ...]:
        payload = dict(event.payload or {})
        resolved: list[str] = []

        direct_user_id = str(payload.get("user_id") or "").strip()
        if direct_user_id:
            resolved.append(direct_user_id)

        owner_user_id = str(payload.get("owner_user_id") or "").strip()
        if owner_user_id:
            resolved.append(owner_user_id)

        owner_user_ids = payload.get("owner_user_ids") or ()
        if isinstance(owner_user_ids, (list, tuple, set)):
            for candidate in owner_user_ids:
                value = str(candidate or "").strip()
                if value:
                    resolved.append(value)

        subject_user_id = str(payload.get("subject_user_id") or "").strip()
        if subject_user_id:
            resolved.append(subject_user_id)

        if event.name == "risk.fraud.detected" and direct_user_id:
            resolved.append(direct_user_id)

        deduped = tuple(dict.fromkeys(resolved))
        return deduped


@dataclass(slots=True)
class MatchWebsocketGateway:
    max_events_per_match: int = 256
    _events_by_match: dict[str, deque[MatchGatewayEnvelope]] = field(
        default_factory=lambda: defaultdict(deque)
    )
    _next_sequence_by_match: dict[str, int] = field(default_factory=dict)
    _active_connections: int = 0
    _delivered_messages: int = 0
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        match_ids = self._resolve_match_ids(event)
        if not match_ids:
            return
        with self._lock:
            for match_id in match_ids:
                next_sequence = self._next_sequence_by_match.get(match_id, 0) + 1
                self._next_sequence_by_match[match_id] = next_sequence
                stream = self._events_by_match[match_id]
                stream.append(
                    MatchGatewayEnvelope(
                        sequence=next_sequence,
                        event_id=event.event_id,
                        event_name=event.name,
                        occurred_at=event.occurred_at,
                        match_id=match_id,
                        payload=dict(event.payload),
                    )
                )
                while len(stream) > self.max_events_per_match:
                    stream.popleft()

    def latest_cursor(self, match_id: str) -> int:
        with self._lock:
            stream = self._events_by_match.get(match_id)
            if not stream:
                return 0
            return stream[-1].sequence

    def events_since(self, match_id: str, cursor: int) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            stream = self._events_by_match.get(match_id)
            if not stream:
                return [], cursor
            if cursor < stream[0].sequence - 1:
                events = [item.as_payload() for item in stream]
                return events, stream[-1].sequence
            events = [item.as_payload() for item in stream if item.sequence > cursor]
            if not events:
                return [], cursor
            return events, stream[-1].sequence

    def register_connection(self) -> None:
        with self._lock:
            self._active_connections += 1

    def unregister_connection(self) -> None:
        with self._lock:
            self._active_connections = max(self._active_connections - 1, 0)

    def record_delivery(self, message_count: int = 1) -> None:
        if message_count <= 0:
            return
        with self._lock:
            self._delivered_messages += message_count

    def metrics(self) -> MatchGatewayMetrics:
        with self._lock:
            return MatchGatewayMetrics(
                active_connections=self._active_connections,
                tracked_streams=len(self._events_by_match),
                delivered_messages=self._delivered_messages,
            )

    @staticmethod
    def channel_for_match(match_id: str) -> str:
        return match_event_channel(match_id)

    @staticmethod
    def _resolve_match_ids(event: DomainEvent) -> tuple[str, ...]:
        payload = dict(event.payload or {})
        resolved: list[str] = []
        for candidate in (
            payload.get("match_id"),
            payload.get("fixture_id"),
            payload.get("resource_id"),
            event.aggregate_id if event.aggregate_type == "competition_match" else None,
        ):
            value = str(candidate or "").strip()
            if value:
                resolved.append(value)
        return tuple(dict.fromkeys(resolved))


class MatchStreamWebSocketGateway:
    def __init__(
        self,
        *,
        redis_url: str | None,
        subscriber: RedisMatchSubscriber | None = None,
        delivery_callback: Callable[[int], None] | None = None,
    ) -> None:
        self._delivery_callback = delivery_callback
        self._subscriber = subscriber or RedisMatchSubscriber(
            redis_url=redis_url,
            on_message=self.broadcast,
        )
        self._connections_by_match: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, match_id: str) -> dict[str, Any]:
        await websocket.accept()
        should_subscribe = False
        async with self._lock:
            connections = self._connections_by_match[match_id]
            if not connections:
                should_subscribe = True
            connections.add(websocket)
        if should_subscribe:
            await self._subscriber.subscribe(match_id)
        return {
            "type": "subscribed",
            "match_id": match_id,
            "channel": match_event_channel(match_id),
        }

    async def disconnect(self, websocket: WebSocket, match_id: str) -> None:
        should_unsubscribe = False
        async with self._lock:
            connections = self._connections_by_match.get(match_id)
            if connections is not None:
                connections.discard(websocket)
                if not connections:
                    self._connections_by_match.pop(match_id, None)
                    should_unsubscribe = True
        if should_unsubscribe:
            await self._subscriber.unsubscribe(match_id)

    async def broadcast(self, match_id: str, payload: dict[str, Any]) -> int:
        async with self._lock:
            recipients = list(self._connections_by_match.get(match_id, ()))
        if not recipients:
            return 0

        delivered = 0
        stale_connections: list[WebSocket] = []
        for websocket in recipients:
            try:
                await websocket.send_json(payload)
                delivered += 1
            except Exception:
                stale_connections.append(websocket)

        if stale_connections:
            should_unsubscribe = False
            async with self._lock:
                connections = self._connections_by_match.get(match_id)
                if connections is not None:
                    for websocket in stale_connections:
                        connections.discard(websocket)
                    if not connections:
                        self._connections_by_match.pop(match_id, None)
                        should_unsubscribe = True
            if should_unsubscribe:
                await self._subscriber.unsubscribe(match_id)

        if delivered > 0 and self._delivery_callback is not None:
            self._delivery_callback(delivered)
        return delivered

    async def shutdown(self) -> None:
        await self._subscriber.shutdown()
        async with self._lock:
            self._connections_by_match.clear()


def get_match_stream_websocket_gateway(app: FastAPI) -> MatchStreamWebSocketGateway:
    gateway = getattr(app.state, "match_stream_websocket_gateway", None)
    if gateway is not None:
        return gateway

    settings = getattr(app.state, "settings", None)
    realtime = getattr(app.state, "realtime", None)
    gateway = MatchStreamWebSocketGateway(
        redis_url=getattr(settings, "redis_url", None),
        delivery_callback=getattr(realtime, "record_match_delivery", None),
    )
    app.state.match_stream_websocket_gateway = gateway
    logger.info(
        "realtime.match_stream_gateway.initialized redis_enabled=%s",
        bool(getattr(settings, "redis_url", None)),
    )
    return gateway


async def shutdown_match_stream_websocket_gateway(app: FastAPI) -> None:
    gateway = getattr(app.state, "match_stream_websocket_gateway", None)
    if gateway is None:
        return
    await gateway.shutdown()
    app.state.match_stream_websocket_gateway = None


__all__ = [
    "MatchGatewayMetrics",
    "MatchStreamWebSocketGateway",
    "MatchWebsocketGateway",
    "WalletGatewayMetrics",
    "WalletWebsocketGateway",
    "get_match_stream_websocket_gateway",
    "shutdown_match_stream_websocket_gateway",
]
