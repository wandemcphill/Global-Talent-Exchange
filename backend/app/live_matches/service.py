from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from threading import RLock, Thread
import time
from typing import Callable

from fastapi import FastAPI
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, JsonCacheNamespace, NullCacheBackend, RedisCacheBackend
from app.live_matches.schemas import (
    LiveMatchPossessionEstimateView,
    LiveMatchScoreView,
    LiveMatchSnapshotView,
    LiveMatchStateView,
    LiveMatchStreamEventView,
)
from app.match_engine.schemas import MatchReplayPayloadView
from app.match_engine.simulation.models import MatchEventType
from app.models.spectator_session import SpectatorSession


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LiveMatchError(ValueError):
    pass


BatchCallback = Callable[[str, list[LiveMatchStreamEventView], LiveMatchSnapshotView], None]
CompleteCallback = Callable[[str], None]


@dataclass(slots=True)
class _LiveBatch:
    events: list[LiveMatchStreamEventView]


@dataclass(slots=True)
class _LiveMatchRuntime:
    match_id: str
    channel: str
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    base_home_possession: int
    base_away_possession: int
    read_only: bool
    event_batches: list[_LiveBatch]
    on_batch: BatchCallback | None = None
    on_complete: CompleteCallback | None = None
    live: bool = True
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
    published_events: list[LiveMatchStreamEventView] = field(default_factory=list)
    spectator_user_ids: set[str] = field(default_factory=set)
    last_snapshot: LiveMatchSnapshotView | None = None


@dataclass(slots=True)
class LiveMatchHub:
    session_factory: sessionmaker[Session] | None = None
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    step_interval_seconds: float = 0.25
    snapshot_ttl_seconds: int = 600
    _matches: dict[str, _LiveMatchRuntime] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _cache: JsonCacheNamespace = field(init=False)

    def __post_init__(self) -> None:
        self._cache = JsonCacheNamespace(self.cache_backend)

    def start_stream(
        self,
        match_id: str,
        replay_payload: MatchReplayPayloadView,
        *,
        read_only: bool = True,
        on_batch: BatchCallback | None = None,
        on_complete: CompleteCallback | None = None,
    ) -> None:
        runtime = _LiveMatchRuntime(
            match_id=match_id,
            channel=f"match:{match_id}",
            home_team_id=replay_payload.summary.home_stats.team_id,
            away_team_id=replay_payload.summary.away_stats.team_id,
            home_team_name=replay_payload.summary.home_stats.team_name,
            away_team_name=replay_payload.summary.away_stats.team_name,
            base_home_possession=replay_payload.summary.home_stats.possession,
            base_away_possession=replay_payload.summary.away_stats.possession,
            read_only=read_only,
            event_batches=self._build_batches(replay_payload),
            on_batch=on_batch,
            on_complete=on_complete,
            last_snapshot=LiveMatchSnapshotView(
                score=LiveMatchScoreView(home=0, away=0),
                possession_estimate=LiveMatchPossessionEstimateView(
                    home=replay_payload.summary.home_stats.possession,
                    away=replay_payload.summary.away_stats.possession,
                ),
                current_minute=0,
                momentum_indicator="balanced",
                status="live",
                read_only=read_only,
            ),
        )
        with self._lock:
            self._matches[match_id] = runtime
        self._cache_snapshot(runtime)
        self._publish_channel(
            runtime.channel,
            {"kind": "snapshot", "payload": runtime.last_snapshot.model_dump(mode="json")},
        )
        Thread(
            target=self._run_stream,
            args=(match_id,),
            name=f"live-match-{match_id[:8]}",
            daemon=True,
        ).start()

    def join_spectate(self, match_id: str, user_id: str) -> SpectatorSession:
        runtime = self._require_live_match(match_id)
        with self._lock:
            runtime.spectator_user_ids.add(user_id)
        if self.session_factory is None:
            return SpectatorSession(
                id=f"spec-{user_id}-{match_id}",
                match_id=match_id,
                user_id=user_id,
                joined_at=utcnow(),
            )
        with self.session_factory() as session:
            item = session.scalar(
                select(SpectatorSession).where(
                    SpectatorSession.match_id == match_id,
                    SpectatorSession.user_id == user_id,
                )
            )
            if item is None:
                item = SpectatorSession(match_id=match_id, user_id=user_id)
                session.add(item)
            item.joined_at = utcnow()
            session.commit()
            session.refresh(item)
            return item

    def validate_session(self, match_id: str, session_id: str) -> SpectatorSession:
        if self.session_factory is None:
            raise LiveMatchError("Spectator sessions are unavailable.")
        with self.session_factory() as session:
            item = session.get(SpectatorSession, session_id)
            if item is None or item.match_id != match_id:
                raise LiveMatchError("Spectator session was not found.")
            return item

    def get_state(self, match_id: str) -> LiveMatchStateView | None:
        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is None or runtime.last_snapshot is None:
                return None
            return LiveMatchStateView(
                match_id=runtime.match_id,
                channel=runtime.channel,
                is_live=runtime.live,
                read_only=runtime.read_only,
                spectator_count=len(runtime.spectator_user_ids),
                event_count=len(runtime.published_events),
                snapshot=runtime.last_snapshot,
            )

    def get_events_since(self, match_id: str, cursor: int) -> tuple[list[LiveMatchStreamEventView], int]:
        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is None:
                return [], cursor
            return list(runtime.published_events[cursor:]), len(runtime.published_events)

    def _run_stream(self, match_id: str) -> None:
        while True:
            with self._lock:
                runtime = self._matches.get(match_id)
                if runtime is None:
                    return
                next_batch = self._next_batch(runtime)
            if next_batch is None:
                break
            with self._lock:
                runtime = self._matches.get(match_id)
                if runtime is None:
                    return
                runtime.published_events.extend(next_batch.events)
                runtime.last_snapshot = self._build_snapshot(runtime)
                snapshot = runtime.last_snapshot
                batch_callback = runtime.on_batch
                channel = runtime.channel
            self._cache_snapshot(runtime)
            self._publish_channel(
                channel,
                {"kind": "events", "payload": [event.model_dump(mode="json") for event in next_batch.events]},
            )
            self._publish_channel(channel, {"kind": "snapshot", "payload": snapshot.model_dump(mode="json")})
            if batch_callback is not None and next_batch.events:
                batch_callback(match_id, next_batch.events, snapshot)
            time.sleep(max(self.step_interval_seconds, 0.01))

        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is None or runtime.last_snapshot is None:
                return
            runtime.live = False
            runtime.completed_at = utcnow()
            runtime.last_snapshot = runtime.last_snapshot.model_copy(update={"status": "completed"})
            snapshot = runtime.last_snapshot
            complete_callback = runtime.on_complete
        self._cache_snapshot(runtime)
        self._publish_channel(runtime.channel, {"kind": "snapshot", "payload": snapshot.model_dump(mode="json")})
        if complete_callback is not None:
            complete_callback(match_id)

    def _next_batch(self, runtime: _LiveMatchRuntime) -> _LiveBatch | None:
        published_count = len(runtime.published_events)
        consumed = 0
        for batch in runtime.event_batches:
            next_consumed = consumed + len(batch.events)
            if published_count < next_consumed:
                start = max(0, published_count - consumed)
                return _LiveBatch(events=batch.events[start:])
            consumed = next_consumed
        return None

    def _build_batches(self, replay_payload: MatchReplayPayloadView) -> list[_LiveBatch]:
        mapped_events = [
            event
            for event in (
                self._map_event(
                    raw_event=raw_event,
                    home_team_id=replay_payload.summary.home_stats.team_id,
                    away_team_id=replay_payload.summary.away_stats.team_id,
                )
                for raw_event in replay_payload.timeline.events
            )
            if event is not None
        ]
        batches: list[_LiveBatch] = []
        current: list[LiveMatchStreamEventView] = []
        last_minute: int | None = None
        for event in mapped_events:
            if current and (len(current) >= 3 or (last_minute is not None and abs(event.minute - last_minute) > 2)):
                batches.append(_LiveBatch(events=list(current)))
                current.clear()
            current.append(event)
            last_minute = event.minute
        if current:
            batches.append(_LiveBatch(events=list(current)))
        return batches

    def _map_event(self, *, raw_event, home_team_id: str, away_team_id: str) -> LiveMatchStreamEventView | None:
        mapped_type = {
            MatchEventType.GOAL: "goal",
            MatchEventType.PENALTY_GOAL: "goal",
            MatchEventType.PENALTY_SCORED: "goal",
            MatchEventType.SHOT: "shot",
            MatchEventType.SHOT_ON_TARGET: "shot",
            MatchEventType.MISSED_CHANCE: "shot",
            MatchEventType.MISSED_BIG_CHANCE: "shot",
            MatchEventType.WOODWORK: "shot",
            MatchEventType.DOUBLE_SAVE: "shot",
            MatchEventType.FOUL: "foul",
            MatchEventType.TACTICAL_FOUL: "foul",
            MatchEventType.YELLOW_CARD: "card",
            MatchEventType.RED_CARD: "card",
            MatchEventType.SUBSTITUTION: "substitution",
        }.get(raw_event.event_type)
        if mapped_type is None:
            return None

        team_side = None
        if raw_event.team_id == home_team_id:
            team_side = "home"
        elif raw_event.team_id == away_team_id:
            team_side = "away"

        metadata = {
            "team_id": raw_event.team_id,
            "team_name": raw_event.team_name,
            "player_name": raw_event.primary_player.player_name if raw_event.primary_player is not None else None,
            "secondary_player_name": raw_event.secondary_player.player_name if raw_event.secondary_player is not None else None,
            "raw_event_type": raw_event.event_type.value,
            "description": raw_event.commentary,
            "home_score": raw_event.home_score,
            "away_score": raw_event.away_score,
            "team_side": team_side,
        }
        if raw_event.event_type in {MatchEventType.YELLOW_CARD, MatchEventType.RED_CARD}:
            metadata["card_type"] = "red" if raw_event.event_type is MatchEventType.RED_CARD else "yellow"

        return LiveMatchStreamEventView(
            minute=raw_event.minute,
            event_type=mapped_type,
            team=raw_event.team_name,
            player=raw_event.primary_player.player_name if raw_event.primary_player is not None else None,
            metadata=metadata,
        )

    def _build_snapshot(self, runtime: _LiveMatchRuntime) -> LiveMatchSnapshotView:
        score = LiveMatchScoreView(home=0, away=0)
        current_minute = 0
        recent_events = runtime.published_events[-3:]
        if runtime.published_events:
            latest = runtime.published_events[-1]
            score = LiveMatchScoreView(
                home=int(latest.metadata.get("home_score", 0) or 0),
                away=int(latest.metadata.get("away_score", 0) or 0),
            )
            current_minute = latest.minute

        home_possession = runtime.base_home_possession
        for event in recent_events:
            side = event.metadata.get("team_side")
            if side == "home" and event.event_type in {"goal", "shot"}:
                home_possession += 3
            elif side == "away" and event.event_type in {"goal", "shot"}:
                home_possession -= 3
            if event.event_type == "card" and event.metadata.get("card_type") == "red":
                if side == "home":
                    home_possession -= 4
                elif side == "away":
                    home_possession += 4

        home_possession = max(20, min(80, home_possession))
        away_possession = 100 - home_possession
        momentum = "balanced"
        if recent_events:
            home_weight = sum(
                1 for event in recent_events if event.metadata.get("team_side") == "home" and event.event_type in {"goal", "shot"}
            )
            away_weight = sum(
                1 for event in recent_events if event.metadata.get("team_side") == "away" and event.event_type in {"goal", "shot"}
            )
            if home_weight > away_weight:
                momentum = "home"
            elif away_weight > home_weight:
                momentum = "away"

        return LiveMatchSnapshotView(
            score=score,
            possession_estimate=LiveMatchPossessionEstimateView(home=home_possession, away=away_possession),
            current_minute=current_minute,
            momentum_indicator=momentum,
            status="live" if runtime.live else "completed",
            read_only=runtime.read_only,
        )

    def _require_live_match(self, match_id: str) -> _LiveMatchRuntime:
        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is None or not runtime.live:
                raise LiveMatchError("Match is not currently live for spectating.")
            return runtime

    def _cache_snapshot(self, runtime: _LiveMatchRuntime) -> None:
        if runtime.last_snapshot is None:
            return
        self._cache.set_json(
            f"live-match:snapshot:{runtime.match_id}",
            runtime.last_snapshot.model_dump(mode="json"),
            ttl_seconds=self.snapshot_ttl_seconds,
        )

    def _publish_channel(self, channel: str, payload: dict[str, object]) -> None:
        if not isinstance(self.cache_backend, RedisCacheBackend):
            return
        try:
            self.cache_backend.client.publish(channel, json.dumps(payload, default=str))
        except RedisError:
            return


def ensure_live_match_hub(app: FastAPI, *, step_interval_seconds: float | None = None) -> LiveMatchHub:
    hub = getattr(app.state, "live_match_hub", None)
    if hub is None:
        hub = LiveMatchHub(
            session_factory=getattr(app.state, "session_factory", None),
            cache_backend=getattr(app.state, "cache_backend", NullCacheBackend()),
        )
        app.state.live_match_hub = hub
    hub.session_factory = getattr(app.state, "session_factory", hub.session_factory)
    hub.cache_backend = getattr(app.state, "cache_backend", hub.cache_backend)
    hub._cache = JsonCacheNamespace(hub.cache_backend)
    if step_interval_seconds is not None:
        hub.step_interval_seconds = step_interval_seconds
    return hub


__all__ = ["LiveMatchError", "LiveMatchHub", "ensure_live_match_hub"]
