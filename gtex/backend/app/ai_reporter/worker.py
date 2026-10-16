from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from threading import Event, Thread

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.ai_reporter.service import AIReporterService
from app.core.container import ApplicationContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AIReporterScheduler:
    session_factory: sessionmaker[Session]
    interval_seconds: float = 86_400.0
    _stop_event: Event = field(default_factory=Event)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-ai-reporter", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.ident is not None:
            self._thread.join(timeout=1.0)

    def run_once(self) -> None:
        with self.session_factory() as session:
            try:
                AIReporterService(session).run_daily_digest(limit_per_beat=3)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("ai_reporter.scheduler.run_failed")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.interval_seconds)


def bind_ai_reporter_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    interval_seconds = max(
        300.0,
        float(os.getenv("GTE_AI_REPORTER_INTERVAL_SECONDS", "86400")),
    )
    enabled = os.getenv("GTE_AI_REPORTER_WORKER_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scheduler = AIReporterScheduler(
        session_factory=context.database.session_factory,
        interval_seconds=interval_seconds,
    )
    app.state.ai_reporter_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_ai_reporter_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "ai_reporter_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = [
    "AIReporterScheduler",
    "bind_ai_reporter_scheduler",
    "shutdown_ai_reporter_scheduler",
]

