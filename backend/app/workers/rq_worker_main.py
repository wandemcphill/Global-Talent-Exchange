from __future__ import annotations

from app.core.config import get_settings
from app.core.task_queue import build_worker
from app.observability.logging import configure_logging


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or f"{settings.kafka_client_id}-jobs"
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
    worker = build_worker(settings)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
