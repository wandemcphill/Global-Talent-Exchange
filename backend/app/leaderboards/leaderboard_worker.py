from __future__ import annotations

from dataclasses import dataclass, field
from queue import Empty, Full, Queue
import logging
import os
from threading import Event as ThreadEvent, Thread
from typing import Any

from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.container import ApplicationContext
from app.core.events import DomainEvent, EventPublisher
from app.leaderboards.leaderboard_service import LeaderboardService
from app.leaderboards.ranking_service import MatchRatingUpdate, RankingService
from app.leaderboards.season_service import SeasonService

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_SIZE = 2048


@dataclass(slots=True)
class LeaderboardWorker:
    session_factory: sessionmaker[Session]
    event_publisher: EventPublisher
    redis_url: str | None = None
    queue_size: int = DEFAULT_QUEUE_SIZE
    _queue: Queue[DomainEvent] = field(init=False, repr=False)
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent, repr=False)
    _thread: Thread | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._queue = Queue(maxsize=max(1, int(self.queue_size)))

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-leaderboard-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def handle_event(self, event: DomainEvent) -> None:
        if event.name != "match.completed":
            return
        try:
            self._queue.put_nowait(event)
        except Full:
            logger.warning("leaderboard.worker.queue_full match_event_id=%s", event.event_id)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                self._process_match_completed(event)
            except Exception:
                logger.exception("leaderboard.worker.process_failed event_id=%s", event.event_id)
            finally:
                self._queue.task_done()

    def _process_match_completed(self, event: DomainEvent) -> None:
        match_context = _extract_match_context(event)
        if match_context is None:
            logger.debug("leaderboard.worker.event_skipped reason=unmappable_match event_id=%s", event.event_id)
            return
        with self.session_factory() as session:
            season_service = SeasonService(
                session=session,
                session_factory=self.session_factory,
                event_publisher=self.event_publisher,
                redis_url=self.redis_url,
            )
            leaderboard_service = LeaderboardService(session=session, redis_url=self.redis_url)
            ranking_service = RankingService(session=session)
            season = season_service.get_current_season(auto_rollover=True)
            try:
                update = ranking_service.record_match_result(
                    season=season,
                    match_id=match_context["match_id"],
                    player_a_id=match_context["player_a_id"],
                    player_b_id=match_context["player_b_id"],
                    result=match_context["result"],
                    source_event_id=event.event_id,
                    metadata=match_context["metadata"],
                )
            except IntegrityError:
                session.rollback()
                logger.info("leaderboard.worker.duplicate_match_skipped match_id=%s", match_context["match_id"])
                return

            session.commit()
            leaderboard_service.sync_players((update.player_a, update.player_b))
            player_a_view = leaderboard_service.build_player_ranks(update.player_a.player_id, season_id=season.id)
            player_b_view = leaderboard_service.build_player_ranks(update.player_b.player_id, season_id=season.id)
            self.event_publisher.publish(
                DomainEvent(
                    name="leaderboard.updated",
                    payload=_leaderboard_update_payload(
                        season_id=season.id,
                        update=update,
                        player_a_view=player_a_view.model_dump(mode="json"),
                        player_b_view=player_b_view.model_dump(mode="json"),
                    ),
                    aggregate_id=match_context["match_id"],
                    aggregate_type="competition_match",
                    partition_key=match_context["match_id"],
                    producer="leaderboard-worker",
                )
            )


def _extract_match_context(event: DomainEvent) -> dict[str, Any] | None:
    payload = dict(event.payload or {})
    match_id = _normalized_string(
        payload.get("match_id")
        or payload.get("fixture_id")
        or payload.get("resource_id")
        or event.aggregate_id
        or event.event_id
    )
    home_user_id = _normalized_string(payload.get("home_user_id"))
    away_user_id = _normalized_string(payload.get("away_user_id"))
    if home_user_id is None or away_user_id is None:
        user_ids = payload.get("user_ids")
        if isinstance(user_ids, list) and len(user_ids) >= 2:
            home_user_id = home_user_id or _normalized_string(user_ids[0])
            away_user_id = away_user_id or _normalized_string(user_ids[1])
    if home_user_id is None or away_user_id is None:
        participants = payload.get("participants")
        if isinstance(participants, list) and len(participants) >= 2:
            home_user_id = home_user_id or _participant_id(participants[0])
            away_user_id = away_user_id or _participant_id(participants[1])
    if home_user_id is None or away_user_id is None or home_user_id == away_user_id:
        return None

    home_goals = _coerce_int(payload.get("home_goals"))
    away_goals = _coerce_int(payload.get("away_goals"))
    if home_goals is None or away_goals is None:
        simulation = payload.get("simulation")
        if isinstance(simulation, dict):
            home = simulation.get("home")
            away = simulation.get("away")
            if isinstance(home, dict):
                home_goals = home_goals if home_goals is not None else _coerce_int(home.get("score"))
            if isinstance(away, dict):
                away_goals = away_goals if away_goals is not None else _coerce_int(away.get("score"))
    if home_goals is None or away_goals is None:
        winner_user_id = _normalized_string(payload.get("winner_user_id") or payload.get("winner_id"))
        if winner_user_id == home_user_id:
            result = 1.0
        elif winner_user_id == away_user_id:
            result = 0.0
        else:
            return None
    elif home_goals > away_goals:
        result = 1.0
    elif away_goals > home_goals:
        result = 0.0
    else:
        result = 0.5

    return {
        "match_id": match_id or event.event_id,
        "player_a_id": home_user_id,
        "player_b_id": away_user_id,
        "result": result,
        "metadata": payload,
    }


def _leaderboard_update_payload(
    *,
    season_id: str,
    update: MatchRatingUpdate,
    player_a_view: dict[str, Any],
    player_b_view: dict[str, Any],
) -> dict[str, Any]:
    return {
        "season_id": season_id,
        "match_id": update.match_id,
        "source_event_id": update.source_event_id,
        "result": update.result,
        "players": [player_a_view, player_b_view],
        "rating_changes": {
            update.player_a.player_id: update.rating_update.player_a_delta,
            update.player_b.player_id: update.rating_update.player_b_delta,
        },
    }


def _participant_id(participant: object) -> str | None:
    if isinstance(participant, dict):
        return _normalized_string(
            participant.get("user_id") or participant.get("participant_id") or participant.get("id")
        )
    return _normalized_string(participant)


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalized_string(value: object) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


def bind_leaderboard_worker(app: FastAPI, context: ApplicationContext) -> None:
    worker = getattr(app.state, "leaderboard_worker", None)
    if worker is None:
        worker = LeaderboardWorker(
            session_factory=context.database.session_factory,
            event_publisher=context.event_publisher,
            redis_url=context.settings.redis_url,
            queue_size=max(1, int(os.getenv("GTE_LEADERBOARD_WORKER_QUEUE_SIZE", DEFAULT_QUEUE_SIZE))),
        )
        app.state.leaderboard_worker = worker
    if not getattr(app.state, "_leaderboard_worker_subscribed", False):
        context.event_publisher.subscribe(worker.handle_event)
        app.state._leaderboard_worker_subscribed = True
    worker.start()


def shutdown_leaderboard_worker(app: FastAPI, _context: ApplicationContext) -> None:
    worker = getattr(app.state, "leaderboard_worker", None)
    if worker is not None:
        worker.stop()


__all__ = [
    "LeaderboardWorker",
    "bind_leaderboard_worker",
    "shutdown_leaderboard_worker",
]
