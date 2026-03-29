from __future__ import annotations

from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
import json
import threading
from time import time
from typing import Any, Iterator
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError, ResponseError


@dataclass(frozen=True, slots=True)
class QueueMessage:
    stream: str
    message_id: str
    payload: dict[str, Any]


class InMemoryStateStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._values: dict[str, tuple[Any, float | None]] = {}
        self._sets: dict[str, set[str]] = defaultdict(set)
        self._sorted_sets: dict[str, dict[str, float]] = defaultdict(dict)
        self._streams: dict[str, deque[QueueMessage]] = defaultdict(deque)
        self._locks: dict[str, tuple[str, float]] = {}
        self._published: list[tuple[str, dict[str, Any]]] = []

    def close(self) -> None:
        return None

    def _purge_expired(self) -> None:
        now = time()
        expired = [key for key, (_, expires_at) in self._values.items() if expires_at is not None and expires_at <= now]
        for key in expired:
            self._values.pop(key, None)
        expired_locks = [key for key, (_, expires_at) in self._locks.items() if expires_at <= now]
        for key in expired_locks:
            self._locks.pop(key, None)

    def get_json(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            self._purge_expired()
            value = self._values.get(key)
            if value is None:
                return None
            payload = value[0]
            return dict(payload) if isinstance(payload, dict) else None

    def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int | None = None) -> None:
        with self._lock:
            expires_at = time() + ttl_seconds if ttl_seconds else None
            self._values[key] = (dict(payload), expires_at)

    def get_decimal(self, key: str) -> Decimal | None:
        with self._lock:
            self._purge_expired()
            value = self._values.get(key)
            if value is None:
                return None
            try:
                return Decimal(str(value[0]))
            except Exception:
                return None

    def set_decimal(self, key: str, value: Decimal, ttl_seconds: int | None = None) -> None:
        with self._lock:
            expires_at = time() + ttl_seconds if ttl_seconds else None
            self._values[key] = (str(value), expires_at)

    def increment_decimal(self, key: str, amount: Decimal) -> Decimal:
        with self._lock:
            current = self.get_decimal(key) or Decimal("0")
            updated = current + amount
            self._values[key] = (str(updated), None)
            return updated

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)
            self._sets.pop(key, None)
            self._sorted_sets.pop(key, None)

    def sadd(self, key: str, *members: str) -> None:
        with self._lock:
            self._sets[key].update(str(member) for member in members)

    def smembers(self, key: str) -> set[str]:
        with self._lock:
            return set(self._sets.get(key, set()))

    def scard(self, key: str) -> int:
        with self._lock:
            return len(self._sets.get(key, set()))

    def zadd(self, key: str, mapping: dict[str, float]) -> None:
        with self._lock:
            for member, score in mapping.items():
                self._sorted_sets[key][str(member)] = float(score)

    def zrevrange(self, key: str, start: int, stop: int, *, withscores: bool = False) -> list[Any]:
        with self._lock:
            items = sorted(self._sorted_sets.get(key, {}).items(), key=lambda item: (-item[1], item[0]))
            if stop == -1:
                selected = items[start:]
            else:
                selected = items[start : stop + 1]
            if withscores:
                return [(member, score) for member, score in selected]
            return [member for member, _ in selected]

    def zrem(self, key: str, *members: str) -> None:
        with self._lock:
            for member in members:
                self._sorted_sets.get(key, {}).pop(str(member), None)

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._published.append((channel, dict(payload)))

    def enqueue(self, stream: str, payload: dict[str, Any], *, maxlen: int = 100000) -> str:
        with self._lock:
            message_id = uuid4().hex
            queue = self._streams[stream]
            queue.append(QueueMessage(stream=stream, message_id=message_id, payload=dict(payload)))
            while len(queue) > maxlen:
                queue.popleft()
            return message_id

    def consume(
        self,
        stream: str,
        *,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> list[QueueMessage]:
        del group, consumer, block_ms
        with self._lock:
            queue = self._streams.get(stream)
            if not queue:
                return []
            items: list[QueueMessage] = []
            while queue and len(items) < count:
                items.append(queue.popleft())
            return items

    def ack(self, stream: str, group: str, message_id: str) -> None:
        del stream, group, message_id
        return None

    @contextmanager
    def distributed_lock(self, key: str, *, ttl_seconds: int) -> Iterator[bool]:
        token = uuid4().hex
        with self._lock:
            self._purge_expired()
            if key in self._locks:
                yield False
                return
            self._locks[key] = (token, time() + ttl_seconds)
        try:
            yield True
        finally:
            with self._lock:
                current = self._locks.get(key)
                if current is not None and current[0] == token:
                    self._locks.pop(key, None)


class RedisStateStore:
    def __init__(self, redis_url: str, *, realtime_channel: str) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self.realtime_channel = realtime_channel

    def close(self) -> None:
        self._redis.close()

    def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            raw_value = self._redis.get(key)
        except RedisError:
            return None
        if not raw_value:
            return None
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        return dict(payload) if isinstance(payload, dict) else None

    def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int | None = None) -> None:
        serialized = json.dumps(payload, default=str)
        if ttl_seconds:
            self._redis.set(key, serialized, ex=ttl_seconds)
            return
        self._redis.set(key, serialized)

    def get_decimal(self, key: str) -> Decimal | None:
        try:
            raw_value = self._redis.get(key)
        except RedisError:
            return None
        if raw_value is None:
            return None
        try:
            return Decimal(str(raw_value))
        except Exception:
            return None

    def set_decimal(self, key: str, value: Decimal, ttl_seconds: int | None = None) -> None:
        if ttl_seconds:
            self._redis.set(key, str(value), ex=ttl_seconds)
            return
        self._redis.set(key, str(value))

    def increment_decimal(self, key: str, amount: Decimal) -> Decimal:
        try:
            return Decimal(str(self._redis.incrbyfloat(key, float(amount))))
        except RedisError:
            return self.get_decimal(key) or Decimal("0")

    def delete(self, key: str) -> None:
        try:
            self._redis.delete(key)
        except RedisError:
            return None

    def sadd(self, key: str, *members: str) -> None:
        try:
            if members:
                self._redis.sadd(key, *members)
        except RedisError:
            return None

    def smembers(self, key: str) -> set[str]:
        try:
            return {str(item) for item in self._redis.smembers(key)}
        except RedisError:
            return set()

    def scard(self, key: str) -> int:
        try:
            return int(self._redis.scard(key))
        except RedisError:
            return 0

    def zadd(self, key: str, mapping: dict[str, float]) -> None:
        try:
            if mapping:
                self._redis.zadd(key, mapping)
        except RedisError:
            return None

    def zrevrange(self, key: str, start: int, stop: int, *, withscores: bool = False) -> list[Any]:
        try:
            return list(self._redis.zrevrange(key, start, stop, withscores=withscores))
        except RedisError:
            return []

    def zrem(self, key: str, *members: str) -> None:
        try:
            if members:
                self._redis.zrem(key, *members)
        except RedisError:
            return None

    def publish(self, channel: str, payload: dict[str, Any]) -> None:
        try:
            self._redis.publish(channel, json.dumps(payload, default=str))
        except RedisError:
            return None

    def enqueue(self, stream: str, payload: dict[str, Any], *, maxlen: int = 100000) -> str:
        try:
            return str(
                self._redis.xadd(
                    stream,
                    {"payload": json.dumps(payload, default=str)},
                    maxlen=maxlen,
                    approximate=True,
                )
            )
        except RedisError:
            return uuid4().hex

    def consume(
        self,
        stream: str,
        *,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> list[QueueMessage]:
        try:
            self._redis.xgroup_create(stream, group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        except RedisError:
            return []
        try:
            messages = self._redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
        except RedisError:
            return []
        items: list[QueueMessage] = []
        for stream_name, stream_messages in messages:
            for message_id, fields in stream_messages:
                raw_payload = fields.get("payload")
                if not isinstance(raw_payload, str):
                    payload = {}
                else:
                    try:
                        payload = json.loads(raw_payload)
                    except json.JSONDecodeError:
                        payload = {}
                items.append(
                    QueueMessage(
                        stream=str(stream_name),
                        message_id=str(message_id),
                        payload=dict(payload),
                    )
                )
        return items

    def ack(self, stream: str, group: str, message_id: str) -> None:
        try:
            self._redis.xack(stream, group, message_id)
            self._redis.xdel(stream, message_id)
        except RedisError:
            return None

    @contextmanager
    def distributed_lock(self, key: str, *, ttl_seconds: int) -> Iterator[bool]:
        token = uuid4().hex
        try:
            acquired = bool(self._redis.set(key, token, nx=True, ex=ttl_seconds))
        except RedisError:
            acquired = False
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    pipeline = self._redis.pipeline(True)
                    while True:
                        try:
                            pipeline.watch(key)
                            if pipeline.get(key) == token:
                                pipeline.multi()
                                pipeline.delete(key)
                                pipeline.execute()
                            break
                        except RedisError:
                            break
                        finally:
                            pipeline.reset()
                except RedisError:
                    pass


def build_state_store(*, redis_url: str | None, realtime_channel: str) -> InMemoryStateStore | RedisStateStore:
    if redis_url:
        try:
            store = RedisStateStore(redis_url, realtime_channel=realtime_channel)
            store._redis.ping()
            return store
        except Exception:
            pass
    return InMemoryStateStore()


__all__ = ["QueueMessage", "build_state_store", "InMemoryStateStore", "RedisStateStore"]
