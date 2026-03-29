from __future__ import annotations

from threading import Event as ThreadEvent

from app.backbone.kafka import KafkaJsonConsumer
from app.backbone.scale_worker_runtime import ScaleTopicConsumerService, build_worker_app, feed_refresh_handler
from app.core.config import get_settings
from app.core.database import DatabaseRuntime
from app.observability.logging import configure_logging


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or f"{settings.kafka_client_id}-feed-worker"
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
    database = DatabaseRuntime.build(settings=settings)
    database.initialize(run_migration_check=settings.run_migration_check)
    app = build_worker_app(
        settings=settings,
        session_factory=database.session_factory,
        read_session_factory=database.read_session_factory,
    )
    consumer = KafkaJsonConsumer(
        brokers=settings.kafka_brokers,
        group_id=f"{settings.kafka_client_id}-feed-workers",
        client_id=f"{settings.kafka_client_id}-feed-worker",
        topics=KafkaJsonConsumer.topic_names(
            prefix=settings.kafka_topic_prefix,
            topics=("feed.cache.refresh.requested",),
        ),
    )
    runtime = ScaleTopicConsumerService(
        consumer=consumer,
        session_factory=database.session_factory,
        handler=feed_refresh_handler(app=app),
    )
    runtime.start()
    try:
        ThreadEvent().wait()
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
