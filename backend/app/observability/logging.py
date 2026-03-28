from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any

try:
    from opentelemetry import trace
except Exception:  # pragma: no cover - optional dependency
    trace = None

_RESERVED_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonLogFormatter(logging.Formatter):
    def __init__(self, *, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "thread": record.threadName,
        }
        if trace is not None:
            span_context = trace.get_current_span().get_span_context()
            if span_context.is_valid:
                payload["trace_id"] = f"{span_context.trace_id:032x}"
                payload["span_id"] = f"{span_context.span_id:016x}"
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _RESERVED_LOG_RECORD_FIELDS:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, json_logs: bool, service_name: str, environment: str) -> None:
    formatter: logging.Formatter
    if json_logs:
        formatter = JsonLogFormatter(service_name=service_name, environment=environment)
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    target_loggers = (
        logging.getLogger(),
        logging.getLogger("gunicorn.error"),
        logging.getLogger("gunicorn.access"),
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("uvicorn.access"),
    )

    seen_handler_ids: set[int] = set()
    configured_handlers = 0
    for logger in target_loggers:
        for handler in logger.handlers:
            if id(handler) in seen_handler_ids:
                continue
            handler.setFormatter(formatter)
            configured_handlers += 1
            seen_handler_ids.add(id(handler))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if configured_handlers == 0:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
