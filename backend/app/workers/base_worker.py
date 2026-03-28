from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from random import random
import socket
from threading import Event as ThreadEvent
import time
from typing import Any
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError, ResponseError

from app.core.config import Settings, get_settings
from app.core.event_backbone import make_json_safe
from app.observability.logging import configure_logging


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat()


def _normalize_string(value: Any, *, field_name: str) -> str:
    resolved = str(value or "").strip()
    if not resolved:
        raise ValueError(f"Event field '{field_name}' is required.")
    return resolved


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            raise ValueError("Event field 'timestamp' cannot be blank.")
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return candidate
    raise ValueError("Event field 'timestamp' must be an ISO 8601 string or datetime.")


def _normalize_string_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(
            candidate.strip()
            for candidate in value.split(",")
            if candidate and candidate.strip()
        )
    if isinstance(value, Iterable):
        return tuple(
            candidate
            for candidate in (str(item).strip() for item in value)
            if candidate
        )
    return ()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a float.") from exc


def _default_consumer_name(worker_name: str) -> str:
    host = socket.gethostname().strip().lower() or "localhost"
    return f"{worker_name}-{host}-{os.getpid()}-{uuid4().hex[:8]}"


def _resolve_service_name(*, settings: Settings, worker_name: str) -> str:
    base_name = settings.observability_service_name or f"gtex-{worker_name}"
    return f"{base_name}-{worker_name}" if settings.observability_service_name else base_name


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 3
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.1

    @classmethod
    def from_environ(cls) -> "RetryPolicy":
        return cls(
            max_retries=max(0, _env_int("GTEX_WORKER_MAX_RETRIES", 3)),
            initial_backoff_seconds=max(0.0, _env_float("GTEX_WORKER_INITIAL_BACKOFF_SECONDS", 1.0)),
            max_backoff_seconds=max(0.0, _env_float("GTEX_WORKER_MAX_BACKOFF_SECONDS", 30.0)),
            multiplier=max(1.0, _env_float("GTEX_WORKER_BACKOFF_MULTIPLIER", 2.0)),
            jitter_ratio=max(0.0, _env_float("GTEX_WORKER_BACKOFF_JITTER_RATIO", 0.1)),
        )

    def backoff_for_retry(self, retry_number: int) -> float:
        delay = min(
            self.max_backoff_seconds,
            self.initial_backoff_seconds * (self.multiplier ** max(0, retry_number)),
        )
        if self.jitter_ratio <= 0:
            return delay
        jitter_span = delay * self.jitter_ratio
        return max(0.0, delay + ((random() * 2.0) - 1.0) * jitter_span)


@dataclass(frozen=True, slots=True)
class WorkerEvent:
    type: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=utcnow_iso)
    key: str | None = None

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any], *, key: str | None = None) -> "WorkerEvent":
        event_type = _normalize_string(raw.get("type") or raw.get("event_type"), field_name="type")
        payload = raw.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("Event field 'payload' must be an object.")
        timestamp = _normalize_timestamp(raw.get("timestamp"))
        return cls(
            type=event_type,
            payload=dict(payload),
            timestamp=timestamp,
            key=key or (str(raw.get("key")).strip() if raw.get("key") is not None else None),
        )

    def to_message(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": make_json_safe(self.payload),
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class ReceivedMessage:
    event: WorkerEvent
    source: str
    delivery_id: str
    _ack_callback: Callable[[], None] = field(repr=False)
    _acknowledged: bool = field(init=False, default=False, repr=False)

    def ack(self) -> None:
        if self._acknowledged:
            return
        self._ack_callback()
        self._acknowledged = True


class EventBroker(ABC):
    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def consume(self) -> ReceivedMessage | None:
        ...

    @abstractmethod
    def publish(self, event: WorkerEvent) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


def _load_kafka_symbols() -> tuple[type[Any], type[Any]]:
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on runtime broker setup
        raise RuntimeError(
            "Kafka worker support requires the 'kafka-python' package to be installed."
        ) from exc
    return KafkaConsumer, KafkaProducer


class KafkaEventBroker(EventBroker):
    def __init__(
        self,
        *,
        brokers: tuple[str, ...],
        topic_prefix: str,
        consumer_group: str,
        consumer_name: str,
        subscriptions: tuple[str, ...],
        client_id_prefix: str,
        poll_timeout_ms: int,
    ) -> None:
        self.brokers = brokers
        self.topic_prefix = topic_prefix.strip(".")
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.subscriptions = subscriptions
        self.client_id_prefix = client_id_prefix
        self.poll_timeout_ms = poll_timeout_ms
        self._consumer: Any | None = None
        self._producer: Any | None = None

    def connect(self) -> None:
        if self._consumer is not None and self._producer is not None:
            return
        kafka_consumer_cls, kafka_producer_cls = _load_kafka_symbols()
        self._consumer = kafka_consumer_cls(
            *tuple(self._topic_name(event_type) for event_type in self.subscriptions),
            bootstrap_servers=list(self.brokers),
            group_id=self.consumer_group,
            client_id=f"{self.client_id_prefix}-{self.consumer_name}",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=1,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            key_deserializer=lambda value: value.decode("utf-8") if value is not None else None,
        )
        self._producer = kafka_producer_cls(
            bootstrap_servers=list(self.brokers),
            client_id=f"{self.client_id_prefix}-{self.consumer_group}-producer",
            acks="all",
            linger_ms=20,
            retries=5,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8") if value is not None else None,
        )

    def consume(self) -> ReceivedMessage | None:
        if self._consumer is None:
            raise RuntimeError("Kafka broker is not connected.")
        records = self._consumer.poll(timeout_ms=self.poll_timeout_ms, max_records=1)
        if not records:
            return None
        _, batch = next(iter(records.items()))
        if not batch:
            return None
        record = batch[0]
        event = WorkerEvent.from_raw(record.value, key=record.key)
        delivery_id = f"{record.topic}:{getattr(record, 'partition', 0)}:{getattr(record, 'offset', 0)}"
        return ReceivedMessage(
            event=event,
            source=record.topic,
            delivery_id=delivery_id,
            _ack_callback=self._consumer.commit,
        )

    def publish(self, event: WorkerEvent) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka broker is not connected.")
        future = self._producer.send(
            self._topic_name(event.type),
            value=event.to_message(),
            key=event.key,
        )
        if hasattr(future, "get"):
            future.get(timeout=30)

    def close(self) -> None:
        if self._consumer is not None and hasattr(self._consumer, "close"):
            self._consumer.close()
            self._consumer = None
        if self._producer is not None and hasattr(self._producer, "close"):
            self._producer.close()
            self._producer = None

    def _topic_name(self, event_type: str) -> str:
        clean_event_type = event_type.strip(".")
        return f"{self.topic_prefix}.{clean_event_type}" if self.topic_prefix else clean_event_type


class RedisStreamEventBroker(EventBroker):
    def __init__(
        self,
        *,
        redis_url: str,
        stream_prefix: str,
        consumer_group: str,
        consumer_name: str,
        subscriptions: tuple[str, ...],
        poll_timeout_ms: int,
        reclaim_idle_ms: int,
    ) -> None:
        self.redis_url = redis_url
        self.stream_prefix = stream_prefix.strip(".")
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.subscriptions = subscriptions
        self.poll_timeout_ms = poll_timeout_ms
        self.reclaim_idle_ms = reclaim_idle_ms
        self._redis: Redis | None = None

    def connect(self) -> None:
        if self._redis is not None:
            return
        self._redis = Redis.from_url(
            self.redis_url,
            decode_responses=True,
            health_check_interval=30,
        )
        for stream_name in self._stream_names:
            try:
                self._redis.xgroup_create(
                    name=stream_name,
                    groupname=self.consumer_group,
                    id="0-0",
                    mkstream=True,
                )
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise

    def consume(self) -> ReceivedMessage | None:
        redis_client = self._require_client()
        claimed_message = self._claim_stale_message(redis_client)
        if claimed_message is not None:
            return claimed_message
        records = redis_client.xreadgroup(
            groupname=self.consumer_group,
            consumername=self.consumer_name,
            streams={stream_name: ">" for stream_name in self._stream_names},
            count=1,
            block=self.poll_timeout_ms,
        )
        return self._parse_stream_records(records)

    def publish(self, event: WorkerEvent) -> None:
        redis_client = self._require_client()
        redis_client.xadd(
            self._stream_name(event.type),
            {"data": json.dumps(event.to_message())},
        )

    def close(self) -> None:
        if self._redis is not None:
            self._redis.close()
            self._redis = None

    @property
    def _stream_names(self) -> tuple[str, ...]:
        return tuple(self._stream_name(event_type) for event_type in self.subscriptions)

    def _stream_name(self, event_type: str) -> str:
        clean_event_type = event_type.strip(".")
        return f"{self.stream_prefix}.{clean_event_type}" if self.stream_prefix else clean_event_type

    def _claim_stale_message(self, redis_client: Redis) -> ReceivedMessage | None:
        if self.reclaim_idle_ms <= 0:
            return None
        for stream_name in self._stream_names:
            try:
                result = redis_client.xautoclaim(
                    name=stream_name,
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    min_idle_time=self.reclaim_idle_ms,
                    start_id="0-0",
                    count=1,
                )
            except ResponseError as exc:
                if "unknown command" in str(exc).lower():
                    self.reclaim_idle_ms = 0
                    return None
                raise
            claimed_entries = self._extract_claimed_entries(result)
            if claimed_entries:
                message_id, fields = claimed_entries[0]
                return self._build_received_message(stream_name, message_id, fields)
        return None

    @staticmethod
    def _extract_claimed_entries(result: Any) -> list[tuple[str, dict[str, Any]]]:
        if not isinstance(result, (list, tuple)) or len(result) < 2:
            return []
        entries = result[1]
        if not isinstance(entries, list):
            return []
        return [
            (str(message_id), dict(fields))
            for message_id, fields in entries
            if isinstance(fields, Mapping)
        ]

    def _parse_stream_records(self, records: Any) -> ReceivedMessage | None:
        if not records:
            return None
        stream_name, entries = records[0]
        if not entries:
            return None
        message_id, fields = entries[0]
        return self._build_received_message(str(stream_name), str(message_id), dict(fields))

    def _build_received_message(
        self,
        stream_name: str,
        message_id: str,
        fields: Mapping[str, Any],
    ) -> ReceivedMessage:
        raw_payload = fields.get("data", fields)
        if isinstance(raw_payload, str):
            envelope = json.loads(raw_payload)
        elif isinstance(raw_payload, Mapping):
            envelope = dict(raw_payload)
        else:
            raise ValueError("Redis stream message payload must be a JSON object or JSON string.")
        event = WorkerEvent.from_raw(envelope)
        return ReceivedMessage(
            event=event,
            source=stream_name,
            delivery_id=f"{stream_name}:{message_id}",
            _ack_callback=lambda: self._require_client().xack(stream_name, self.consumer_group, message_id),
        )

    def _require_client(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis broker is not connected.")
        return self._redis


def build_event_broker(
    *,
    settings: Settings,
    worker_name: str,
    consumer_group: str,
    subscriptions: tuple[str, ...],
) -> EventBroker:
    broker_backend = os.getenv("GTEX_WORKER_BROKER", "auto").strip().lower() or "auto"
    poll_timeout_ms = max(100, _env_int("GTEX_WORKER_POLL_TIMEOUT_MS", 1000))
    kafka_brokers = _normalize_string_sequence(os.getenv("GTE_KAFKA_BROKERS") or settings.kafka_brokers)
    redis_url = (os.getenv("GTE_REDIS_URL") or settings.redis_url or "").strip()

    if broker_backend not in {"auto", "kafka", "redis"}:
        raise ValueError("GTEX_WORKER_BROKER must be one of: auto, kafka, redis.")

    if broker_backend in {"auto", "kafka"} and kafka_brokers:
        return KafkaEventBroker(
            brokers=kafka_brokers,
            topic_prefix=os.getenv("GTE_KAFKA_TOPIC_PREFIX", settings.kafka_topic_prefix),
            consumer_group=consumer_group,
            consumer_name=_default_consumer_name(worker_name),
            subscriptions=subscriptions,
            client_id_prefix=os.getenv("GTE_KAFKA_CLIENT_ID", settings.kafka_client_id),
            poll_timeout_ms=poll_timeout_ms,
        )

    if broker_backend == "kafka":
        raise RuntimeError("Kafka worker broker selected but GTE_KAFKA_BROKERS is not configured.")

    if broker_backend in {"auto", "redis"} and redis_url:
        return RedisStreamEventBroker(
            redis_url=redis_url,
            stream_prefix=os.getenv(
                "GTEX_WORKER_REDIS_STREAM_PREFIX",
                settings.redis_event_channel,
            ),
            consumer_group=consumer_group,
            consumer_name=_default_consumer_name(worker_name),
            subscriptions=subscriptions,
            poll_timeout_ms=poll_timeout_ms,
            reclaim_idle_ms=max(0, _env_int("GTEX_WORKER_REDIS_RECLAIM_IDLE_MS", 30000)),
        )

    if broker_backend == "redis":
        raise RuntimeError("Redis worker broker selected but GTE_REDIS_URL is not configured.")

    raise RuntimeError(
        "No worker broker is configured. Set GTE_KAFKA_BROKERS for Kafka or GTE_REDIS_URL for Redis."
    )


class BaseWorker(ABC):
    def __init__(
        self,
        *,
        worker_name: str,
        consumes: tuple[str, ...],
        emits: tuple[str, ...],
        consumer_group: str,
        settings: Settings | None = None,
        broker: EventBroker | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.worker_name = worker_name
        self.consumes = consumes
        self.emits = emits
        self.consumer_group = consumer_group
        self.settings = settings or get_settings()
        self.retry_policy = retry_policy or RetryPolicy.from_environ()
        self.broker = broker or build_event_broker(
            settings=self.settings,
            worker_name=self.worker_name,
            consumer_group=self.consumer_group,
            subscriptions=self.consumes,
        )
        self.logger = logging.getLogger(f"app.workers.{self.worker_name}")
        self._stop_event = ThreadEvent()

    @abstractmethod
    def handle_event(self, event: WorkerEvent) -> WorkerEvent | Iterable[WorkerEvent] | None:
        ...

    def run(self) -> None:
        self.broker.connect()
        self.logger.info(
            "worker started",
            extra={
                "worker": self.worker_name,
                "consumer_group": self.consumer_group,
                "consumes": list(self.consumes),
                "emits": list(self.emits),
            },
        )
        try:
            while not self._stop_event.is_set():
                message = self.broker.consume()
                if message is None:
                    continue
                self._process_message(message)
        finally:
            self.broker.close()
            self.logger.info("worker stopped", extra={"worker": self.worker_name})

    def stop(self) -> None:
        self._stop_event.set()

    def emit_event(
        self,
        *,
        event_type: str,
        payload: Mapping[str, Any],
        key: str | None = None,
        timestamp: str | None = None,
    ) -> WorkerEvent:
        return WorkerEvent(
            type=event_type,
            payload=dict(payload),
            timestamp=timestamp or utcnow_iso(),
            key=key,
        )

    def _process_message(self, message: ReceivedMessage) -> None:
        if message.event.type not in self.consumes:
            raise ValueError(
                f"Worker '{self.worker_name}' received unsupported event type '{message.event.type}'."
            )
        started_at = time.perf_counter()
        for retry_number in range(self.retry_policy.max_retries + 1):
            attempt = retry_number + 1
            try:
                self.logger.info(
                    "worker processing event",
                    extra={
                        "worker": self.worker_name,
                        "event_type": message.event.type,
                        "delivery_id": message.delivery_id,
                        "source": message.source,
                        "attempt": attempt,
                    },
                )
                outputs = self._normalize_outputs(self.handle_event(message.event))
                for output in outputs:
                    if self.emits and output.type not in self.emits:
                        raise ValueError(
                            f"Worker '{self.worker_name}' cannot emit unexpected event type '{output.type}'."
                        )
                    self.broker.publish(output)
                message.ack()
                self.logger.info(
                    "worker processed event",
                    extra={
                        "worker": self.worker_name,
                        "event_type": message.event.type,
                        "delivery_id": message.delivery_id,
                        "attempt": attempt,
                        "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
                        "emitted_events": len(outputs),
                    },
                )
                return
            except Exception:
                terminal_attempt = retry_number >= self.retry_policy.max_retries
                self.logger.exception(
                    "worker failed to process event",
                    extra={
                        "worker": self.worker_name,
                        "event_type": message.event.type,
                        "delivery_id": message.delivery_id,
                        "attempt": attempt,
                        "max_retries": self.retry_policy.max_retries,
                        "terminal": terminal_attempt,
                    },
                )
                if terminal_attempt:
                    raise
                delay = self.retry_policy.backoff_for_retry(retry_number)
                self.logger.warning(
                    "worker retry scheduled",
                    extra={
                        "worker": self.worker_name,
                        "event_type": message.event.type,
                        "delivery_id": message.delivery_id,
                        "retry_in_seconds": round(delay, 3),
                    },
                )
                time.sleep(delay)

    @staticmethod
    def _normalize_outputs(result: WorkerEvent | Iterable[WorkerEvent] | None) -> list[WorkerEvent]:
        if result is None:
            return []
        if isinstance(result, WorkerEvent):
            return [result]
        if isinstance(result, Iterable):
            return [item for item in result]
        raise TypeError("Worker handler must return a WorkerEvent, an iterable of WorkerEvent, or None.")


def run_worker(worker: BaseWorker) -> None:
    service_name = _resolve_service_name(settings=worker.settings, worker_name=worker.worker_name)
    configure_logging(
        json_logs=worker.settings.observability_log_json,
        service_name=service_name,
        environment=worker.settings.app_env,
    )
    try:
        worker.run()
    except KeyboardInterrupt:
        worker.logger.info("worker shutdown requested", extra={"worker": worker.worker_name})
    except (RedisError, RuntimeError):
        worker.logger.exception("worker stopped with a runtime error", extra={"worker": worker.worker_name})
        raise


__all__ = [
    "BaseWorker",
    "EventBroker",
    "KafkaEventBroker",
    "ReceivedMessage",
    "RedisStreamEventBroker",
    "RetryPolicy",
    "WorkerEvent",
    "build_event_broker",
    "run_worker",
    "utcnow",
    "utcnow_iso",
]
