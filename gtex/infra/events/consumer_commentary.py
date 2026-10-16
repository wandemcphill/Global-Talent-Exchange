from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Iterable, Mapping
from typing import Any

import requests

DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
DEFAULT_TOPIC = "match.events"
DEFAULT_GROUP_ID = "gtex-commentary"
DEFAULT_CLIENT_ID = "gtex-commentary-consumer"
DEFAULT_ENDPOINT = "http://commentary:8000/commentary"
DEFAULT_TIMEOUT_SECONDS = 5.0

_BOOTSTRAP_SERVERS_ENV = "GTE_EVENT_PIPELINE_BOOTSTRAP_SERVERS"
_TOPIC_ENV = "GTE_EVENT_PIPELINE_TOPIC"
_GROUP_ID_ENV = "GTE_EVENT_PIPELINE_COMMENTARY_GROUP_ID"
_CLIENT_ID_ENV = "GTE_EVENT_PIPELINE_COMMENTARY_CLIENT_ID"
_ENDPOINT_ENV = "GTE_EVENT_PIPELINE_COMMENTARY_URL"
_TIMEOUT_ENV = "GTE_EVENT_PIPELINE_COMMENTARY_TIMEOUT_SECONDS"

logger = logging.getLogger(__name__)


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_bootstrap_servers(raw: str | None = None) -> list[str]:
    candidate = raw if raw is not None else os.getenv(_BOOTSTRAP_SERVERS_ENV, DEFAULT_BOOTSTRAP_SERVERS)
    servers = _split_csv(candidate)
    return servers or [DEFAULT_BOOTSTRAP_SERVERS]


def resolve_topic(raw: str | None = None) -> str:
    candidate = raw if raw is not None else os.getenv(_TOPIC_ENV, DEFAULT_TOPIC)
    normalized = candidate.strip()
    return normalized or DEFAULT_TOPIC


def resolve_endpoint(raw: str | None = None) -> str:
    candidate = raw if raw is not None else os.getenv(_ENDPOINT_ENV, DEFAULT_ENDPOINT)
    normalized = candidate.strip()
    return normalized or DEFAULT_ENDPOINT


def resolve_timeout_seconds(raw: float | str | None = None) -> float:
    candidate = raw if raw is not None else os.getenv(_TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(float(candidate), 0.1)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def create_consumer(
    *,
    bootstrap_servers: str | list[str] | tuple[str, ...] | None = None,
    topic: str | None = None,
    group_id: str | None = None,
    client_id: str | None = None,
) -> Any:
    from kafka import KafkaConsumer  # type: ignore[import-not-found]

    servers = resolve_bootstrap_servers(",".join(bootstrap_servers) if isinstance(bootstrap_servers, (list, tuple)) else bootstrap_servers)
    return KafkaConsumer(
        resolve_topic(topic),
        bootstrap_servers=servers,
        group_id=(group_id or os.getenv(_GROUP_ID_ENV, DEFAULT_GROUP_ID)).strip() or DEFAULT_GROUP_ID,
        client_id=(client_id or os.getenv(_CLIENT_ID_ENV, DEFAULT_CLIENT_ID)).strip() or DEFAULT_CLIENT_ID,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def _commit(consumer: Any) -> None:
    if hasattr(consumer, "commit"):
        consumer.commit()


def _idempotency_key(event: Mapping[str, Any]) -> str:
    event_id = event.get("event_id")
    if event_id is not None and str(event_id).strip():
        return str(event_id).strip()
    match_id = str(event.get("match_id") or "").strip()
    minute = event.get("minute")
    event_type = str(event.get("event_type") or event.get("type") or "").strip()
    if match_id and minute is not None and event_type:
        return f"{match_id}:{minute}:{event_type}"
    fingerprint = json.dumps(dict(event), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(fingerprint).hexdigest()


def deliver_commentary_event(
    event: Mapping[str, Any],
    *,
    endpoint: str | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float | None = None,
) -> None:
    managed_session = session or requests.Session()
    created_session = session is None
    try:
        response = managed_session.post(
            resolve_endpoint(endpoint),
            json=dict(event),
            timeout=resolve_timeout_seconds(timeout_seconds),
            headers={"Idempotency-Key": _idempotency_key(event)},
        )
        response.raise_for_status()
    finally:
        if created_session:
            managed_session.close()


def process_stream(
    consumer: Iterable[object],
    *,
    endpoint: str | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float | None = None,
) -> int:
    delivered = 0
    for message in consumer:
        payload = getattr(message, "value", message)
        if not isinstance(payload, Mapping):
            logger.warning("commentary_consumer.skipping_invalid_payload", extra={"payload_type": type(payload).__name__})
            _commit(consumer)
            continue
        deliver_commentary_event(payload, endpoint=endpoint, session=session, timeout_seconds=timeout_seconds)
        _commit(consumer)
        delivered += 1
    return delivered


def run_consumer(
    *,
    consumer: Any | None = None,
    endpoint: str | None = None,
    session: requests.Session | None = None,
    timeout_seconds: float | None = None,
) -> int:
    managed_consumer = consumer or create_consumer()
    managed_session = session or requests.Session()
    created_consumer = consumer is None
    created_session = session is None
    try:
        return process_stream(
            managed_consumer,
            endpoint=endpoint,
            session=managed_session,
            timeout_seconds=timeout_seconds,
        )
    finally:
        if created_session:
            managed_session.close()
        if created_consumer and hasattr(managed_consumer, "close"):
            managed_consumer.close()


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    run_consumer()


if __name__ == "__main__":
    main()

