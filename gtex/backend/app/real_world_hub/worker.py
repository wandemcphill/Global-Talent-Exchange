from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from threading import Event, Thread
from time import sleep

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.core.container import ApplicationContext
from app.real_world_hub.service import RealWorldHubService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RealWorldHubScheduler:
    session_factory: sessionmaker[Session]
    interval_seconds: float = 60.0
    _stop_event: Event = field(default_factory=Event)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-real-world-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def run_once(self) -> None:
        with self.session_factory() as session:
            try:
                RealWorldHubService(session=session).sync_due_providers()
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("real_world_hub.scheduler.run_failed")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            sleep(self.interval_seconds)


def bind_real_world_hub_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    interval_seconds = max(5.0, float(os.getenv("GTE_REAL_WORLD_SYNC_INTERVAL_SECONDS", "60")))
    enabled = os.getenv("GTE_REAL_WORLD_SYNC_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    scheduler = RealWorldHubScheduler(
        session_factory=context.database.session_factory,
        interval_seconds=interval_seconds,
    )
    app.state.real_world_hub_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_real_world_hub_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "real_world_hub_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = [
    "RealWorldHubScheduler",
    "bind_real_world_hub_scheduler",
    "shutdown_real_world_hub_scheduler",
]
