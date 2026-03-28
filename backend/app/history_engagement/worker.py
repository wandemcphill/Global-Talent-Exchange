from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from threading import Event, Thread
from time import sleep

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.core.container import ApplicationContext
from app.history_engagement.service import HistoryEngagementService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HistoryEngagementScheduler:
    session_factory: sessionmaker[Session]
    interval_seconds: float = 300.0
    _stop_event: Event = field(default_factory=Event)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-history-engagement", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def run_once(self) -> None:
        with self.session_factory() as session:
            try:
                HistoryEngagementService(session=session).run_workers_once()
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("history_engagement.scheduler.run_failed")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            sleep(self.interval_seconds)


def bind_history_engagement_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    interval_seconds = max(
        30.0,
        float(os.getenv("GTE_HISTORY_ENGAGEMENT_WORKER_INTERVAL_SECONDS", "300")),
    )
    enabled = os.getenv("GTE_HISTORY_ENGAGEMENT_WORKER_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scheduler = HistoryEngagementScheduler(
        session_factory=context.database.session_factory,
        interval_seconds=interval_seconds,
    )
    app.state.history_engagement_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_history_engagement_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "history_engagement_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = [
    "HistoryEngagementScheduler",
    "bind_history_engagement_scheduler",
    "shutdown_history_engagement_scheduler",
]
