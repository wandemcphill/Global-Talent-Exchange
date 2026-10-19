from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from threading import Event, Thread
from typing import Any

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.core.container import ApplicationContext
from app.national_team_engine.tournament_service import NationalTeamTournamentService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NationalTeamLifecycleScheduler:
    session_factory: sessionmaker[Session]
    interval_seconds: float = 300.0
    _stop_event: Event = field(default_factory=Event, init=False)
    _thread: Thread | None = field(default=None, init=False)
    last_run_summary: dict[str, Any] = field(default_factory=dict, init=False)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._run_loop,
            name="gtex-national-team-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.ident is not None:
            self._thread.join(timeout=1.0)
        self._thread = None

    def run_once(self) -> dict[str, Any]:
        with self.session_factory() as session:
            try:
                rental_cleanup = NationalTeamTournamentService(session).cleanup_expired_rentals()
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("national_team.scheduler.run_failed")
                raise
        summary = {"rental_cleanup": rental_cleanup}
        self.last_run_summary = summary
        return summary

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("national_team.scheduler.loop_iteration_failed")
            self._stop_event.wait(timeout=max(self.interval_seconds, 1.0))


def bind_national_team_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    interval_seconds = max(10.0, float(os.getenv("GTE_NATIONAL_TEAM_WORKER_INTERVAL_SECONDS", "300")))
    enabled = os.getenv("GTE_NATIONAL_TEAM_WORKER_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scheduler = NationalTeamLifecycleScheduler(
        session_factory=context.database.session_factory,
        interval_seconds=interval_seconds,
    )
    app.state.national_team_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_national_team_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "national_team_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = [
    "NationalTeamLifecycleScheduler",
    "bind_national_team_scheduler",
    "shutdown_national_team_scheduler",
]
