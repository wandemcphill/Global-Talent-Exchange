from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Protocol
from uuid import uuid4

from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher

JobCallable = Callable[[], Any]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class JobExecution:
    job_id: str
    name: str
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: Any = None


class BackgroundJobBackend(Protocol):
    def run(self, name: str, operation: JobCallable) -> JobExecution:
        ...

    def list_recent(self, limit: int = 20) -> list[JobExecution]:
        ...


@dataclass(slots=True)
class InlineJobBackend:
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)
    _executions: list[JobExecution] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock)

    def run(self, name: str, operation: JobCallable) -> JobExecution:
        execution = JobExecution(
            job_id=f"job_{uuid4().hex[:12]}",
            name=name,
            status="queued",
            queued_at=utcnow(),
        )
        with self._lock:
            self._executions.append(execution)

        execution.status = "running"
        execution.started_at = utcnow()
        self.event_publisher.publish(
            DomainEvent(
                name="jobs.started",
                payload={"job_id": execution.job_id, "name": execution.name},
            )
        )
        try:
            execution.result = operation()
            execution.status = "success"
            return execution
        except Exception as exc:
            execution.status = "failed"
            execution.error = str(exc)
            raise
        finally:
            execution.finished_at = utcnow()
            self.event_publisher.publish(
                DomainEvent(
                    name=f"jobs.{execution.status}",
                    payload={
                        "job_id": execution.job_id,
                        "name": execution.name,
                        "error": execution.error,
                    },
                )
            )

    def list_recent(self, limit: int = 20) -> list[JobExecution]:
        with self._lock:
            return list(self._executions[-limit:])
