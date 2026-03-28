from __future__ import annotations

from threading import Event as ThreadEvent

from app.core.config import get_settings
from app.core.container import build_application_context


def main() -> None:
    settings = get_settings()
    context = build_application_context(settings=settings)
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
