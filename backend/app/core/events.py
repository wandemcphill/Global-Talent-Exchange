from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Protocol

EventSubscriber = Callable[["DomainEvent"], None]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=utcnow)


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
