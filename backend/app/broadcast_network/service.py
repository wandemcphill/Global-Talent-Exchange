from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.broadcast_network.commentary_service import CommentaryOrchestratorService
from app.broadcast_network.schemas import (
    BroadcastAudioManifestView,
    BroadcastChannelView,
    BroadcastDirectorFocusView,
    BroadcastHomeView,
    BroadcastProgramSlotView,
    BroadcastWatchRewardView,
    ChannelSessionView,
)
from app.core.cache import CacheBackend, JsonCacheNamespace, NullCacheBackend
from app.infinite_league.service import ensure_infinite_league_runtime
from app.live_matches.schemas import LiveMatchSpeedModeView, SpectatorSessionView
from app.live_matches.service import ensure_live_match_hub
from app.live_ops.service import LiveOpsService
from app.models.broadcast_watch_session import BroadcastWatchSession
from app.models.competition_match import CompetitionMatch


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return _utcnow()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _merge_session_access(base: dict[str, Any], overlay: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base)
    if overlay is None:
        return merged
    premium_features = dict(merged.get("premium_features") or {})
    premium_features.update(dict(overlay.get("premium_features") or {}))
    if premium_features:
        merged["premium_features"] = premium_features
    channel_context = dict(merged.get("channel_context") or {})
    channel_context.update(dict(overlay.get("channel_context") or {}))
    if channel_context:
        merged["channel_context"] = channel_context
    for key in ("sponsored_overlays", "stadium_ads"):
        values = list(merged.get(key) or [])
        values.extend(list(overlay.get(key) or []))
        if values:
            merged[key] = values
    for key in ("access_source", "rights_owner_id", "viewing_fee_coin", "sync_strategy", "watch_party_enabled", "reactions_enabled"):
        if key in overlay and overlay.get(key) is not None:
            merged[key] = overlay[key]
    return merged


class BroadcastNetworkError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _ProgramCandidate:
    match_id: str
    title: str
    subtitle: str
    viewer_count: int
    goals: int
    minute: int
    match_stage: float
    rivalry: float
    upset_probability: float
    recent_moment_velocity: float
    momentum: str
    focus_target: str
    focus_reason: str
    score: float
    is_live: bool
    watch_route: str
    replay_route: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BroadcastDirectorService:
    def score(self, candidate: _ProgramCandidate) -> float:
        return round(
            float(candidate.viewer_count)
            + (candidate.goals * 25.0)
            + (candidate.match_stage * 18.0)
            + (candidate.rivalry * 20.0)
            + (candidate.upset_probability * 18.0)
            + (candidate.recent_moment_velocity * 14.0),
            3,
        )

    def focus(self, candidate: _ProgramCandidate) -> BroadcastDirectorFocusView:
        return BroadcastDirectorFocusView(
            match_id=candidate.match_id,
            score=self.score(candidate),
            viewer_count=candidate.viewer_count,
            goals=candidate.goals,
            match_stage=round(candidate.match_stage, 3),
            rivalry=round(candidate.rivalry, 3),
            upset_probability=round(candidate.upset_probability, 3),
            recent_moment_velocity=round(candidate.recent_moment_velocity, 3),
            momentum=candidate.momentum,
            focus_target=candidate.focus_target,
            focus_reason=candidate.focus_reason,
            metadata=dict(candidate.metadata),
        )


@dataclass(slots=True)
class BroadcastNetworkRuntime:
    app: FastAPI
    session_factory: sessionmaker[Session] | None = None
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    schedule_ttl_seconds: int = 15
    commentary_orchestrator: CommentaryOrchestratorService = field(default_factory=CommentaryOrchestratorService)
    director_service: BroadcastDirectorService = field(default_factory=BroadcastDirectorService)
    _cache: JsonCacheNamespace = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._cache = JsonCacheNamespace(self.cache_backend)

    def list_channels(self) -> list[BroadcastChannelView]:
        channels, _ = self._channel_bundle()
        return channels

    def home(self) -> BroadcastHomeView:
        cache_key = "broadcast_network:home"
        cached = self._cache.get_json(cache_key)
        if isinstance(cached, dict) and isinstance(cached.get("payload"), dict):
            try:
                payload = BroadcastHomeView.model_validate(cached["payload"])
                if self._home_payload_is_current(payload):
                    return payload
            except Exception:
                pass
        channels, ranked = self._channel_bundle()
        featured_channel = next((channel for channel in channels if channel.channel_id == "trending"), channels[0] if channels else None)
        payload = BroadcastHomeView(
            channels=channels,
            featured_channel=featured_channel,
            match_of_the_moment=featured_channel.current_program if featured_channel is not None else None,
            highest_engagement_match=ranked[0] if ranked else None,
            generated_at=_utcnow(),
            metadata={"channel_count": len(channels)},
        )
        self._cache.set_json(cache_key, payload.model_dump(mode="json"), ttl_seconds=self.schedule_ttl_seconds)
        return payload

    def join_channel(self, *, channel_id: str, user_id: str) -> ChannelSessionView:
        channel = self._session_channel_by_id(channel_id)
        if channel is None:
            raise BroadcastNetworkError("Broadcast channel was not found.")
        session = self._create_watch_session(
            user_id=user_id,
            channel_id=channel_id,
            current_match_id=channel.current_program.match_id if channel.current_program is not None else None,
        )
        return self.refresh_channel_session(channel_id=channel_id, session_id=session.id, hydrate_match_session=True)

    def refresh_channel_session(
        self,
        *,
        channel_id: str,
        session_id: str,
        hydrate_match_session: bool = False,
    ) -> ChannelSessionView:
        watch_session = self._load_watch_session(session_id=session_id, channel_id=channel_id)
        channel = self._session_channel_by_id(channel_id)
        if channel is None:
            raise BroadcastNetworkError("Broadcast channel was not found.")
        current_program = channel.current_program
        reward = self._touch_watch_session(
            session_id=watch_session.id,
            current_match_id=current_program.match_id if current_program is not None else None,
        )
        match_session = None
        if hydrate_match_session and current_program is not None and current_program.match_id is not None:
            match_session = self._join_match_session(
                match_id=current_program.match_id,
                user_id=watch_session.user_id,
                channel_id=channel_id,
                channel_type=channel.channel_type,
            )
        return ChannelSessionView(
            session_id=watch_session.id,
            channel=channel,
            current_program=current_program,
            upcoming_programs=list(channel.upcoming_programs),
            director_focus=self._director_focus_for_program(current_program),
            match_session=match_session,
            fallback_replay_route=current_program.replay_route if current_program is not None else None,
            websocket_path=f"/api/broadcast/channels/{channel_id}/stream?session_id={watch_session.id}",
            audio_stem_websocket_path=f"/api/broadcast/channels/{channel_id}/audio/stems/stream?session_id={watch_session.id}",
            watch_reward=reward,
            joined_at=watch_session.started_at,
            metadata={"auto_switch_enabled": channel.auto_switch_enabled},
        )

    def finalize_watch_session(self, *, session_id: str, channel_id: str) -> BroadcastWatchRewardView:
        watch_session = self._load_watch_session(session_id=session_id, channel_id=channel_id)
        if self.session_factory is None:
            return self._watch_reward_view(watch_session)
        with self.session_factory() as session:
            item = session.get(BroadcastWatchSession, watch_session.id)
            if item is None:
                return self._watch_reward_view(watch_session)
            now = _utcnow()
            item.watched_seconds += max((now - _as_utc(item.last_seen_at)).total_seconds(), 0.0)
            item.last_seen_at = now
            item.ended_at = now
            item.status = "completed"
            if item.rewarded_at is None:
                xp_amount = max(5, int(item.watched_seconds // 60) * 10 or 5)
                grant = LiveOpsService(session).award_xp(
                    user_id=item.user_id,
                    source_type="broadcast_watch",
                    amount=xp_amount,
                    reference_key=f"broadcast-watch:{item.id}",
                    metadata={
                        "channel_id": item.channel_id,
                        "current_match_id": item.current_match_id,
                        "watched_seconds": round(item.watched_seconds, 2),
                        "switch_count": item.switch_count,
                    },
                )
                item.reward_xp = int(grant.amount)
                item.rewarded_at = now
            session.commit()
            session.refresh(item)
            return self._watch_reward_view(item)

    def audio_manifest(self, *, channel_id: str, session_id: str) -> BroadcastAudioManifestView:
        watch_session = self._load_watch_session(session_id=session_id, channel_id=channel_id)
        channel = self._session_channel_by_id(channel_id)
        match_id = (
            channel.current_program.match_id
            if channel is not None and channel.current_program is not None and channel.current_program.match_id is not None
            else watch_session.current_match_id
        )
        return self.commentary_orchestrator.build_manifest(channel_id=channel_id, match_id=match_id)

    def audio_frames(self, *, channel_id: str, session_id: str, cursor: int) -> tuple[list[dict[str, Any]], int]:
        watch_session = self._load_watch_session(session_id=session_id, channel_id=channel_id)
        if not watch_session.current_match_id:
            return [], cursor
        hub = ensure_live_match_hub(self.app)
        events, next_cursor = hub.get_events_since(watch_session.current_match_id, cursor)
        frames = self.commentary_orchestrator.build_frames(events, channel_id=channel_id)
        return [item.model_dump(mode="json") for item in frames], next_cursor

    def _channel_bundle(self) -> tuple[list[BroadcastChannelView], list[BroadcastDirectorFocusView]]:
        live_candidates = self._live_candidates()
        ai_candidates = self._ai_candidates()
        ranked_candidates = sorted(
            [*live_candidates, *ai_candidates],
            key=lambda candidate: (candidate.score, candidate.viewer_count, candidate.goals, candidate.title),
            reverse=True,
        )[:20]
        ranked_focus = [self.director_service.focus(candidate) for candidate in ranked_candidates[:20]]
        viewer_counts = self._channel_viewer_counts()
        channels = [
            self._build_channel(
                channel_id="live",
                name="Live Channel",
                channel_type="live",
                description="Ongoing live coverage across the GTEX network.",
                candidates=live_candidates,
                viewer_count=viewer_counts.get("live", 0),
            ),
            self._build_channel(
                channel_id="trending",
                name="Trending Channel",
                channel_type="trending",
                description="Highest-engagement match selection with auto-switching.",
                candidates=list(ranked_candidates),
                viewer_count=viewer_counts.get("trending", 0),
            ),
            self._build_channel(
                channel_id="ai",
                name="AI Channel",
                channel_type="ai",
                description="24/7 AI-generated fixtures and replay loops.",
                candidates=ai_candidates,
                viewer_count=viewer_counts.get("ai", 0),
            ),
            self._build_channel(
                channel_id="tournament",
                name="Tournament Channel",
                channel_type="tournament",
                description="Official finals, cups, and pressure matches.",
                candidates=[
                    candidate
                    for candidate in ranked_candidates
                    if bool(candidate.metadata.get("is_final")) or bool(candidate.metadata.get("is_tournament"))
                ],
                viewer_count=viewer_counts.get("tournament", 0),
            ),
        ]
        for channel in channels:
            self._cache.set_json(
                f"broadcast_network:channel:{channel.channel_id}",
                channel.model_dump(mode="json"),
                ttl_seconds=self.schedule_ttl_seconds,
            )
        return channels, ranked_focus

    def _channel_by_id(self, channel_id: str, *, use_cache: bool = True) -> BroadcastChannelView | None:
        if use_cache:
            cached = self._cache.get_json(f"broadcast_network:channel:{channel_id}")
            if isinstance(cached, dict) and isinstance(cached.get("payload"), dict):
                try:
                    return BroadcastChannelView.model_validate(cached["payload"])
                except Exception:
                    pass
        channels, _ = self._channel_bundle()
        return next((channel for channel in channels if channel.channel_id == channel_id), None)

    def _session_channel_by_id(self, channel_id: str) -> BroadcastChannelView | None:
        if channel_id == "live":
            return self._build_channel(
                channel_id="live",
                name="Live Channel",
                channel_type="live",
                description="Ongoing live coverage across the GTEX network.",
                candidates=self._live_candidates(),
                viewer_count=self._channel_viewer_counts().get("live", 0),
            )
        return self._channel_by_id(channel_id, use_cache=False)

    def _ranked_candidates(self) -> list[_ProgramCandidate]:
        candidates = [*self._live_candidates(), *self._ai_candidates()]
        return sorted(
            candidates,
            key=lambda candidate: (candidate.score, candidate.viewer_count, candidate.goals, candidate.title),
            reverse=True,
        )[:20]

    def _live_candidates(self) -> list[_ProgramCandidate]:
        hub = ensure_live_match_hub(self.app)
        print(
            "DEBUG _live_candidates",
            {
                "app_id": id(self.app),
                "hub_id": id(hub),
                "state_hub_id": id(getattr(self.app.state, "live_match_hub", None)),
                "active_before": hub.list_active_matches(),
                "match_keys": list(getattr(hub, "_matches", {}).keys()),
            },
        )
        active_match_ids = set(hub.list_active_matches())
        with hub._lock:
            for runtime in hub._matches.values():
                if runtime.last_snapshot is None:
                    continue
                if runtime.live or runtime.completed_at is None:
                    active_match_ids.add(runtime.match_id)
                    continue
                age_seconds = max((_utcnow() - _as_utc(runtime.completed_at)).total_seconds(), 0.0)
                if age_seconds <= self.schedule_ttl_seconds:
                    active_match_ids.add(runtime.match_id)
        if not active_match_ids:
            return []
        matches: dict[str, CompetitionMatch] = {}
        if self.session_factory is not None:
            with self.session_factory() as session:
                matches = {
                    item.id: item
                    for item in session.scalars(
                        select(CompetitionMatch).where(CompetitionMatch.id.in_(active_match_ids))
                    ).all()
                }
        candidates: list[_ProgramCandidate] = []
        for match_id in sorted(active_match_ids):
            state = hub.get_state(match_id)
            print("DEBUG _live_candidates.state", match_id, state)
            if state is None:
                continue
            snapshot = state.snapshot
            score = snapshot.score
            match = matches.get(match_id)
            metadata_json = dict(match.metadata_json or {}) if match is not None else {}
            replay_payload = metadata_json.get("replay_payload") if isinstance(metadata_json.get("replay_payload"), dict) else {}
            summary = replay_payload.get("summary") if isinstance(replay_payload, dict) else {}
            home_stats = summary.get("home_stats") if isinstance(summary, dict) else {}
            away_stats = summary.get("away_stats") if isinstance(summary, dict) else {}
            atmosphere_profile = str(metadata_json.get("atmosphere_profile") or replay_payload.get("atmosphere_profile") or "standard")
            home_team_name = str(home_stats.get("team_name") or metadata_json.get("home_team_name") or "Home")
            away_team_name = str(away_stats.get("team_name") or metadata_json.get("away_team_name") or "Away")
            minute = int(snapshot.current_minute or 0)
            goals = int(score.home or 0) + int(score.away or 0)
            rivalry = self._rivalry_score(
                atmosphere_profile=atmosphere_profile,
                stage=str(match.stage or "") if match is not None else "",
                metadata=metadata_json,
            )
            recent_velocity = _clamp((0.72 if snapshot.dramatic_event else 0.24) + (goals * 0.08), 0.0, 1.0)
            momentum = snapshot.momentum_indicator or "balanced"
            focus_target, focus_reason = self._focus_target(snapshot=snapshot.model_dump(mode="json"), momentum=momentum)
            candidate = _ProgramCandidate(
                match_id=match_id,
                title=f"{home_team_name} vs {away_team_name}",
                subtitle=f"{minute}' - {state.spectator_count} watching",
                viewer_count=int(state.spectator_count),
                goals=goals,
                minute=minute,
                match_stage=_clamp(minute / 95.0, 0.0, 1.0),
                rivalry=rivalry,
                upset_probability=self._upset_probability(
                    home_score=int(score.home or 0),
                    away_score=int(score.away or 0),
                    snapshot=snapshot.model_dump(mode="json"),
                ),
                recent_moment_velocity=recent_velocity,
                momentum=momentum,
                focus_target=focus_target,
                focus_reason=focus_reason,
                score=0.0,
                is_live=bool(state.is_live),
                watch_route=f"/matches/{match_id}/watch",
                replay_route=f"/api/matches/{match_id}/highlights",
                metadata={
                    "ai_match": False,
                    "is_final": self._is_final(match),
                    "is_tournament": match is not None,
                    "atmosphere_profile": atmosphere_profile,
                    "home_team_name": home_team_name,
                    "away_team_name": away_team_name,
                },
            )
            candidates.append(replace(candidate, score=self.director_service.score(candidate)))
        print("DEBUG _live_candidates.result", [candidate.match_id for candidate in candidates])
        return candidates

    def _ai_candidates(self) -> list[_ProgramCandidate]:
        runtime = ensure_infinite_league_runtime(self.app)
        hub = ensure_live_match_hub(self.app)
        candidates: list[_ProgramCandidate] = []
        for match in runtime.list_matches(limit=8):
            state = hub.get_state(match.match_id)
            minute = int(state.snapshot.current_minute) if state is not None else min(90, (match.round_number * 7) % 90)
            viewer_count = int(state.spectator_count) if state is not None else max(6, match.viral_score // 10)
            goals = int(match.home_goals) + int(match.away_goals)
            candidate = _ProgramCandidate(
                match_id=match.match_id,
                title=f"{match.home_club_name} vs {match.away_club_name}",
                subtitle=f"Season {match.season} - Round {match.round_number} - AI feed",
                viewer_count=viewer_count,
                goals=goals,
                minute=minute,
                match_stage=_clamp(minute / 95.0, 0.0, 1.0),
                rivalry=0.72 if "derby" in match.headline.lower() else 0.44,
                upset_probability=0.65 if match.upset else 0.28,
                recent_moment_velocity=_clamp((match.viral_score / 100.0) + (0.12 if state is not None and state.snapshot.dramatic_event else 0.0), 0.0, 1.0),
                momentum=state.snapshot.momentum_indicator if state is not None else "balanced",
                focus_target="final_third" if goals > 0 else "midfield",
                focus_reason="ai_highlight_loop" if goals > 0 else "ai_schedule_fill",
                score=0.0,
                is_live=True,
                watch_route=f"/matches/{match.match_id}/watch",
                replay_route=f"/api/matches/{match.match_id}/highlights",
                metadata={
                    "ai_match": True,
                    "is_final": False,
                    "is_tournament": False,
                    "league_name": match.league_name,
                    "headline": match.headline,
                    "viral_score": match.viral_score,
                },
            )
            candidates.append(replace(candidate, score=self.director_service.score(candidate)))
        return candidates

    def _build_channel(
        self,
        *,
        channel_id: str,
        name: str,
        channel_type: str,
        description: str,
        candidates: list[_ProgramCandidate],
        viewer_count: int,
    ) -> BroadcastChannelView:
        now = _utcnow()
        selected = candidates[:6]
        current_program = (
            self._program_slot(channel_id=channel_id, candidate=selected[0], start_at=now - timedelta(seconds=45), offset_minutes=10)
            if selected
            else self._fallback_slot(channel_id=channel_id, generated_at=now)
        )
        upcoming_programs = [
            self._program_slot(channel_id=channel_id, candidate=candidate, start_at=now + timedelta(minutes=index * 12), offset_minutes=12)
            for index, candidate in enumerate(selected[1:6], start=1)
        ]
        return BroadcastChannelView(
            channel_id=channel_id,
            name=name,
            channel_type=channel_type,
            description=description,
            is_live=bool(current_program is not None and current_program.is_live),
            auto_switch_enabled=True,
            viewer_count=viewer_count,
            featured_match_id=current_program.match_id if current_program is not None else None,
            current_program=current_program,
            upcoming_programs=upcoming_programs,
            metadata={"scheduler": "director_cache", "program_count": len(selected)},
        )

    def _program_slot(
        self,
        *,
        channel_id: str,
        candidate: _ProgramCandidate,
        start_at: datetime,
        offset_minutes: int,
    ) -> BroadcastProgramSlotView:
        return BroadcastProgramSlotView(
            slot_id=f"{channel_id}:{candidate.match_id}:{candidate.minute}",
            channel_id=channel_id,
            match_id=candidate.match_id,
            title=candidate.title,
            subtitle=candidate.subtitle,
            program_type="ai_match" if bool(candidate.metadata.get("ai_match")) else "live_match",
            start_at=start_at,
            end_at=start_at + timedelta(minutes=max(offset_minutes, 8)),
            score=candidate.score,
            is_live=candidate.is_live,
            watch_route=candidate.watch_route,
            replay_route=candidate.replay_route,
            metadata=dict(candidate.metadata),
        )

    def _fallback_slot(self, *, channel_id: str, generated_at: datetime) -> BroadcastProgramSlotView:
        return BroadcastProgramSlotView(
            slot_id=f"{channel_id}:replay-loop",
            channel_id=channel_id,
            match_id=None,
            title="GTEX Replay Loop",
            subtitle="Switching to replay coverage while the next live window is prepared.",
            program_type="replay_loop",
            start_at=generated_at,
            end_at=generated_at + timedelta(minutes=15),
            score=0.0,
            is_live=False,
            watch_route=None,
            replay_route="/api/matches/highlights",
            metadata={"fallback_mode": "replay"},
        )

    def _director_focus_for_program(self, program: BroadcastProgramSlotView | None) -> BroadcastDirectorFocusView | None:
        if program is None or program.match_id is None:
            return None
        for candidate in self._ranked_candidates():
            if candidate.match_id == program.match_id:
                return self.director_service.focus(candidate)
        return None

    def _join_match_session(
        self,
        *,
        match_id: str,
        user_id: str,
        channel_id: str,
        channel_type: str,
    ) -> SpectatorSessionView | None:
        hub = ensure_live_match_hub(self.app)
        state = hub.get_state(match_id)
        if state is None:
            self._bootstrap_infinite_league_stream(hub, match_id)
            state = hub.get_state(match_id)
        if state is None:
            return None
        spectator_session = hub.join_spectate(match_id, user_id)
        access_payload = {
            "access_source": "infinite_league" if channel_type == "ai" else "broadcast_network",
            "viewing_fee_coin": 0,
            "premium_features": {
                "generated_commentary": True,
                "instant_replay": True,
                "dual_commentary": True,
            },
            "channel_context": {
                "channel_id": channel_id,
                "channel_type": channel_type,
                "auto_switch_enabled": True,
            },
            "sync_strategy": state.spectator_sync.sync_strategy if state.spectator_sync is not None else "deterministic_playback",
            "watch_party_enabled": True,
            "reactions_enabled": True,
        }
        ticketing_runtime = getattr(self.app.state, "ticketing_runtime", None)
        if ticketing_runtime is not None:
            access_payload = _merge_session_access(
                access_payload,
                ticketing_runtime.resolve_attendee_access_for_user_id(
                    match_id=match_id,
                    user_id=user_id,
                    consume=True,
                ),
            )
        return SpectatorSessionView(
            id=spectator_session.id,
            match_id=match_id,
            user_id=user_id,
            joined_at=spectator_session.joined_at,
            read_only=True,
            channel=f"match:{match_id}:events",
            websocket_path=f"/api/matches/{match_id}/stream?session_id={spectator_session.id}",
            commentary_websocket_path=f"/api/matches/{match_id}/commentary/stream?session_id={spectator_session.id}",
            audio_stem_websocket_path=f"/api/matches/{match_id}/audio/stems/stream?session_id={spectator_session.id}",
            presence_channel=f"match:{match_id}:events",
            presence_websocket_path=f"/ws/spectate/{match_id}",
            tts_websocket_path="/tts/live?voice=default",
            replay_route=f"/api/matches/{match_id}/highlights",
            speed_modes=[
                LiveMatchSpeedModeView(key="normal", label="Normal", target_duration_seconds=90),
                LiveMatchSpeedModeView(key="fast", label="Fast", target_duration_seconds=30),
                LiveMatchSpeedModeView(key="turbo", label="Turbo", target_duration_seconds=10),
            ],
            access_source=access_payload.get("access_source"),
            rights_owner_id=access_payload.get("rights_owner_id"),
            viewing_fee_coin=access_payload.get("viewing_fee_coin") or 0,
            premium_features=dict(access_payload.get("premium_features") or {}),
            sponsored_overlays=list(access_payload.get("sponsored_overlays") or []),
            stadium_ads=list(access_payload.get("stadium_ads") or []),
            channel_context=dict(access_payload.get("channel_context") or {}),
            sync_strategy=str(access_payload.get("sync_strategy") or "deterministic_playback"),
            watch_party_enabled=bool(access_payload.get("watch_party_enabled", True)),
            reactions_enabled=bool(access_payload.get("reactions_enabled", True)),
        )

    def _create_watch_session(self, *, user_id: str, channel_id: str, current_match_id: str | None) -> BroadcastWatchSession:
        if self.session_factory is None:
            return BroadcastWatchSession(
                user_id=user_id,
                channel_id=channel_id,
                current_match_id=current_match_id,
                metadata_json={},
            )
        with self.session_factory() as session:
            item = BroadcastWatchSession(
                user_id=user_id,
                channel_id=channel_id,
                current_match_id=current_match_id,
                metadata_json={"source": "broadcast_network"},
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def _load_watch_session(self, *, session_id: str, channel_id: str) -> BroadcastWatchSession:
        if self.session_factory is None:
            raise BroadcastNetworkError("Broadcast watch sessions are unavailable.")
        with self.session_factory() as session:
            item = session.get(BroadcastWatchSession, session_id)
            if item is None or item.channel_id != channel_id:
                raise BroadcastNetworkError("Broadcast watch session was not found.")
            return item

    def _touch_watch_session(self, *, session_id: str, current_match_id: str | None) -> BroadcastWatchRewardView:
        if self.session_factory is None:
            return BroadcastWatchRewardView(session_id=session_id, channel_id="unknown")
        with self.session_factory() as session:
            item = session.get(BroadcastWatchSession, session_id)
            if item is None:
                raise BroadcastNetworkError("Broadcast watch session was not found.")
            now = _utcnow()
            item.watched_seconds += max((now - _as_utc(item.last_seen_at)).total_seconds(), 0.0)
            if item.current_match_id and current_match_id and item.current_match_id != current_match_id:
                item.switch_count += 1
            item.current_match_id = current_match_id
            item.last_seen_at = now
            session.commit()
            session.refresh(item)
            return self._watch_reward_view(item)

    @staticmethod
    def _watch_reward_view(item: BroadcastWatchSession) -> BroadcastWatchRewardView:
        return BroadcastWatchRewardView(
            session_id=item.id,
            channel_id=item.channel_id,
            watched_seconds=float(item.watched_seconds),
            switch_count=int(item.switch_count),
            rewarded=item.rewarded_at is not None,
            xp_awarded=int(item.reward_xp),
            finalized_at=item.rewarded_at or item.ended_at,
            metadata=dict(item.metadata_json or {}),
        )

    def _channel_viewer_counts(self) -> dict[str, int]:
        if self.session_factory is None:
            return {}
        with self.session_factory() as session:
            rows = session.execute(
                select(
                    BroadcastWatchSession.channel_id,
                    func.count(func.distinct(BroadcastWatchSession.user_id)),
                ).where(BroadcastWatchSession.status == "active").group_by(BroadcastWatchSession.channel_id)
            ).all()
        return {str(channel_id): int(count) for channel_id, count in rows}

    def _bootstrap_infinite_league_stream(self, hub, match_id: str) -> bool:
        stream = ensure_infinite_league_runtime(self.app).live_stream(match_id)
        if stream is None:
            return False
        hub.start_synthetic_stream(
            match_id=stream.match_id,
            home_team_id=stream.home_team_id,
            away_team_id=stream.away_team_id,
            home_team_name=stream.home_team_name,
            away_team_name=stream.away_team_name,
            base_home_possession=stream.base_home_possession,
            base_away_possession=stream.base_away_possession,
            events=stream.events,
            atmosphere_profile=stream.atmosphere_profile,
            sync_strategy=stream.sync_strategy,
            checkpoint_interval_seconds=stream.checkpoint_interval_seconds,
            max_latency_ms=stream.max_latency_ms,
            read_only=True,
        )
        return True

    @staticmethod
    def _rivalry_score(*, atmosphere_profile: str, stage: str, metadata: dict[str, Any]) -> float:
        normalized_atmosphere = (atmosphere_profile or "").strip().lower()
        normalized_stage = (stage or "").strip().lower()
        if normalized_atmosphere in {"derby", "fever", "volatile"}:
            return 0.86
        if "final" in normalized_stage:
            return 0.78
        context = metadata.get("competition_context")
        if isinstance(context, dict) and bool(context.get("is_final")):
            return 0.78
        return 0.34

    @staticmethod
    def _upset_probability(*, home_score: int, away_score: int, snapshot: dict[str, Any]) -> float:
        win_probability = snapshot.get("win_probability") if isinstance(snapshot.get("win_probability"), dict) else {}
        if home_score == away_score:
            return 0.18
        if home_score > away_score:
            home_probability = float(win_probability.get("home") or 0.5)
            return round(_clamp(max(0.0, 0.62 - home_probability), 0.0, 1.0), 3)
        away_probability = float(win_probability.get("away") or 0.5)
        return round(_clamp(max(0.0, 0.62 - away_probability), 0.0, 1.0), 3)

    @staticmethod
    def _focus_target(*, snapshot: dict[str, Any], momentum: str) -> tuple[str, str]:
        if bool(snapshot.get("dramatic_event")):
            return "penalty_box", "dramatic_event"
        if momentum == "home":
            return "home_attack", "home_momentum"
        if momentum == "away":
            return "away_attack", "away_momentum"
        return "midfield", "match_state"

    @staticmethod
    def _is_final(match: CompetitionMatch | None) -> bool:
        if match is None:
            return False
        if "final" in str(match.stage or "").strip().lower():
            return True
        context = dict(match.metadata_json or {}).get("competition_context")
        return bool(context.get("is_final")) if isinstance(context, dict) else False

    def _home_payload_is_current(self, payload: BroadcastHomeView) -> bool:
        current_program = payload.match_of_the_moment
        if current_program is not None and current_program.match_id is not None:
            return True
        if payload.channels:
            live_channel = next((channel for channel in payload.channels if channel.channel_id == "live"), None)
            if live_channel is not None and live_channel.current_program is not None and live_channel.current_program.match_id is not None:
                return True
        return not any(
            candidate.match_id
            for candidate in self._ranked_candidates()
            if not bool(candidate.metadata.get("ai_match"))
        )


def ensure_broadcast_network_runtime(app: FastAPI) -> BroadcastNetworkRuntime:
    runtime = getattr(app.state, "broadcast_network_runtime", None)
    if runtime is None:
        runtime = BroadcastNetworkRuntime(
            app=app,
            session_factory=getattr(app.state, "session_factory", None),
            cache_backend=getattr(app.state, "cache_backend", NullCacheBackend()),
        )
        app.state.broadcast_network_runtime = runtime
    runtime.session_factory = getattr(app.state, "session_factory", runtime.session_factory)
    runtime.cache_backend = getattr(app.state, "cache_backend", runtime.cache_backend)
    runtime._cache = JsonCacheNamespace(runtime.cache_backend)
    return runtime


def bind_broadcast_network_runtime(app: FastAPI, _context) -> None:
    ensure_broadcast_network_runtime(app)


def shutdown_broadcast_network_runtime(app: FastAPI, _context) -> None:
    app.state.broadcast_network_runtime = None


__all__ = [
    "BroadcastDirectorService",
    "BroadcastNetworkError",
    "BroadcastNetworkRuntime",
    "bind_broadcast_network_runtime",
    "ensure_broadcast_network_runtime",
    "shutdown_broadcast_network_runtime",
]
