from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from math import hypot
from typing import Any

from app.live_matches.schemas import LiveMatchStateView, LiveMatchStreamEventView
from app.match_engine.schemas import (
    MatchBadgeVisualView,
    MatchCrowdStateView,
    MatchEventView,
    MatchKitVisualView,
    MatchMotionPredictionView,
    MatchPlayerStatsView,
    MatchPlayerVisualView,
    MatchReplayPayloadView,
    MatchRenderSyncEventView,
    MatchTeamVisualIdentityView,
)
from app.match_engine.simulation.models import MatchEventType, PlayerRole
from app.replay_archive.schemas import ReplayArchiveRecord, ReplayMomentView
from app.schemas.match_viewer import (
    MatchViewerAnimationState,
    MatchViewerCameraPreset,
    MatchTimelineFrameView,
    MatchViewerBallFrameView,
    MatchViewerEventType,
    MatchViewerEventView,
    MatchViewerPhase,
    MatchViewerPlaybackStage,
    MatchViewerPlayerFrameView,
    MatchViewerPlayerState,
    MatchViewerPossessionPhase,
    MatchViewerSide,
    MatchViewerTeamView,
    MatchViewerTransitionState,
    MatchViewerVector2View,
    MatchViewStateView,
)

_SUPPORTED_FORMATIONS = {"4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "4-4-1"}
_LINE_Y_MAP = {
    1: (50.0,),
    2: (34.0, 66.0),
    3: (22.0, 50.0, 78.0),
    4: (18.0, 39.0, 61.0, 82.0),
    5: (14.0, 32.0, 50.0, 68.0, 86.0),
}


@dataclass(slots=True)
class _PlayerRuntime:
    player_id: str
    team_id: str
    side: MatchViewerSide
    label: str
    shirt_number: int | None
    role: PlayerRole
    minutes_played: int | None = None
    substituted_in_minute: int | None = None
    substituted_out_minute: int | None = None
    rating: float | None = None
    base_stamina_pct: float | None = None


@dataclass(slots=True)
class _TeamRuntime:
    view: MatchViewerTeamView
    players_by_id: dict[str, _PlayerRuntime]
    lineup: list[str]
    bench: list[str]
    current_formation: str
    team_stamina_pct: float | None = None


@dataclass(slots=True)
class _ViewerEventContext:
    view: MatchViewerEventView
    source_type: str
    team_side: MatchViewerSide | None
    home_formation: str | None = None
    away_formation: str | None = None
    fallback_formation: str | None = None
    render_contract: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    motion: MatchMotionPredictionView | None = None
    crowd: MatchCrowdStateView | None = None


class MatchTimelineService:
    def build_from_replay_payload(self, replay_payload: MatchReplayPayloadView) -> MatchViewStateView:
        if replay_payload.visual_identity is None:
            raise ValueError("Viewer timeline requires replay visual identity data.")

        player_stats_by_id = {item.player_id: item for item in replay_payload.summary.player_stats}
        render_sync_by_event_id = {
            item.event_id: item
            for item in (replay_payload.render_sync.events if replay_payload.render_sync is not None else [])
        }
        home_stamina_pct = (
            float(replay_payload.halftime_analytics.home_stamina)
            if replay_payload.halftime_analytics is not None
            else None
        )
        away_stamina_pct = (
            float(replay_payload.halftime_analytics.away_stamina)
            if replay_payload.halftime_analytics is not None
            else None
        )
        home_team = self._team_view(
            replay_payload.visual_identity.home_team,
            side=MatchViewerSide.HOME,
            formation=replay_payload.summary.home_stats.started_formation,
        )
        away_team = self._team_view(
            replay_payload.visual_identity.away_team,
            side=MatchViewerSide.AWAY,
            formation=replay_payload.summary.away_stats.started_formation,
        )
        home_runtime = self._team_runtime(
            replay_payload.visual_identity.home_team,
            home_team,
            player_stats_by_id=player_stats_by_id,
            team_stamina_pct=home_stamina_pct,
        )
        away_runtime = self._team_runtime(
            replay_payload.visual_identity.away_team,
            away_team,
            player_stats_by_id=player_stats_by_id,
            team_stamina_pct=away_stamina_pct,
        )
        events = [
            self._context_from_match_event(
                item,
                render_sync=render_sync_by_event_id.get(item.event_id),
            )
            for item in replay_payload.timeline.events
        ]
        events = self._ensure_control_events(
            match_id=replay_payload.match_id,
            events=events,
            duration_seconds=float(replay_payload.timeline.presentation_duration_seconds),
            final_home_score=replay_payload.summary.home_score,
            final_away_score=replay_payload.summary.away_score,
        )
        frames = self._build_frames(
            match_id=replay_payload.match_id,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            events=events,
            duration_seconds=float(replay_payload.timeline.presentation_duration_seconds),
        )
        return MatchViewStateView(
            match_id=replay_payload.match_id,
            source="simulation",
            supports_offside=any(item.view.event_type is MatchViewerEventType.OFFSIDE for item in events),
            deterministic_seed=replay_payload.seed,
            duration_seconds=max(
                replay_payload.timeline.presentation_duration_seconds, int(frames[-1].time_seconds) if frames else 0
            ),
            home_team=home_team,
            away_team=away_team,
            events=[item.view for item in events],
            frames=frames,
        )

    def build_from_archive_record(self, record: ReplayArchiveRecord) -> MatchViewStateView:
        if record.visual_identity is None:
            raise ValueError("Viewer timeline fallback requires replay archive visual identity data.")

        home_formation = self._infer_formation(record.visual_identity.home_team.player_visuals)
        away_formation = self._infer_formation(record.visual_identity.away_team.player_visuals)
        home_team = self._team_view(
            record.visual_identity.home_team,
            side=MatchViewerSide.HOME,
            formation=home_formation,
        )
        away_team = self._team_view(
            record.visual_identity.away_team,
            side=MatchViewerSide.AWAY,
            formation=away_formation,
        )
        home_runtime = self._team_runtime(record.visual_identity.home_team, home_team)
        away_runtime = self._team_runtime(record.visual_identity.away_team, away_team)
        duration_seconds = float(max(180, (record.competition_context.presentation_duration_minutes or 3) * 60))
        events = self._archive_events(record, duration_seconds=duration_seconds)
        frames = self._build_frames(
            match_id=record.fixture_id,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            events=events,
            duration_seconds=duration_seconds,
        )
        return MatchViewStateView(
            match_id=record.fixture_id,
            source="replay_archive",
            supports_offside=any(item.view.event_type is MatchViewerEventType.OFFSIDE for item in events),
            deterministic_seed=None,
            duration_seconds=max(int(duration_seconds), int(frames[-1].time_seconds) if frames else 0),
            home_team=home_team,
            away_team=away_team,
            events=[item.view for item in events],
            frames=frames,
        )

    def build_from_live_stream(
        self,
        *,
        match_id: str,
        source: str,
        home_team_id: str | None,
        home_team_name: str | None,
        away_team_id: str | None,
        away_team_name: str | None,
        events: list[LiveMatchStreamEventView],
        live_state: LiveMatchStateView | None = None,
    ) -> MatchViewStateView:
        ordered_events = sorted(
            events,
            key=lambda item: (
                self._live_event_time_seconds(item),
                int(item.sequence_id or item.sequence or 0),
                item.event_id or "",
            ),
        )
        resolved_home_team_id = home_team_id or self._team_id_from_live_events(
            ordered_events, side=MatchViewerSide.HOME
        )
        resolved_away_team_id = away_team_id or self._team_id_from_live_events(
            ordered_events, side=MatchViewerSide.AWAY
        )
        resolved_home_team_id = resolved_home_team_id or f"{match_id}:home"
        resolved_away_team_id = resolved_away_team_id or f"{match_id}:away"
        resolved_home_team_name = home_team_name or self._team_name_from_live_events(
            ordered_events,
            team_id=resolved_home_team_id,
            side=MatchViewerSide.HOME,
        )
        resolved_away_team_name = away_team_name or self._team_name_from_live_events(
            ordered_events,
            team_id=resolved_away_team_id,
            side=MatchViewerSide.AWAY,
        )
        resolved_home_team_name = resolved_home_team_name or "Home"
        resolved_away_team_name = resolved_away_team_name or "Away"

        home_identity = self._synthetic_team_identity(
            match_id=match_id,
            team_id=resolved_home_team_id,
            team_name=resolved_home_team_name,
            side=MatchViewerSide.HOME,
            events=ordered_events,
        )
        away_identity = self._synthetic_team_identity(
            match_id=match_id,
            team_id=resolved_away_team_id,
            team_name=resolved_away_team_name,
            side=MatchViewerSide.AWAY,
            events=ordered_events,
        )
        home_team = self._team_view(home_identity, side=MatchViewerSide.HOME, formation="4-3-3")
        away_team = self._team_view(away_identity, side=MatchViewerSide.AWAY, formation="4-3-3")
        home_runtime = self._team_runtime(home_identity, home_team)
        away_runtime = self._team_runtime(away_identity, away_team)

        contexts = [
            self._context_from_live_event(
                event,
                home_team_id=resolved_home_team_id,
                home_team_name=resolved_home_team_name,
                away_team_id=resolved_away_team_id,
                away_team_name=resolved_away_team_name,
            )
            for event in ordered_events
        ]
        current_minute = (
            int(live_state.snapshot.current_minute)
            if live_state is not None
            else (max((item.minute for item in ordered_events), default=0))
        )
        duration_seconds = max(
            max((self._live_event_time_seconds(item) for item in ordered_events), default=0.0),
            float(current_minute * 60),
            90.0,
        )
        final_home_score, final_away_score = self._live_scoreline(ordered_events, live_state=live_state)
        contexts = self._ensure_control_events(
            match_id=match_id,
            events=contexts,
            duration_seconds=duration_seconds,
            final_home_score=final_home_score,
            final_away_score=final_away_score,
            include_halftime=current_minute >= 45,
            include_fulltime=self._live_stream_is_complete(ordered_events, live_state=live_state),
        )
        frames = self._build_frames(
            match_id=match_id,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            events=contexts,
            duration_seconds=duration_seconds,
        )
        return MatchViewStateView(
            match_id=match_id,
            source=source,
            supports_offside=any(item.view.event_type is MatchViewerEventType.OFFSIDE for item in contexts),
            deterministic_seed=None,
            duration_seconds=max(int(round(duration_seconds)), int(frames[-1].time_seconds) if frames else 0),
            home_team=home_team,
            away_team=away_team,
            events=[item.view for item in contexts],
            frames=frames,
        )

    def _archive_events(
        self,
        record: ReplayArchiveRecord,
        *,
        duration_seconds: float,
    ) -> list[_ViewerEventContext]:
        source_events = list(record.timeline)
        source_events.sort(key=lambda item: (item.minute, item.event_id))
        spread_times = self._spread_archive_times(source_events, duration_seconds=duration_seconds)
        contexts = [
            self._context_from_archive_event(item, sequence=index + 1, time_seconds=spread_times[index])
            for index, item in enumerate(source_events)
        ]
        return self._ensure_control_events(
            match_id=record.fixture_id,
            events=contexts,
            duration_seconds=duration_seconds,
            final_home_score=record.scoreline.home_goals,
            final_away_score=record.scoreline.away_goals,
        )

    def _team_view(
        self,
        team: MatchTeamVisualIdentityView,
        *,
        side: MatchViewerSide,
        formation: str,
    ) -> MatchViewerTeamView:
        return MatchViewerTeamView(
            team_id=team.team_id,
            team_name=team.team_name,
            short_name=team.short_club_code,
            side=side,
            formation=formation if formation in _SUPPORTED_FORMATIONS else self._normalize_formation(formation),
            primary_color=team.selected_kit.primary_color,
            secondary_color=team.selected_kit.secondary_color,
            accent_color=team.selected_kit.accent_color,
            goalkeeper_color=team.goalkeeper_kit.primary_color,
        )

    def _team_runtime(
        self,
        team: MatchTeamVisualIdentityView,
        team_view: MatchViewerTeamView,
        *,
        player_stats_by_id: dict[str, MatchPlayerStatsView] | None = None,
        team_stamina_pct: float | None = None,
    ) -> _TeamRuntime:
        starters = team.player_visuals[:11]
        bench = team.player_visuals[11:]
        players_by_id = {
            item.player_id: _PlayerRuntime(
                player_id=item.player_id,
                team_id=team_view.team_id,
                side=team_view.side,
                label=item.display_name[:3].upper() if item.shirt_number is None else str(item.shirt_number),
                shirt_number=item.shirt_number,
                role=item.role,
                minutes_played=(
                    player_stats_by_id[item.player_id].minutes_played
                    if player_stats_by_id is not None
                    and item.player_id in player_stats_by_id
                    and player_stats_by_id[item.player_id].team_id == team_view.team_id
                    else None
                ),
                substituted_in_minute=(
                    player_stats_by_id[item.player_id].substituted_in_minute
                    if player_stats_by_id is not None
                    and item.player_id in player_stats_by_id
                    and player_stats_by_id[item.player_id].team_id == team_view.team_id
                    else None
                ),
                substituted_out_minute=(
                    player_stats_by_id[item.player_id].substituted_out_minute
                    if player_stats_by_id is not None
                    and item.player_id in player_stats_by_id
                    and player_stats_by_id[item.player_id].team_id == team_view.team_id
                    else None
                ),
                rating=(
                    player_stats_by_id[item.player_id].rating
                    if player_stats_by_id is not None
                    and item.player_id in player_stats_by_id
                    and player_stats_by_id[item.player_id].team_id == team_view.team_id
                    else None
                ),
                base_stamina_pct=team_stamina_pct,
            )
            for item in team.player_visuals
        }
        return _TeamRuntime(
            view=team_view,
            players_by_id=players_by_id,
            lineup=[item.player_id for item in starters],
            bench=[item.player_id for item in bench],
            current_formation=team_view.formation,
            team_stamina_pct=team_stamina_pct,
        )

    def _context_from_match_event(
        self,
        event: MatchEventView,
        *,
        render_sync: MatchRenderSyncEventView | None = None,
    ) -> _ViewerEventContext:
        metadata = event.metadata or {}
        context_metadata = dict(metadata)
        if render_sync is not None:
            context_metadata.update(render_sync.meta)
        viewer_type = self._viewer_event_type_from_match_event(event)
        return _ViewerEventContext(
            view=MatchViewerEventView(
                event_id=event.event_id,
                sequence=event.sequence,
                event_type=viewer_type,
                minute=event.minute,
                added_time=event.added_time,
                clock_label=event.clock_label,
                time_seconds=float(event.presentation_second),
                team_id=event.team_id,
                team_name=event.team_name,
                primary_player_id=event.primary_player.player_id if event.primary_player is not None else None,
                primary_player_name=event.primary_player.player_name if event.primary_player is not None else None,
                secondary_player_id=event.secondary_player.player_id if event.secondary_player is not None else None,
                secondary_player_name=(
                    event.secondary_player.player_name if event.secondary_player is not None else None
                ),
                home_score=event.home_score,
                away_score=event.away_score,
                banner_text=self._banner_text(event.commentary, event.event_type.value),
                commentary=event.commentary,
                emphasis_level=self._emphasis_level(viewer_type),
                highlighted_player_ids=[
                    player_id
                    for player_id in (
                        event.primary_player.player_id if event.primary_player is not None else None,
                        event.secondary_player.player_id if event.secondary_player is not None else None,
                    )
                    if player_id is not None
                ],
                flags=[],
                playback_profile=self._optional_text(metadata.get("build_up_profile")) or "neutral",
                miss_variant=self._optional_text(metadata.get("miss_variant")),
                reviewable=bool(metadata.get("reviewable", False)),
                review_reason=self._optional_text(metadata.get("review_reason")),
                review_decision=self._optional_text(metadata.get("review_decision")),
                score_commit=self._optional_text(metadata.get("score_commit")) or "immediate",
            ),
            source_type=event.event_type.value,
            team_side=None,
            home_formation=self._optional_text(metadata.get("home_formation")),
            away_formation=self._optional_text(metadata.get("away_formation")),
            fallback_formation=self._optional_text(metadata.get("fallback_formation")),
            render_contract=self._render_contract(metadata.get("render")),
            metadata=context_metadata,
            motion=(
                render_sync.experience.motion
                if render_sync is not None and render_sync.experience is not None
                else None
            ),
            crowd=(
                render_sync.experience.crowd if render_sync is not None and render_sync.experience is not None else None
            ),
        )

    def _context_from_archive_event(
        self,
        event: ReplayMomentView,
        *,
        sequence: int,
        time_seconds: float,
    ) -> _ViewerEventContext:
        viewer_type = self._viewer_event_type_from_archive_event(event)
        commentary = event.description or self._archive_default_commentary(event)
        return _ViewerEventContext(
            view=MatchViewerEventView(
                event_id=event.event_id,
                sequence=sequence,
                event_type=viewer_type,
                minute=event.minute,
                added_time=0,
                clock_label=f"{event.minute}'",
                time_seconds=time_seconds,
                team_id=event.club_id,
                team_name=event.club_name,
                primary_player_id=event.player_id,
                primary_player_name=event.player_name,
                secondary_player_id=event.secondary_player_id,
                secondary_player_name=event.secondary_player_name,
                home_score=event.home_score,
                away_score=event.away_score,
                banner_text=self._banner_text(commentary, event.event_type),
                commentary=commentary,
                emphasis_level=self._emphasis_level(viewer_type),
                highlighted_player_ids=[
                    player_id for player_id in (event.player_id, event.secondary_player_id) if player_id is not None
                ],
                flags=[],
                playback_profile="neutral",
                miss_variant=None,
                reviewable=False,
                review_reason=None,
                review_decision=None,
                score_commit="immediate",
            ),
            source_type=event.event_type,
            team_side=None,
            render_contract=None,
            metadata=None,
        )

    def _context_from_live_event(
        self,
        event: LiveMatchStreamEventView,
        *,
        home_team_id: str,
        home_team_name: str,
        away_team_id: str,
        away_team_name: str,
    ) -> _ViewerEventContext:
        raw_event_type = (
            self._optional_text(event.source_event_type)
            or self._optional_text(event.metadata.get("raw_event_type"))
            or event.event_type
        )
        viewer_type = self._viewer_event_type_from_live_event(event, raw_event_type=raw_event_type)
        team_side = self._live_team_side(
            event,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        primary_player_name = event.player or self._optional_text(event.metadata.get("player_name"))
        secondary_player_name = event.secondary_player or self._optional_text(
            event.metadata.get("secondary_player_name")
        )
        primary_player_id = self._live_actor_id(
            player_id=event.player_id,
            player_name=primary_player_name,
            side=team_side,
        )
        secondary_player_id = self._live_actor_id(
            player_id=event.secondary_player_id,
            player_name=secondary_player_name,
            side=team_side,
        )
        commentary = (
            event.commentary
            or self._optional_text(event.metadata.get("description"))
            or self._banner_text(raw_event_type, raw_event_type)
        )
        team_id = event.team_id or (
            home_team_id
            if team_side is MatchViewerSide.HOME
            else away_team_id if team_side is MatchViewerSide.AWAY else None
        )
        team_name = event.team or self._optional_text(event.metadata.get("team_name"))
        if not team_name:
            if team_side is MatchViewerSide.HOME:
                team_name = home_team_name
            elif team_side is MatchViewerSide.AWAY:
                team_name = away_team_name
        context_metadata = dict(event.metadata)
        context_metadata.update(event.meta)
        return _ViewerEventContext(
            view=MatchViewerEventView(
                event_id=event.event_id
                or f"{event.match_id or 'live'}:{raw_event_type}:{int(self._live_event_time_seconds(event))}",
                sequence=int(event.sequence_id or event.sequence or 0),
                event_type=viewer_type,
                minute=event.minute,
                added_time=0,
                clock_label=event.clock_label or f"{event.minute}'",
                time_seconds=self._live_event_time_seconds(event),
                team_id=team_id,
                team_name=team_name,
                primary_player_id=primary_player_id,
                primary_player_name=primary_player_name,
                secondary_player_id=secondary_player_id,
                secondary_player_name=secondary_player_name,
                home_score=int(event.home_score or event.metadata.get("home_score") or 0),
                away_score=int(event.away_score or event.metadata.get("away_score") or 0),
                banner_text=self._banner_text(commentary, raw_event_type),
                commentary=commentary,
                emphasis_level=self._emphasis_level(viewer_type),
                highlighted_player_ids=[
                    player_id for player_id in (primary_player_id, secondary_player_id) if player_id is not None
                ],
                flags=[],
                playback_profile=self._optional_text(event.meta.get("chance_family"))
                or ("build_up" if viewer_type is MatchViewerEventType.ATTACK else "neutral"),
                miss_variant="wide" if viewer_type is MatchViewerEventType.MISS else None,
                reviewable=bool(event.meta.get("reviewable", False)),
                review_reason=self._optional_text(event.meta.get("review_reason")),
                review_decision=self._optional_text(event.meta.get("review_decision")),
                score_commit="immediate",
            ),
            source_type=raw_event_type,
            team_side=team_side,
            render_contract=self._live_render_contract(event),
            metadata=context_metadata,
            motion=event.experience.motion if event.experience is not None else None,
            crowd=event.experience.crowd if event.experience is not None else None,
        )

    def _ensure_control_events(
        self,
        *,
        match_id: str,
        events: list[_ViewerEventContext],
        duration_seconds: float,
        final_home_score: int,
        final_away_score: int,
        include_halftime: bool = True,
        include_fulltime: bool = True,
    ) -> list[_ViewerEventContext]:
        ordered = sorted(events, key=lambda item: (item.view.time_seconds, item.view.sequence, item.view.event_id))
        has_kickoff = any(item.view.event_type is MatchViewerEventType.KICKOFF for item in ordered)
        has_halftime = any(item.view.event_type is MatchViewerEventType.HALFTIME for item in ordered)
        has_fulltime = any(item.view.event_type is MatchViewerEventType.FULLTIME for item in ordered)

        synthetic: list[_ViewerEventContext] = []
        if not has_kickoff:
            synthetic.append(
                _ViewerEventContext(
                    view=MatchViewerEventView(
                        event_id=f"{match_id}:kickoff",
                        sequence=0,
                        event_type=MatchViewerEventType.KICKOFF,
                        minute=0,
                        added_time=0,
                        clock_label="0'",
                        time_seconds=0.0,
                        team_id=None,
                        team_name=None,
                        primary_player_id=None,
                        primary_player_name=None,
                        secondary_player_id=None,
                        secondary_player_name=None,
                        home_score=0,
                        away_score=0,
                        banner_text="Kickoff",
                        commentary="Kickoff",
                        emphasis_level=1,
                        highlighted_player_ids=[],
                        flags=[],
                    ),
                    source_type="kickoff",
                    team_side=None,
                )
            )
        if include_halftime and not has_halftime:
            halftime_score = self._score_before_minute(ordered, 45)
            synthetic.append(
                _ViewerEventContext(
                    view=MatchViewerEventView(
                        event_id=f"{match_id}:halftime",
                        sequence=9998,
                        event_type=MatchViewerEventType.HALFTIME,
                        minute=45,
                        added_time=0,
                        clock_label="45'",
                        time_seconds=max(duration_seconds / 2.0, 1.0),
                        team_id=None,
                        team_name=None,
                        primary_player_id=None,
                        primary_player_name=None,
                        secondary_player_id=None,
                        secondary_player_name=None,
                        home_score=halftime_score[0],
                        away_score=halftime_score[1],
                        banner_text="Halftime",
                        commentary="Halftime",
                        emphasis_level=1,
                        highlighted_player_ids=[],
                        flags=[],
                    ),
                    source_type="halftime",
                    team_side=None,
                )
            )
        if include_fulltime and not has_fulltime:
            synthetic.append(
                _ViewerEventContext(
                    view=MatchViewerEventView(
                        event_id=f"{match_id}:fulltime",
                        sequence=9999,
                        event_type=MatchViewerEventType.FULLTIME,
                        minute=90,
                        added_time=0,
                        clock_label="90'",
                        time_seconds=max(duration_seconds, 1.0),
                        team_id=None,
                        team_name=None,
                        primary_player_id=None,
                        primary_player_name=None,
                        secondary_player_id=None,
                        secondary_player_name=None,
                        home_score=final_home_score,
                        away_score=final_away_score,
                        banner_text="Fulltime",
                        commentary="Fulltime",
                        emphasis_level=1,
                        highlighted_player_ids=[],
                        flags=[],
                    ),
                    source_type="fulltime",
                    team_side=None,
                )
            )

        ordered.extend(synthetic)
        ordered.sort(key=lambda item: (item.view.time_seconds, item.view.sequence, item.view.event_id))
        for index, item in enumerate(ordered):
            item.view.sequence = index
        return ordered

    def _synthetic_team_identity(
        self,
        *,
        match_id: str,
        team_id: str,
        team_name: str,
        side: MatchViewerSide,
        events: list[LiveMatchStreamEventView],
    ) -> MatchTeamVisualIdentityView:
        player_visuals = self._synthetic_player_visuals(
            match_id=match_id,
            team_id=team_id,
            team_name=team_name,
            side=side,
            events=events,
        )
        colors = (
            {
                "primary": "#103A7A",
                "secondary": "#F7F9FC",
                "accent": "#E8B647",
                "goalkeeper": "#157F3B",
            }
            if side is MatchViewerSide.HOME
            else {
                "primary": "#8B1E3F",
                "secondary": "#FFF6EA",
                "accent": "#F0A202",
                "goalkeeper": "#16697A",
            }
        )
        return MatchTeamVisualIdentityView(
            team_id=team_id,
            team_name=team_name,
            short_club_code=self._short_club_code(team_name, fallback=side.value[:3].upper()),
            badge=MatchBadgeVisualView(
                shape="shield",
                initials=self._short_club_code(team_name, fallback=side.value[:3].upper()),
                primary_color=colors["primary"],
                secondary_color=colors["secondary"],
                accent_color=colors["accent"],
            ),
            selected_kit=MatchKitVisualView(
                kit_type="home" if side is MatchViewerSide.HOME else "away",
                primary_color=colors["primary"],
                secondary_color=colors["secondary"],
                accent_color=colors["accent"],
                shorts_color=colors["primary"],
                socks_color=colors["secondary"],
                pattern_type="solid",
                collar_style="crew",
                sleeve_style="short",
                badge_placement="left_chest",
                front_text=None,
            ),
            alternate_kit=MatchKitVisualView(
                kit_type="alternate",
                primary_color=colors["secondary"],
                secondary_color=colors["primary"],
                accent_color=colors["accent"],
                shorts_color=colors["secondary"],
                socks_color=colors["primary"],
                pattern_type="solid",
                collar_style="crew",
                sleeve_style="short",
                badge_placement="left_chest",
                front_text=None,
            ),
            goalkeeper_kit=MatchKitVisualView(
                kit_type="goalkeeper",
                primary_color=colors["goalkeeper"],
                secondary_color="#091F14",
                accent_color=colors["secondary"],
                shorts_color=colors["goalkeeper"],
                socks_color="#091F14",
                pattern_type="solid",
                collar_style="crew",
                sleeve_style="short",
                badge_placement="left_chest",
                front_text=None,
            ),
            player_visuals=player_visuals,
            clash_adjusted=False,
        )

    def _synthetic_player_visuals(
        self,
        *,
        match_id: str,
        team_id: str,
        team_name: str,
        side: MatchViewerSide,
        events: list[LiveMatchStreamEventView],
    ) -> list[MatchPlayerVisualView]:
        observed = self._observed_live_players(events=events, team_id=team_id, side=side)
        defenders = observed[6:10]
        midfielders = observed[3:6]
        forwards = observed[:3]
        bench = observed[10:]
        starter_roles = (
            (PlayerRole.GOALKEEPER, 1, None),
            (PlayerRole.DEFENDER, 2, defenders[0] if len(defenders) > 0 else None),
            (PlayerRole.DEFENDER, 4, defenders[1] if len(defenders) > 1 else None),
            (PlayerRole.DEFENDER, 5, defenders[2] if len(defenders) > 2 else None),
            (PlayerRole.DEFENDER, 3, defenders[3] if len(defenders) > 3 else None),
            (PlayerRole.MIDFIELDER, 6, midfielders[0] if len(midfielders) > 0 else None),
            (PlayerRole.MIDFIELDER, 8, midfielders[1] if len(midfielders) > 1 else None),
            (PlayerRole.MIDFIELDER, 10, midfielders[2] if len(midfielders) > 2 else None),
            (PlayerRole.FORWARD, 7, forwards[0] if len(forwards) > 0 else None),
            (PlayerRole.FORWARD, 9, forwards[1] if len(forwards) > 1 else None),
            (PlayerRole.FORWARD, 11, forwards[2] if len(forwards) > 2 else None),
        )
        players = [
            self._build_synthetic_player_visual(
                match_id=match_id,
                team_id=team_id,
                team_name=team_name,
                side=side,
                role=role,
                shirt_number=shirt_number,
                actor=actor,
            )
            for role, shirt_number, actor in starter_roles
        ]
        bench_roles = (PlayerRole.DEFENDER, PlayerRole.MIDFIELDER, PlayerRole.FORWARD)
        for index, actor in enumerate(bench[:7], start=1):
            role = bench_roles[(index - 1) % len(bench_roles)]
            players.append(
                self._build_synthetic_player_visual(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    side=side,
                    role=role,
                    shirt_number=20 + index,
                    actor=actor,
                )
            )
        return players

    def _build_synthetic_player_visual(
        self,
        *,
        match_id: str,
        team_id: str,
        team_name: str,
        side: MatchViewerSide,
        role: PlayerRole,
        shirt_number: int,
        actor: dict[str, Any] | None,
    ) -> MatchPlayerVisualView:
        if actor is not None:
            player_id = str(actor["player_id"])
            display_name = str(actor["player_name"])
        else:
            role_label = {
                PlayerRole.GOALKEEPER: "Goalkeeper",
                PlayerRole.DEFENDER: "Defender",
                PlayerRole.MIDFIELDER: "Midfielder",
                PlayerRole.FORWARD: "Forward",
            }[role]
            display_name = f"{team_name} {role_label} {shirt_number}"
            player_id = f"{match_id}:{side.value}:{role.value}:{shirt_number}"
        return MatchPlayerVisualView(
            player_id=player_id,
            display_name=display_name,
            shirt_name=self._shirt_name(display_name),
            shirt_number=shirt_number,
            role=role,
        )

    def _observed_live_players(
        self,
        *,
        events: list[LiveMatchStreamEventView],
        team_id: str,
        side: MatchViewerSide,
    ) -> list[dict[str, Any]]:
        observed: dict[str, dict[str, Any]] = {}
        for index, event in enumerate(events):
            event_side = self._live_team_side(
                event,
                home_team_id=team_id if side is MatchViewerSide.HOME else "",
                away_team_id=team_id if side is MatchViewerSide.AWAY else "",
            )
            if event_side is not None and event_side is not side:
                continue
            if event_side is None and event.team_id != team_id:
                continue
            weight = float(event.importance_score or 0.0) + (12.0 if event.event_type == "goal" else 4.0)
            primary_name = event.player or self._optional_text(event.metadata.get("player_name"))
            primary_id = self._live_actor_id(player_id=event.player_id, player_name=primary_name, side=side)
            self._remember_live_player(
                observed, player_id=primary_id, player_name=primary_name, weight=weight + (len(events) - index)
            )
            if event.event_type == "substitution":
                secondary_name = event.secondary_player or self._optional_text(
                    event.metadata.get("secondary_player_name")
                )
                secondary_id = self._live_actor_id(
                    player_id=event.secondary_player_id, player_name=secondary_name, side=side
                )
                self._remember_live_player(
                    observed,
                    player_id=secondary_id,
                    player_name=secondary_name,
                    weight=max(weight - 1.0, 1.0),
                )
        return sorted(observed.values(), key=lambda item: (-float(item["weight"]), str(item["player_name"])))

    def _remember_live_player(
        self,
        observed: dict[str, dict[str, Any]],
        *,
        player_id: str | None,
        player_name: str | None,
        weight: float,
    ) -> None:
        if player_id is None or player_name is None:
            return
        current = observed.get(player_id)
        if current is None:
            observed[player_id] = {
                "player_id": player_id,
                "player_name": player_name,
                "weight": weight,
            }
            return
        current["weight"] = max(float(current["weight"]), weight)

    def _short_club_code(self, team_name: str, *, fallback: str) -> str:
        tokens = [token for token in team_name.replace("-", " ").split() if token]
        initials = "".join(token[0] for token in tokens[:3]).upper()
        if len(initials) >= 2:
            return initials[:4]
        letters = "".join(character for character in team_name.upper() if character.isalpha())
        return (letters[:4] or fallback).upper()

    def _shirt_name(self, display_name: str) -> str:
        token = display_name.split()[-1] if display_name.split() else display_name
        return token[:16].upper()

    def _team_id_from_live_events(
        self,
        events: list[LiveMatchStreamEventView],
        *,
        side: MatchViewerSide,
    ) -> str | None:
        for event in events:
            event_side = self._parse_live_side(event.team_side)
            if event_side is side and event.team_id:
                return event.team_id
        return None

    def _team_name_from_live_events(
        self,
        events: list[LiveMatchStreamEventView],
        *,
        team_id: str,
        side: MatchViewerSide,
    ) -> str | None:
        for event in events:
            event_side = self._live_team_side(
                event,
                home_team_id=team_id if side is MatchViewerSide.HOME else "",
                away_team_id=team_id if side is MatchViewerSide.AWAY else "",
            )
            if event_side is not None and event_side is not side:
                continue
            if event.team_id == team_id and event.team:
                return event.team
            metadata_team_name = self._optional_text(event.metadata.get("team_name"))
            if event.team_id == team_id and metadata_team_name:
                return metadata_team_name
        return None

    def _live_scoreline(
        self,
        events: list[LiveMatchStreamEventView],
        *,
        live_state: LiveMatchStateView | None,
    ) -> tuple[int, int]:
        if live_state is not None:
            return int(live_state.snapshot.score.home), int(live_state.snapshot.score.away)
        if not events:
            return 0, 0
        last = events[-1]
        return (
            int(last.home_score or last.metadata.get("home_score") or 0),
            int(last.away_score or last.metadata.get("away_score") or 0),
        )

    def _live_stream_is_complete(
        self,
        events: list[LiveMatchStreamEventView],
        *,
        live_state: LiveMatchStateView | None,
    ) -> bool:
        if any(
            self._viewer_event_type_from_live_event(
                item, raw_event_type=self._optional_text(item.metadata.get("raw_event_type")) or item.event_type
            )
            is MatchViewerEventType.FULLTIME
            for item in events
        ):
            return True
        if live_state is None:
            return False
        return not live_state.is_live or str(live_state.snapshot.status).lower() in {
            "completed",
            "full_time",
            "finished",
        }

    def _live_event_time_seconds(self, event: LiveMatchStreamEventView) -> float:
        if event.presentation_second is not None:
            return float(event.presentation_second)
        meta_second = event.meta.get("presentation_second")
        if meta_second is not None:
            return float(meta_second)
        if event.tick is not None:
            return float(event.tick)
        return float(max(0, event.minute * 60))

    def _live_team_side(
        self,
        event: LiveMatchStreamEventView,
        *,
        home_team_id: str,
        away_team_id: str,
    ) -> MatchViewerSide | None:
        parsed = self._parse_live_side(event.team_side)
        if parsed is not None:
            return parsed
        if home_team_id and event.team_id == home_team_id:
            return MatchViewerSide.HOME
        if away_team_id and event.team_id == away_team_id:
            return MatchViewerSide.AWAY
        return None

    def _parse_live_side(self, value: str | None) -> MatchViewerSide | None:
        if value == "home":
            return MatchViewerSide.HOME
        if value == "away":
            return MatchViewerSide.AWAY
        return None

    def _live_actor_id(
        self,
        *,
        player_id: str | None,
        player_name: str | None,
        side: MatchViewerSide | None,
    ) -> str | None:
        if player_id:
            return player_id
        if not player_name:
            return None
        normalized = "".join(character.lower() if character.isalnum() else "-" for character in player_name).strip("-")
        if not normalized:
            normalized = md5(player_name.encode("utf-8")).hexdigest()[:10]
        prefix = "neutral" if side is None else side.value
        return f"{prefix}:{normalized}"

    def _live_render_contract(self, event: LiveMatchStreamEventView) -> dict[str, Any] | None:
        payload: dict[str, Any] = {}
        if event.position is not None:
            payload["origin"] = event.position.model_dump(mode="json")
        if event.target_position is not None:
            payload["target"] = event.target_position.model_dump(mode="json")
        camera_mode = self._optional_text(event.meta.get("camera_mode"))
        if camera_mode:
            payload["camera"] = {"mode": camera_mode}
        ball_contract = {
            key: event.meta.get(key)
            for key in ("ball_motion", "ball_height", "ball_speed")
            if event.meta.get(key) is not None
        }
        if ball_contract:
            payload["ball"] = {
                "motion": ball_contract.get("ball_motion"),
                "height": ball_contract.get("ball_height"),
                "speed": ball_contract.get("ball_speed"),
            }
        replay_eligible = event.meta.get("replay_eligible")
        replay_speed = event.meta.get("replay_speed")
        if replay_eligible is not None or replay_speed is not None:
            payload["replay"] = {}
            if replay_eligible is not None:
                payload["replay"]["eligible"] = bool(replay_eligible)
            if replay_speed is not None:
                payload["replay"]["speed"] = float(replay_speed)
        return payload or None

    def _build_frames(
        self,
        *,
        match_id: str,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        events: list[_ViewerEventContext],
        duration_seconds: float,
    ) -> list[MatchTimelineFrameView]:
        frames: list[MatchTimelineFrameView] = []
        if not events:
            return frames

        last_possession = MatchViewerSide.HOME
        last_time = 0.0

        def append_frame(
            *,
            time_seconds: float,
            clock_minute: float,
            home_score: int,
            away_score: int,
            active_event: _ViewerEventContext | None,
            phase: MatchViewerPhase,
            stage: str,
            possession_side: MatchViewerSide,
            camera_preset: MatchViewerCameraPreset,
            overlay_text: str | None = None,
            pause_playback: bool = False,
            playback_rate: float = 1.0,
            flag_animation: bool = False,
            celebration_team_id: str | None = None,
        ) -> None:
            nonlocal last_time
            resolved_time = max(
                0.0,
                time_seconds if not frames else max(time_seconds, last_time + 0.05),
            )
            frames.append(
                self._frame(
                    match_id=match_id,
                    home_runtime=home_runtime,
                    away_runtime=away_runtime,
                    time_seconds=resolved_time,
                    clock_minute=clock_minute,
                    home_score=home_score,
                    away_score=away_score,
                    active_event=active_event,
                    phase=phase,
                    stage=stage,
                    possession_side=possession_side,
                    camera_preset=camera_preset,
                    overlay_text=overlay_text,
                    pause_playback=pause_playback,
                    playback_rate=playback_rate,
                    flag_animation=flag_animation,
                    celebration_team_id=celebration_team_id,
                )
            )
            last_time = frames[-1].time_seconds

        for index, event in enumerate(events):
            event.team_side = self._team_side_from_team_id(home_runtime, away_runtime, event.view.team_id)
            if event.team_side is not None:
                last_possession = event.team_side
            prior_home_score = frames[-1].home_score if frames else 0
            prior_away_score = frames[-1].away_score if frames else 0
            phase = self._phase_for_event(event.view.event_type)
            possession_side = event.team_side or last_possession
            build_up = self._build_up_seconds(event.view)
            event_time = max(event.view.time_seconds, last_time + 0.1)
            pre_time = max(last_time + 0.4, event_time - build_up)
            goal_confirmed = (
                event.view.event_type is MatchViewerEventType.GOAL
                and event.view.review_decision != "disallowed"
                and (event.view.home_score != prior_home_score or event.view.away_score != prior_away_score)
            )

            def display_score(stage_name: str) -> tuple[int, int]:
                if event.view.event_type is not MatchViewerEventType.GOAL:
                    return event.view.home_score, event.view.away_score
                if goal_confirmed and stage_name in {"decision", "post", "reset"}:
                    return event.view.home_score, event.view.away_score
                return prior_home_score, prior_away_score

            pre_camera = (
                MatchViewerCameraPreset.ATTACK_PUSH
                if event.view.event_type
                in {
                    MatchViewerEventType.GOAL,
                    MatchViewerEventType.SAVE,
                    MatchViewerEventType.MISS,
                    MatchViewerEventType.OFFSIDE,
                }
                else MatchViewerCameraPreset.BROADCAST
            )
            pre_camera = self._camera_preset_from_render(event, stage="pre", fallback=pre_camera)
            event_camera = (
                MatchViewerCameraPreset.BOX_ZOOM
                if event.view.event_type
                in {
                    MatchViewerEventType.GOAL,
                    MatchViewerEventType.SAVE,
                    MatchViewerEventType.MISS,
                    MatchViewerEventType.OFFSIDE,
                    MatchViewerEventType.FOUL,
                    MatchViewerEventType.YELLOW_CARD,
                    MatchViewerEventType.RED_CARD,
                }
                else MatchViewerCameraPreset.BROADCAST
            )
            event_camera = self._camera_preset_from_render(event, stage="event", fallback=event_camera)

            if not frames:
                append_frame(
                    time_seconds=0.0,
                    clock_minute=0.0,
                    home_score=0,
                    away_score=0,
                    active_event=None,
                    phase=MatchViewerPhase.KICKOFF,
                    stage="reset",
                    possession_side=MatchViewerSide.HOME,
                    camera_preset=MatchViewerCameraPreset.BROADCAST,
                )

            if pre_time > last_time + 0.1:
                append_frame(
                    time_seconds=pre_time,
                    clock_minute=max(0.0, self._pre_clock(frames[-1].clock_minute, event.view.minute)),
                    home_score=prior_home_score,
                    away_score=prior_away_score,
                    active_event=event,
                    phase=phase,
                    stage="pre",
                    possession_side=possession_side,
                    camera_preset=pre_camera,
                )

            if event.view.event_type is MatchViewerEventType.SUBSTITUTION:
                self._apply_persistent_event(home_runtime, away_runtime, event)

            append_frame(
                time_seconds=event_time,
                clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                home_score=display_score("event")[0],
                away_score=display_score("event")[1],
                active_event=event,
                phase=phase,
                stage="event",
                possession_side=possession_side,
                camera_preset=event_camera,
                playback_rate=self._playback_rate_from_render(event, stage="event"),
            )

            if event.view.event_type is not MatchViewerEventType.SUBSTITUTION:
                self._apply_persistent_event(home_runtime, away_runtime, event)

            if event.view.event_type is MatchViewerEventType.GOAL:
                if event.view.reviewable:
                    append_frame(
                        time_seconds=last_time + 0.6,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                        home_score=prior_home_score,
                        away_score=prior_away_score,
                        active_event=event,
                        phase=phase,
                        stage="hold",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.BOX_ZOOM,
                        overlay_text="Checking...",
                        pause_playback=True,
                    )
                    append_frame(
                        time_seconds=last_time + 2.4,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                        home_score=prior_home_score,
                        away_score=prior_away_score,
                        active_event=event,
                        phase=phase,
                        stage="review",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.VAR_REPLAY,
                        overlay_text="Checking...",
                        playback_rate=0.35,
                    )
                    append_frame(
                        time_seconds=last_time + 1.0,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.05,
                        home_score=display_score("decision")[0],
                        away_score=display_score("decision")[1],
                        active_event=event,
                        phase=phase,
                        stage="decision",
                        possession_side=possession_side,
                        camera_preset=(
                            MatchViewerCameraPreset.GOAL_CELEBRATION
                            if goal_confirmed
                            else MatchViewerCameraPreset.BROADCAST
                        ),
                        overlay_text="Confirmed" if goal_confirmed else "Disallowed",
                        pause_playback=True,
                        celebration_team_id=event.view.team_id if goal_confirmed else None,
                    )
                    append_frame(
                        time_seconds=last_time + (1.8 if goal_confirmed else 0.8),
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.12,
                        home_score=display_score("post")[0],
                        away_score=display_score("post")[1],
                        active_event=event,
                        phase=phase,
                        stage="post",
                        possession_side=possession_side,
                        camera_preset=(
                            MatchViewerCameraPreset.GOAL_CELEBRATION
                            if goal_confirmed
                            else MatchViewerCameraPreset.BROADCAST
                        ),
                        celebration_team_id=event.view.team_id if goal_confirmed else None,
                    )
                    append_frame(
                        time_seconds=last_time + 0.8,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.2,
                        home_score=display_score("reset")[0],
                        away_score=display_score("reset")[1],
                        active_event=event,
                        phase=MatchViewerPhase.KICKOFF if goal_confirmed else MatchViewerPhase.OPEN_PLAY,
                        stage="reset",
                        possession_side=(
                            self._restart_side_after_goal(
                                event.view.home_score,
                                event.view.away_score,
                            )
                            if goal_confirmed
                            else self._opposite_side(possession_side)
                        ),
                        camera_preset=MatchViewerCameraPreset.BROADCAST,
                    )
                else:
                    append_frame(
                        time_seconds=last_time + 0.7,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.05,
                        home_score=display_score("decision")[0],
                        away_score=display_score("decision")[1],
                        active_event=event,
                        phase=phase,
                        stage="decision",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.GOAL_CELEBRATION,
                        celebration_team_id=event.view.team_id,
                    )
                    append_frame(
                        time_seconds=last_time + 1.8,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.12,
                        home_score=display_score("post")[0],
                        away_score=display_score("post")[1],
                        active_event=event,
                        phase=phase,
                        stage="post",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.GOAL_CELEBRATION,
                        celebration_team_id=event.view.team_id,
                    )
                    append_frame(
                        time_seconds=last_time + 0.8,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.2,
                        home_score=display_score("reset")[0],
                        away_score=display_score("reset")[1],
                        active_event=event,
                        phase=MatchViewerPhase.KICKOFF,
                        stage="reset",
                        possession_side=self._restart_side_after_goal(
                            event.view.home_score,
                            event.view.away_score,
                        ),
                        camera_preset=MatchViewerCameraPreset.BROADCAST,
                    )
            elif event.view.event_type is MatchViewerEventType.OFFSIDE:
                append_frame(
                    time_seconds=last_time + 0.6,
                    clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                    home_score=prior_home_score,
                    away_score=prior_away_score,
                    active_event=event,
                    phase=phase,
                    stage="hold",
                    possession_side=possession_side,
                    camera_preset=MatchViewerCameraPreset.ASSISTANT_FLAG,
                    pause_playback=True,
                    flag_animation=True,
                )
                append_frame(
                    time_seconds=last_time + 1.4,
                    clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.05,
                    home_score=prior_home_score,
                    away_score=prior_away_score,
                    active_event=event,
                    phase=phase,
                    stage="decision",
                    possession_side=possession_side,
                    camera_preset=MatchViewerCameraPreset.ASSISTANT_FLAG,
                    overlay_text="OFFSIDE",
                    pause_playback=True,
                    flag_animation=True,
                )
                append_frame(
                    time_seconds=last_time + 0.8,
                    clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.12,
                    home_score=prior_home_score,
                    away_score=prior_away_score,
                    active_event=event,
                    phase=MatchViewerPhase.OPEN_PLAY,
                    stage="reset",
                    possession_side=self._opposite_side(possession_side),
                    camera_preset=MatchViewerCameraPreset.BROADCAST,
                )
            elif event.view.event_type is MatchViewerEventType.FOUL:
                if event.view.reviewable:
                    append_frame(
                        time_seconds=last_time + 1.2,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=phase,
                        stage="hold",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.BOX_ZOOM,
                        overlay_text="Checking...",
                        pause_playback=True,
                    )
                    append_frame(
                        time_seconds=last_time + 2.4,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=phase,
                        stage="review",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.VAR_REPLAY,
                        overlay_text="Checking...",
                        playback_rate=0.35,
                    )
                    append_frame(
                        time_seconds=last_time + 1.0,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.04,
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.SET_PIECE,
                        stage="decision",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.BROADCAST,
                        overlay_text=("Confirmed" if event.view.review_decision == "confirmed" else "Disallowed"),
                        pause_playback=True,
                    )
                    append_frame(
                        time_seconds=last_time + 0.8,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.1,
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.OPEN_PLAY,
                        stage="reset",
                        possession_side=self._opposite_side(possession_side),
                        camera_preset=MatchViewerCameraPreset.BROADCAST,
                    )
                else:
                    append_frame(
                        time_seconds=last_time + 0.8,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.05,
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.SET_PIECE,
                        stage="post",
                        possession_side=possession_side,
                        camera_preset=MatchViewerCameraPreset.BOX_ZOOM,
                        overlay_text="FOUL",
                        pause_playback=True,
                    )
                    append_frame(
                        time_seconds=last_time + 0.8,
                        clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.1,
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.OPEN_PLAY,
                        stage="reset",
                        possession_side=self._opposite_side(possession_side),
                        camera_preset=MatchViewerCameraPreset.BROADCAST,
                    )
            elif event.view.event_type in {
                MatchViewerEventType.YELLOW_CARD,
                MatchViewerEventType.RED_CARD,
            }:
                append_frame(
                    time_seconds=last_time + 0.9,
                    clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.05,
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=phase,
                    stage="post",
                    possession_side=possession_side,
                    camera_preset=MatchViewerCameraPreset.BOX_ZOOM,
                    overlay_text=(
                        "RED CARD" if event.view.event_type is MatchViewerEventType.RED_CARD else "YELLOW CARD"
                    ),
                    pause_playback=True,
                )
                append_frame(
                    time_seconds=last_time + 0.8,
                    clock_minute=self._clock_value(event.view.minute, event.view.added_time) + 0.1,
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=MatchViewerPhase.OPEN_PLAY,
                    stage="reset",
                    possession_side=last_possession,
                    camera_preset=MatchViewerCameraPreset.BROADCAST,
                )
            elif event.view.event_type is MatchViewerEventType.HALFTIME:
                append_frame(
                    time_seconds=last_time + 1.0,
                    clock_minute=45.0,
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=MatchViewerPhase.HALFTIME,
                    stage="post",
                    possession_side=possession_side,
                    camera_preset=MatchViewerCameraPreset.BROADCAST,
                    overlay_text="HALFTIME",
                    pause_playback=True,
                )
                append_frame(
                    time_seconds=last_time + 1.4,
                    clock_minute=45.1,
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=MatchViewerPhase.KICKOFF,
                    stage="reset",
                    possession_side=MatchViewerSide.AWAY,
                    camera_preset=MatchViewerCameraPreset.BROADCAST,
                )
            elif event.view.event_type is not MatchViewerEventType.FULLTIME:
                append_frame(
                    time_seconds=last_time + self._settle_seconds(event.view.event_type),
                    clock_minute=min(
                        120.0,
                        self._clock_value(event.view.minute, event.view.added_time) + 0.12,
                    ),
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=phase,
                    stage="post",
                    possession_side=possession_side,
                    camera_preset=self._camera_preset_from_render(event, stage="post", fallback=event_camera),
                    playback_rate=self._playback_rate_from_render(event, stage="post"),
                )

            if event.view.event_type is MatchViewerEventType.FULLTIME:
                last_time = max(last_time, event_time)

            if index == len(events) - 1 and frames[-1].time_seconds < duration_seconds:
                append_frame(
                    time_seconds=duration_seconds,
                    clock_minute=max(90.0, frames[-1].clock_minute),
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=MatchViewerPhase.FULLTIME,
                    stage="post",
                    possession_side=last_possession,
                    camera_preset=MatchViewerCameraPreset.BROADCAST,
                )

        deduped: list[MatchTimelineFrameView] = []
        for frame in sorted(frames, key=lambda item: (item.time_seconds, item.clock_minute, item.frame_id)):
            if deduped and abs(deduped[-1].time_seconds - frame.time_seconds) < 0.01:
                deduped.append(frame.model_copy(update={"time_seconds": round(deduped[-1].time_seconds + 0.05, 2)}))
                continue
            deduped.append(frame)
        return self._enrich_frames(
            frames=deduped,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            events=events,
        )

    def _frame(
        self,
        *,
        match_id: str,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        time_seconds: float,
        clock_minute: float,
        home_score: int,
        away_score: int,
        active_event: _ViewerEventContext | None,
        phase: MatchViewerPhase,
        stage: str,
        possession_side: MatchViewerSide,
        camera_preset: MatchViewerCameraPreset,
        overlay_text: str | None = None,
        pause_playback: bool = False,
        playback_rate: float = 1.0,
        flag_animation: bool = False,
        celebration_team_id: str | None = None,
    ) -> MatchTimelineFrameView:
        home_attacks_right = clock_minute < 45.0
        player_payloads = self._player_payloads(
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            home_attacks_right=home_attacks_right,
            active_event=active_event,
            stage=stage,
            possession_side=possession_side,
        )
        ball_payload = self._ball_payload(
            player_payloads=player_payloads,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            home_attacks_right=home_attacks_right,
            active_event=active_event,
            stage=stage,
            possession_side=possession_side,
        )
        return MatchTimelineFrameView(
            frame_id=f"{match_id}:{int(round(time_seconds * 100))}:{stage}",
            time_seconds=round(max(0.0, time_seconds), 2),
            clock_minute=round(max(0.0, min(120.0, clock_minute)), 2),
            phase=phase,
            home_score=home_score,
            away_score=away_score,
            home_attacks_right=home_attacks_right,
            possession_side=possession_side,
            active_event_id=active_event.view.event_id if active_event is not None else None,
            event_banner=(
                active_event.view.banner_text
                if active_event is not None and stage in {"event", "decision", "post"}
                else None
            ),
            stage=self._playback_stage(stage),
            camera_preset=camera_preset,
            overlay_text=overlay_text,
            pause_playback=pause_playback,
            playback_rate=playback_rate,
            flag_animation=flag_animation,
            celebration_team_id=celebration_team_id,
            players=[MatchViewerPlayerFrameView.model_validate(item) for item in player_payloads],
            ball=MatchViewerBallFrameView.model_validate(ball_payload),
        )

    def _player_payloads(
        self,
        *,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        home_attacks_right: bool,
        active_event: _ViewerEventContext | None,
        stage: str,
        possession_side: MatchViewerSide,
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for runtime in (home_runtime, away_runtime):
            anchors = self._anchors_for_team(
                runtime=runtime,
                team_attacks_right=(
                    home_attacks_right if runtime.view.side is MatchViewerSide.HOME else not home_attacks_right
                ),
            )
            attack_direction = (
                1.0
                if (home_attacks_right if runtime.view.side is MatchViewerSide.HOME else not home_attacks_right)
                else -1.0
            )
            for player_id in runtime.lineup:
                player = runtime.players_by_id[player_id]
                anchor = anchors[player_id]
                line = self._line_for_player(runtime, player_id)
                position = dict(anchor)
                highlighted = active_event is not None and player_id in active_event.view.highlighted_player_ids
                state = MatchViewerPlayerState.IDLE

                push = self._push_amount(line=line, owns_ball=runtime.view.side is possession_side)
                if stage == "reset":
                    position = self._kickoff_position(position, attack_direction, player.role, highlighted)
                    state = MatchViewerPlayerState.MOVING
                else:
                    position["x"] = self._clamp(position["x"] + (push * attack_direction))
                    if runtime.view.side is not possession_side:
                        position["x"] = self._clamp(position["x"] - (2.8 * attack_direction))
                        state = MatchViewerPlayerState.DEFENDING
                    else:
                        state = MatchViewerPlayerState.ATTACKING if line == "attack" else MatchViewerPlayerState.MOVING

                if active_event is not None:
                    position, state = self._event_adjusted_position(
                        runtime=runtime,
                        opponent=away_runtime if runtime is home_runtime else home_runtime,
                        player=player,
                        line=line,
                        position=position,
                        anchor=anchor,
                        active_event=active_event,
                        home_attacks_right=home_attacks_right,
                        stage=stage,
                    )

                payloads.append(
                    {
                        "player_id": player.player_id,
                        "team_id": player.team_id,
                        "side": player.side,
                        "shirt_number": player.shirt_number,
                        "label": player.label,
                        "role": player.role,
                        "line": line,
                        "state": state,
                        "active": True,
                        "highlighted": highlighted,
                        "position": position,
                        "anchor_position": anchor,
                    }
                )

        self._resolve_collisions(payloads)
        return payloads

    def _apply_persistent_event(
        self,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        event: _ViewerEventContext,
    ) -> None:
        if event.home_formation:
            home_runtime.current_formation = self._normalize_formation(event.home_formation)
        if event.away_formation:
            away_runtime.current_formation = self._normalize_formation(event.away_formation)

        runtime = self._runtime_from_side(home_runtime, away_runtime, event.team_side)
        if runtime is None:
            return

        if event.view.event_type is MatchViewerEventType.SUBSTITUTION:
            outgoing = event.view.secondary_player_id
            incoming = event.view.primary_player_id
            if outgoing in runtime.lineup and incoming in runtime.players_by_id:
                runtime.lineup[runtime.lineup.index(outgoing)] = incoming
                if incoming in runtime.bench:
                    runtime.bench.remove(incoming)
                runtime.bench.append(outgoing)
        if event.view.event_type is MatchViewerEventType.RED_CARD and event.view.primary_player_id in runtime.lineup:
            runtime.lineup.remove(event.view.primary_player_id)
            if event.fallback_formation:
                runtime.current_formation = self._normalize_formation(event.fallback_formation)

    def _anchors_for_team(
        self,
        *,
        runtime: _TeamRuntime,
        team_attacks_right: bool,
    ) -> dict[str, dict[str, float]]:
        lineup = list(runtime.lineup)
        if not lineup:
            return {}
        goalkeeper_id = lineup[0]
        outfield_ids = lineup[1:]
        line_sizes = self._line_sizes(runtime.current_formation, outfield_ids, runtime)
        line_x_values = self._line_x_values(line_sizes, team_attacks_right=team_attacks_right)
        anchors: dict[str, dict[str, float]] = {goalkeeper_id: {"x": 8.0 if team_attacks_right else 92.0, "y": 50.0}}
        cursor = 0
        for group_index, group_size in enumerate(line_sizes):
            y_values = self._line_y_values(group_size)
            line_x = line_x_values[group_index]
            for local_index in range(group_size):
                player_id = outfield_ids[cursor + local_index]
                anchors[player_id] = {"x": line_x, "y": y_values[local_index]}
            cursor += group_size
        return anchors

    def _line_for_player(self, runtime: _TeamRuntime, player_id: str) -> str:
        if not runtime.lineup:
            return "midfield"
        if runtime.lineup[0] == player_id:
            return "goalkeeper"
        outfield_ids = runtime.lineup[1:]
        line_sizes = self._line_sizes(runtime.current_formation, outfield_ids, runtime)
        cursor = 0
        for group_index, group_size in enumerate(line_sizes):
            group_ids = outfield_ids[cursor : cursor + group_size]
            if player_id in group_ids:
                if group_index == 0:
                    return "defense"
                if group_index == len(line_sizes) - 1:
                    return "attack"
                return "midfield"
            cursor += group_size
        return "midfield"

    def _line_sizes(self, formation: str, outfield_ids: list[str], runtime: _TeamRuntime) -> list[int]:
        normalized = self._normalize_formation(formation)
        try:
            line_sizes = [int(part) for part in normalized.split("-")]
        except ValueError:
            line_sizes = []
        if line_sizes and sum(line_sizes) == len(outfield_ids):
            return line_sizes
        defenders = sum(1 for item in outfield_ids if runtime.players_by_id[item].role is PlayerRole.DEFENDER)
        midfielders = sum(1 for item in outfield_ids if runtime.players_by_id[item].role is PlayerRole.MIDFIELDER)
        forwards = sum(1 for item in outfield_ids if runtime.players_by_id[item].role is PlayerRole.FORWARD)
        if defenders + midfielders + forwards == len(outfield_ids) and defenders and midfielders and forwards:
            return [defenders, midfielders, forwards]
        if len(outfield_ids) == 10:
            return [4, 3, 3]
        if len(outfield_ids) == 9:
            return [4, 4, 1]
        if len(outfield_ids) == 8:
            return [4, 3, 1]
        bucket = max(1, len(outfield_ids) // 3)
        return [bucket, bucket, max(1, len(outfield_ids) - (2 * bucket))]

    def _line_x_values(self, line_sizes: list[int], *, team_attacks_right: bool) -> list[float]:
        if len(line_sizes) == 4:
            base = [22.0, 41.0, 59.0, 78.0]
        elif len(line_sizes) == 3:
            base = [24.0, 50.0, 76.0]
        else:
            gap = 58.0 / max(1, len(line_sizes))
            base = [20.0 + (gap * index) for index in range(len(line_sizes))]
        return base if team_attacks_right else [100.0 - item for item in base]

    def _line_y_values(self, count: int) -> list[float]:
        return list(
            _LINE_Y_MAP.get(count, tuple(10.0 + ((index + 1) * (80.0 / (count + 1))) for index in range(count)))
        )

    def _resolve_collisions(self, payloads: list[dict[str, Any]]) -> None:
        for index, item in enumerate(payloads):
            for other_index in range(index + 1, len(payloads)):
                other = payloads[other_index]
                if item["team_id"] != other["team_id"]:
                    continue
                delta_x = other["position"]["x"] - item["position"]["x"]
                delta_y = other["position"]["y"] - item["position"]["y"]
                distance_squared = (delta_x * delta_x) + (delta_y * delta_y)
                if distance_squared >= 12.0:
                    continue
                angle_seed = self._fraction(f"{item['player_id']}:{other['player_id']}")
                offset_x = (2.2 * angle_seed) - 1.1
                offset_y = (2.2 * (1.0 - angle_seed)) - 1.1
                item["position"]["x"] = self._clamp(item["position"]["x"] - offset_x)
                item["position"]["y"] = self._clamp(item["position"]["y"] - offset_y)
                other["position"]["x"] = self._clamp(other["position"]["x"] + offset_x)
                other["position"]["y"] = self._clamp(other["position"]["y"] + offset_y)

    def _event_adjusted_position(
        self,
        *,
        runtime: _TeamRuntime,
        opponent: _TeamRuntime,
        player: _PlayerRuntime,
        line: str,
        position: dict[str, float],
        anchor: dict[str, float],
        active_event: _ViewerEventContext,
        home_attacks_right: bool,
        stage: str,
    ) -> tuple[dict[str, float], MatchViewerPlayerState]:
        viewer_type = active_event.view.event_type
        primary_side = self._team_side_from_player(
            home_runtime=runtime, away_runtime=opponent, player_id=active_event.view.primary_player_id
        )
        secondary_side = self._team_side_from_player(
            home_runtime=runtime, away_runtime=opponent, player_id=active_event.view.secondary_player_id
        )
        attacking_side = active_event.team_side or secondary_side or primary_side
        defending_side = None if attacking_side is None else self._opposite_side(attacking_side)
        player_side = runtime.view.side
        fallback_target = self._target_zone(
            side=attacking_side or MatchViewerSide.HOME,
            home_attacks_right=home_attacks_right,
            event_id=active_event.view.event_id,
            viewer_type=viewer_type,
        )
        event_target = self._render_point(active_event, "target") or fallback_target
        event_origin = self._render_point(active_event, "origin") or dict(anchor)
        goalkeeper_target = self._goalkeeper_zone(
            side=defending_side or self._opposite_side(player_side),
            home_attacks_right=home_attacks_right,
            event_id=active_event.view.event_id,
        )

        state = MatchViewerPlayerState.MOVING
        if player.player_id == active_event.view.primary_player_id:
            if viewer_type is MatchViewerEventType.RED_CARD:
                state = MatchViewerPlayerState.SENT_OFF
                position["x"] = self._clamp(anchor["x"] + (3.0 if player_side is MatchViewerSide.HOME else -3.0))
                return position, state
            if player_side is attacking_side:
                state = MatchViewerPlayerState.ATTACKING
                if stage == "pre":
                    position["x"] = self._lerp(position["x"], event_origin["x"], 0.42)
                    position["y"] = self._lerp(position["y"], event_origin["y"], 0.42)
                else:
                    position["x"] = self._lerp(position["x"], event_target["x"], 0.82 if stage == "event" else 0.58)
                    position["y"] = self._lerp(position["y"], event_target["y"], 0.82 if stage == "event" else 0.58)
            elif viewer_type is MatchViewerEventType.SAVE:
                state = MatchViewerPlayerState.DEFENDING
                position["x"] = self._lerp(position["x"], goalkeeper_target["x"], 0.78 if stage == "event" else 0.55)
                position["y"] = self._lerp(position["y"], goalkeeper_target["y"], 0.78 if stage == "event" else 0.55)
            return position, state

        if player.player_id == active_event.view.secondary_player_id:
            if viewer_type is MatchViewerEventType.SAVE and secondary_side is attacking_side:
                state = MatchViewerPlayerState.ATTACKING
                position["x"] = self._lerp(
                    position["x"],
                    event_origin["x"] if stage == "pre" else event_target["x"],
                    0.66 if stage != "pre" else 0.38,
                )
                position["y"] = self._lerp(
                    position["y"],
                    event_origin["y"] if stage == "pre" else event_target["y"],
                    0.66 if stage != "pre" else 0.38,
                )
                return position, state
            if viewer_type is MatchViewerEventType.GOAL and secondary_side is attacking_side:
                state = MatchViewerPlayerState.ATTACKING
                position["x"] = self._lerp(
                    position["x"], event_target["x"] - (5.0 if attacking_side is MatchViewerSide.HOME else -5.0), 0.52
                )
                position["y"] = self._lerp(position["y"], event_target["y"] + 6.0, 0.52)
                return position, state

        if viewer_type in {
            MatchViewerEventType.GOAL,
            MatchViewerEventType.MISS,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.ATTACK,
            MatchViewerEventType.PENALTY,
            MatchViewerEventType.SET_PIECE,
            MatchViewerEventType.OFFSIDE,
            MatchViewerEventType.FOUL,
        }:
            if player.role is PlayerRole.GOALKEEPER and player_side is defending_side:
                state = MatchViewerPlayerState.DEFENDING
                position["x"] = self._lerp(position["x"], goalkeeper_target["x"], 0.35 if stage == "pre" else 0.68)
                position["y"] = self._lerp(position["y"], goalkeeper_target["y"], 0.35 if stage == "pre" else 0.68)
                return position, state
            if player_side is attacking_side and line == "attack":
                state = MatchViewerPlayerState.ATTACKING
                position["x"] = self._lerp(
                    position["x"], event_target["x"] - (2.5 if attacking_side is MatchViewerSide.HOME else -2.5), 0.38
                )
                position["y"] = self._lerp(position["y"], event_target["y"], 0.25)
                return position, state
            if player_side is defending_side and line in {"defense", "midfield"}:
                state = MatchViewerPlayerState.PRESSING
                position["x"] = self._lerp(position["x"], event_target["x"], 0.18)
                position["y"] = self._lerp(position["y"], event_target["y"], 0.16)
                return position, state

        return position, state

    def _ball_payload(
        self,
        *,
        player_payloads: list[dict[str, Any]],
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        home_attacks_right: bool,
        active_event: _ViewerEventContext | None,
        stage: str,
        possession_side: MatchViewerSide,
    ) -> dict[str, Any]:
        positions = {item["player_id"]: item["position"] for item in player_payloads}
        default_owner = self._default_owner(home_runtime if possession_side is MatchViewerSide.HOME else away_runtime)
        trajectory_point = self._render_ball_trajectory_point(active_event, stage=stage)
        ball_height = self._render_ball_height(active_event, stage=stage)
        ball_spin = self._render_ball_vector(active_event, key="spin")
        ball_velocity = self._render_ball_vector(active_event, key="velocity")

        def ball_frame(*, position: dict[str, float], owner_player_id: str | None, state: str) -> dict[str, Any]:
            resolved_position = trajectory_point or position
            return {
                "position": resolved_position,
                "height": ball_height,
                "owner_player_id": owner_player_id,
                "state": state,
                "spin": ball_spin,
                "velocity": ball_velocity,
            }

        if stage == "reset":
            return ball_frame(position={"x": 50.0, "y": 50.0}, owner_player_id=default_owner, state="placed")
        if active_event is None:
            owner = default_owner
            return ball_frame(
                position=self._ball_near_player(positions.get(owner) or {"x": 50.0, "y": 50.0}),
                owner_player_id=owner,
                state="rolling",
            )

        viewer_type = active_event.view.event_type
        primary = active_event.view.primary_player_id
        secondary = active_event.view.secondary_player_id
        primary_side = self._player_side_lookup(home_runtime, away_runtime, primary)
        secondary_side = self._player_side_lookup(home_runtime, away_runtime, secondary)
        attacking_side = active_event.team_side or secondary_side or primary_side or possession_side
        defending_side = self._opposite_side(attacking_side)
        fallback_target = self._target_zone(
            side=attacking_side,
            home_attacks_right=home_attacks_right,
            event_id=active_event.view.event_id,
            viewer_type=viewer_type,
        )
        wide_target = self._wide_target_zone(
            side=attacking_side,
            home_attacks_right=home_attacks_right,
            event_id=active_event.view.event_id,
        )
        goalkeeper_target = self._goalkeeper_zone(
            side=defending_side,
            home_attacks_right=home_attacks_right,
            event_id=active_event.view.event_id,
        )
        primary_pos = positions.get(primary) if primary is not None else None
        secondary_pos = positions.get(secondary) if secondary is not None else None
        event_target = self._render_point(active_event, "target") or fallback_target
        event_origin = self._render_point(active_event, "origin") or primary_pos or event_target

        if viewer_type is MatchViewerEventType.GOAL:
            if stage == "pre":
                return ball_frame(
                    position=self._ball_near_player(primary_pos or event_origin),
                    owner_player_id=primary,
                    state=self._ball_state_from_render(active_event, fallback="controlled"),
                )
            if stage == "event":
                return ball_frame(
                    position=event_target,
                    owner_player_id=None,
                    state=self._ball_state_from_render(active_event, fallback="shot"),
                )
            return ball_frame(
                position={"x": event_target["x"], "y": event_target["y"]}, owner_player_id=None, state="in_goal"
            )
        if viewer_type is MatchViewerEventType.SAVE:
            if stage == "pre":
                return ball_frame(
                    position=self._ball_near_player(secondary_pos or primary_pos or event_origin),
                    owner_player_id=secondary or primary,
                    state=self._ball_state_from_render(active_event, fallback="controlled"),
                )
            if stage == "event":
                return ball_frame(
                    position=event_target,
                    owner_player_id=None,
                    state=self._ball_state_from_render(active_event, fallback="saved"),
                )
            return ball_frame(
                position=self._ball_near_player(goalkeeper_target),
                owner_player_id=primary if primary_side is defending_side else secondary,
                state="held",
            )
        if viewer_type is MatchViewerEventType.MISS:
            if stage == "pre":
                return ball_frame(
                    position=self._ball_near_player(primary_pos or event_origin),
                    owner_player_id=primary,
                    state=self._ball_state_from_render(active_event, fallback="controlled"),
                )
            resolved_miss_target = event_target if stage == "event" else wide_target
            return ball_frame(
                position=resolved_miss_target if stage == "event" else self._ball_near_player(resolved_miss_target),
                owner_player_id=None,
                state=self._ball_state_from_render(active_event, fallback="missed"),
            )
        if viewer_type is MatchViewerEventType.FOUL:
            return ball_frame(
                position=self._ball_near_player(primary_pos or event_origin),
                owner_player_id=primary or default_owner,
                state="stopped",
            )
        if viewer_type is MatchViewerEventType.OFFSIDE:
            return ball_frame(
                position=event_target if stage != "pre" else self._ball_near_player(primary_pos or event_origin),
                owner_player_id=primary,
                state="stopped",
            )
        if viewer_type in {MatchViewerEventType.RED_CARD, MatchViewerEventType.HALFTIME, MatchViewerEventType.FULLTIME}:
            return ball_frame(
                position=self._ball_near_player(primary_pos or positions.get(default_owner) or {"x": 50.0, "y": 50.0}),
                owner_player_id=primary or default_owner,
                state="stopped",
            )
        if viewer_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE, MatchViewerEventType.ATTACK}:
            if stage == "pre":
                return ball_frame(
                    position=self._ball_near_player(primary_pos or event_origin),
                    owner_player_id=primary or default_owner,
                    state=self._ball_state_from_render(active_event, fallback="controlled"),
                )
            if stage == "event":
                return ball_frame(
                    position=event_target,
                    owner_player_id=None,
                    state=self._ball_state_from_render(active_event, fallback="traveling"),
                )
        owner = primary or default_owner
        return ball_frame(
            position=self._ball_near_player(positions.get(owner) or event_target),
            owner_player_id=owner,
            state=self._ball_state_from_render(active_event, fallback="rolling"),
        )

    def _enrich_frames(
        self,
        *,
        frames: list[MatchTimelineFrameView],
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        events: list[_ViewerEventContext],
    ) -> list[MatchTimelineFrameView]:
        if not frames:
            return []

        event_lookup = {item.view.event_id: item for item in events}
        player_lookup = {
            **home_runtime.players_by_id,
            **away_runtime.players_by_id,
        }
        previous_positions: dict[str, Any] = {}
        previous_time: float | None = None
        enriched: list[MatchTimelineFrameView] = []

        for frame in frames:
            event = event_lookup.get(frame.active_event_id or "")
            ball_owner = (
                frame.ball.owner_player_id
                if frame.ball.owner_player_id is not None and self._ball_is_controlled(frame.ball.state)
                else None
            )
            ball_point = {
                "x": float(frame.ball.position.x),
                "y": float(frame.ball.position.y),
            }
            danger_zone = self._danger_zone_label(
                ball_point=ball_point,
                possession_side=frame.possession_side,
                home_attacks_right=frame.home_attacks_right,
                phase=frame.phase,
            )
            transition_state = self._transition_state_for_frame(
                frame=frame,
                event=event,
                possession_side=frame.possession_side,
                home_attacks_right=frame.home_attacks_right,
            )
            pressure_index = self._pressure_index_for_frame(
                frame=frame,
                event=event,
                ball_point=ball_point,
            )
            compactness_home = self._compactness_for_team(frame.players, side=MatchViewerSide.HOME)
            compactness_away = self._compactness_for_team(frame.players, side=MatchViewerSide.AWAY)
            possession_phase = self._possession_phase_for_frame(
                frame=frame,
                event=event,
                danger_zone=danger_zone,
                transition_state=transition_state,
            )

            delta_t = 0.0 if previous_time is None else max(0.0, frame.time_seconds - previous_time)
            updated_players: list[MatchViewerPlayerFrameView] = []
            current_positions: dict[str, Any] = {}
            for player in frame.players:
                current_positions[player.player_id] = player.position
                runtime = player_lookup.get(player.player_id)
                velocity = self._player_velocity(
                    current=player.position,
                    previous=previous_positions.get(player.player_id),
                    delta_t=delta_t,
                )
                has_possession = ball_owner == player.player_id
                speed_ratio = self._player_speed_ratio(
                    player=player,
                    event=event,
                    velocity=velocity,
                )
                facing = self._player_facing(
                    player=player,
                    frame=frame,
                    event=event,
                    velocity=velocity,
                    ball_point=ball_point,
                    has_possession=has_possession,
                )
                stamina_pct = self._player_stamina_pct(
                    player=player,
                    runtime=runtime,
                    clock_minute=frame.clock_minute,
                    event=event,
                    speed_ratio=speed_ratio,
                )
                blend_factor = self._player_blend_factor(
                    player=player,
                    event=event,
                    speed_ratio=speed_ratio,
                )
                animation_state = self._player_animation_state(
                    player=player,
                    frame=frame,
                    event=event,
                    has_possession=has_possession,
                    speed_ratio=speed_ratio,
                )
                updated_players.append(
                    player.model_copy(
                        update={
                            "animation_state": animation_state,
                            "speed_ratio": speed_ratio,
                            "blend_factor": blend_factor,
                            "stamina_pct": stamina_pct,
                            "has_possession": has_possession,
                            "facing": facing,
                            "velocity": velocity,
                        }
                    )
                )

            enriched.append(
                frame.model_copy(
                    update={
                        "possession_phase": possession_phase,
                        "transition_state": transition_state,
                        "danger_zone": danger_zone,
                        "pressure_index": pressure_index,
                        "compactness_home": compactness_home,
                        "compactness_away": compactness_away,
                        "frame_tags": self._frame_tags(
                            frame=frame,
                            event=event,
                            danger_zone=danger_zone,
                            possession_phase=possession_phase,
                            transition_state=transition_state,
                            pressure_index=pressure_index,
                        ),
                        "players": updated_players,
                    }
                )
            )
            previous_positions = current_positions
            previous_time = frame.time_seconds

        return enriched

    def _ball_is_controlled(self, state: str) -> bool:
        return state not in {"shot", "traveling", "saved", "missed", "in_goal"}

    def _danger_zone_label(
        self,
        *,
        ball_point: dict[str, float],
        possession_side: MatchViewerSide,
        home_attacks_right: bool,
        phase: MatchViewerPhase,
    ) -> str:
        if phase is MatchViewerPhase.SET_PIECE:
            return "set_piece_lane"
        progress = self._goal_progress(
            point=ball_point,
            side=possession_side,
            home_attacks_right=home_attacks_right,
        )
        if progress >= 88.0 and 38.0 <= ball_point["y"] <= 62.0:
            return "central_box"
        if progress >= 82.0:
            return "wide_box"
        if progress >= 68.0:
            return "final_third"
        if progress >= 45.0:
            return "middle_third"
        return "build_up"

    def _transition_state_for_frame(
        self,
        *,
        frame: MatchTimelineFrameView,
        event: _ViewerEventContext | None,
        possession_side: MatchViewerSide,
        home_attacks_right: bool,
    ) -> MatchViewerTransitionState:
        if frame.stage is MatchViewerPlaybackStage.RESET:
            return (
                MatchViewerTransitionState.HOME_RESET
                if possession_side is MatchViewerSide.HOME
                else MatchViewerTransitionState.AWAY_RESET
            )
        if event is None:
            return MatchViewerTransitionState.STABLE
        if frame.pause_playback and event.view.event_type in {
            MatchViewerEventType.FOUL,
            MatchViewerEventType.OFFSIDE,
            MatchViewerEventType.YELLOW_CARD,
            MatchViewerEventType.RED_CARD,
            MatchViewerEventType.HALFTIME,
            MatchViewerEventType.FULLTIME,
            MatchViewerEventType.INJURY,
            MatchViewerEventType.SUBSTITUTION,
        }:
            return MatchViewerTransitionState.STOPPED

        origin = self._render_point(event, "origin") or {"x": 50.0, "y": 50.0}
        target = self._render_point(event, "target") or {
            "x": float(frame.ball.position.x),
            "y": float(frame.ball.position.y),
        }
        progress_delta = self._goal_progress(
            point=target,
            side=possession_side,
            home_attacks_right=home_attacks_right,
        ) - self._goal_progress(
            point=origin,
            side=possession_side,
            home_attacks_right=home_attacks_right,
        )
        build_up_pattern = self._optional_text((event.metadata or {}).get("build_up_pattern"))
        if event.view.event_type in {
            MatchViewerEventType.ATTACK,
            MatchViewerEventType.GOAL,
            MatchViewerEventType.MISS,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.PENALTY,
            MatchViewerEventType.SET_PIECE,
        } and (progress_delta >= 14.0 or build_up_pattern == "counterattack"):
            return (
                MatchViewerTransitionState.HOME_BREAK
                if possession_side is MatchViewerSide.HOME
                else MatchViewerTransitionState.AWAY_BREAK
            )
        return MatchViewerTransitionState.STABLE

    def _pressure_index_for_frame(
        self,
        *,
        frame: MatchTimelineFrameView,
        event: _ViewerEventContext | None,
        ball_point: dict[str, float],
    ) -> float:
        defending_distances = sorted(
            self._distance(
                {"x": float(player.position.x), "y": float(player.position.y)},
                ball_point,
            )
            for player in frame.players
            if player.side is not frame.possession_side
        )
        nearest_slice = defending_distances[:3]
        proximity_pressure = 0.0
        if nearest_slice:
            proximity_pressure = self._clamp_unit(1.0 - ((sum(nearest_slice) / len(nearest_slice)) / 24.0))

        motion_pressure = event.motion.pressure if event is not None and event.motion is not None else 0.0
        emphasis_pressure = ((event.view.emphasis_level - 1) / 2.0) if event is not None else 0.0
        territory_pressure = (
            self._goal_progress(
                point=ball_point,
                side=frame.possession_side,
                home_attacks_right=frame.home_attacks_right,
            )
            / 100.0
        )
        crowd_pressure = 0.0
        if event is not None and event.crowd is not None:
            crowd_pressure = max(event.crowd.home_intensity, event.crowd.away_intensity)
        stage_bonus = (
            0.1
            if frame.stage
            in {
                MatchViewerPlaybackStage.EVENT,
                MatchViewerPlaybackStage.REVIEW,
                MatchViewerPlaybackStage.DECISION,
            }
            else 0.0
        )

        return round(
            self._clamp_unit(
                (motion_pressure * 0.38)
                + (proximity_pressure * 0.22)
                + (territory_pressure * 0.18)
                + (emphasis_pressure * 0.12)
                + (crowd_pressure * 0.10)
                + stage_bonus
            ),
            3,
        )

    def _compactness_for_team(
        self,
        players: list[MatchViewerPlayerFrameView],
        *,
        side: MatchViewerSide,
    ) -> float:
        team_players = [
            player for player in players if player.side is side and player.active and player.line != "goalkeeper"
        ]
        if len(team_players) < 3:
            return 0.5
        x_values = [float(player.position.x) for player in team_players]
        y_values = [float(player.position.y) for player in team_players]
        x_span = max(x_values) - min(x_values)
        y_span = max(y_values) - min(y_values)
        spread = ((x_span / 64.0) + (y_span / 78.0)) / 2.0
        return round(self._clamp_unit(1.0 - spread), 3)

    def _possession_phase_for_frame(
        self,
        *,
        frame: MatchTimelineFrameView,
        event: _ViewerEventContext | None,
        danger_zone: str,
        transition_state: MatchViewerTransitionState,
    ) -> MatchViewerPossessionPhase:
        if frame.phase is MatchViewerPhase.KICKOFF or frame.stage is MatchViewerPlaybackStage.RESET:
            return MatchViewerPossessionPhase.RESTART
        if frame.phase is MatchViewerPhase.SET_PIECE:
            return MatchViewerPossessionPhase.SET_PIECE
        if frame.phase in {MatchViewerPhase.HALFTIME, MatchViewerPhase.FULLTIME}:
            return MatchViewerPossessionPhase.DEAD_BALL
        if (
            event is not None
            and event.view.event_type
            in {
                MatchViewerEventType.FOUL,
                MatchViewerEventType.OFFSIDE,
                MatchViewerEventType.YELLOW_CARD,
                MatchViewerEventType.RED_CARD,
                MatchViewerEventType.SUBSTITUTION,
                MatchViewerEventType.INJURY,
            }
            and frame.pause_playback
        ):
            return MatchViewerPossessionPhase.DEAD_BALL
        if transition_state in {
            MatchViewerTransitionState.HOME_BREAK,
            MatchViewerTransitionState.AWAY_BREAK,
        }:
            return MatchViewerPossessionPhase.TRANSITION
        if danger_zone in {"central_box", "wide_box"}:
            return MatchViewerPossessionPhase.BOX_ATTACK
        if danger_zone == "final_third":
            return MatchViewerPossessionPhase.FINAL_THIRD
        return MatchViewerPossessionPhase.BUILD_UP

    def _frame_tags(
        self,
        *,
        frame: MatchTimelineFrameView,
        event: _ViewerEventContext | None,
        danger_zone: str,
        possession_phase: MatchViewerPossessionPhase,
        transition_state: MatchViewerTransitionState,
        pressure_index: float,
    ) -> list[str]:
        tags = [
            f"phase:{frame.phase.value}",
            f"stage:{frame.stage.value}",
            f"camera:{frame.camera_preset.value}",
            f"zone:{danger_zone}",
        ]
        if event is not None:
            tags.append(f"event:{event.view.event_type.value}")
        if possession_phase is not MatchViewerPossessionPhase.BUILD_UP:
            tags.append(f"possession:{possession_phase.value}")
        if transition_state is not MatchViewerTransitionState.STABLE:
            tags.append(f"transition:{transition_state.value}")
        if pressure_index >= 0.72:
            tags.append("high_pressure")
        elif pressure_index >= 0.45:
            tags.append("medium_pressure")
        if frame.playback_rate < 1.0:
            tags.append("slow_motion")
        if frame.pause_playback:
            tags.append("paused")
        if frame.flag_animation:
            tags.append("assistant_flag")
        if frame.celebration_team_id is not None:
            tags.append("celebration")

        deduped: list[str] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    def _player_velocity(
        self,
        *,
        current,
        previous,
        delta_t: float,
    ) -> MatchViewerVector2View:
        if previous is None or delta_t <= 0.0:
            return MatchViewerVector2View()
        return MatchViewerVector2View(
            x=round((float(current.x) - float(previous.x)) / max(delta_t, 0.05), 3),
            y=round((float(current.y) - float(previous.y)) / max(delta_t, 0.05), 3),
        )

    def _player_speed_ratio(
        self,
        *,
        player: MatchViewerPlayerFrameView,
        event: _ViewerEventContext | None,
        velocity: MatchViewerVector2View,
    ) -> float:
        if player.state is MatchViewerPlayerState.SENT_OFF:
            return 0.0
        speed = hypot(float(velocity.x), float(velocity.y))
        resolved = self._clamp_unit(speed / 12.0)
        if event is not None and event.motion is not None and player.player_id in event.view.highlighted_player_ids:
            resolved = max(
                resolved,
                self._clamp_unit(
                    (event.motion.run_weight * 0.45)
                    + (event.motion.sprint_weight * 0.95)
                    + (event.motion.shoot_weight * 0.75)
                ),
            )
        state_floor = {
            MatchViewerPlayerState.IDLE: 0.0,
            MatchViewerPlayerState.MOVING: 0.16,
            MatchViewerPlayerState.ATTACKING: 0.28,
            MatchViewerPlayerState.PRESSING: 0.34,
            MatchViewerPlayerState.DEFENDING: 0.22,
            MatchViewerPlayerState.SENT_OFF: 0.0,
        }[player.state]
        return round(max(resolved, state_floor), 3)

    def _player_facing(
        self,
        *,
        player: MatchViewerPlayerFrameView,
        frame: MatchTimelineFrameView,
        event: _ViewerEventContext | None,
        velocity: MatchViewerVector2View,
        ball_point: dict[str, float],
        has_possession: bool,
    ) -> MatchViewerVector2View:
        velocity_magnitude = hypot(float(velocity.x), float(velocity.y))
        if velocity_magnitude >= 0.05:
            return self._normalize_vector(float(velocity.x), float(velocity.y))

        target = None
        if event is not None and (
            has_possession
            or player.player_id in event.view.highlighted_player_ids
            or player.state in {MatchViewerPlayerState.PRESSING, MatchViewerPlayerState.DEFENDING}
        ):
            target = self._render_point(event, "target")
        if target is None and player.state in {MatchViewerPlayerState.PRESSING, MatchViewerPlayerState.DEFENDING}:
            target = ball_point
        if target is None:
            target = {
                "x": float(player.anchor_position.x),
                "y": float(player.anchor_position.y),
            }
        direction_x = float(target["x"]) - float(player.position.x)
        direction_y = float(target["y"]) - float(player.position.y)
        if abs(direction_x) < 0.01 and abs(direction_y) < 0.01:
            attacks_right = (
                frame.home_attacks_right if player.side is MatchViewerSide.HOME else not frame.home_attacks_right
            )
            direction_x = 1.0 if attacks_right else -1.0
            direction_y = 0.0
        return self._normalize_vector(direction_x, direction_y)

    def _player_stamina_pct(
        self,
        *,
        player: MatchViewerPlayerFrameView,
        runtime: _PlayerRuntime | None,
        clock_minute: float,
        event: _ViewerEventContext | None,
        speed_ratio: float,
    ) -> float:
        baseline = runtime.base_stamina_pct if runtime is not None and runtime.base_stamina_pct is not None else 84.0
        active_minute = min(
            clock_minute,
            (
                float(runtime.substituted_out_minute)
                if runtime is not None and runtime.substituted_out_minute is not None
                else clock_minute
            ),
        )
        freshness_bonus = 0.0
        if runtime is not None and runtime.substituted_in_minute is not None:
            active_minute = max(0.0, active_minute - float(runtime.substituted_in_minute))
            if active_minute <= 12.0:
                freshness_bonus = 7.0
        line_load = {
            "goalkeeper": 0.36,
            "defense": 0.58,
            "midfield": 0.72,
            "attack": 0.68,
        }.get(player.line, 0.64)
        stamina = baseline - (active_minute * (0.18 + (speed_ratio * 0.11)) * line_load) + freshness_bonus
        if (
            event is not None
            and event.motion is not None
            and player.player_id in event.view.highlighted_player_ids
            and event.motion.fatigue_load is not None
        ):
            stamina = min(stamina, 100.0 - (event.motion.fatigue_load * 100.0))
        if player.state is MatchViewerPlayerState.SENT_OFF:
            stamina = min(stamina, 40.0)
        return round(max(0.0, min(100.0, stamina)), 1)

    def _player_blend_factor(
        self,
        *,
        player: MatchViewerPlayerFrameView,
        event: _ViewerEventContext | None,
        speed_ratio: float,
    ) -> float:
        displacement = self._distance(
            {"x": float(player.position.x), "y": float(player.position.y)},
            {"x": float(player.anchor_position.x), "y": float(player.anchor_position.y)},
        )
        emphasis = 0.25 if player.highlighted else 0.0
        motion_blend = 0.0
        if event is not None and event.motion is not None and player.player_id in event.view.highlighted_player_ids:
            motion_blend = max(event.motion.run_weight, event.motion.sprint_weight, event.motion.shoot_weight) * 0.55
        return round(
            self._clamp_unit(max(displacement / 24.0, min(1.0, (speed_ratio * 0.55) + emphasis + motion_blend))),
            3,
        )

    def _player_animation_state(
        self,
        *,
        player: MatchViewerPlayerFrameView,
        frame: MatchTimelineFrameView,
        event: _ViewerEventContext | None,
        has_possession: bool,
        speed_ratio: float,
    ) -> MatchViewerAnimationState:
        if player.state is MatchViewerPlayerState.SENT_OFF:
            return MatchViewerAnimationState.SENT_OFF
        if (
            frame.celebration_team_id == player.team_id
            and event is not None
            and event.view.event_type is MatchViewerEventType.GOAL
            and frame.stage in {MatchViewerPlaybackStage.DECISION, MatchViewerPlaybackStage.POST}
        ):
            return MatchViewerAnimationState.CELEBRATE
        if (
            event is not None
            and player.role is PlayerRole.GOALKEEPER
            and event.view.event_type is MatchViewerEventType.SAVE
            and player.player_id
            in {
                event.view.primary_player_id,
                event.view.secondary_player_id,
            }
        ):
            return MatchViewerAnimationState.SAVE
        if has_possession and event is not None:
            if event.view.event_type in {
                MatchViewerEventType.PENALTY,
                MatchViewerEventType.SET_PIECE,
            } and frame.stage in {MatchViewerPlaybackStage.PRE, MatchViewerPlaybackStage.EVENT}:
                return MatchViewerAnimationState.SET_PIECE
            if event.view.event_type in {
                MatchViewerEventType.GOAL,
                MatchViewerEventType.MISS,
                MatchViewerEventType.SAVE,
            } and frame.stage in {MatchViewerPlaybackStage.EVENT, MatchViewerPlaybackStage.POST}:
                return MatchViewerAnimationState.SHOOT
            if event.view.event_type in {
                MatchViewerEventType.ATTACK,
                MatchViewerEventType.OFFSIDE,
            } and frame.stage in {MatchViewerPlaybackStage.PRE, MatchViewerPlaybackStage.EVENT}:
                return MatchViewerAnimationState.PASS
        if player.state in {MatchViewerPlayerState.PRESSING, MatchViewerPlayerState.DEFENDING} and speed_ratio >= 0.35:
            return MatchViewerAnimationState.PRESS
        if speed_ratio >= 0.75:
            return MatchViewerAnimationState.SPRINT
        if speed_ratio >= 0.42:
            return MatchViewerAnimationState.RUN
        if speed_ratio >= 0.16:
            return MatchViewerAnimationState.JOG
        return MatchViewerAnimationState.IDLE

    def _goal_progress(
        self,
        *,
        point: dict[str, float],
        side: MatchViewerSide,
        home_attacks_right: bool,
    ) -> float:
        if side is MatchViewerSide.HOME:
            return float(point["x"]) if home_attacks_right else 100.0 - float(point["x"])
        return 100.0 - float(point["x"]) if home_attacks_right else float(point["x"])

    def _distance(self, point_a: dict[str, float], point_b: dict[str, float]) -> float:
        return hypot(float(point_a["x"]) - float(point_b["x"]), float(point_a["y"]) - float(point_b["y"]))

    def _normalize_vector(self, x: float, y: float) -> MatchViewerVector2View:
        magnitude = max(hypot(x, y), 0.0001)
        return MatchViewerVector2View(
            x=round(x / magnitude, 3),
            y=round(y / magnitude, 3),
        )

    def _clamp_unit(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _viewer_event_type_from_match_event(self, event: MatchEventView) -> MatchViewerEventType:
        mapping = {
            MatchEventType.KICKOFF: MatchViewerEventType.KICKOFF,
            MatchEventType.GOAL: MatchViewerEventType.GOAL,
            MatchEventType.PENALTY_SCORED: MatchViewerEventType.GOAL,
            MatchEventType.FOUL: MatchViewerEventType.FOUL,
            MatchEventType.TACTICAL_FOUL: MatchViewerEventType.FOUL,
            MatchEventType.OFFSIDE: MatchViewerEventType.OFFSIDE,
            MatchEventType.GOALKEEPER_SAVE: MatchViewerEventType.SAVE,
            MatchEventType.DOUBLE_SAVE: MatchViewerEventType.SAVE,
            MatchEventType.MISSED_CHANCE: MatchViewerEventType.MISS,
            MatchEventType.MISSED_BIG_CHANCE: MatchViewerEventType.MISS,
            MatchEventType.WOODWORK: MatchViewerEventType.MISS,
            MatchEventType.PENALTY_MISSED: MatchViewerEventType.MISS,
            MatchEventType.RED_CARD: MatchViewerEventType.RED_CARD,
            MatchEventType.YELLOW_CARD: MatchViewerEventType.YELLOW_CARD,
            MatchEventType.SUBSTITUTION: MatchViewerEventType.SUBSTITUTION,
            MatchEventType.INJURY: MatchViewerEventType.INJURY,
            MatchEventType.HALFTIME: MatchViewerEventType.HALFTIME,
            MatchEventType.FULLTIME: MatchViewerEventType.FULLTIME,
            MatchEventType.PENALTY_AWARDED: MatchViewerEventType.PENALTY,
            MatchEventType.SET_PIECE_CHANCE: MatchViewerEventType.SET_PIECE,
            MatchEventType.DANGEROUS_ATTACK: MatchViewerEventType.ATTACK,
            MatchEventType.COUNTER_ATTACK: MatchViewerEventType.ATTACK,
            MatchEventType.SHOT: MatchViewerEventType.ATTACK,
            MatchEventType.SHOT_ON_TARGET: MatchViewerEventType.ATTACK,
        }
        return mapping.get(event.event_type, MatchViewerEventType.NEUTRAL)

    def _viewer_event_type_from_live_event(
        self,
        event: LiveMatchStreamEventView,
        *,
        raw_event_type: str,
    ) -> MatchViewerEventType:
        normalized_raw = (raw_event_type or "").strip().lower()
        normalized_event = (event.event_type or "").strip().lower()
        if normalized_event == "goal" or normalized_raw in {"goal", "penalty_goal", "penalty_scored"}:
            return MatchViewerEventType.GOAL
        if normalized_event == "save" or normalized_raw in {"save", "goalkeeper_save", "double_save", "shot_on_target"}:
            return MatchViewerEventType.SAVE
        if normalized_event == "chance" or normalized_raw in {
            "chance",
            "miss",
            "missed_chance",
            "missed_big_chance",
            "woodwork",
            "penalty_missed",
        }:
            return MatchViewerEventType.MISS
        if normalized_event in {"attack", "shot"} or normalized_raw in {"attack", "counter", "counter_attack"}:
            return MatchViewerEventType.ATTACK
        if normalized_event in {"full_time", "fulltime"} or normalized_raw in {"full_time", "fulltime"}:
            return MatchViewerEventType.FULLTIME
        if normalized_event == "card" or normalized_raw in {"red_card", "yellow_card"}:
            if normalized_raw == "red_card" or event.metadata.get("card_type") == "red":
                return MatchViewerEventType.RED_CARD
            return MatchViewerEventType.YELLOW_CARD
        if normalized_event == "substitution" or normalized_raw == "substitution":
            return MatchViewerEventType.SUBSTITUTION
        if normalized_event == "offside" or normalized_raw == "offside":
            return MatchViewerEventType.OFFSIDE
        if normalized_event == "foul" or normalized_raw in {"foul", "tactical_foul"}:
            return MatchViewerEventType.FOUL
        if normalized_raw in {"free_kick", "corner"}:
            return MatchViewerEventType.SET_PIECE
        if normalized_raw == "penalty_awarded":
            return MatchViewerEventType.PENALTY
        return MatchViewerEventType.NEUTRAL

    def _viewer_event_type_from_archive_event(self, event: ReplayMomentView) -> MatchViewerEventType:
        description = (event.description or "").lower()
        if event.event_type == "goals":
            return MatchViewerEventType.GOAL
        if event.event_type == "red_cards":
            return MatchViewerEventType.RED_CARD
        if event.event_type == "yellow_cards":
            return MatchViewerEventType.YELLOW_CARD
        if event.event_type == "substitutions":
            return MatchViewerEventType.SUBSTITUTION
        if event.event_type == "injuries":
            return MatchViewerEventType.INJURY
        if event.event_type == "penalties":
            if "saved" in description or "denied" in description:
                return MatchViewerEventType.SAVE
            if "miss" in description:
                return MatchViewerEventType.MISS
            return MatchViewerEventType.GOAL
        if "offside" in description:
            return MatchViewerEventType.OFFSIDE
        if "foul" in description:
            return MatchViewerEventType.FOUL
        if "save" in description or "denied" in description or "keeps out" in description:
            return MatchViewerEventType.SAVE
        if event.event_type == "missed_chances":
            return MatchViewerEventType.MISS
        return MatchViewerEventType.NEUTRAL

    def _phase_for_event(self, event_type: MatchViewerEventType) -> MatchViewerPhase:
        if event_type is MatchViewerEventType.KICKOFF:
            return MatchViewerPhase.KICKOFF
        if event_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE}:
            return MatchViewerPhase.SET_PIECE
        if event_type is MatchViewerEventType.HALFTIME:
            return MatchViewerPhase.HALFTIME
        if event_type is MatchViewerEventType.FULLTIME:
            return MatchViewerPhase.FULLTIME
        return MatchViewerPhase.OPEN_PLAY

    def _build_up_seconds(self, event: MatchViewerEventView) -> float:
        if event.playback_profile == "foul" or event.event_type in {
            MatchViewerEventType.FOUL,
            MatchViewerEventType.YELLOW_CARD,
            MatchViewerEventType.RED_CARD,
        }:
            return 1.6
        if event.playback_profile in {"goal", "offside"} or event.event_type in {
            MatchViewerEventType.GOAL,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.OFFSIDE,
        }:
            return 2.2
        return 1.1

    def _lead_seconds(self, event_type: MatchViewerEventType) -> float:
        if event_type in {
            MatchViewerEventType.GOAL,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.RED_CARD,
            MatchViewerEventType.OFFSIDE,
        }:
            return 2.2
        if event_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE}:
            return 1.8
        return 1.1

    def _settle_seconds(self, event_type: MatchViewerEventType) -> float:
        if event_type is MatchViewerEventType.GOAL:
            return 2.4
        if event_type in {
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.RED_CARD,
            MatchViewerEventType.FOUL,
        }:
            return 1.8
        if event_type in {MatchViewerEventType.HALFTIME, MatchViewerEventType.FULLTIME}:
            return 1.2
        return 1.1

    def _push_amount(self, *, line: str, owns_ball: bool) -> float:
        if line == "goalkeeper":
            return 0.0 if owns_ball else -1.0
        if line == "defense":
            return 2.8 if owns_ball else 0.8
        if line == "midfield":
            return 4.2 if owns_ball else 1.6
        return 6.0 if owns_ball else 1.8

    def _kickoff_position(
        self,
        position: dict[str, float],
        attack_direction: float,
        role: PlayerRole,
        highlighted: bool,
    ) -> dict[str, float]:
        if role is PlayerRole.GOALKEEPER:
            return position
        center_bias = 0.56 if highlighted else 0.22
        position["x"] = self._lerp(
            position["x"], 50.0 + (attack_direction * (1.2 if highlighted else 5.0)), center_bias
        )
        position["y"] = self._lerp(position["y"], 50.0, 0.26 if highlighted else 0.14)
        return position

    def _target_zone(
        self,
        *,
        side: MatchViewerSide,
        home_attacks_right: bool,
        event_id: str,
        viewer_type: MatchViewerEventType,
    ) -> dict[str, float]:
        attacks_right = home_attacks_right if side is MatchViewerSide.HOME else not home_attacks_right
        target_y = 26.0 + (self._fraction(event_id) * 48.0)
        target_x = (
            96.0
            if attacks_right and viewer_type is MatchViewerEventType.GOAL
            else 90.0 if attacks_right else 4.0 if viewer_type is MatchViewerEventType.GOAL else 10.0
        )
        if viewer_type in {
            MatchViewerEventType.PENALTY,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.SET_PIECE,
        }:
            target_x = 88.0 if attacks_right else 12.0
        if viewer_type is MatchViewerEventType.OFFSIDE:
            target_x = 82.0 if attacks_right else 18.0
        if viewer_type is MatchViewerEventType.FOUL:
            target_x = 62.0 if attacks_right else 38.0
        return {"x": target_x, "y": target_y}

    def _wide_target_zone(
        self,
        *,
        side: MatchViewerSide,
        home_attacks_right: bool,
        event_id: str,
    ) -> dict[str, float]:
        attacks_right = home_attacks_right if side is MatchViewerSide.HOME else not home_attacks_right
        miss_high = self._fraction(f"{event_id}:miss") > 0.5
        return {
            "x": 97.0 if attacks_right else 3.0,
            "y": 8.0 if miss_high else 92.0,
        }

    def _goalkeeper_zone(
        self,
        *,
        side: MatchViewerSide,
        home_attacks_right: bool,
        event_id: str,
    ) -> dict[str, float]:
        attacks_right = home_attacks_right if side is MatchViewerSide.HOME else not home_attacks_right
        base_x = 8.0 if attacks_right else 92.0
        target_y = 38.0 + (self._fraction(f"{event_id}:gk") * 24.0)
        return {"x": base_x, "y": target_y}

    def _ball_near_player(self, position: dict[str, float]) -> dict[str, float]:
        return {
            "x": self._clamp(position["x"] + 1.1),
            "y": self._clamp(position["y"] + 0.8),
        }

    def _default_owner(self, runtime: _TeamRuntime) -> str | None:
        attackers = [
            player_id for player_id in runtime.lineup if runtime.players_by_id[player_id].role is PlayerRole.FORWARD
        ]
        midfielders = [
            player_id for player_id in runtime.lineup if runtime.players_by_id[player_id].role is PlayerRole.MIDFIELDER
        ]
        if attackers:
            return attackers[0]
        if midfielders:
            return midfielders[0]
        return runtime.lineup[0] if runtime.lineup else None

    def _runtime_from_side(
        self,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        side: MatchViewerSide | None,
    ) -> _TeamRuntime | None:
        if side is MatchViewerSide.HOME:
            return home_runtime
        if side is MatchViewerSide.AWAY:
            return away_runtime
        return None

    def _team_side_from_team_id(
        self,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        team_id: str | None,
    ) -> MatchViewerSide | None:
        if team_id == home_runtime.view.team_id:
            return MatchViewerSide.HOME
        if team_id == away_runtime.view.team_id:
            return MatchViewerSide.AWAY
        return None

    def _player_side_lookup(
        self,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        player_id: str | None,
    ) -> MatchViewerSide | None:
        if player_id is None:
            return None
        if player_id in home_runtime.players_by_id:
            return MatchViewerSide.HOME
        if player_id in away_runtime.players_by_id:
            return MatchViewerSide.AWAY
        return None

    def _team_side_from_player(
        self,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        player_id: str | None,
    ) -> MatchViewerSide | None:
        return self._player_side_lookup(home_runtime, away_runtime, player_id)

    def _opposite_side(self, side: MatchViewerSide) -> MatchViewerSide:
        return MatchViewerSide.AWAY if side is MatchViewerSide.HOME else MatchViewerSide.HOME

    def _restart_side_after_goal(self, home_score: int, away_score: int) -> MatchViewerSide:
        return MatchViewerSide.AWAY if home_score > away_score else MatchViewerSide.HOME

    def _clock_value(self, minute: int, added_time: int) -> float:
        return float(minute) + (float(added_time) / 10.0)

    def _pre_clock(self, previous_clock: float, next_minute: int) -> float:
        if next_minute <= previous_clock:
            return previous_clock
        return max(previous_clock, float(next_minute) - 0.35)

    def _playback_stage(self, stage: str) -> MatchViewerPlaybackStage:
        mapping = {
            "pre": MatchViewerPlaybackStage.PRE,
            "event": MatchViewerPlaybackStage.EVENT,
            "hold": MatchViewerPlaybackStage.HOLD,
            "review": MatchViewerPlaybackStage.REVIEW,
            "decision": MatchViewerPlaybackStage.DECISION,
            "post": MatchViewerPlaybackStage.POST,
            "reset": MatchViewerPlaybackStage.RESET,
        }
        return mapping.get(stage, MatchViewerPlaybackStage.EVENT)

    def _score_before_minute(self, events: list[_ViewerEventContext], minute: int) -> tuple[int, int]:
        home_score = 0
        away_score = 0
        for item in events:
            if item.view.minute > minute:
                break
            home_score = item.view.home_score
            away_score = item.view.away_score
        return home_score, away_score

    def _spread_archive_times(self, events: list[ReplayMomentView], *, duration_seconds: float) -> list[float]:
        if not events:
            return []
        if len(events) == 1:
            return [max(15.0, duration_seconds * 0.4)]
        last_clock = max(float(item.minute) for item in events)
        last_clock = max(last_clock, 90.0)
        output: list[float] = []
        for item in events:
            output.append(round((float(item.minute) / last_clock) * max(60.0, duration_seconds - 8.0), 2))
        return output

    def _infer_formation(self, player_visuals: list[Any]) -> str:
        starters = list(player_visuals[:11])
        defenders = sum(1 for item in starters if item.role is PlayerRole.DEFENDER)
        midfielders = sum(1 for item in starters if item.role is PlayerRole.MIDFIELDER)
        forwards = sum(1 for item in starters if item.role is PlayerRole.FORWARD)
        if defenders == 4 and midfielders == 3 and forwards == 3:
            return "4-3-3"
        if defenders == 4 and midfielders == 5 and forwards == 1:
            return "4-2-3-1"
        if defenders == 4 and midfielders == 4 and forwards == 2:
            return "4-4-2"
        if defenders == 3 and midfielders == 5 and forwards == 2:
            return "3-5-2"
        return "4-3-3"

    def _normalize_formation(self, formation: str | None) -> str:
        if not formation:
            return "4-3-3"
        normalized = str(formation).strip()
        if normalized in _SUPPORTED_FORMATIONS:
            return normalized
        try:
            parts = [int(part) for part in normalized.split("-")]
        except ValueError:
            return "4-3-3"
        if sum(parts) in {9, 10} and len(parts) in {3, 4}:
            return normalized
        return "4-3-3"

    def _archive_default_commentary(self, event: ReplayMomentView) -> str:
        if event.club_name and event.player_name:
            return f"{event.club_name}: {event.player_name}"
        return event.club_name or event.player_name or event.event_type.replace("_", " ")

    def _banner_text(self, commentary: str, fallback: str) -> str:
        normalized = commentary.strip()
        if normalized:
            return normalized if len(normalized) <= 72 else f"{normalized[:69].rstrip()}..."
        return fallback.replace("_", " ").title()

    def _emphasis_level(self, event_type: MatchViewerEventType) -> int:
        if event_type in {MatchViewerEventType.GOAL, MatchViewerEventType.RED_CARD}:
            return 3
        if event_type in {
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.FOUL,
            MatchViewerEventType.OFFSIDE,
            MatchViewerEventType.PENALTY,
        }:
            return 2
        return 1

    def _optional_text(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _render_contract(self, value: object | None) -> dict[str, Any] | None:
        return value if isinstance(value, dict) else None

    def _render_ball_contract(self, event: _ViewerEventContext | None) -> dict[str, Any] | None:
        if event is None or not event.render_contract:
            return None
        ball = event.render_contract.get("ball")
        return ball if isinstance(ball, dict) else None

    def _render_point(self, event: _ViewerEventContext | None, key: str) -> dict[str, float] | None:
        if event is None or not event.render_contract:
            return None
        raw = event.render_contract.get(key)
        if not isinstance(raw, dict):
            return None
        x = raw.get("x")
        y = raw.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        return {"x": self._clamp(float(x)), "y": self._clamp(float(y))}

    def _render_ball_trajectory_point(
        self,
        event: _ViewerEventContext | None,
        *,
        stage: str,
    ) -> dict[str, float] | None:
        ball = self._render_ball_contract(event)
        if ball is None:
            return None
        trajectory = ball.get("trajectory")
        if not isinstance(trajectory, list) or not trajectory:
            return None
        index = 0 if stage == "pre" else len(trajectory) // 2 if stage == "event" else len(trajectory) - 1
        point = trajectory[max(0, min(index, len(trajectory) - 1))]
        if not isinstance(point, dict):
            return None
        x = point.get("x")
        y = point.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        return {"x": self._clamp(float(x)), "y": self._clamp(float(y))}

    def _render_ball_height(
        self,
        event: _ViewerEventContext | None,
        *,
        stage: str,
    ) -> float:
        ball = self._render_ball_contract(event)
        if ball is None:
            return 0.0
        trajectory = ball.get("trajectory")
        if isinstance(trajectory, list) and trajectory:
            index = 0 if stage == "pre" else len(trajectory) // 2 if stage == "event" else len(trajectory) - 1
            point = trajectory[max(0, min(index, len(trajectory) - 1))]
            if isinstance(point, dict) and isinstance(point.get("z"), (int, float)):
                return round(max(0.0, float(point["z"])), 3)
        height = ball.get("max_height", ball.get("height", 0.0))
        return round(max(0.0, float(height or 0.0)), 3)

    def _render_ball_vector(self, event: _ViewerEventContext | None, *, key: str) -> dict[str, float] | None:
        ball = self._render_ball_contract(event)
        if ball is None:
            return None
        raw = ball.get(key)
        if not isinstance(raw, dict):
            return None
        x = raw.get("x")
        y = raw.get("y")
        z = raw.get("z")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)) or not isinstance(z, (int, float)):
            return None
        return {"x": round(float(x), 3), "y": round(float(y), 3), "z": round(float(z), 3)}

    def _render_camera_mode(self, event: _ViewerEventContext | None) -> str | None:
        if event is None or not event.render_contract:
            return None
        camera = event.render_contract.get("camera")
        if not isinstance(camera, dict):
            return None
        return self._optional_text(camera.get("mode"))

    def _render_slow_motion(self, event: _ViewerEventContext | None) -> bool:
        if event is None or not event.render_contract:
            return False
        camera = event.render_contract.get("camera")
        return isinstance(camera, dict) and bool(camera.get("slow_motion", False))

    def _camera_preset_from_render(
        self,
        event: _ViewerEventContext | None,
        *,
        stage: str,
        fallback: MatchViewerCameraPreset,
    ) -> MatchViewerCameraPreset:
        mode = self._render_camera_mode(event)
        if mode == "assistant_flag":
            return MatchViewerCameraPreset.ASSISTANT_FLAG
        if mode == "goal_camera":
            return (
                MatchViewerCameraPreset.GOAL_CELEBRATION
                if stage in {"decision", "post"}
                else MatchViewerCameraPreset.BOX_ZOOM
            )
        if mode == "attack_zoom":
            return MatchViewerCameraPreset.ATTACK_PUSH if stage == "pre" else MatchViewerCameraPreset.BOX_ZOOM
        if mode == "var_replay":
            return MatchViewerCameraPreset.VAR_REPLAY
        if mode == "broadcast":
            return MatchViewerCameraPreset.BROADCAST
        return fallback

    def _playback_rate_from_render(
        self,
        event: _ViewerEventContext | None,
        *,
        stage: str,
        fallback: float = 1.0,
    ) -> float:
        if stage in {"event", "post"} and self._render_slow_motion(event):
            return 0.5
        return fallback

    def _ball_state_from_render(self, event: _ViewerEventContext | None, *, fallback: str) -> str:
        if event is None or not event.render_contract:
            return fallback
        ball = event.render_contract.get("ball")
        if not isinstance(ball, dict):
            return fallback
        motion = self._optional_text(ball.get("motion"))
        return motion or fallback

    def _fraction(self, seed: str) -> float:
        digest = md5(seed.encode("utf-8")).hexdigest()[:8]
        return int(digest, 16) / 0xFFFFFFFF

    def _clamp(self, value: float) -> float:
        return max(0.0, min(100.0, round(value, 2)))

    def _lerp(self, start: float, end: float, t: float) -> float:
        return self._clamp(start + ((end - start) * t))
