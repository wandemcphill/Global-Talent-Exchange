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
_SESSION_PENDING_KEY = "gtex.session_pending"
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
    transaction = _current_transaction(session)
    if transaction is None:
        publisher.publish(event)
        return
    pending = session.info.setdefault(_POST_COMMIT_EVENTS_KEY, {})
    pending.setdefault(transaction, []).append((publisher, event))


def defer_session_callback_until_commit(session: Session, *, callback: Callable[[], None]) -> None:
    _ensure_session_hooks_registered()
    transaction = _current_transaction(session)
    if transaction is None:
        callback()
        return
    pending = session.info.setdefault(_POST_COMMIT_CALLBACKS_KEY, {})
    pending.setdefault(transaction, []).append(callback)


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
            transaction = _current_transaction(session)
            if transaction is None:
                _flush_pending(session, transaction=_SESSION_PENDING_KEY)
                return
            if session.in_nested_transaction():
                _promote_pending(session, transaction=transaction)
                return
            _flush_pending(session, transaction=transaction)

        @sqlalchemy_event.listens_for(Session, "after_transaction_end")
        def _clear_deferred_state(session: Session, transaction: Any) -> None:
            if transaction is None:
                return
            _discard_pending(session, transaction=transaction)
            if transaction.parent is None:
                _discard_pending(session, transaction=_SESSION_PENDING_KEY)

        _LISTENERS_REGISTERED = True


def _current_transaction(session: Session) -> Any:
    return session.get_nested_transaction() or session.get_transaction() or _SESSION_PENDING_KEY


def _flush_pending(session: Session, *, transaction: Any) -> None:
    pending_events = session.info.setdefault(_POST_COMMIT_EVENTS_KEY, {})
    pending_callbacks = session.info.setdefault(_POST_COMMIT_CALLBACKS_KEY, {})
    for publisher, event in pending_events.pop(transaction, []):
        publisher.publish(event)
    for callback in pending_callbacks.pop(transaction, []):
        callback()


def _promote_pending(session: Session, *, transaction: Any) -> None:
    parent = getattr(transaction, "parent", None) or _SESSION_PENDING_KEY
    pending_events = session.info.setdefault(_POST_COMMIT_EVENTS_KEY, {})
    pending_callbacks = session.info.setdefault(_POST_COMMIT_CALLBACKS_KEY, {})
    child_events = pending_events.pop(transaction, [])
    if child_events:
        pending_events.setdefault(parent, []).extend(child_events)
    child_callbacks = pending_callbacks.pop(transaction, [])
    if child_callbacks:
        pending_callbacks.setdefault(parent, []).extend(child_callbacks)


def _discard_pending(session: Session, *, transaction: Any) -> None:
    pending_events = session.info.get(_POST_COMMIT_EVENTS_KEY)
    if isinstance(pending_events, dict):
        pending_events.pop(transaction, None)
        if not pending_events:
            session.info.pop(_POST_COMMIT_EVENTS_KEY, None)
    pending_callbacks = session.info.get(_POST_COMMIT_CALLBACKS_KEY)
    if isinstance(pending_callbacks, dict):
        pending_callbacks.pop(transaction, None)
        if not pending_callbacks:
            session.info.pop(_POST_COMMIT_CALLBACKS_KEY, None)


__all__ = [
    "build_outbox_event",
    "defer_event_publish_until_commit",
    "defer_session_callback_until_commit",
    "make_json_safe",
]
