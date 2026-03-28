from __future__ import annotations

from threading import Event as ThreadEvent

from app.backbone.kafka import KafkaJsonConsumer
from app.backbone.projection_runtime import ProjectionWorkerService
from app.core.config import get_settings
from app.core.container import build_application_context
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or settings.kafka_client_id or "gtex-projection-worker"
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
    if not settings.projection_workers_enabled:
        raise RuntimeError("Projection workers are disabled. Set GTE_PROJECTION_WORKERS_ENABLED=true.")
    context = build_application_context(settings=settings)
    configure_tracing(
        enabled=settings.observability_tracing_enabled,
        service_name=service_name,
        environment=settings.app_env,
        service_version=settings.app_version,
        exporter_endpoint=settings.observability_otlp_traces_endpoint,
        sample_ratio=settings.observability_trace_sample_ratio,
        engine=context.database.engine,
    )
    if settings.observability_metrics_enabled:
        context.metrics.start_http_server(settings.observability_metrics_port)
    context.metrics.refresh_from_database()
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
        metrics=context.metrics,
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
