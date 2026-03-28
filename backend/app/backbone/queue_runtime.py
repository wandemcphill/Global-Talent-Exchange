from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event as ThreadEvent, Thread
import traceback

from app.backbone.kafka import KafkaJsonConsumer
from app.competition_engine.queue_contracts import (
    BracketAdvancementJob,
    MatchSimulationJob,
    NotificationJob,
    PayoutSettlementJob,
)
from app.match_engine.services.execution_runtime import LocalMatchExecutionWorker


@dataclass(slots=True)
class ApiQueueConsumerService:
    consumer: KafkaJsonConsumer
    worker: LocalMatchExecutionWorker
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
            if message.topic.endswith("competition.notification.requested"):
                self.worker.execute_notification(NotificationJob.model_validate(job_payload))
                handled += 1
            elif message.topic.endswith("competition.advancement.requested"):
                self.worker.execute_advancement(BracketAdvancementJob.model_validate(job_payload))
                handled += 1
            elif message.topic.endswith("competition.settlement.requested"):
                self.worker.execute_settlement(PayoutSettlementJob.model_validate(job_payload))
                handled += 1
            self.consumer.commit()
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
            self.worker.execute_match_simulation(MatchSimulationJob.model_validate(job_payload))
            self.consumer.commit()
            handled += 1
        return handled

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                traceback.print_exc()
                self._stop_event.wait(1.0)


__all__ = ["ApiQueueConsumerService", "SimulationQueueConsumerService"]
