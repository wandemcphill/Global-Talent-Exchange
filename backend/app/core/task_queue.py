from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Protocol

from redis import Redis
from redis.exceptions import RedisError
from rq import Queue, Retry, Worker
from rq.job import Job

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

TaskCallable = Callable[..., Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class TaskExecution:
    job_id: str
    name: str
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: Any = None
    owner_user_id: str | None = None


class TaskQueueBackend(Protocol):
    def enqueue(
        self,
        *,
        name: str,
        callable_: TaskCallable,
        kwargs: dict[str, Any] | None = None,
        job_id: str | None = None,
        timeout_seconds: int = 60,
        retry_intervals_seconds: Sequence[int] = (),
        owner_user_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> TaskExecution:
        ...

    def get(self, job_id: str) -> TaskExecution | None:
        ...


class NullTaskQueueBackend:
    def enqueue(
        self,
        *,
        name: str,
        callable_: TaskCallable,
        kwargs: dict[str, Any] | None = None,
        job_id: str | None = None,
        timeout_seconds: int = 60,
        retry_intervals_seconds: Sequence[int] = (),
        owner_user_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> TaskExecution:
        del name, callable_, kwargs, job_id, timeout_seconds, retry_intervals_seconds, owner_user_id, meta
        raise RuntimeError("Task queue is unavailable.")

    def get(self, job_id: str) -> TaskExecution | None:
        del job_id
        return None


class RQTaskQueueBackend:
    def __init__(self, settings: Settings):
        if not settings.redis_url:
            raise ValueError("Redis is required for the task queue.")
        self.settings = settings
        self.connection = Redis.from_url(settings.redis_url, decode_responses=False)
        self.queue = Queue(
            name=settings.task_queue_name,
            connection=self.connection,
            default_timeout=60,
        )

    def enqueue(
        self,
        *,
        name: str,
        callable_: TaskCallable,
        kwargs: dict[str, Any] | None = None,
        job_id: str | None = None,
        timeout_seconds: int = 60,
        retry_intervals_seconds: Sequence[int] = (),
        owner_user_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> TaskExecution:
        try:
            job = self.queue.enqueue_call(
                func=callable_,
                kwargs=kwargs or {},
                job_id=job_id,
                job_timeout=max(1, timeout_seconds),
                retry=(
                    Retry(
                        max=len(tuple(retry_intervals_seconds)) + 1,
                        interval=list(retry_intervals_seconds),
                    )
                    if retry_intervals_seconds
                    else None
                ),
                result_ttl=self.settings.task_queue_result_ttl_seconds,
                failure_ttl=self.settings.task_queue_failure_ttl_seconds,
                meta={
                    "task_name": name,
                    "owner_user_id": owner_user_id,
                    **dict(meta or {}),
                },
                description=name,
            )
        except RedisError as exc:
            logger.exception("task_queue.enqueue_failed name=%s", name)
            raise RuntimeError("Unable to enqueue task.") from exc
        return self._to_execution(job)

    def get(self, job_id: str) -> TaskExecution | None:
        try:
            job = Job.fetch(job_id, connection=self.connection)
        except Exception:
            return None
        return self._to_execution(job)

    def _to_execution(self, job: Job) -> TaskExecution:
        status = self._map_status(job.get_status(refresh=True))
        queued_at = getattr(job, "enqueued_at", None) or _utcnow()
        error = None
        if job.is_failed:
            error = self._format_exc(job.exc_info)
        result = job.result if job.is_finished else None
        owner_user_id = None
        if isinstance(job.meta, dict):
            raw_owner = job.meta.get("owner_user_id")
            owner_user_id = str(raw_owner) if raw_owner else None
        return TaskExecution(
            job_id=job.id,
            name=str(job.meta.get("task_name") if isinstance(job.meta, dict) else job.description or job.id),
            status=status,
            queued_at=queued_at,
            started_at=getattr(job, "started_at", None),
            finished_at=getattr(job, "ended_at", None),
            error=error,
            result=result,
            owner_user_id=owner_user_id,
        )

    @staticmethod
    def _map_status(status: str) -> str:
        mapping = {
            "queued": "queued",
            "started": "running",
            "finished": "success",
            "failed": "failed",
            "deferred": "queued",
            "scheduled": "queued",
        }
        return mapping.get(status, status)

    @staticmethod
    def _format_exc(exc_info: str | None) -> str | None:
        if not exc_info:
            return None
        tail = exc_info.strip().splitlines()
        return tail[-1][:500] if tail else "Task failed."


def build_task_queue_backend(settings: Settings | None = None) -> TaskQueueBackend:
    resolved = settings or get_settings()
    if not resolved.task_queue_enabled or not resolved.redis_url:
        return NullTaskQueueBackend()
    try:
        backend = RQTaskQueueBackend(resolved)
        backend.connection.ping()
        return backend
    except Exception:
        logger.exception("task_queue.backend_unavailable")
        return NullTaskQueueBackend()


def get_task_queue_backend(app) -> TaskQueueBackend:
    backend = getattr(app.state, "task_queue", None)
    if backend is None:
        backend = build_task_queue_backend(getattr(app.state, "settings", None))
        app.state.task_queue = backend
    return backend


def build_worker(settings: Settings | None = None) -> Worker:
    resolved = settings or get_settings()
    backend = RQTaskQueueBackend(resolved)
    return Worker([backend.queue], connection=backend.connection)


__all__ = [
    "NullTaskQueueBackend",
    "RQTaskQueueBackend",
    "TaskExecution",
    "TaskQueueBackend",
    "build_task_queue_backend",
    "build_worker",
    "get_task_queue_backend",
]
