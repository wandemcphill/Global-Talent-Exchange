from __future__ import annotations

from threading import Event as ThreadEvent

from app.backbone.kafka import KafkaJsonConsumer
from app.backbone.scale_worker_runtime import ScaleTopicConsumerService, build_worker_app, creator_earnings_handler
from app.core.config import get_settings
from app.core.database import DatabaseRuntime
from app.observability.logging import configure_logging


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or f"{settings.kafka_client_id}-earnings-worker"
    database = None
    runtime = None
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
    try:
        database = DatabaseRuntime.build(settings=settings)
        database.initialize(run_migration_check=settings.run_migration_check)
        app = build_worker_app(
            settings=settings,
            session_factory=database.session_factory,
            read_session_factory=database.read_session_factory,
        )
        if settings.observability_metrics_enabled:
            app.state.metrics.start_http_server(settings.observability_metrics_port)
        app.state.metrics.refresh_from_database()
        consumer = KafkaJsonConsumer(
            brokers=settings.kafka_brokers,
            group_id=f"{settings.kafka_client_id}-earnings-workers",
            client_id=f"{settings.kafka_client_id}-earnings-worker",
            topics=KafkaJsonConsumer.topic_names(
                prefix=settings.kafka_topic_prefix,
                topics=("creator.earnings.recompute.requested",),
            ),
        )
        runtime = ScaleTopicConsumerService(
            consumer=consumer,
            session_factory=database.session_factory,
            handler=creator_earnings_handler(),
            consumer_name="creator-earnings-worker",
            metrics=app.state.metrics,
        )
        runtime.start()
        ThreadEvent().wait()
    finally:
        if runtime is not None:
            runtime.stop()
        if database is not None:
            database.close()


if __name__ == "__main__":
    main()
