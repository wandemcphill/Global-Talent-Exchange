from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

from app.core.events import DomainEvent


@dataclass(slots=True)
class RealtimeSnapshot:
    total_events: int
    channels: dict[str, int]
    last_event_name: str | None
    last_event_at: datetime | None


@dataclass(slots=True)
class RealtimeHub:
    total_events: int = 0
    channels: dict[str, int] = field(default_factory=dict)
    last_event_name: str | None = None
    last_event_at: datetime | None = None
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        channel = event.name.split(".", maxsplit=1)[0]
        with self._lock:
            self.total_events += 1
            self.channels[channel] = self.channels.get(channel, 0) + 1
            self.last_event_name = event.name
            self.last_event_at = event.occurred_at

    def snapshot(self) -> RealtimeSnapshot:
        with self._lock:
            return RealtimeSnapshot(
                total_events=self.total_events,
                channels=dict(self.channels),
                last_event_name=self.last_event_name,
                last_event_at=self.last_event_at,
            )
