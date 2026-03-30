from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Protocol
from uuid import uuid4

from app.core.serialization import make_json_safe
try:
    from app.observability.tracing import enrich_trace_headers
except Exception:  # pragma: no cover - optional observability dependency
    def enrich_trace_headers(headers: dict[str, Any] | None = None) -> dict[str, str]:
        return {
            str(key): str(value)
            for key, value in dict(headers or {}).items()
            if value is not None
        }

EventSubscriber = Callable[["DomainEvent"], None]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utcnow)
    aggregate_id: str | None = None
    aggregate_type: str | None = None
    version: int = 1
    producer: str | None = None
    partition_key: str | None = None
    headers: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.name

    @property
    def timestamp(self) -> datetime:
        return self.occurred_at

    def envelope(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "version": self.version,
            "timestamp": self.occurred_at,
            "producer": self.producer or "gtex-app",
            "partition_key": self.partition_key or self.aggregate_id,
            "payload": make_json_safe(self.payload),
            "headers": make_json_safe(enrich_trace_headers(self.headers)),
        }


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None:
        ...

    def subscribe(self, subscriber: EventSubscriber) -> None:
        ...


@dataclass(slots=True)
class InMemoryEventPublisher:
    published_events: list[DomainEvent] = field(default_factory=list)
    _subscribers: list[EventSubscriber] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock)

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            self.published_events.append(event)
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber(event)

    def subscribe(self, subscriber: EventSubscriber) -> None:
        with self._lock:
            self._subscribers.append(subscriber)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)
