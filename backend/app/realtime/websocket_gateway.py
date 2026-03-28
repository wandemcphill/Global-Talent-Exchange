from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any

from app.core.events import DomainEvent


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


__all__ = ["WalletGatewayMetrics", "WalletWebsocketGateway"]
