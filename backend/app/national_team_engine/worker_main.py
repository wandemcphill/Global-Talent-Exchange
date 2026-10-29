from __future__ import annotations

import logging
import os
import signal
from threading import Event

from app.core.config import get_settings
from app.core.container import build_application_context
from app.national_team_engine.worker import NationalTeamLifecycleScheduler
from app.observability.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name="gtex-national-team-worker",
        environment=settings.app_env,
    )
    enabled = os.getenv("GTE_NATIONAL_TEAM_WORKER_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled:
        raise RuntimeError("GTE_NATIONAL_TEAM_WORKER_ENABLED must be true for the dedicated worker.")

    interval_seconds = max(10.0, float(os.getenv("GTE_NATIONAL_TEAM_WORKER_INTERVAL_SECONDS", "300")))
    context = build_application_context(settings=settings)
    scheduler = NationalTeamLifecycleScheduler(
        session_factory=context.database.session_factory,
        interval_seconds=interval_seconds,
    )
    stop_event = Event()
    previous_handlers = {}

    def request_stop(signum, _frame) -> None:
        logger.info("national_team.worker.stop_requested signal=%s", signum)
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[sig] = signal.signal(sig, request_stop)

    logger.info(
        "national_team.worker.started interval_seconds=%s",
        interval_seconds,
    )
    try:
        while not stop_event.is_set():
            try:
                summary = scheduler.run_once()
                cleanup = summary.get("rental_cleanup", {})
                logger.info(
                    "national_team.worker.cycle_complete released_contracts=%s expiring_notifications=%s",
                    cleanup.get("released_contracts", 0),
                    cleanup.get("expiring_notifications", 0),
                )
            except Exception:
                # run_once rolls its transaction back; keep the worker alive and retry next cycle.
                logger.exception("national_team.worker.cycle_failed")
            stop_event.wait(interval_seconds)
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        context.shutdown()
        logger.info("national_team.worker.stopped")


if __name__ == "__main__":
    main()
