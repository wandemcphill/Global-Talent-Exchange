from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from threading import RLock, Thread
import time
from typing import Callable, Sequence

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.cache import HotPathCache
from app.core.cache import CacheBackend, NullCacheBackend
from app.core.events import DomainEvent, EventPublisher
from app.broadcast_network.stadium_service import StadiumImmersionProfile, StadiumImmersionService
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
from app.match_engine.commentary.live_engine import GeneratedCommentary, LiveCommentaryEngine
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
from app.schemas.match_viewer import MatchViewStateView
from app.services.match_timeline_service import MatchTimelineService


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LiveMatchError(ValueError):
    pass


BatchCallback = Callable[[str, list[LiveMatchStreamEventView], LiveMatchSnapshotView], None]
CompleteCallback = Callable[[str], None]
AttendanceOverlayProvider = Callable[[str, MatchCrowdStateView | None], MatchCrowdStateView | None]


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
    stadium_profile: StadiumImmersionProfile
    sync_strategy: str
    checkpoint_interval_seconds: int
    max_latency_ms: int
    pause_replay_enabled: bool
    reactions_enabled: bool
    read_only: bool
    step_interval_seconds: float
    event_batches: list[_LiveBatch]
    on_batch: BatchCallback | None = None
    on_complete: CompleteCallback | None = None
    live: bool = True
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
    published_events: list[LiveMatchStreamEventView] = field(default_factory=list)
    spectator_user_ids: set[str] = field(default_factory=set)
    last_snapshot: LiveMatchSnapshotView | None = None
    viewer_state: MatchViewStateView | None = None
    target_runtime_seconds: float = 0.0


@dataclass(slots=True)
class LiveMatchPlaybackContext:
    viewer_state: MatchViewStateView | None
    elapsed_runtime_seconds: float
    target_runtime_seconds: float
    is_live: bool


@dataclass(slots=True)
class LiveMatchHub:
    session_factory: sessionmaker[Session] | None = None
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    step_interval_seconds: float = 0.25
    snapshot_ttl_seconds: int = 600
    commentary_engine: LiveCommentaryEngine = field(default_factory=LiveCommentaryEngine)
    stadium_service: StadiumImmersionService = field(default_factory=StadiumImmersionService)
    event_publisher: EventPublisher | None = None
    attendance_overlay_provider: AttendanceOverlayProvider | None = None
    _matches: dict[str, _LiveMatchRuntime] = field(default_factory=dict)
    _halted_matches: dict[str, dict[str, object]] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _hot_cache: HotPathCache = field(init=False)

    def __post_init__(self) -> None:
        self._hot_cache = HotPathCache(self.cache_backend)
        self.commentary_engine.configure(cache_backend=self.cache_backend)
        self.stadium_service.session_factory = self.session_factory

    def start_stream(
        self,
        match_id: str,
        replay_payload: MatchReplayPayloadView,
        *,
        read_only: bool = True,
        target_runtime_seconds: float | None = None,
        on_batch: BatchCallback | None = None,
        on_complete: CompleteCallback | None = None,
    ) -> None:
        if self.is_match_halted(match_id):
            raise LiveMatchError("Match is currently halted by the admin kill switch.")
        self.commentary_engine.reset_match(match_id)
        self.stadium_service.session_factory = self.session_factory
        stadium_profile = self.stadium_service.resolve(
            home_team_id=replay_payload.summary.home_stats.team_id,
            away_team_id=replay_payload.summary.away_stats.team_id,
            atmosphere_profile=replay_payload.atmosphere_profile or "standard",
        )
        event_batches = self._build_batches(replay_payload, stadium_profile=stadium_profile)
        step_interval_seconds = self._resolve_step_interval(
            batch_count=len(event_batches),
            target_runtime_seconds=target_runtime_seconds,
        )
        target_runtime_seconds_resolved = max(
            step_interval_seconds * max(len(event_batches), 1),
            step_interval_seconds,
            1.0,
        )
        viewer_state = None
        try:
            viewer_state = MatchTimelineService().build_from_replay_payload(replay_payload)
        except Exception:
            viewer_state = None
        runtime = _LiveMatchRuntime(
            match_id=match_id,
            channel=f"match:{match_id}:events",
            home_team_id=replay_payload.summary.home_stats.team_id,
            away_team_id=replay_payload.summary.away_stats.team_id,
            home_team_name=replay_payload.summary.home_stats.team_name,
            away_team_name=replay_payload.summary.away_stats.team_name,
            base_home_possession=replay_payload.summary.home_stats.possession,
            base_away_possession=replay_payload.summary.away_stats.possession,
            atmosphere_profile=replay_payload.atmosphere_profile or "standard",
            stadium_profile=stadium_profile,
            sync_strategy=(
                replay_payload.spectator_package.sync_strategy
                if replay_payload.spectator_package is not None
                else "deterministic_playback"
            ),
            checkpoint_interval_seconds=(
                replay_payload.sync_contract.checkpoint_interval_seconds
                if replay_payload.sync_contract is not None
                else 15
            ),
            max_latency_ms=(
                replay_payload.sync_contract.max_latency_ms if replay_payload.sync_contract is not None else 320
            ),
            pause_replay_enabled=(
                replay_payload.spectator_package.can_pause if replay_payload.spectator_package is not None else False
            ),
            reactions_enabled=(
                replay_payload.spectator_package.reactions_enabled
                if replay_payload.spectator_package is not None
                else True
            ),
            read_only=read_only,
            step_interval_seconds=step_interval_seconds,
            event_batches=event_batches,
            on_batch=on_batch,
            on_complete=on_complete,
            last_snapshot=self._build_initial_snapshot(
                home_possession=replay_payload.summary.home_stats.possession,
                away_possession=replay_payload.summary.away_stats.possession,
                read_only=read_only,
            ),
            viewer_state=viewer_state,
            target_runtime_seconds=target_runtime_seconds_resolved,
        )
        self._start_runtime(runtime)

    def start_synthetic_stream(
        self,
        *,
        match_id: str,
        home_team_id: str,
        away_team_id: str,
        home_team_name: str,
        away_team_name: str,
        base_home_possession: int,
        base_away_possession: int,
        events: Sequence[LiveMatchStreamEventView],
        atmosphere_profile: str = "standard",
        sync_strategy: str = "deterministic_playback",
        checkpoint_interval_seconds: int = 15,
        max_latency_ms: int = 320,
        pause_replay_enabled: bool = False,
        reactions_enabled: bool = True,
        read_only: bool = True,
        target_runtime_seconds: float | None = None,
        on_batch: BatchCallback | None = None,
        on_complete: CompleteCallback | None = None,
    ) -> None:
        if self.is_match_halted(match_id):
            raise LiveMatchError("Match is currently halted by the admin kill switch.")
        with self._lock:
            existing = self._matches.get(match_id)
            if existing is not None and existing.live:
                return
        self.commentary_engine.reset_match(match_id)
        self.stadium_service.session_factory = self.session_factory
        stadium_profile = self.stadium_service.resolve(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            atmosphere_profile=atmosphere_profile,
        )
        event_batches = self._build_event_batches(events, stadium_profile=stadium_profile)
        step_interval_seconds = self._resolve_step_interval(
            batch_count=len(event_batches),
            target_runtime_seconds=target_runtime_seconds,
        )
        target_runtime_seconds_resolved = max(
            step_interval_seconds * max(len(event_batches), 1),
            step_interval_seconds,
            1.0,
        )
        viewer_state = None
        try:
            viewer_state = MatchTimelineService().build_from_live_stream(
                match_id=match_id,
                source=self._resolve_viewer_source(events),
                home_team_id=home_team_id,
                home_team_name=home_team_name,
                away_team_id=away_team_id,
                away_team_name=away_team_name,
                events=list(events),
                live_state=None,
            )
        except Exception:
            viewer_state = None
        runtime = _LiveMatchRuntime(
            match_id=match_id,
            channel=f"match:{match_id}:events",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=home_team_name,
            away_team_name=away_team_name,
            base_home_possession=base_home_possession,
            base_away_possession=base_away_possession,
            atmosphere_profile=atmosphere_profile,
            stadium_profile=stadium_profile,
            sync_strategy=sync_strategy,
            checkpoint_interval_seconds=checkpoint_interval_seconds,
            max_latency_ms=max_latency_ms,
            pause_replay_enabled=pause_replay_enabled,
            reactions_enabled=reactions_enabled,
            read_only=read_only,
            step_interval_seconds=step_interval_seconds,
            event_batches=event_batches,
            on_batch=on_batch,
            on_complete=on_complete,
            last_snapshot=self._build_initial_snapshot(
                home_possession=base_home_possession,
                away_possession=base_away_possession,
                read_only=read_only,
            ),
            viewer_state=viewer_state,
            target_runtime_seconds=target_runtime_seconds_resolved,
        )
        self._start_runtime(runtime)

    def join_spectate(self, match_id: str, user_id: str) -> SpectatorSession:
        runtime = self._resolve_runtime_for_spectate(match_id)
        with self._lock:
            if runtime is not None:
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
            if runtime is not None and runtime.last_snapshot is not None:
                return self._build_state_view(runtime)
        cached_state = self._hot_cache.get_match_state(match_id)
        if not isinstance(cached_state, dict):
            return None
        try:
            return LiveMatchStateView.model_validate(cached_state)
        except Exception:
            return None

    def get_events_since(self, match_id: str, cursor: int) -> tuple[list[LiveMatchStreamEventView], int]:
        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is not None:
                return list(runtime.published_events[cursor:]), len(runtime.published_events)
        cached_events = self._hot_cache.get_match_events(match_id, cursor=0)
        if not cached_events:
            return [], cursor
        events: list[LiveMatchStreamEventView] = []
        for item in cached_events[cursor:]:
            try:
                events.append(LiveMatchStreamEventView.model_validate(item))
            except Exception:
                continue
        return events, len(cached_events)

    def get_playback_context(self, match_id: str) -> LiveMatchPlaybackContext | None:
        with self._lock:
            runtime = self._matches.get(match_id)
            if runtime is None:
                return None
            viewer_state = runtime.viewer_state
            started_at = runtime.started_at
            completed_at = runtime.completed_at
            target_runtime_seconds = max(runtime.target_runtime_seconds, runtime.step_interval_seconds, 1.0)
            is_live = runtime.live
        reference_time = completed_at or utcnow()
        elapsed_runtime_seconds = max(0.0, (reference_time - started_at).total_seconds())
        return LiveMatchPlaybackContext(
            viewer_state=viewer_state,
            elapsed_runtime_seconds=min(elapsed_runtime_seconds, target_runtime_seconds),
            target_runtime_seconds=target_runtime_seconds,
            is_live=is_live,
        )

    def list_active_matches(self) -> list[str]:
        with self._lock:
            active = sorted(runtime.match_id for runtime in self._matches.values() if runtime.live)
        if active:
            return active
        return self._hot_cache.list_active_matches()

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
                self._hot_cache.clear_match_state(match_id)
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
            self._hot_cache.append_match_events(
                match_id,
                [event.model_dump(mode="json") for event in next_batch.events],
                ttl_seconds=self.snapshot_ttl_seconds,
            )
            self._publish_channel(
                channel,
                {"kind": "events", "payload": [event.model_dump(mode="json") for event in next_batch.events]},
            )
            self._publish_domain_events(match_id, next_batch.events)
            self._publish_channel(channel, {"kind": "snapshot", "payload": snapshot.model_dump(mode="json")})
            if batch_callback is not None and next_batch.events:
                batch_callback(match_id, next_batch.events, snapshot)
            time.sleep(max(runtime.step_interval_seconds, 0.01))

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

    def _build_batches(
        self,
        replay_payload: MatchReplayPayloadView,
        *,
        stadium_profile: StadiumImmersionProfile | None = None,
    ) -> list[_LiveBatch]:
        resolved_stadium_profile = stadium_profile or self.stadium_service.resolve(
            home_team_id=replay_payload.summary.home_stats.team_id,
            away_team_id=replay_payload.summary.away_stats.team_id,
            atmosphere_profile=replay_payload.atmosphere_profile or "standard",
        )
        tick_rate_hz = replay_payload.sync_contract.tick_rate_hz if replay_payload.sync_contract is not None else 20
        max_latency_ms = (
            replay_payload.sync_contract.max_latency_ms if replay_payload.sync_contract is not None else 320
        )
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
                    home_team_name=replay_payload.summary.home_stats.team_name,
                    away_team_name=replay_payload.summary.away_stats.team_name,
                    tick_rate_hz=tick_rate_hz,
                    atmosphere_profile=replay_payload.atmosphere_profile or "standard",
                    stadium_profile=resolved_stadium_profile,
                    max_latency_ms=max_latency_ms,
                    checkpoint_interval_seconds=checkpoint_interval_seconds,
                )
                for raw_event in replay_payload.timeline.events
            )
            if event is not None
        ]
        return self._build_event_batches(mapped_events, stadium_profile=resolved_stadium_profile)

    def _resolve_step_interval(self, *, batch_count: int, target_runtime_seconds: float | None) -> float:
        if batch_count <= 0:
            return max(self.step_interval_seconds, 0.01)
        if target_runtime_seconds is None or target_runtime_seconds <= 0:
            return max(self.step_interval_seconds, 0.01)
        return max(float(target_runtime_seconds) / float(batch_count), 0.01)

    def _build_event_batches(
        self,
        events: Sequence[LiveMatchStreamEventView],
        *,
        stadium_profile: StadiumImmersionProfile | None = None,
    ) -> list[_LiveBatch]:
        batches: list[_LiveBatch] = []
        current: list[LiveMatchStreamEventView] = []
        last_minute: int | None = None
        for index, event in enumerate(events, start=1):
            normalized_event = self._normalize_stream_event(
                event,
                index=index,
                stadium_profile=stadium_profile,
            )
            if current and (len(current) >= 3 or (last_minute is not None and abs(event.minute - last_minute) > 2)):
                batches.append(_LiveBatch(events=list(current)))
                current.clear()
            current.append(normalized_event)
            last_minute = normalized_event.minute
        if current:
            batches.append(_LiveBatch(events=list(current)))
        return batches

    def _normalize_stream_event(
        self,
        event: LiveMatchStreamEventView,
        *,
        index: int,
        stadium_profile: StadiumImmersionProfile | None,
    ) -> LiveMatchStreamEventView:
        source_event_id = event.source_event_id or event.event_id or f"{event.match_id or 'match'}:source:{index}"
        sequence_id = int(event.sequence_id or event.sequence or index)
        importance_score = float(event.importance_score or event.meta.get("importance", 0.0) or 0.0)
        audio_stem_channels = list(event.audio_stem_channels or ["commentary", "crowd", "stadium_fx"])
        experience = event.experience
        if stadium_profile is not None and experience is not None and experience.crowd is not None:
            crowd = experience.crowd.model_copy(
                update={
                    "stadium_theme": experience.crowd.stadium_theme or stadium_profile.stadium_theme,
                    "stadium_name": experience.crowd.stadium_name or stadium_profile.stadium_name,
                    "region_personality": experience.crowd.region_personality or stadium_profile.region_personality,
                    "crowd_personality": experience.crowd.crowd_personality or stadium_profile.crowd_personality,
                    "crowd_bias": experience.crowd.crowd_bias or experience.crowd.dominant_side,
                    "crowd_intensity": experience.crowd.crowd_intensity or experience.crowd.chant_level,
                }
            )
            experience = experience.model_copy(update={"crowd": crowd})
        return event.model_copy(
            update={
                "source_event_id": source_event_id,
                "sequence": sequence_id,
                "sequence_id": sequence_id,
                "importance_score": importance_score,
                "audio_stem_channels": audio_stem_channels,
                "experience": experience,
            }
        )

    def _build_initial_snapshot(
        self,
        *,
        home_possession: int,
        away_possession: int,
        read_only: bool,
    ) -> LiveMatchSnapshotView:
        win_probability = _build_win_probability(
            minute=0,
            home_score=0,
            away_score=0,
            home_possession=home_possession,
            dramatic_event=False,
        )
        return LiveMatchSnapshotView(
            score=LiveMatchScoreView(home=0, away=0),
            possession_estimate=LiveMatchPossessionEstimateView(
                home=home_possession,
                away=away_possession,
            ),
            current_minute=0,
            momentum_indicator="balanced",
            win_probability=win_probability,
            market_pulse=_build_market_pulse(
                probability=win_probability,
                minute=0,
                dramatic_event=False,
            ),
            dramatic_event=False,
            status="live",
            read_only=read_only,
        )

    def _start_runtime(self, runtime: _LiveMatchRuntime) -> None:
        match_id = runtime.match_id
        with self._lock:
            self._matches[match_id] = runtime
        self._hot_cache.clear_match_events(match_id)
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

    def _map_event(
        self,
        *,
        match_id: str,
        raw_event,
        home_team_id: str,
        away_team_id: str,
        home_team_name: str,
        away_team_name: str,
        tick_rate_hz: int,
        atmosphere_profile: str,
        stadium_profile: StadiumImmersionProfile,
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
        generated_commentary = self.commentary_engine.generate(
            match_id=match_id,
            event=raw_event,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=home_team_name,
            away_team_name=away_team_name,
        )

        metadata = {
            "team_id": raw_event.team_id,
            "team_name": raw_event.team_name,
            "player_name": raw_event.primary_player.player_name if raw_event.primary_player is not None else None,
            "secondary_player_name": (
                raw_event.secondary_player.player_name if raw_event.secondary_player is not None else None
            ),
            "raw_event_type": raw_event.event_type.value,
            "description": generated_commentary.line,
            "home_score": raw_event.home_score,
            "away_score": raw_event.away_score,
            "team_side": team_side,
            "commentary_tier": generated_commentary.tier,
            "commentary_provider": generated_commentary.provider,
            "commentary_context": generated_commentary.context,
            "source_event_id": raw_event.event_id,
            "sequence_id": raw_event.sequence,
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
            "commentary_tier": generated_commentary.tier,
            "commentary_provider": generated_commentary.provider,
            "source_event_id": raw_event.event_id,
            "sequence_id": raw_event.sequence,
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
            source_event_id=raw_event.event_id,
            sequence=raw_event.sequence,
            sequence_id=raw_event.sequence,
            tick=max(0, int(round(raw_event.presentation_second * tick_rate_hz))),
            minute=raw_event.minute,
            event_type=mapped_type,
            source_event_type=raw_event.event_type.value,
            team_id=home_team_id if team_side == "home" else away_team_id if team_side == "away" else raw_event.team_id,
            team=raw_event.team_name,
            team_side=team_side,
            player_id=self._actor_player_id(
                raw_event=raw_event, team_side=team_side, home_team_id=home_team_id, away_team_id=away_team_id
            ),
            player=raw_event.primary_player.player_name if raw_event.primary_player is not None else None,
            secondary_player_id=self._secondary_actor_id(
                raw_event=raw_event, team_side=team_side, home_team_id=home_team_id, away_team_id=away_team_id
            ),
            secondary_player=raw_event.secondary_player.player_name if raw_event.secondary_player is not None else None,
            commentary=generated_commentary.line,
            home_score=raw_event.home_score,
            away_score=raw_event.away_score,
            clock_label=raw_event.clock_label,
            presentation_second=raw_event.presentation_second,
            importance_score=float(meta["importance"] or 0.0),
            highlight_eligible=bool(
                replay.get("eligible", False)
                or mapped_type == "goal"
                or raw_event.event_type is MatchEventType.RED_CARD
            ),
            audio_stem_channels=["commentary", "crowd", "stadium_fx"],
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
                stadium_profile=stadium_profile,
                team_side=team_side,
                max_latency_ms=max_latency_ms,
                checkpoint_interval_seconds=checkpoint_interval_seconds,
                generated_commentary=generated_commentary,
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
        event_side = (
            "home" if raw_event.team_id == home_team_id else "away" if raw_event.team_id == away_team_id else None
        )
        if team_side is None or event_side == team_side:
            return raw_event.primary_player.player_id if raw_event.primary_player is not None else None
        return (
            raw_event.secondary_player.player_id
            if raw_event.secondary_player is not None
            else raw_event.primary_player.player_id if raw_event.primary_player is not None else None
        )

    def _secondary_actor_id(
        self, *, raw_event, team_side: str | None, home_team_id: str, away_team_id: str
    ) -> str | None:
        event_side = (
            "home" if raw_event.team_id == home_team_id else "away" if raw_event.team_id == away_team_id else None
        )
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
            event.event_type == "goal" or (event.event_type == "card" and event.metadata.get("card_type") == "red")
            for event in recent_events
        )
        if recent_events:
            home_weight = sum(
                1
                for event in recent_events
                if event.metadata.get("team_side") == "home" and event.event_type in {"goal", "shot"}
            )
            away_weight = sum(
                1
                for event in recent_events
                if event.metadata.get("team_side") == "away" and event.event_type in {"goal", "shot"}
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

    def _resolve_runtime_for_spectate(self, match_id: str) -> _LiveMatchRuntime | None:
        with self._lock:
            runtime = self._matches.get(match_id)
            if match_id in self._halted_matches:
                raise LiveMatchError("Match has been halted by the admin kill switch.")
            if runtime is not None and runtime.live:
                return runtime
        cached_state = self.get_state(match_id)
        if cached_state is None or not cached_state.is_live:
            raise LiveMatchError("Match is not currently live for spectating.")
        return None

    def _resolve_viewer_source(self, events: Sequence[LiveMatchStreamEventView]) -> str:
        for event in events:
            source = str(event.meta.get("source") or event.metadata.get("source") or "").strip().lower()
            if source == "infinite_league":
                return "infinite_league_runtime"
        return "live_match_hub"

    def _build_state_view(self, runtime: _LiveMatchRuntime) -> LiveMatchStateView:
        crowd_state = _runtime_crowd_state(runtime)
        if self.attendance_overlay_provider is not None:
            crowd_state = self.attendance_overlay_provider(runtime.match_id, crowd_state)
        return LiveMatchStateView(
            match_id=runtime.match_id,
            channel=runtime.channel,
            is_live=runtime.live,
            read_only=runtime.read_only,
            spectator_count=len(runtime.spectator_user_ids),
            event_count=len(runtime.published_events),
            snapshot=runtime.last_snapshot,
            crowd_state=crowd_state,
            spectator_sync=_runtime_spectator_sync(runtime),
        )

    def _cache_snapshot(self, runtime: _LiveMatchRuntime) -> None:
        if runtime.last_snapshot is None:
            return
        self._hot_cache.set_match_state(
            runtime.match_id,
            self._build_state_view(runtime).model_dump(mode="json"),
            ttl_seconds=self.snapshot_ttl_seconds,
        )

    def _publish_channel(self, channel: str, payload: dict[str, object]) -> None:
        if not channel.startswith("match:"):
            return
        self._hot_cache.publish_match_channel(channel, dict(payload))

    def _publish_domain_events(self, match_id: str, events: Sequence[LiveMatchStreamEventView]) -> None:
        if self.event_publisher is None:
            return
        for event in events:
            payload = {
                "match_id": match_id,
                "event_id": event.event_id,
                "source_event_id": event.source_event_id or event.event_id,
                "sequence": event.sequence,
                "sequence_id": event.sequence_id or event.sequence,
                "event_type": event.event_type,
                "source_event_type": event.source_event_type or event.event_type,
                "minute": event.minute,
                "clock": event.clock_label,
                "team_id": event.team_id,
                "team": event.team,
                "team_side": event.team_side,
                "player_id": event.player_id,
                "player": event.player,
                "secondary_player_id": event.secondary_player_id,
                "secondary_player": event.secondary_player,
                "home_score": event.home_score,
                "away_score": event.away_score,
                "presentation_second": event.presentation_second,
                "tick": event.tick,
                "importance_score": event.importance_score,
                "highlight_eligible": event.highlight_eligible,
                "audio_stem_channels": list(event.audio_stem_channels),
                "metadata": event.metadata,
            }
            self.event_publisher.publish(
                DomainEvent(
                    name="match.events",
                    payload=payload,
                    aggregate_id=match_id,
                    aggregate_type="match",
                    partition_key=match_id,
                    producer="live-match-hub",
                )
            )


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
    draw_signal = 0.95 - (abs(score_swing) * 1.05) - (time_factor * 0.45) - (abs(possession_tilt) * 0.35)

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
    hub._hot_cache = HotPathCache(hub.cache_backend)
    hub.event_publisher = getattr(app.state, "event_publisher", hub.event_publisher)
    hub.attendance_overlay_provider = getattr(
        app.state, "stadium_ticket_crowd_overlay_provider", hub.attendance_overlay_provider
    )
    hub.stadium_service.session_factory = getattr(app.state, "session_factory", hub.session_factory)
    hub.commentary_engine.configure(
        settings=getattr(app.state, "settings", None),
        cache_backend=hub.cache_backend,
    )
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
    stadium_profile: StadiumImmersionProfile,
    team_side: str | None,
    max_latency_ms: int,
    checkpoint_interval_seconds: int,
    generated_commentary: GeneratedCommentary | None,
) -> MatchExperienceLayerView:
    pressure = _pressure_value(raw_event.metadata.get("pressure_level"))
    speed = _clamp_float(float(meta.get("ball_speed", 0.0) or 0.0) / 36.0, 0.0, 1.0)
    shoot_score = (
        0.72
        if raw_event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_SCORED}
        else (
            0.46
            if raw_event.event_type
            in {MatchEventType.SHOT, MatchEventType.SHOT_ON_TARGET, MatchEventType.MISSED_BIG_CHANCE}
            else 0.08
        )
    )
    sprint_score = 0.20 + (pressure * 0.42) + (speed * 0.24)
    run_score = 0.28 + ((1.0 - pressure) * 0.20)
    total = max(run_score + sprint_score + shoot_score, 0.0001)

    position = meta.get("curve", 0.0)
    home = _clamp_float(float(raw_event.metadata.get("crowd_home", 0.5) or 0.5), 0.0, 1.0)
    away = _clamp_float(float(raw_event.metadata.get("crowd_away", 0.5) or 0.5), 0.0, 1.0)
    top_moment = raw_event.event_type in {
        MatchEventType.GOAL,
        MatchEventType.PENALTY_GOAL,
        MatchEventType.PENALTY_SCORED,
        MatchEventType.MISSED_BIG_CHANCE,
        MatchEventType.RED_CARD,
    }
    rivalry_intensity = _clamp_float(
        _float_value(raw_event.metadata.get("rivalry_intensity"), default=0.0)
        or (0.85 if str(profile).strip().lower() in {"derby", "fever", "volatile"} else 0.35),
        0.0,
        1.0,
    )
    raw_event_type = str(getattr(raw_event.event_type, "value", raw_event.event_type) or "").strip().lower()
    crowd_state = StadiumImmersionService().event_crowd_state(
        profile=stadium_profile,
        base_home=home,
        base_away=away,
        raw_event_type=raw_event_type,
        rivalry_intensity=rivalry_intensity,
        scoring_side=team_side,
    )

    commentary_line = generated_commentary.line if generated_commentary is not None else raw_event.commentary
    commentary_tone = (
        generated_commentary.tone if generated_commentary is not None else "hype" if top_moment else "tactical"
    )
    commentary_commentator = (
        generated_commentary.commentator if generated_commentary is not None else "lead" if top_moment else "analyst"
    )
    commentary_intensity = (
        generated_commentary.intensity
        if generated_commentary is not None
        else round(
            _clamp_float(((int(meta.get("importance", 1) or 1) - 1) / 4.0) + (0.25 if top_moment else 0.0), 0.18, 1.0),
            3,
        )
    )
    commentary_audio_channel = (
        generated_commentary.audio_channel
        if generated_commentary is not None
        else "headline" if top_moment else "match_bed"
    )
    speaker_role = "lead" if commentary_commentator in {"lead", "main", "play_by_play"} else "analyst"
    voice_profile = "play_by_play" if speaker_role == "lead" else "analyst"
    speech_rate = round(_clamp_float(0.92 + (commentary_intensity * 0.38), 0.85, 1.3), 3)
    interrupt_priority = (
        95
        if raw_event_type in {"goal", "penalty_goal", "penalty_scored"}
        else 82 if raw_event_type in {"red_card", "card"} else 68 if top_moment else 36
    )

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
            line=commentary_line,
            tone=commentary_tone,
            commentator=commentary_commentator,
            speaker_role=speaker_role,
            language="en",
            intensity=commentary_intensity,
            tts_ready=bool(str(commentary_line).strip()),
            banter_layer=raw_event.secondary_player is not None and top_moment,
            audio_channel=commentary_audio_channel,
            voice_profile=voice_profile,
            voice_id=f"gtex-{voice_profile}",
            accent=stadium_profile.region_personality,
            energy_level=commentary_intensity,
            speech_rate=speech_rate,
            interrupt_priority=interrupt_priority,
            stem_routing=["commentary"] if not top_moment else ["commentary", "stadium_fx"],
        ),
        crowd=MatchCrowdStateView(
            profile=profile,
            home_intensity=float(crowd_state["home_intensity"]),
            away_intensity=float(crowd_state["away_intensity"]),
            dominant_side=str(crowd_state["dominant_side"]),
            chant_level=float(crowd_state["chant_level"]),
            hostility=float(crowd_state["hostility"]),
            spike=bool(crowd_state["spike"]),
            crowd_intensity=float(crowd_state["crowd_intensity"]),
            crowd_bias=str(crowd_state["crowd_bias"]),
            crowd_mood=str(crowd_state["crowd_mood"]),
            stadium_theme=str(crowd_state["stadium_theme"]),
            stadium_name=str(crowd_state["stadium_name"]),
            region_personality=str(crowd_state["region_personality"]),
            crowd_personality=str(crowd_state["crowd_personality"]),
            stadium_fx=str(crowd_state["stadium_fx"]),
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


__all__ = ["LiveMatchError", "LiveMatchHub", "LiveMatchPlaybackContext", "ensure_live_match_hub"]
