from __future__ import annotations

from threading import Event as ThreadEvent

from app.core.config import get_settings
from app.core.container import build_application_context
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or settings.kafka_client_id or "gtex-outbox-relay"
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
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
    outbox_relay = getattr(context, "outbox_relay", None)
    if outbox_relay is None:
        raise RuntimeError("Outbox relay is not enabled. Set GTE_KAFKA_BROKERS and GTE_OUTBOX_RELAY_ENABLED.")
    try:
        ThreadEvent().wait()
    finally:
        outbox_relay.stop()
        if hasattr(context.event_publisher, "close"):
            context.event_publisher.close()


if __name__ == "__main__":
    main()
