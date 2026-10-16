from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from threading import Event, Thread
from time import monotonic

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.core.container import ApplicationContext
from app.viral.ranking_service import build_viral_ranking_service, ensure_viral_leaderboard_store

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ViralRankingScheduler:
    app: FastAPI
    session_factory: sessionmaker[Session]
    hot_interval_seconds: float = 30.0
    cold_interval_seconds: float = 300.0
    _stop_event: Event = field(default_factory=Event, repr=False)
    _thread: Thread | None = field(default=None, init=False, repr=False)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-viral-ranking", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def run_once(self, *, scope: str) -> None:
        with self.session_factory() as session:
            try:
                build_viral_ranking_service(app=self.app, session=session).recompute(scope=scope)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("viral.ranking.scheduler.run_failed scope=%s", scope)

    def _run_loop(self) -> None:
        self.run_once(scope="all")
        last_cold_run = monotonic()
        while not self._stop_event.wait(self.hot_interval_seconds):
            self.run_once(scope="hot")
            now = monotonic()
            if now - last_cold_run >= self.cold_interval_seconds:
                self.run_once(scope="all")
                last_cold_run = now


def bind_viral_ranking_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    ensure_viral_leaderboard_store(app, settings=context.settings)
    hot_interval_seconds = max(
        1.0,
        float(os.getenv("GTE_VIRAL_RANKING_HOT_INTERVAL_SECONDS", "30")),
    )
    cold_interval_seconds = max(
        hot_interval_seconds,
        float(os.getenv("GTE_VIRAL_RANKING_COLD_INTERVAL_SECONDS", "300")),
    )
    enabled = os.getenv("GTE_VIRAL_RANKING_WORKER_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scheduler = getattr(app.state, "viral_ranking_scheduler", None)
    if scheduler is None:
        scheduler = ViralRankingScheduler(
            app=app,
            session_factory=context.database.session_factory,
            hot_interval_seconds=hot_interval_seconds,
            cold_interval_seconds=cold_interval_seconds,
        )
        app.state.viral_ranking_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_viral_ranking_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "viral_ranking_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = [
    "ViralRankingScheduler",
    "bind_viral_ranking_scheduler",
    "shutdown_viral_ranking_scheduler",
]
