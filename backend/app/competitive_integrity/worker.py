from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from threading import Event, Thread
from time import sleep

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.competitive_integrity.service import CompetitiveIntegrityService
from app.core.container import ApplicationContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CompetitiveIntegrityScheduler:
    session_factory: sessionmaker[Session]
    interval_seconds: float = 30.0
    _stop_event: Event = field(default_factory=Event)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-competitive-integrity", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            if self._thread.ident is not None:
                self._thread.join(timeout=1.0)
            self._thread = None

    def run_once(self) -> None:
        with self.session_factory() as session:
            try:
                CompetitiveIntegrityService(session=session).run_workers_once()
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("competitive_integrity.scheduler.run_failed")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            sleep(self.interval_seconds)


def bind_competitive_integrity_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    interval_seconds = max(
        1.0,
        float(os.getenv("GTE_COMPETITIVE_INTEGRITY_WORKER_INTERVAL_SECONDS", "30")),
    )
    enabled = os.getenv("GTE_COMPETITIVE_INTEGRITY_WORKER_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scheduler = CompetitiveIntegrityScheduler(
        session_factory=context.database.session_factory,
        interval_seconds=interval_seconds,
    )
    app.state.competitive_integrity_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_competitive_integrity_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "competitive_integrity_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = [
    "CompetitiveIntegrityScheduler",
    "bind_competitive_integrity_scheduler",
    "shutdown_competitive_integrity_scheduler",
]
