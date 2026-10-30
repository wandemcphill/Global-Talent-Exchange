from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import os
from threading import Event, Thread

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, NullCacheBackend
from app.core.container import ApplicationContext
from app.services.gtex_news_engine import GTEXNewsEngineService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GTEXNewsScheduler:
    session_factory: sessionmaker[Session]
    cache_backend: CacheBackend | None = None
    light_interval_seconds: float = 21_600.0
    full_interval_seconds: float = 86_400.0
    _stop_event: Event = field(default_factory=Event)
    _thread: Thread | None = None
    _last_full_run_at: datetime | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-news-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.ident is not None:
            self._thread.join(timeout=1.0)

    def run_once(self, *, scope: str = "light") -> None:
        with self.session_factory() as session:
            try:
                payload = GTEXNewsEngineService(
                    session,
                    cache_backend=self.cache_backend or NullCacheBackend(),
                ).daily_news(force=True, scope=scope)
                from app.story_feed_engine.bridges import publish_news_engine_payload

                bridge_stats = publish_news_engine_payload(session, payload)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("gtex_news.scheduler.daily_news_failed scope=%s", scope)
                return

            rising_stats = {"created": 0, "skipped": 0}
            try:
                from app.regen_universe.service import RegenUniverseService

                rising_stats = RegenUniverseService(session).announce_rising_stars_to_story_feed(
                    limit=5 if scope == "light" else 8
                )
                session.commit()
            except Exception:
                session.rollback()
                logger.exception(
                    "gtex_news.scheduler.rising_star_announce_failed scope=%s",
                    scope,
                )

            logger.info(
                "gtex_news.scheduler.published_to_story_feed scope=%s created=%s skipped=%s rising=%s",
                scope,
                bridge_stats.get("created"),
                bridge_stats.get("skipped"),
                rising_stats.get("created"),
            )

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            self.run_once(scope="light")
            if self._last_full_run_at is None or now - self._last_full_run_at >= timedelta(
                seconds=self.full_interval_seconds
            ):
                self.run_once(scope="daily")
                self._last_full_run_at = now
            self._stop_event.wait(self.light_interval_seconds)


def bind_gtex_news_scheduler(app: FastAPI, context: ApplicationContext) -> None:
    light_interval_seconds = max(300.0, float(os.getenv("GTE_NEWS_LIGHT_INTERVAL_SECONDS", "21600")))
    full_interval_seconds = max(light_interval_seconds, float(os.getenv("GTE_NEWS_FULL_INTERVAL_SECONDS", "86400")))
    enabled = os.getenv("GTE_NEWS_WORKER_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scheduler = GTEXNewsScheduler(
        session_factory=context.database.session_factory,
        cache_backend=context.cache_backend or NullCacheBackend(),
        light_interval_seconds=light_interval_seconds,
        full_interval_seconds=full_interval_seconds,
    )
    app.state.gtex_news_scheduler = scheduler
    if enabled:
        scheduler.start()


def shutdown_gtex_news_scheduler(app: FastAPI, _context: ApplicationContext) -> None:
    scheduler = getattr(app.state, "gtex_news_scheduler", None)
    if scheduler is not None:
        scheduler.stop()


__all__ = ["GTEXNewsScheduler", "bind_gtex_news_scheduler", "shutdown_gtex_news_scheduler"]
