from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.ledger.models import LedgerEventRecord, LedgerEventType


@dataclass(slots=True)
class LedgerEventService:
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)

    def append_event(
        self,
        session: Session,
        *,
        aggregate_type: str,
        aggregate_id: str,
        user_id: str,
        event_type: LedgerEventType,
        payload: dict[str, Any],
    ) -> LedgerEventRecord:
        event_record = LedgerEventRecord(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            user_id=user_id,
            event_type=event_type,
            payload_json=payload,
        )
        session.add(event_record)
        session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name=event_type.value,
                payload={
                    "aggregate_type": aggregate_type,
                    "aggregate_id": aggregate_id,
                    "user_id": user_id,
                    **payload,
                },
            )
        )
        return event_record
