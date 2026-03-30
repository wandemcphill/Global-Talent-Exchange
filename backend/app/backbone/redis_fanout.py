from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from threading import Event as ThreadEvent, RLock, Thread
from typing import Any
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from app.core.event_backbone import make_json_safe
from app.core.events import DomainEvent, EventSubscriber, InMemoryEventPublisher

logger = logging.getLogger(__name__)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported event timestamp {value!r}")


@dataclass(slots=True)
class HybridEventPublisher:
    redis_url: str | None = None
    redis_channel: str = "gtex.events"
    delegate: InMemoryEventPublisher = field(default_factory=InMemoryEventPublisher)
    instance_id: str = field(default_factory=lambda: uuid4().hex)
    max_seen_events: int = 2048
    _redis: Redis | None = field(init=False, default=None)
    _stop_event: ThreadEvent = field(init=False, default_factory=ThreadEvent)
    _listener_thread: Thread | None = field(init=False, default=None)
    _seen_event_ids: deque[str] = field(init=False, default_factory=deque)
    _seen_lookup: set[str] = field(init=False, default_factory=set)
    _seen_lock: RLock = field(init=False, default_factory=RLock)

    def __post_init__(self) -> None:
        if self.redis_url:
            try:
                self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            except RedisError:
                self._redis = None

    def publish(self, event: DomainEvent) -> None:
        self._record_seen(event.event_id)
        self.delegate.publish(event)
        if self._redis is None:
            return
        envelope = make_json_safe(event.envelope())
        envelope["fanout_instance_id"] = self.instance_id
        try:
            self._redis.publish(self.redis_channel, json.dumps(envelope))
        except RedisError:
            return

    def subscribe(self, subscriber: EventSubscriber) -> None:
        self.delegate.subscribe(subscriber)

    @property
    def published_events(self) -> list[DomainEvent]:
        return self.delegate.published_events

    @property
    def subscriber_count(self) -> int:
        return self.delegate.subscriber_count

    def start(self) -> None:
        if self._redis is None or self._listener_thread is not None:
            return
        self._stop_event.clear()
        self._listener_thread = Thread(
            target=self._run_listener,
            name="gtex-redis-event-fanout",
            daemon=True,
        )
        self._listener_thread.start()

    def close(self) -> None:
        self._stop_event.set()
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=2.0)
            self._listener_thread = None
        if self._redis is not None:
            try:
                self._redis.close()
            except RedisError:
                pass

    def _run_listener(self) -> None:
        assert self._redis is not None
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        try:
            try:
                pubsub.subscribe(self.redis_channel)
            except RedisError:
                logger.warning("backbone.redis_fanout.subscribe_failed channel=%s", self.redis_channel)
                return
            while not self._stop_event.is_set():
                try:
                    message = pubsub.get_message(timeout=1.0)
                except RedisError:
                    logger.warning("backbone.redis_fanout.listen_failed channel=%s", self.redis_channel)
                    return
                if not message or message.get("type") != "message":
                    continue
                raw = message.get("data")
                if not isinstance(raw, str) or not raw.strip():
                    continue
                try:
                    envelope = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if envelope.get("fanout_instance_id") == self.instance_id:
                    continue
                event_id = str(envelope.get("event_id") or "")
                if not event_id or self._has_seen(event_id):
                    continue
                try:
                    event = DomainEvent(
                        name=str(envelope.get("event_type") or envelope.get("name") or "event.unknown"),
                        payload=dict(envelope.get("payload") or {}),
                        event_id=event_id,
                        occurred_at=_parse_datetime(envelope.get("timestamp")),
                        aggregate_id=_optional_string(envelope.get("aggregate_id")),
                        aggregate_type=_optional_string(envelope.get("aggregate_type")),
                        version=int(envelope.get("version") or 1),
                        producer=_optional_string(envelope.get("producer")),
                        partition_key=_optional_string(envelope.get("partition_key")),
                        headers=dict(envelope.get("headers") or {}),
                    )
                except Exception:
                    continue
                self._record_seen(event.event_id)
                self.delegate.publish(event)
        finally:
            try:
                pubsub.close()
            except RedisError:
                logger.warning("backbone.redis_fanout.close_failed channel=%s", self.redis_channel)

    def _record_seen(self, event_id: str) -> None:
        with self._seen_lock:
            if event_id in self._seen_lookup:
                return
            self._seen_event_ids.append(event_id)
            self._seen_lookup.add(event_id)
            while len(self._seen_event_ids) > self.max_seen_events:
                removed = self._seen_event_ids.popleft()
                self._seen_lookup.discard(removed)

    def _has_seen(self, event_id: str) -> bool:
        with self._seen_lock:
            return event_id in self._seen_lookup


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


__all__ = ["HybridEventPublisher"]
