from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
import json
import logging
from queue import Empty, Queue
from threading import Event as ThreadEvent
from threading import Lock, Thread
import time
from typing import Any

from fastapi import FastAPI
from app.backbone.kafka import KafkaBackboneUnavailable
from app.core.config import Settings
from app.core.events import DomainEvent, EventPublisher
from app.viral.distribution import (
    InMemoryViralDispatchPoolStore,
    ViralDispatchPoolStore,
    ensure_viral_dispatch_pool_store,
    inject_into_distribution_pool,
)
from app.viral.ingestion_schemas import CLIP_EVENT_TOPICS, ClipEvent

logger = logging.getLogger(__name__)


class ClipEventIngestionUnavailable(RuntimeError):
    pass


class ClipEventQueueSaturated(RuntimeError):
    pass


def _load_kafka_runtime() -> tuple[type[Any], type[Any], type[Any]]:
    try:
        from kafka import KafkaProducer  # type: ignore[import-not-found]
        from kafka.admin import KafkaAdminClient, NewTopic  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on runtime install
        raise KafkaBackboneUnavailable(
            "Kafka support requires the 'kafka-python' package to be installed."
        ) from exc
    return KafkaProducer, KafkaAdminClient, NewTopic


@dataclass(frozen=True, slots=True)
class ClipEventTopicManager:
    brokers: tuple[str, ...]
    client_id: str
    partitions: int
    replication_factor: int

    def ensure_topics(self) -> None:
        if not self.brokers:
            raise ClipEventIngestionUnavailable("Kafka brokers are not configured for clip event ingestion.")
        _producer_cls, kafka_admin_cls, new_topic_cls = _load_kafka_runtime()
        admin = kafka_admin_cls(
            bootstrap_servers=list(self.brokers),
            client_id=f"{self.client_id}-clip-admin",
        )
        try:
            existing_topics = set(admin.list_topics())
            missing_topics = [
                new_topic_cls(
                    name=topic_name,
                    num_partitions=max(self.partitions, 1),
                    replication_factor=max(self.replication_factor, 1),
                )
                for topic_name in CLIP_EVENT_TOPICS
                if topic_name not in existing_topics
            ]
            if missing_topics:
                admin.create_topics(new_topics=missing_topics, validate_only=False)
        finally:
            admin.close()


@dataclass
class ClipEventKafkaProducer:
    settings: Settings
    topic_manager: ClipEventTopicManager | None = None
    producer: Any | None = None
    queue_batch_size: int | None = None
    flush_interval_ms: int | None = None
    max_pending_events: int | None = None

    def __post_init__(self) -> None:
        if self.topic_manager is None:
            self.topic_manager = ClipEventTopicManager(
                brokers=self.settings.kafka_brokers,
                client_id=self.settings.kafka_client_id,
                partitions=self.settings.viral_event_topic_partitions,
                replication_factor=self.settings.viral_event_topic_replication_factor,
            )
        self.queue_batch_size = max(1, int(self.queue_batch_size or self.settings.viral_event_batch_size))
        self.flush_interval_ms = max(1, int(self.flush_interval_ms or self.settings.viral_event_batch_interval_ms))
        self.max_pending_events = max(1, int(self.max_pending_events or self.settings.viral_event_queue_maxsize))
        self._queue: Queue[list[ClipEvent]] = Queue()
        self._pending_events = 0
        self._pending_lock = Lock()
        self._lifecycle_lock = Lock()
        self._stop_event = ThreadEvent()
        self._worker_thread: Thread | None = None
        self._start_error: str | None = None

    @property
    def is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        with self._lifecycle_lock:
            if self.is_running:
                return
            self._stop_event.clear()
            self._start_error = None
            if not self.settings.kafka_brokers:
                self._start_error = "Kafka brokers are not configured for clip event ingestion."
                logger.warning("viral.ingestion.kafka_unconfigured")
                return
            try:
                self.topic_manager.ensure_topics()
                kafka_producer_cls, _kafka_admin_cls, _new_topic_cls = _load_kafka_runtime()
                self.producer = kafka_producer_cls(
                    bootstrap_servers=list(self.settings.kafka_brokers),
                    client_id=f"{self.settings.kafka_client_id}-clip-ingestion",
                    acks=1,
                    linger_ms=max(1, self.flush_interval_ms),
                    retries=5,
                    batch_size=262_144,
                    compression_type="gzip",
                    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                    key_serializer=lambda value: value.encode("utf-8") if value is not None else None,
                )
            except Exception as exc:
                self.producer = None
                self._start_error = str(exc)
                logger.exception("viral.ingestion.start_failed")
                return
            worker_thread = Thread(
                target=self._run,
                name="gtex-clip-event-producer",
                daemon=True,
            )
            self._worker_thread = worker_thread
            worker_thread.start()
            logger.info("viral.ingestion.started topics=%s", ",".join(CLIP_EVENT_TOPICS))

    def stop(self) -> None:
        with self._lifecycle_lock:
            self._stop_event.set()
            worker_thread = self._worker_thread
            self._worker_thread = None
        if worker_thread is not None and worker_thread.is_alive():
            worker_thread.join(timeout=5)
        if self.producer is not None and hasattr(self.producer, "flush"):
            try:
                self.producer.flush(timeout=5)
            except Exception:
                logger.warning("viral.ingestion.flush_failed")
        if self.producer is not None and hasattr(self.producer, "close"):
            try:
                self.producer.close()
            except Exception:
                logger.warning("viral.ingestion.close_failed")
        self.producer = None

    def enqueue_many(self, events: Sequence[ClipEvent]) -> int:
        if not events:
            return self.queue_depth()
        if not self.is_running:
            self.start()
        if self.producer is None:
            raise ClipEventIngestionUnavailable(self._start_error or "Clip event ingestion is unavailable.")
        event_batch = list(events)
        batch_size = len(event_batch)
        with self._pending_lock:
            if self._pending_events + batch_size > self.max_pending_events:
                raise ClipEventQueueSaturated("Clip event ingestion buffer is saturated.")
            self._pending_events += batch_size
            pending_depth = self._pending_events
        try:
            self._queue.put_nowait(event_batch)
        except Exception as exc:
            with self._pending_lock:
                self._pending_events = max(0, self._pending_events - batch_size)
            raise ClipEventQueueSaturated("Clip event ingestion buffer is saturated.") from exc
        return pending_depth

    def queue_depth(self) -> int:
        with self._pending_lock:
            return self._pending_events

    def _run(self) -> None:
        while not self._stop_event.is_set() or self.queue_depth() > 0:
            try:
                batch = self._queue.get(timeout=self.flush_interval_ms / 1000)
            except Empty:
                continue
            pending = list(batch)
            deadline = time.monotonic() + (self.flush_interval_ms / 1000)
            while len(pending) < self.queue_batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    pending.extend(self._queue.get(timeout=remaining))
                except Empty:
                    break
            try:
                self._publish_in_chunks(pending)
            except Exception:
                logger.exception("viral.ingestion.publish_failed batch_size=%s", len(pending))
                time.sleep(0.25)
                self._queue.put_nowait(pending)

    def _publish_in_chunks(self, events: Sequence[ClipEvent]) -> None:
        offset = 0
        while offset < len(events):
            chunk = list(events[offset : offset + self.queue_batch_size])
            self._publish_chunk(chunk)
            with self._pending_lock:
                self._pending_events = max(0, self._pending_events - len(chunk))
            offset += len(chunk)

    def _publish_chunk(self, events: Sequence[ClipEvent]) -> None:
        if self.producer is None:
            raise ClipEventIngestionUnavailable("Clip event Kafka producer is not available.")
        for event in events:
            future = self.producer.send(
                event.kafka_topic,
                key=event.clip_id,
                value=event.to_kafka_payload(),
                headers=[
                    ("event_id", str(event.event_id).encode("utf-8")),
                    ("event_type", event.event_type.value.encode("utf-8")),
                ],
            )
            if hasattr(future, "add_errback"):
                future.add_errback(self._log_publish_error, event)

    @staticmethod
    def _log_publish_error(exc: BaseException, event: ClipEvent) -> None:
        logger.error(
            "viral.ingestion.kafka_send_failed event_id=%s clip_id=%s topic=%s error=%s",
            event.event_id,
            event.clip_id,
            event.kafka_topic,
            exc,
        )


@dataclass(slots=True)
class ViralDispatchRuntime:
    pool_store: ViralDispatchPoolStore
    _subscription_enabled: bool = False
    _closed: bool = False

    def ensure_event_subscription(self, event_publisher: EventPublisher | None) -> None:
        if self._subscription_enabled or self._closed or event_publisher is None:
            return
        event_publisher.subscribe(self.handle_event)
        self._subscription_enabled = True

    def stop(self) -> None:
        self._closed = True

    def handle_event(self, event: DomainEvent) -> None:
        if self._closed or event.name != "viral.clip.dispatch.requested":
            return
        payload = dict(event.payload or {})
        clip_id = _dispatch_clip_id(payload)
        if clip_id is None:
            logger.warning("viral.dispatch.ignored_missing_clip_id event_id=%s", event.event_id)
            return
        initial_score = _dispatch_initial_score(payload)
        normalized_payload = _normalize_dispatch_payload(
            event=event,
            clip_id=clip_id,
            payload=payload,
            initial_score=initial_score,
        )
        try:
            inject_into_distribution_pool(
                clip_id=clip_id,
                score=initial_score,
                payload=normalized_payload,
                store=self.pool_store,
            )
        except Exception:
            logger.exception("viral.dispatch.pool_injection_failed clip_id=%s", clip_id)


def ensure_viral_dispatch_runtime(app: FastAPI) -> ViralDispatchRuntime:
    runtime = getattr(app.state, "viral_dispatch_runtime", None)
    if isinstance(runtime, ViralDispatchRuntime):
        event_publisher = getattr(app.state, "event_publisher", None)
        runtime.ensure_event_subscription(event_publisher)
        return runtime
    runtime = ViralDispatchRuntime(
        pool_store=ensure_viral_dispatch_pool_store(app, settings=getattr(app.state, "settings", None))
    )
    app.state.viral_dispatch_runtime = runtime
    runtime.ensure_event_subscription(getattr(app.state, "event_publisher", None))
    return runtime


def shutdown_viral_dispatch_runtime(app: FastAPI) -> None:
    runtime = getattr(app.state, "viral_dispatch_runtime", None)
    if isinstance(runtime, ViralDispatchRuntime):
        runtime.stop()
    app.state.viral_dispatch_runtime = None
    pool_store = getattr(app.state, "viral_dispatch_pool_store", None)
    if isinstance(pool_store, InMemoryViralDispatchPoolStore):
        pool_store.clear()
    app.state.viral_dispatch_pool_store = None


def _dispatch_clip_id(payload: dict[str, Any]) -> str | None:
    candidate = payload.get("clip_id") or payload.get("base_clip_id") or payload.get("moment_id")
    if candidate is None:
        return None
    normalized = str(candidate).strip()
    return normalized or None


def _dispatch_initial_score(payload: dict[str, Any]) -> float:
    for key in ("priority_score", "initial_score", "ranking_score", "trending_score"):
        if key not in payload:
            continue
        try:
            return max(float(payload.get(key) or 0.0), 0.0)
        except (TypeError, ValueError):
            continue
    return 1.0


def _normalize_dispatch_payload(
    *,
    event: DomainEvent,
    clip_id: str,
    payload: dict[str, Any],
    initial_score: float,
) -> dict[str, Any]:
    normalized = dict(payload)
    metadata = dict(normalized.get("metadata") or {})
    metadata.setdefault("dispatch_event_id", event.event_id)
    metadata.setdefault("dispatch_event_name", event.name)
    metadata.setdefault("dispatch_occurred_at", event.occurred_at.astimezone(UTC).isoformat())
    if event.producer is not None:
        metadata.setdefault("dispatch_producer", event.producer)
    if event.aggregate_id is not None:
        metadata.setdefault("aggregate_id", event.aggregate_id)
    if event.aggregate_type is not None:
        metadata.setdefault("aggregate_type", event.aggregate_type)
    normalized["clip_id"] = clip_id
    normalized["metadata"] = metadata
    normalized.setdefault("initial_score", round(float(initial_score), 6))
    return normalized
