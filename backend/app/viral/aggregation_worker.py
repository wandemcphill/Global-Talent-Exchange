from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from threading import Event as ThreadEvent

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from app.backbone.kafka import KafkaJsonConsumer, KafkaMessage
from app.core.config import Settings, get_settings
from app.observability.logging import configure_logging
from app.viral.ingestion_runtime import ClipEventTopicManager
from app.viral.ingestion_schemas import CLIP_EVENT_TOPICS, CLIP_METRIC_FIELDS, ClipEvent, ClipEventType
from app.viral.trust import LOW_TRUST_THRESHOLD

logger = logging.getLogger(__name__)

CLIP_EVENT_DEDUPE_KEY_PATTERN = "clip:event:{event_id}"
CLIP_METRICS_KEY_PATTERN = "clip:{clip_id}:metrics"
CLIP_VELOCITY_KEY_PATTERN = "clip:{clip_id}:velocity"
CLIP_LOW_TRUST_VELOCITY_KEY_PATTERN = "clip:{clip_id}:velocity:low_trust"
CLIP_TRUST_METRICS_KEY_PATTERN = "clip:{clip_id}:trust"
VELOCITY_HASH_TTL_SECONDS = 60 * 60 * 2


def clip_metrics_key(clip_id: str) -> str:
    return CLIP_METRICS_KEY_PATTERN.format(clip_id=clip_id)


def clip_event_dedupe_key(event_id: str) -> str:
    return CLIP_EVENT_DEDUPE_KEY_PATTERN.format(event_id=event_id)


def clip_velocity_key(clip_id: str) -> str:
    return CLIP_VELOCITY_KEY_PATTERN.format(clip_id=clip_id)


def clip_low_trust_velocity_key(clip_id: str) -> str:
    return CLIP_LOW_TRUST_VELOCITY_KEY_PATTERN.format(clip_id=clip_id)


def clip_trust_metrics_key(clip_id: str) -> str:
    return CLIP_TRUST_METRICS_KEY_PATTERN.format(clip_id=clip_id)


@dataclass(frozen=True, slots=True)
class ClipEventAggregationResult:
    received: int = 0
    processed: int = 0
    duplicates: int = 0
    invalid: int = 0
    shadow_banned: int = 0


@dataclass
class ClipEventAggregationService:
    redis_client: Redis
    dedupe_ttl_seconds: int

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ClipEventAggregationService":
        resolved_settings = settings or get_settings()
        if not resolved_settings.redis_url:
            raise RuntimeError("Redis is required for clip analytics aggregation.")
        return cls(
            redis_client=Redis.from_url(
                resolved_settings.redis_url,
                decode_responses=True,
                health_check_interval=30,
            ),
            dedupe_ttl_seconds=resolved_settings.viral_event_dedupe_ttl_seconds,
        )

    def process_messages(self, messages: Sequence[KafkaMessage]) -> ClipEventAggregationResult:
        valid_events: list[ClipEvent] = []
        invalid_events = 0
        for message in messages:
            try:
                valid_events.append(ClipEvent.model_validate(message.value))
            except ValidationError:
                invalid_events += 1
                logger.warning("viral.aggregation.invalid_message topic=%s payload=%s", message.topic, message.value)
        if not valid_events:
            return ClipEventAggregationResult(
                received=len(messages),
                processed=0,
                duplicates=0,
                invalid=invalid_events,
                shadow_banned=0,
            )
        processed = 0
        duplicates = 0
        shadow_banned = 0
        for event in valid_events:
            if not self._claim_event(str(event.event_id)):
                duplicates += 1
                continue
            processed += 1
            if event.trust.shadow_banned:
                shadow_banned += 1
            self._apply_weighted_metrics(event)
        return ClipEventAggregationResult(
            received=len(messages),
            processed=processed,
            duplicates=duplicates,
            invalid=invalid_events,
            shadow_banned=shadow_banned,
        )

    def close(self) -> None:
        try:
            self.redis_client.close()
        except Exception:
            logger.warning("viral.aggregation.redis_close_failed")

    def _claim_event(self, event_id: str) -> bool:
        result = self.redis_client.set(
            clip_event_dedupe_key(event_id),
            "1",
            nx=True,
            ex=self.dedupe_ttl_seconds,
        )
        return bool(result)

    def _apply_weighted_metrics(self, event: ClipEvent) -> None:
        deltas = event.weighted_redis_metric_deltas
        bucket = _minute_bucket(event.timestamp)
        pipeline = self.redis_client.pipeline(transaction=False)
        for field_name, delta in deltas.items():
            pipeline.hincrbyfloat(clip_metrics_key(event.clip_id), field_name, float(delta))
        pipeline.expire(clip_metrics_key(event.clip_id), max(self.dedupe_ttl_seconds, VELOCITY_HASH_TTL_SECONDS))
        pipeline.hincrbyfloat(clip_trust_metrics_key(event.clip_id), "trust_weight_sum", float(event.trust.trust_score))
        pipeline.hincrbyfloat(clip_trust_metrics_key(event.clip_id), "event_count", 1.0)
        if event.trust.shadow_banned:
            pipeline.hincrbyfloat(clip_trust_metrics_key(event.clip_id), "shadow_banned_events", 1.0)
        if event.event_type is ClipEventType.VIEW:
            if event.trust.velocity_weight > 0:
                pipeline.hincrbyfloat(clip_velocity_key(event.clip_id), bucket, float(event.trust.velocity_weight))
                pipeline.expire(clip_velocity_key(event.clip_id), VELOCITY_HASH_TTL_SECONDS)
            if event.trust.trust_score < LOW_TRUST_THRESHOLD:
                pipeline.hincrbyfloat(clip_low_trust_velocity_key(event.clip_id), bucket, 1.0)
                pipeline.expire(clip_low_trust_velocity_key(event.clip_id), VELOCITY_HASH_TTL_SECONDS)
        pipeline.expire(clip_trust_metrics_key(event.clip_id), VELOCITY_HASH_TTL_SECONDS)
        pipeline.execute()


@dataclass
class ClipEventAggregationWorker:
    consumer: KafkaJsonConsumer
    aggregator: ClipEventAggregationService

    def __post_init__(self) -> None:
        self._stop_event = ThreadEvent()

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            messages = self.consumer.poll()
            if not messages:
                continue
            self.aggregator.process_messages(messages)
            self.consumer.commit()

    def stop(self) -> None:
        self._stop_event.set()
        self.consumer.close()
        self.aggregator.close()


def redis_schema() -> dict[str, object]:
    return {
        "metrics_key_pattern": CLIP_METRICS_KEY_PATTERN,
        "dedupe_key_pattern": CLIP_EVENT_DEDUPE_KEY_PATTERN,
        "velocity_key_pattern": CLIP_VELOCITY_KEY_PATTERN,
        "low_trust_velocity_key_pattern": CLIP_LOW_TRUST_VELOCITY_KEY_PATTERN,
        "trust_key_pattern": CLIP_TRUST_METRICS_KEY_PATTERN,
        "metric_fields": list(CLIP_METRIC_FIELDS),
        "topics": list(CLIP_EVENT_TOPICS),
    }


def _minute_bucket(value: datetime) -> str:
    resolved = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return str(int(resolved.astimezone(UTC).timestamp() // 60))


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or f"{settings.kafka_client_id}-clip-analytics"
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
    if not settings.kafka_brokers:
        raise RuntimeError("Kafka brokers are required for the clip analytics worker.")
    if not settings.redis_url:
        raise RuntimeError("Redis is required for the clip analytics worker.")
    ClipEventTopicManager(
        brokers=settings.kafka_brokers,
        client_id=settings.kafka_client_id,
        partitions=settings.viral_event_topic_partitions,
        replication_factor=settings.viral_event_topic_replication_factor,
    ).ensure_topics()
    consumer = KafkaJsonConsumer(
        brokers=settings.kafka_brokers,
        group_id=settings.viral_event_consumer_group,
        client_id=f"{settings.kafka_client_id}-clip-analytics",
        topics=CLIP_EVENT_TOPICS,
        poll_timeout_ms=250,
    )
    worker = ClipEventAggregationWorker(
        consumer=consumer,
        aggregator=ClipEventAggregationService.from_settings(settings),
    )
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        logger.info("viral.aggregation.stopping")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
