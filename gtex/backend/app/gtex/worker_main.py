from __future__ import annotations

import logging
import os
from threading import Thread

from app.gtex.worker_runtime import (
    run_ai_brain_worker,
    run_ai_matchmaker_worker,
    run_jackpot_worker,
    run_valuation_worker,
)
from app.observability.logging import configure_logging

logger = logging.getLogger(__name__)

_WORKERS = {
    "jackpot": run_jackpot_worker,
    "valuation": run_valuation_worker,
    "matchmaker": run_ai_matchmaker_worker,
    "brain": run_ai_brain_worker,
}


def _selected_workers() -> list[str]:
    raw_value = os.getenv("GTE_GTEX_WORKERS", "valuation,matchmaker,brain,jackpot")
    selected = [item.strip().lower() for item in raw_value.split(",") if item.strip()]
    invalid = [item for item in selected if item not in _WORKERS]
    if invalid:
        raise ValueError(f"Unsupported GTEX worker kinds: {', '.join(sorted(invalid))}")
    if not selected:
        raise ValueError("At least one GTEX worker kind must be configured.")
    return selected


def main() -> None:
    configure_logging(
        json_logs=os.getenv("GTE_LOG_JSON", "false").strip().lower() in {"1", "true", "yes", "on"},
        service_name=os.getenv("GTE_APP_NAME", "Global Talent Exchange GTEX Worker"),
        environment=os.getenv("GTE_APP_ENV", "development"),
    )
    worker_names = _selected_workers()
    logger.info("gtex.worker_main.start kinds=%s", worker_names)
    threads: list[Thread] = []
    for name in worker_names:
        thread = Thread(target=_WORKERS[name], name=f"gtex-{name}-worker", daemon=False)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
        logger.error("gtex.worker_main.thread_exited thread_name=%s", thread.name)
        raise RuntimeError(f"GTEX worker thread exited unexpectedly: {thread.name}")


if __name__ == "__main__":
    main()
