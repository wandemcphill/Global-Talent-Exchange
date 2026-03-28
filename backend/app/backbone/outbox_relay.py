from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Event as ThreadEvent, Thread
import traceback
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.backbone.kafka import KafkaJsonProducer
from app.backbone.routing import OutboxTopicRouter
from app.models.event_backbone import EventOutbox


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class OutboxRelayService:
    session_factory: sessionmaker[Session]
    producer: KafkaJsonProducer
    router: OutboxTopicRouter
    batch_size: int = 100
    poll_interval_ms: int = 1000
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._run_loop,
            name="gtex-outbox-relay",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.producer.close()

    def relay_once(self) -> int:
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(EventOutbox)
                    .where(EventOutbox.status == "pending")
                    .order_by(EventOutbox.occurred_at.asc(), EventOutbox.id.asc())
                    .limit(self.batch_size)
                ).all()
            )
            if not rows:
                return 0

            delivered = 0
            for row in rows:
                row.relay_attempts += 1
                envelope = self._envelope(row)
                topic = self.router.topic_for(row.event_type)
                try:
                    self.producer.send(
                        topic=topic,
                        key=row.partition_key or row.aggregate_id or row.event_id,
                        value=envelope,
                        headers={"event_type": row.event_type, "producer": row.producer},
                    )
                except Exception as exc:
                    row.last_error = f"{type(exc).__name__}: {exc}"
                    row.status = "pending"
                    session.commit()
                    continue
                row.status = "processed"
                row.processed_at = utcnow()
                row.last_error = None
                delivered += 1
            session.commit()
            return delivered

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.relay_once()
            except Exception:
                traceback.print_exc()
            self._stop_event.wait(max(self.poll_interval_ms, 100) / 1000)

    @staticmethod
    def _envelope(row: EventOutbox) -> dict[str, Any]:
        return {
            "event_id": row.event_id,
            "event_type": row.event_type,
            "aggregate_id": row.aggregate_id,
            "aggregate_type": row.aggregate_type,
            "version": row.version,
            "timestamp": row.occurred_at.isoformat(),
            "producer": row.producer,
            "partition_key": row.partition_key,
            "payload": dict(row.payload_json or {}),
            "headers": dict(row.headers_json or {}),
        }


__all__ = ["OutboxRelayService"]
