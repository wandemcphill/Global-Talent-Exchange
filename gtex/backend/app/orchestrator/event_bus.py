from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeAlias

from .schemas import BaseEvent


EventHandler: TypeAlias = Callable[[BaseEvent], Any]


class EventBus:
    def __init__(
        self,
        subscribers: Mapping[type[BaseEvent], Iterable[EventHandler]] | None = None,
    ) -> None:
        self._subscribers: dict[type[BaseEvent], list[EventHandler]] = defaultdict(list)
        if subscribers is not None:
            for event_type, handlers in subscribers.items():
                for handler in handlers:
                    self.subscribe(event_type, handler)

    def subscribe(self, event_type: type[BaseEvent], handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: BaseEvent) -> tuple[Any, ...]:
        results: list[Any] = []
        for event_type, handlers in self._subscribers.items():
            if not isinstance(event, event_type):
                continue
            for handler in handlers:
                results.append(handler(event))
        return tuple(results)

