from __future__ import annotations

import inspect
import logging
import os
from threading import Thread

from app.core.config import get_settings
from app.core.database import DatabaseRuntime
from app.gtex.worker_runtime import (
    WorkerContext,
    build_worker_context,
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


def _build_worker_kwargs(
    worker_fn,
    *,
    settings,
    shared_database: DatabaseRuntime,
    seed_defaults: bool,
    built_contexts: list[WorkerContext],
) -> dict[str, object]:
    parameters = inspect.signature(worker_fn).parameters
    if "context" not in parameters:
        return {}
    context = build_worker_context(
        settings=settings,
        database=shared_database,
        run_migration_check=False,
        seed_defaults=seed_defaults,
    )
    built_contexts.append(context)
    return {"context": context}


def main() -> None:
    settings = get_settings()
    configure_logging(
        json_logs=os.getenv("GTE_LOG_JSON", "false").strip().lower() in {"1", "true", "yes", "on"},
        service_name=os.getenv("GTE_APP_NAME", "Global Talent Exchange GTEX Worker"),
        environment=settings.app_env,
    )
    worker_names = _selected_workers()
    logger.info("gtex.worker_main.start kinds=%s", worker_names)

    # Initialize and migrate the database once on the main thread before spawning
    # worker threads so concurrent threads never race on Alembic global proxies.
    shared_database = DatabaseRuntime.build(settings=settings)
    built_contexts: list[WorkerContext] = []
    worker_specs: list[tuple[str, object, dict[str, object]]] = []
    try:
        shared_database.initialize(run_migration_check=settings.run_migration_check)
        for index, name in enumerate(worker_names):
            worker_fn = _WORKERS[name]
            kwargs = _build_worker_kwargs(
                worker_fn,
                settings=settings,
                shared_database=shared_database,
                seed_defaults=(index == 0),
                built_contexts=built_contexts,
            )
            worker_specs.append((name, worker_fn, kwargs))
    except Exception:
        for context in built_contexts:
            context.shutdown()
        shared_database.close()
        raise

    threads: list[Thread] = []
    for name, worker_fn, kwargs in worker_specs:
        thread = Thread(target=worker_fn, kwargs=kwargs, name=f"gtex-{name}-worker", daemon=False)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
        logger.error("gtex.worker_main.thread_exited thread_name=%s", thread.name)
        raise RuntimeError(f"GTEX worker thread exited unexpectedly: {thread.name}")


if __name__ == "__main__":
    main()
