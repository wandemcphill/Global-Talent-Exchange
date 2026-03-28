from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from threading import Lock
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session

from app.models.event_backbone import EventOutbox

_POST_COMMIT_EVENTS_KEY = "gtex.post_commit_events"
_POST_COMMIT_CALLBACKS_KEY = "gtex.post_commit_callbacks"
_LISTENER_LOCK = Lock()
_LISTENERS_REGISTERED = False


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return make_json_safe(value.value)
    if isinstance(value, BaseModel):
        return make_json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [make_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump(mode="json"))
    return str(value)


def build_outbox_event(*, domain_event: Any) -> EventOutbox:
    if hasattr(domain_event, "envelope"):
        envelope = domain_event.envelope()
    else:
        envelope = {
            "event_id": getattr(domain_event, "event_id"),
            "event_type": getattr(domain_event, "event_type", getattr(domain_event, "name", "event.unknown")),
            "aggregate_id": getattr(domain_event, "aggregate_id", None),
            "aggregate_type": getattr(domain_event, "aggregate_type", None),
            "version": getattr(domain_event, "version", 1),
            "timestamp": getattr(domain_event, "occurred_at"),
            "producer": getattr(domain_event, "producer", None) or "gtex",
            "partition_key": getattr(domain_event, "partition_key", None),
            "payload": make_json_safe(getattr(domain_event, "payload", {})),
            "headers": make_json_safe(getattr(domain_event, "headers", {})),
        }

    return EventOutbox(
        event_id=str(envelope["event_id"]),
        event_type=str(envelope["event_type"]),
        aggregate_type=_optional_string(envelope.get("aggregate_type")),
        aggregate_id=_optional_string(envelope.get("aggregate_id")),
        partition_key=_optional_string(envelope.get("partition_key")),
        producer=str(envelope.get("producer") or "gtex"),
        version=int(envelope.get("version") or 1),
        occurred_at=_coerce_datetime(envelope.get("timestamp")),
        payload_json=make_json_safe(envelope.get("payload") or {}),
        headers_json=make_json_safe(envelope.get("headers") or {}),
    )


def defer_event_publish_until_commit(session: Session, *, publisher: Any, event: Any) -> None:
    _ensure_session_hooks_registered()
    pending = session.info.setdefault(_POST_COMMIT_EVENTS_KEY, [])
    pending.append((publisher, event))


def defer_session_callback_until_commit(session: Session, *, callback: Callable[[], None]) -> None:
    _ensure_session_hooks_registered()
    pending = session.info.setdefault(_POST_COMMIT_CALLBACKS_KEY, [])
    pending.append(callback)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"Unsupported timestamp value for outbox event: {value!r}")


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


def _ensure_session_hooks_registered() -> None:
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return
    with _LISTENER_LOCK:
        if _LISTENERS_REGISTERED:
            return

        @sqlalchemy_event.listens_for(Session, "after_commit")
        def _publish_deferred_events(session: Session) -> None:
            pending = session.info.pop(_POST_COMMIT_EVENTS_KEY, [])
            for publisher, event in pending:
                publisher.publish(event)
            callbacks = session.info.pop(_POST_COMMIT_CALLBACKS_KEY, [])
            for callback in callbacks:
                callback()

        @sqlalchemy_event.listens_for(Session, "after_rollback")
        def _clear_deferred_events_on_rollback(session: Session) -> None:
            session.info.pop(_POST_COMMIT_EVENTS_KEY, None)
            session.info.pop(_POST_COMMIT_CALLBACKS_KEY, None)

        @sqlalchemy_event.listens_for(Session, "after_soft_rollback")
        def _clear_deferred_events_on_soft_rollback(session: Session, previous_transaction: Any) -> None:
            del previous_transaction
            session.info.pop(_POST_COMMIT_EVENTS_KEY, None)
            session.info.pop(_POST_COMMIT_CALLBACKS_KEY, None)

        _LISTENERS_REGISTERED = True


__all__ = [
    "build_outbox_event",
    "defer_event_publish_until_commit",
    "defer_session_callback_until_commit",
    "make_json_safe",
]
