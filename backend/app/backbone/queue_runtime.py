from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event as ThreadEvent, Thread
from time import perf_counter
import traceback

from sqlalchemy.orm import Session, sessionmaker

from app.backbone.event_processing import claim_event, mark_event_failed, mark_event_processed
from app.backbone.kafka import KafkaJsonConsumer
from app.competition_engine.queue_contracts import (
    BracketAdvancementJob,
    MatchSimulationJob,
    NotificationJob,
    PayoutSettlementJob,
)
from app.observability.metrics import GTexMetrics
from app.observability.tracing import start_consumer_span
from typing import Any


@dataclass(slots=True)
class ApiQueueConsumerService:
    consumer: KafkaJsonConsumer
    worker: Any
    metrics: GTexMetrics | None = None
    consumer_name: str = "api-queue-consumer"
    max_attempts: int = 5
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-api-queue-consumer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.consumer.close()

    def poll_once(self) -> int:
        handled = 0
        for message in self.consumer.poll():
            job_payload = dict(message.value.get("payload", {}).get("job_payload") or {})
            carrier = _message_carrier(message)
            claim = None
            session_factory = _worker_session_factory(self.worker)
            started_at = perf_counter()
            job_name = "unknown"
            try:
                claim = _claim_message(
                    session_factory=session_factory,
                    consumer_name=self.consumer_name,
                    message=message,
                    job_payload=job_payload,
                    carrier=carrier,
                    max_attempts=self.max_attempts,
                )
                if session_factory is not None and claim is None:
                    self.consumer.commit()
                    continue
                if message.topic.endswith("competition.notification.requested"):
                    job_name = "notification"
                    with start_consumer_span(
                        "queue.consume.notification",
                        carrier=carrier,
                        attributes={"messaging.destination.name": message.topic},
                    ):
                        self.worker.execute_notification(NotificationJob.model_validate(job_payload))
                elif message.topic.endswith("competition.advancement.requested"):
                    job_name = "bracket_advancement"
                    with start_consumer_span(
                        "queue.consume.bracket_advancement",
                        carrier=carrier,
                        attributes={"messaging.destination.name": message.topic},
                    ):
                        self.worker.execute_advancement(BracketAdvancementJob.model_validate(job_payload))
                elif message.topic.endswith("competition.settlement.requested"):
                    job_name = "payout_settlement"
                    with start_consumer_span(
                        "queue.consume.payout_settlement",
                        carrier=carrier,
                        attributes={"messaging.destination.name": message.topic},
                    ):
                        self.worker.execute_settlement(PayoutSettlementJob.model_validate(job_payload))
                else:
                    raise ValueError(f"Unsupported API queue topic: {message.topic}")
                _mark_processed(session_factory=session_factory, claim=claim)
                self.consumer.commit()
                handled += 1
                if self.metrics is not None:
                    self.metrics.record_queue_message(queue_name="api_queue", job_name=job_name, result="processed")
                    self.metrics.record_worker_job(
                        job_name=job_name,
                        result="success",
                        duration_seconds=perf_counter() - started_at,
                    )
            except Exception as exc:
                if session_factory is not None and claim is not None:
                    dead_lettered = mark_event_failed(
                        session_factory,
                        claim=claim,
                        error=exc,
                        max_attempts=self.max_attempts,
                    )
                    if dead_lettered:
                        self.consumer.commit()
                if self.metrics is not None:
                    self.metrics.record_queue_message(queue_name="api_queue", job_name=job_name, result="error")
                    self.metrics.record_worker_job(
                        job_name=job_name,
                        result="error",
                        duration_seconds=perf_counter() - started_at,
                    )
                raise
        return handled

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                traceback.print_exc()
                self._stop_event.wait(1.0)


@dataclass(slots=True)
class SimulationQueueConsumerService:
    consumer: KafkaJsonConsumer
    worker: Any
    metrics: GTexMetrics | None = None
    consumer_name: str = "simulation-queue-consumer"
    max_attempts: int = 5
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-simulation-queue-consumer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.consumer.close()

    def poll_once(self) -> int:
        handled = 0
        for message in self.consumer.poll():
            job_payload = dict(message.value.get("payload", {}).get("job_payload") or {})
            carrier = _message_carrier(message)
            claim = None
            session_factory = _worker_session_factory(self.worker)
            started_at = perf_counter()
            try:
                claim = _claim_message(
                    session_factory=session_factory,
                    consumer_name=self.consumer_name,
                    message=message,
                    job_payload=job_payload,
                    carrier=carrier,
                    max_attempts=self.max_attempts,
                )
                if session_factory is not None and claim is None:
                    self.consumer.commit()
                    continue
                with start_consumer_span(
                    "queue.consume.match_simulation",
                    carrier=carrier,
                    attributes={"messaging.destination.name": message.topic},
                ):
                    self.worker.execute_match_simulation(MatchSimulationJob.model_validate(job_payload))
                _mark_processed(session_factory=session_factory, claim=claim)
                self.consumer.commit()
                handled += 1
                if self.metrics is not None:
                    self.metrics.record_queue_message(
                        queue_name="match_simulation",
                        job_name="match_simulation",
                        result="processed",
                    )
                    self.metrics.record_worker_job(
                        job_name="match_simulation",
                        result="success",
                        duration_seconds=perf_counter() - started_at,
                    )
            except Exception as exc:
                if session_factory is not None and claim is not None:
                    dead_lettered = mark_event_failed(
                        session_factory,
                        claim=claim,
                        error=exc,
                        max_attempts=self.max_attempts,
                    )
                    if dead_lettered:
                        self.consumer.commit()
                if self.metrics is not None:
                    self.metrics.record_queue_message(
                        queue_name="match_simulation",
                        job_name="match_simulation",
                        result="error",
                    )
                    self.metrics.record_worker_job(
                        job_name="match_simulation",
                        result="error",
                        duration_seconds=perf_counter() - started_at,
                    )
                raise
        return handled

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                traceback.print_exc()
                self._stop_event.wait(1.0)


__all__ = ["ApiQueueConsumerService", "SimulationQueueConsumerService"]


def _message_carrier(message) -> dict[str, str]:
    carrier = {
        str(key): str(value)
        for key, value in dict(message.headers or {}).items()
        if value is not None
    }
    envelope_headers = message.value.get("headers") if isinstance(message.value, dict) else None
    if isinstance(envelope_headers, dict):
        for key, value in envelope_headers.items():
            if value is None:
                continue
            carrier.setdefault(str(key), str(value))
    return carrier


def _message_event_id(message) -> str:
    envelope = message.value if isinstance(message.value, dict) else {}
    raw_event_id = str(envelope.get("event_id") or "").strip()
    if raw_event_id:
        return raw_event_id
    return ":".join(
        [
            str(message.topic or "topic"),
            str(message.partition if message.partition is not None else "partition"),
            str(message.offset if message.offset is not None else "offset"),
        ]
    )


def _worker_session_factory(worker: Any) -> sessionmaker[Session] | None:
    return getattr(worker, "session_factory", None)


def _claim_message(
    *,
    session_factory: sessionmaker[Session] | None,
    consumer_name: str,
    message,
    job_payload: dict[str, object],
    carrier: dict[str, str],
    max_attempts: int,
):
    if session_factory is None:
        return None
    with session_factory() as session:
        claim = claim_event(
            session,
            consumer_name=consumer_name,
            event_id=_message_event_id(message),
            event_type=str(message.topic or "event.unknown"),
            aggregate_id=str(job_payload.get("competition_id") or job_payload.get("fixture_id") or "") or None,
            payload_json=message.value if isinstance(message.value, dict) else {},
            headers_json=carrier,
            max_attempts=max_attempts,
        )
        session.commit()
        return claim


def _mark_processed(*, session_factory: sessionmaker[Session] | None, claim) -> None:
    if session_factory is None or claim is None:
        return
    with session_factory() as session:
        mark_event_processed(session, claim=claim)
        session.commit()
