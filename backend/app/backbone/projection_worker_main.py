from __future__ import annotations

from threading import Event as ThreadEvent

from app.backbone.kafka import KafkaJsonConsumer
from app.backbone.projection_runtime import ProjectionWorkerService
from app.core.config import get_settings
from app.core.container import build_application_context


def main() -> None:
    settings = get_settings()
    if not settings.projection_workers_enabled:
        raise RuntimeError("Projection workers are disabled. Set GTE_PROJECTION_WORKERS_ENABLED=true.")
    context = build_application_context(settings=settings)
    consumer = KafkaJsonConsumer(
        brokers=settings.kafka_brokers,
        group_id=settings.kafka_projection_consumer_group,
        client_id=f"{settings.kafka_client_id}-projections",
        topics=KafkaJsonConsumer.topic_names(
            prefix=settings.kafka_topic_prefix,
            topics=("match.completed",),
        ),
    )
    runtime = ProjectionWorkerService(
        session_factory=context.database.session_factory,
        consumer=consumer,
    )
    runtime.start()
    try:
        ThreadEvent().wait()
    finally:
        runtime.stop()
        outbox_relay = getattr(context, "outbox_relay", None)
        if outbox_relay is not None:
            outbox_relay.stop()
        if hasattr(context.event_publisher, "close"):
            context.event_publisher.close()


if __name__ == "__main__":
    main()
