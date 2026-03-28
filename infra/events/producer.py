from __future__ import annotations

import atexit
import json
import os
from collections.abc import Mapping
from typing import Any

DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
DEFAULT_TOPIC = "match.events"
DEFAULT_CLIENT_ID = "gtex-match-events-producer"

_BOOTSTRAP_SERVERS_ENV = "GTE_EVENT_PIPELINE_BOOTSTRAP_SERVERS"
_TOPIC_ENV = "GTE_EVENT_PIPELINE_TOPIC"
_CLIENT_ID_ENV = "GTE_EVENT_PIPELINE_PRODUCER_CLIENT_ID"

_PRODUCER: Any | None = None


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


def create_producer(
    *,
    bootstrap_servers: str | list[str] | tuple[str, ...] | None = None,
    client_id: str | None = None,
) -> Any:
    from kafka import KafkaProducer  # type: ignore[import-not-found]

    servers = resolve_bootstrap_servers(",".join(bootstrap_servers) if isinstance(bootstrap_servers, (list, tuple)) else bootstrap_servers)
    return KafkaProducer(
        bootstrap_servers=servers,
        client_id=(client_id or os.getenv(_CLIENT_ID_ENV, DEFAULT_CLIENT_ID)).strip() or DEFAULT_CLIENT_ID,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8") if value is not None else None,
        linger_ms=20,
    )


def get_producer() -> Any:
    global _PRODUCER
    if _PRODUCER is None:
        _PRODUCER = create_producer()
    return _PRODUCER


def _default_message_key(event: Mapping[str, Any]) -> str | None:
    for field in ("match_id", "fixture_id", "event_id"):
        value = event.get(field)
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _encode_headers(headers: Mapping[str, Any] | None) -> list[tuple[str, bytes]] | None:
    if not headers:
        return None
    return [(str(key), str(value).encode("utf-8")) for key, value in headers.items()]


def publish_event(
    event: Mapping[str, Any],
    *,
    topic: str | None = None,
    key: str | None = None,
    headers: Mapping[str, Any] | None = None,
    producer: Any | None = None,
) -> None:
    active_producer = producer or get_producer()
    future = active_producer.send(
        resolve_topic(topic),
        value=dict(event),
        key=key or _default_message_key(event),
        headers=_encode_headers(headers),
    )
    if hasattr(future, "get"):
        future.get(timeout=30)
    if hasattr(active_producer, "flush"):
        active_producer.flush()


def close_producer() -> None:
    global _PRODUCER
    if _PRODUCER is not None and hasattr(_PRODUCER, "close"):
        _PRODUCER.close()
    _PRODUCER = None


atexit.register(close_producer)


__all__ = [
    "close_producer",
    "create_producer",
    "get_producer",
    "publish_event",
    "resolve_bootstrap_servers",
    "resolve_topic",
]

