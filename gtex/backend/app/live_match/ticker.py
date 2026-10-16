"""Server-side live-match ticker (Increment 2).

A daemon thread that advances every *active* live-match session one minute per
interval and broadcasts the new state, so clients only READ (poll GET or
subscribe to the spectator websocket) — they never drive the clock.

Broadcast path: the ticker publishes each updated state onto the same Redis
channel `MatchRoomManager` already subscribes to (`match:{id}:events`), in the
same envelope shape, so any web worker holding spectator websockets fans it out.
This keeps the ticker fully decoupled from the asyncio event loop.

Leader election: with multiple processes, only the holder of a short-lived Redis
lease advances sessions, so a match isn't double-ticked. Without Redis (local
single-process dev) the lone process is always leader and clients poll GET.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from threading import Event, RLock, Thread

from redis import Redis
from redis.exceptions import RedisError

from app.live_match.service import (
    LiveMatchEngine,
    LiveMatchError,
    get_live_match_engine,
    session_public_state,
)

logger = logging.getLogger(__name__)

_LEADER_KEY = "live-match:ticker:leader"
_MATCH_CHANNEL = "match:{match_id}:events"


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


@dataclass
class LiveMatchTicker:
    redis_url: str | None = None
    engine: LiveMatchEngine = field(default_factory=get_live_match_engine)
    tick_interval_seconds: float = 3.0
    enabled: bool = True
    instance_id: str = field(default_factory=lambda: os.urandom(8).hex())
    _client: Redis | None = field(init=False, default=None)
    _worker: Thread | None = field(init=False, default=None)
    _stop_event: Event = field(init=False, default_factory=Event)
    _lock: RLock = field(init=False, default_factory=RLock)

    @classmethod
    def from_settings(cls, settings) -> "LiveMatchTicker":
        redis_enabled = bool(getattr(settings, "redis_enabled", False))
        redis_url = getattr(settings, "redis_url", None) if redis_enabled else None
        return cls(
            redis_url=redis_url,
            tick_interval_seconds=_env_float("GTE_LIVE_MATCH_TICK_SECONDS", 3.0, minimum=0.5),
            enabled=_env_bool("GTE_LIVE_MATCH_TICKER_ENABLED", True),
        )

    def start(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            if self.redis_url:
                self._client = Redis.from_url(self.redis_url, decode_responses=True)
            self._stop_event.clear()
            self._worker = Thread(target=self._run_loop, name="gtex-live-match-ticker", daemon=True)
            self._worker.start()
            logger.info("live_match.ticker.started interval=%.2fs", self.tick_interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=2)
        if self._client is not None:
            try:
                self._client.close()
            except RedisError:
                pass
            self._client = None

    # ---- internals --------------------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._is_leader():
                    self._advance_once()
            except Exception:  # pragma: no cover - defensive: never kill the thread
                logger.exception("live_match.ticker.cycle_failed")
            self._stop_event.wait(self.tick_interval_seconds)

    def _is_leader(self) -> bool:
        # No Redis → single process → always leader.
        if self._client is None:
            return True
        lease_ms = int(self.tick_interval_seconds * 1000 * 3) + 1000
        try:
            # Renew if we already hold it, else try to acquire.
            if self._client.get(_LEADER_KEY) == self.instance_id:
                self._client.set(_LEADER_KEY, self.instance_id, px=lease_ms)
                return True
            return bool(self._client.set(_LEADER_KEY, self.instance_id, nx=True, px=lease_ms))
        except RedisError:
            return False

    def _advance_once(self) -> None:
        for match_id in self.engine.store.active_ids():
            try:
                session = self.engine.tick(match_id)
            except LiveMatchError:
                # Session expired/removed — drop it from the active registry.
                self.engine.store.mark_finished(match_id)
                continue
            self._publish_state(match_id, session_public_state(session))

    def _publish_state(self, match_id: str, state: dict) -> None:
        if self._client is None:
            return
        message = {"type": "live_match_state", **state}
        envelope = {"instance_id": self.instance_id, "message": message}
        try:
            self._client.publish(_MATCH_CHANNEL.format(match_id=match_id), json.dumps(envelope))
        except RedisError:
            logger.warning("live_match.ticker.publish_failed match_id=%s", match_id)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def ensure_live_match_ticker(app) -> LiveMatchTicker:
    ticker = getattr(app.state, "live_match_ticker", None)
    if ticker is None:
        ticker = LiveMatchTicker.from_settings(getattr(app.state, "settings", None))
        app.state.live_match_ticker = ticker
    return ticker


def bind_live_match_ticker(app, _context) -> None:
    ensure_live_match_ticker(app).start()


def shutdown_live_match_ticker(app, _context) -> None:
    ticker = getattr(app.state, "live_match_ticker", None)
    if ticker is not None:
        ticker.stop()
