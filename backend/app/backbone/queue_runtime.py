from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event as ThreadEvent, Thread
from time import perf_counter
import traceback

from app.backbone.kafka import KafkaJsonConsumer
from app.competition_engine.queue_contracts import (
    BracketAdvancementJob,
    MatchSimulationJob,
    NotificationJob,
    PayoutSettlementJob,
)
from app.match_engine.services.execution_runtime import LocalMatchExecutionWorker
from app.observability.metrics import GTexMetrics
from app.observability.tracing import start_consumer_span


@dataclass(slots=True)
class ApiQueueConsumerService:
    consumer: KafkaJsonConsumer
    worker: LocalMatchExecutionWorker
    metrics: GTexMetrics | None = None
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
            started_at = perf_counter()
            job_name = "unknown"
            try:
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
                    continue
                self.consumer.commit()
                handled += 1
                if self.metrics is not None:
                    self.metrics.record_queue_message(queue_name="api_queue", job_name=job_name, result="processed")
                    self.metrics.record_worker_job(
                        job_name=job_name,
                        result="success",
                        duration_seconds=perf_counter() - started_at,
                    )
            except Exception:
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
    worker: LocalMatchExecutionWorker
    metrics: GTexMetrics | None = None
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
            started_at = perf_counter()
            try:
                with start_consumer_span(
                    "queue.consume.match_simulation",
                    carrier=carrier,
                    attributes={"messaging.destination.name": message.topic},
                ):
                    self.worker.execute_match_simulation(MatchSimulationJob.model_validate(job_payload))
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
            except Exception:
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
