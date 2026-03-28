from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
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
    LiveMatchMarketPulseView,
    LiveMatchRenderPointView,
    LiveMatchScoreView,
    LiveMatchSnapshotView,
    LiveMatchStateView,
    LiveMatchStreamEventView,
    LiveMatchWinProbabilityView,
)
from app.match_engine.schemas import MatchReplayPayloadView
from app.match_engine.schemas import (
    MatchCommentaryCueView,
    MatchCrowdStateView,
    MatchExperienceLayerView,
    MatchMotionDirectionView,
    MatchMotionPredictionView,
    MatchSpectatorSyncView,
)
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
    atmosphere_profile: str
    sync_strategy: str
    checkpoint_interval_seconds: int
    max_latency_ms: int
    pause_replay_enabled: bool
    reactions_enabled: bool
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
    _halted_matches: dict[str, dict[str, object]] = field(default_factory=dict)
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
        if self.is_match_halted(match_id):
            raise LiveMatchError("Match is currently halted by the admin kill switch.")
        runtime = _LiveMatchRuntime(
            match_id=match_id,
            channel=f"match:{match_id}",
            home_team_id=replay_payload.summary.home_stats.team_id,
            away_team_id=replay_payload.summary.away_stats.team_id,
            home_team_name=replay_payload.summary.home_stats.team_name,
            away_team_name=replay_payload.summary.away_stats.team_name,
            base_home_possession=replay_payload.summary.home_stats.possession,
            base_away_possession=replay_payload.summary.away_stats.possession,
            atmosphere_profile=replay_payload.atmosphere_profile or "standard",
            sync_strategy=(replay_payload.spectator_package.sync_strategy if replay_payload.spectator_package is not None else "deterministic_playback"),
            checkpoint_interval_seconds=(replay_payload.sync_contract.checkpoint_interval_seconds if replay_payload.sync_contract is not None else 15),
            max_latency_ms=(replay_payload.sync_contract.max_latency_ms if replay_payload.sync_contract is not None else 320),
            pause_replay_enabled=(replay_payload.spectator_package.can_pause if replay_payload.spectator_package is not None else False),
            reactions_enabled=(replay_payload.spectator_package.reactions_enabled if replay_payload.spectator_package is not None else True),
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
                win_probability=_build_win_probability(
                    minute=0,
                    home_score=0,
                    away_score=0,
                    home_possession=replay_payload.summary.home_stats.possession,
                    dramatic_event=False,
                ),
                market_pulse=_build_market_pulse(
                    probability=_build_win_probability(
                        minute=0,
                        home_score=0,
                        away_score=0,
                        home_possession=replay_payload.summary.home_stats.possession,
                        dramatic_event=False,
                    ),
                    minute=0,
                    dramatic_event=False,
                ),
                dramatic_event=False,
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
                crowd_state=_runtime_crowd_state(runtime),
                spectator_sync=_runtime_spectator_sync(runtime),
            )

    def get_events_since(self, match_id: str, cursor: int) -> tuple[list[LiveMatchStreamEventView], int]:
        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is None:
                return [], cursor
            return list(runtime.published_events[cursor:]), len(runtime.published_events)

    def halt_match(
        self,
        match_id: str,
        *,
        reason: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict[str, object]:
        with self._lock:
            self._halted_matches[match_id] = {
                "reason": (reason or "").strip() or None,
                "actor_user_id": actor_user_id,
                "updated_at": utcnow().isoformat(),
            }
            runtime = self._matches.get(match_id)
            if runtime is None:
                return {"match_id": match_id, "enabled": True, **self._halted_matches[match_id]}
            runtime.live = False
            runtime.completed_at = utcnow()
            snapshot = None
            if runtime.last_snapshot is not None:
                runtime.last_snapshot = runtime.last_snapshot.model_copy(update={"status": "halted"})
                snapshot = runtime.last_snapshot
            channel = runtime.channel
        if runtime is not None and snapshot is not None:
            self._cache_snapshot(runtime)
            self._publish_channel(channel, {"kind": "snapshot", "payload": snapshot.model_dump(mode="json")})
        return {"match_id": match_id, "enabled": True, **self._halted_matches[match_id]}

    def clear_match_halt(self, match_id: str) -> dict[str, object]:
        with self._lock:
            removed = self._halted_matches.pop(match_id, None)
        return {
            "match_id": match_id,
            "enabled": False,
            "reason": None if removed is None else removed.get("reason"),
            "actor_user_id": None if removed is None else removed.get("actor_user_id"),
            "updated_at": None if removed is None else removed.get("updated_at"),
        }

    def is_match_halted(self, match_id: str) -> bool:
        with self._lock:
            return match_id in self._halted_matches

    def get_match_halt_state(self, match_id: str) -> dict[str, object] | None:
        with self._lock:
            state = self._halted_matches.get(match_id)
            if state is None:
                return None
            return {"match_id": match_id, "enabled": True, **state}

    def _run_stream(self, match_id: str) -> None:
        while True:
            with self._lock:
                runtime = self._matches.get(match_id)
                if runtime is None:
                    return
                halted_state = self._halted_matches.get(match_id)
                if halted_state is not None:
                    runtime.live = False
                    runtime.completed_at = utcnow()
                    snapshot = None
                    if runtime.last_snapshot is not None:
                        runtime.last_snapshot = runtime.last_snapshot.model_copy(update={"status": "halted"})
                        snapshot = runtime.last_snapshot
                    complete_callback = runtime.on_complete
                    channel = runtime.channel
                    halted = True
                    next_batch = None
                else:
                    halted = False
                    snapshot = None
                    complete_callback = None
                    channel = runtime.channel
                    next_batch = self._next_batch(runtime)
            if halted:
                if snapshot is not None:
                    self._cache_snapshot(runtime)
                    self._publish_channel(channel, {"kind": "snapshot", "payload": snapshot.model_dump(mode="json")})
                if complete_callback is not None:
                    complete_callback(match_id)
                return
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
        tick_rate_hz = replay_payload.sync_contract.tick_rate_hz if replay_payload.sync_contract is not None else 20
        max_latency_ms = replay_payload.sync_contract.max_latency_ms if replay_payload.sync_contract is not None else 320
        checkpoint_interval_seconds = (
            replay_payload.sync_contract.checkpoint_interval_seconds if replay_payload.sync_contract is not None else 15
        )
        mapped_events = [
            event
            for event in (
                self._map_event(
                    match_id=replay_payload.match_id,
                    raw_event=raw_event,
                    home_team_id=replay_payload.summary.home_stats.team_id,
                    away_team_id=replay_payload.summary.away_stats.team_id,
                    tick_rate_hz=tick_rate_hz,
                    atmosphere_profile=replay_payload.atmosphere_profile or "standard",
                    max_latency_ms=max_latency_ms,
                    checkpoint_interval_seconds=checkpoint_interval_seconds,
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

    def _map_event(
        self,
        *,
        match_id: str,
        raw_event,
        home_team_id: str,
        away_team_id: str,
        tick_rate_hz: int,
        atmosphere_profile: str,
        max_latency_ms: int,
        checkpoint_interval_seconds: int,
    ) -> LiveMatchStreamEventView | None:
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
        render = raw_event.metadata.get("render") if isinstance(raw_event.metadata.get("render"), dict) else {}
        actors = render.get("actors") if isinstance(render.get("actors"), dict) else {}
        camera = render.get("camera") if isinstance(render.get("camera"), dict) else {}
        ball = render.get("ball") if isinstance(render.get("ball"), dict) else {}
        replay = render.get("replay") if isinstance(render.get("replay"), dict) else {}
        render_team_side = actors.get("team_side")
        if isinstance(render_team_side, str) and render_team_side in {"home", "away"}:
            team_side = render_team_side
        position = self._render_point(render.get("origin"))
        target_position = self._render_point(render.get("target"), fallback=position)

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
        meta = {
            "render_type": render.get("type"),
            "chance_family": raw_event.metadata.get("chance_family"),
            "importance": int(raw_event.metadata.get("importance", 1) or 1),
            "xg": float(raw_event.metadata.get("xg", raw_event.metadata.get("chance_quality", 0.0)) or 0.0),
            "camera_mode": camera.get("mode"),
            "ball_motion": ball.get("motion"),
            "ball_height": float(ball.get("height", 0.0) or 0.0),
            "ball_speed": float(ball.get("speed", 0.0) or 0.0),
            "replay_eligible": bool(replay.get("eligible", False)),
            "replay_speed": float(replay.get("speed", 0.0) or 0.0),
            "reviewable": bool(raw_event.metadata.get("reviewable", False)),
            "review_decision": raw_event.metadata.get("review_decision"),
            "clock_label": raw_event.clock_label,
            "presentation_second": raw_event.presentation_second,
        }
        if meta["ball_speed"] > 0:
            meta["shot_power"] = round(meta["ball_speed"], 2)
        if position is not None and target_position is not None and position.y != target_position.y:
            meta["curve"] = round(abs(target_position.y - position.y) / 100.0, 2)
        if raw_event.event_type in {MatchEventType.YELLOW_CARD, MatchEventType.RED_CARD}:
            metadata["card_type"] = "red" if raw_event.event_type is MatchEventType.RED_CARD else "yellow"

        return LiveMatchStreamEventView(
            match_id=match_id,
            event_id=raw_event.event_id,
            tick=max(0, int(round(raw_event.presentation_second * tick_rate_hz))),
            minute=raw_event.minute,
            event_type=mapped_type,
            team_id=home_team_id if team_side == "home" else away_team_id if team_side == "away" else raw_event.team_id,
            team=raw_event.team_name,
            player_id=self._actor_player_id(raw_event=raw_event, team_side=team_side, home_team_id=home_team_id, away_team_id=away_team_id),
            player=raw_event.primary_player.player_name if raw_event.primary_player is not None else None,
            secondary_player_id=self._secondary_actor_id(raw_event=raw_event, team_side=team_side, home_team_id=home_team_id, away_team_id=away_team_id),
            position=position,
            target_position=target_position,
            meta=meta,
            metadata=metadata,
            experience=_live_experience_layer(
                match_id=match_id,
                raw_event=raw_event,
                tick=max(0, int(round(raw_event.presentation_second * tick_rate_hz))),
                meta=meta,
                profile=atmosphere_profile,
                max_latency_ms=max_latency_ms,
                checkpoint_interval_seconds=checkpoint_interval_seconds,
            ),
        )

    def _render_point(
        self,
        value: object | None,
        *,
        fallback: LiveMatchRenderPointView | None = None,
    ) -> LiveMatchRenderPointView | None:
        if isinstance(value, dict):
            return LiveMatchRenderPointView(
                x=float(value.get("x", 50.0) or 50.0),
                y=float(value.get("y", 50.0) or 50.0),
            )
        return fallback

    def _actor_player_id(self, *, raw_event, team_side: str | None, home_team_id: str, away_team_id: str) -> str | None:
        event_side = "home" if raw_event.team_id == home_team_id else "away" if raw_event.team_id == away_team_id else None
        if team_side is None or event_side == team_side:
            return raw_event.primary_player.player_id if raw_event.primary_player is not None else None
        return raw_event.secondary_player.player_id if raw_event.secondary_player is not None else raw_event.primary_player.player_id if raw_event.primary_player is not None else None

    def _secondary_actor_id(self, *, raw_event, team_side: str | None, home_team_id: str, away_team_id: str) -> str | None:
        event_side = "home" if raw_event.team_id == home_team_id else "away" if raw_event.team_id == away_team_id else None
        if team_side is None or event_side == team_side:
            return raw_event.secondary_player.player_id if raw_event.secondary_player is not None else None
        return raw_event.primary_player.player_id if raw_event.primary_player is not None else None

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
        dramatic_event = any(
            event.event_type == "goal"
            or (
                event.event_type == "card"
                and event.metadata.get("card_type") == "red"
            )
            for event in recent_events
        )
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
        win_probability = _build_win_probability(
            minute=current_minute,
            home_score=score.home,
            away_score=score.away,
            home_possession=home_possession,
            dramatic_event=dramatic_event,
        )

        return LiveMatchSnapshotView(
            score=score,
            possession_estimate=LiveMatchPossessionEstimateView(home=home_possession, away=away_possession),
            current_minute=current_minute,
            momentum_indicator=momentum,
            win_probability=win_probability,
            market_pulse=_build_market_pulse(
                probability=win_probability,
                minute=current_minute,
                dramatic_event=dramatic_event,
            ),
            dramatic_event=dramatic_event,
            status="live" if runtime.live else "completed",
            read_only=runtime.read_only,
        )

    def _require_live_match(self, match_id: str) -> _LiveMatchRuntime:
        with self._lock:
            runtime = self._matches.get(match_id)
            if match_id in self._halted_matches:
                raise LiveMatchError("Match has been halted by the admin kill switch.")
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


def _build_win_probability(
    *,
    minute: int,
    home_score: int,
    away_score: int,
    home_possession: int,
    dramatic_event: bool,
) -> LiveMatchWinProbabilityView:
    time_factor = max(1, min(minute, 95)) / 95
    score_swing = float(home_score - away_score)
    possession_tilt = ((home_possession - 50) / 50) * 1.35
    dramatic_swing = possession_tilt * 0.4 if dramatic_event else 0.0
    score_weight = score_swing * (1.35 + (time_factor * 1.05))

    home_signal = score_weight + possession_tilt + dramatic_swing
    away_signal = (-score_weight) - possession_tilt - dramatic_swing
    draw_signal = (
        0.95
        - (abs(score_swing) * 1.05)
        - (time_factor * 0.45)
        - (abs(possession_tilt) * 0.35)
    )

    max_signal = max(home_signal, draw_signal, away_signal)
    home_weight = math.exp(home_signal - max_signal)
    draw_weight = math.exp(draw_signal - max_signal)
    away_weight = math.exp(away_signal - max_signal)
    total = home_weight + draw_weight + away_weight

    return LiveMatchWinProbabilityView(
        home=home_weight / total,
        draw=draw_weight / total,
        away=away_weight / total,
    )


def _build_market_pulse(
    *,
    probability: LiveMatchWinProbabilityView,
    minute: int,
    dramatic_event: bool,
) -> LiveMatchMarketPulseView:
    volatility = min(
        1.0,
        max(
            0.12,
            (abs(probability.home - probability.away) * 0.55)
            + ((minute / 95) * 0.25)
            + (0.2 if dramatic_event else 0.0),
        ),
    )
    if dramatic_event:
        tension = "breaking"
    elif volatility >= 0.72:
        tension = "boiling"
    elif volatility >= 0.48:
        tension = "rising"
    else:
        tension = "locked"

    return LiveMatchMarketPulseView(
        home_line=_decimal_line(probability.home),
        draw_line=_decimal_line(probability.draw),
        away_line=_decimal_line(probability.away),
        volatility=volatility,
        tension=tension,
    )


def _decimal_line(probability: float) -> float:
    safe_probability = min(0.86, max(0.08, probability))
    return round(1 / safe_probability, 2)


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


def _live_experience_layer(
    *,
    match_id: str,
    raw_event,
    tick: int,
    meta: dict[str, object],
    profile: str,
    max_latency_ms: int,
    checkpoint_interval_seconds: int,
) -> MatchExperienceLayerView:
    pressure = _pressure_value(raw_event.metadata.get("pressure_level"))
    speed = _clamp_float(float(meta.get("ball_speed", 0.0) or 0.0) / 36.0, 0.0, 1.0)
    shoot_score = 0.72 if raw_event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_SCORED} else 0.46 if raw_event.event_type in {MatchEventType.SHOT, MatchEventType.SHOT_ON_TARGET, MatchEventType.MISSED_BIG_CHANCE} else 0.08
    sprint_score = 0.20 + (pressure * 0.42) + (speed * 0.24)
    run_score = 0.28 + ((1.0 - pressure) * 0.20)
    total = max(run_score + sprint_score + shoot_score, 0.0001)

    position = meta.get("curve", 0.0)
    home = _clamp_float(float(raw_event.metadata.get("crowd_home", 0.5) or 0.5), 0.0, 1.0)
    away = _clamp_float(float(raw_event.metadata.get("crowd_away", 0.5) or 0.5), 0.0, 1.0)
    top_moment = raw_event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_SCORED, MatchEventType.MISSED_BIG_CHANCE, MatchEventType.RED_CARD}

    return MatchExperienceLayerView(
        motion=MatchMotionPredictionView(
            model_key="gtex_motion_blend_v1",
            run_weight=round(run_score / total, 3),
            sprint_weight=round(sprint_score / total, 3),
            shoot_weight=round(shoot_score / total, 3),
            direction=MatchMotionDirectionView(
                x=round(_clamp_float((float(position) * 2.0) - 1.0, -1.0, 1.0), 3),
                y=round(_clamp_float(pressure - 0.5, -1.0, 1.0), 3),
            ),
            pressure=round(pressure, 3),
            ball_distance=round(abs(float(raw_event.metadata.get("chance_quality", 0.0) or 0.0) - 0.5) * 30.0, 2),
            nearest_defender_distance=round(max(1.5, (1.0 - pressure) * 18.0), 2),
            fatigue_load=round(_float_value(raw_event.metadata.get("fatigue_pressure"), default=0.0), 3),
            role_encoding="featured_actor" if raw_event.primary_player is not None else None,
        ),
        commentary=MatchCommentaryCueView(
            line=raw_event.commentary,
            tone="hype" if top_moment else "tactical",
            commentator="lead" if top_moment else "analyst",
            language="en",
            intensity=round(_clamp_float(((int(meta.get("importance", 1) or 1) - 1) / 4.0) + (0.25 if top_moment else 0.0), 0.18, 1.0), 3),
            tts_ready=bool(raw_event.commentary.strip()),
            banter_layer=raw_event.secondary_player is not None and top_moment,
            audio_channel="headline" if top_moment else "match_bed",
        ),
        crowd=MatchCrowdStateView(
            profile=profile,
            home_intensity=round(home, 3),
            away_intensity=round(away, 3),
            dominant_side="home" if home >= away else "away",
            chant_level=round(max(home, away), 3),
            hostility=round(_clamp_float(abs(home - away) + (0.12 if top_moment else 0.0), 0.0, 1.0), 3),
            spike=top_moment,
        ),
        spectator_sync=MatchSpectatorSyncView(
            room_id=f"match_{match_id}",
            sync_strategy="deterministic_playback",
            shared_clock_second=raw_event.presentation_second,
            tick=tick,
            max_latency_ms=max_latency_ms,
            checkpoint_interval_seconds=checkpoint_interval_seconds,
            pause_replay_enabled=False,
            reactions_enabled=True,
        ),
    )


def _runtime_crowd_state(runtime: _LiveMatchRuntime) -> MatchCrowdStateView | None:
    if not runtime.published_events:
        return MatchCrowdStateView(profile=runtime.atmosphere_profile)
    latest = runtime.published_events[-1]
    if latest.experience is not None and latest.experience.crowd is not None:
        return latest.experience.crowd
    return MatchCrowdStateView(profile=runtime.atmosphere_profile)


def _runtime_spectator_sync(runtime: _LiveMatchRuntime) -> MatchSpectatorSyncView:
    if runtime.published_events:
        latest = runtime.published_events[-1]
        if latest.experience is not None and latest.experience.spectator_sync is not None:
            return latest.experience.spectator_sync
        tick = int(latest.tick or 0)
        shared_clock_second = int(latest.meta.get("presentation_second", 0) or 0)
    else:
        tick = 0
        shared_clock_second = 0
    return MatchSpectatorSyncView(
        room_id=f"match_{runtime.match_id}",
        sync_strategy=runtime.sync_strategy,
        shared_clock_second=shared_clock_second,
        tick=tick,
        max_latency_ms=runtime.max_latency_ms,
        checkpoint_interval_seconds=runtime.checkpoint_interval_seconds,
        pause_replay_enabled=runtime.pause_replay_enabled,
        reactions_enabled=runtime.reactions_enabled,
    )


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _float_value(value: object | None, *, default: float) -> float:
    if isinstance(value, (int, float)):
        return _clamp_float(float(value), 0.0, 1.0)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return default
        try:
            return _clamp_float(float(normalized), 0.0, 1.0)
        except ValueError:
            return default
    return default


def _pressure_value(value: object | None) -> float:
    if isinstance(value, str):
        normalized = value.strip().lower()
        lookup = {
            "opening_phase": 0.18,
            "settled": 0.24,
            "build_up": 0.36,
            "building": 0.42,
            "rising": 0.54,
            "high": 0.72,
            "extreme": 0.88,
            "late_push": 0.76,
        }
        if normalized in lookup:
            return lookup[normalized]
    return _float_value(value, default=0.0)


__all__ = ["LiveMatchError", "LiveMatchHub", "ensure_live_match_hub"]
