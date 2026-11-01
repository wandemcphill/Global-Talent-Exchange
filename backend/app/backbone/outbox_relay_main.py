from __future__ import annotations

import logging
import signal
from threading import Event as ThreadEvent

from app.core.config import get_settings
from app.core.container import build_application_context
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or settings.kafka_client_id or "gtex-outbox-relay"
    context = None
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )

    shutdown_event = ThreadEvent()

    def _handle_signal(signum: int, _frame) -> None:
        logger.info("Signal %s received; gracefully shutting down outbox relay...", signum)
        shutdown_event.set()

    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is not None:
            try:
                signal.signal(sig, _handle_signal)
            except Exception:
                pass

    try:
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
            logger.info("Outbox relay disabled. Standing by.")
            shutdown_event.wait()
            return
        shutdown_event.wait()
    except Exception as exc:
        logger.exception("outbox_relay_main unhandled exception: %s", exc)
        raise
    finally:
        if context is not None:
            shutdown = getattr(context, "shutdown", None)
            if callable(shutdown):
                shutdown()
            else:
                outbox_relay = getattr(context, "outbox_relay", None)
                if outbox_relay is not None:
                    outbox_relay.stop()
                if hasattr(context.event_publisher, "close"):
                    context.event_publisher.close()


if __name__ == "__main__":
    main()
