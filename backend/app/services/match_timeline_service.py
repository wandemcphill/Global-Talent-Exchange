from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from typing import Any

from app.match_engine.schemas import MatchEventView, MatchReplayPayloadView, MatchTeamVisualIdentityView
from app.match_engine.simulation.models import MatchEventType, PlayerRole
from app.replay_archive.schemas import ReplayArchiveRecord, ReplayMomentView
from app.schemas.match_viewer import (
    MatchViewerCameraPreset,
    MatchTimelineFrameView,
    MatchViewerBallFrameView,
    MatchViewerEventType,
    MatchViewerEventView,
    MatchViewerPhase,
    MatchViewerPlaybackStage,
    MatchViewerPlayerFrameView,
    MatchViewerPlayerState,
    MatchViewerSide,
    MatchViewerTeamView,
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


@dataclass(slots=True)
class _TeamRuntime:
    view: MatchViewerTeamView
    players_by_id: dict[str, _PlayerRuntime]
    lineup: list[str]
    bench: list[str]
    current_formation: str


@dataclass(slots=True)
class _ViewerEventContext:
    view: MatchViewerEventView
    source_type: str
    team_side: MatchViewerSide | None
    home_formation: str | None = None
    away_formation: str | None = None
    fallback_formation: str | None = None
    render_contract: dict[str, Any] | None = None


class MatchTimelineService:
    def build_from_replay_payload(self, replay_payload: MatchReplayPayloadView) -> MatchViewStateView:
        if replay_payload.visual_identity is None:
            raise ValueError("Viewer timeline requires replay visual identity data.")

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
        home_runtime = self._team_runtime(replay_payload.visual_identity.home_team, home_team)
        away_runtime = self._team_runtime(replay_payload.visual_identity.away_team, away_team)
        events = [self._context_from_match_event(item) for item in replay_payload.timeline.events]
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
            duration_seconds=max(replay_payload.timeline.presentation_duration_seconds, int(frames[-1].time_seconds) if frames else 0),
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

    def _team_runtime(self, team: MatchTeamVisualIdentityView, team_view: MatchViewerTeamView) -> _TeamRuntime:
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
            )
            for item in team.player_visuals
        }
        return _TeamRuntime(
            view=team_view,
            players_by_id=players_by_id,
            lineup=[item.player_id for item in starters],
            bench=[item.player_id for item in bench],
            current_formation=team_view.formation,
        )

    def _context_from_match_event(self, event: MatchEventView) -> _ViewerEventContext:
        metadata = event.metadata or {}
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
                secondary_player_name=event.secondary_player.player_name if event.secondary_player is not None else None,
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
                    player_id
                    for player_id in (event.player_id, event.secondary_player_id)
                    if player_id is not None
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
        )

    def _ensure_control_events(
        self,
        *,
        match_id: str,
        events: list[_ViewerEventContext],
        duration_seconds: float,
        final_home_score: int,
        final_away_score: int,
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
        if not has_halftime:
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
        if not has_fulltime:
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
                and (
                    event.view.home_score != prior_home_score
                    or event.view.away_score != prior_away_score
                )
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
                        overlay_text=(
                            "Confirmed"
                            if event.view.review_decision == "confirmed"
                            else "Disallowed"
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
                        "RED CARD"
                        if event.view.event_type is MatchViewerEventType.RED_CARD
                        else "YELLOW CARD"
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
                        self._clock_value(event.view.minute, event.view.added_time)
                        + 0.12,
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
        return deduped

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
            event_banner=active_event.view.banner_text if active_event is not None and stage in {"event", "decision", "post"} else None,
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
                team_attacks_right=home_attacks_right if runtime.view.side is MatchViewerSide.HOME else not home_attacks_right,
            )
            attack_direction = 1.0 if (home_attacks_right if runtime.view.side is MatchViewerSide.HOME else not home_attacks_right) else -1.0
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
        anchors: dict[str, dict[str, float]] = {
            goalkeeper_id: {"x": 8.0 if team_attacks_right else 92.0, "y": 50.0}
        }
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
            group_ids = outfield_ids[cursor:cursor + group_size]
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
        return list(_LINE_Y_MAP.get(count, tuple(10.0 + ((index + 1) * (80.0 / (count + 1))) for index in range(count))))

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
        primary_side = self._team_side_from_player(home_runtime=runtime, away_runtime=opponent, player_id=active_event.view.primary_player_id)
        secondary_side = self._team_side_from_player(home_runtime=runtime, away_runtime=opponent, player_id=active_event.view.secondary_player_id)
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
                position["x"] = self._lerp(position["x"], event_origin["x"] if stage == "pre" else event_target["x"], 0.66 if stage != "pre" else 0.38)
                position["y"] = self._lerp(position["y"], event_origin["y"] if stage == "pre" else event_target["y"], 0.66 if stage != "pre" else 0.38)
                return position, state
            if viewer_type is MatchViewerEventType.GOAL and secondary_side is attacking_side:
                state = MatchViewerPlayerState.ATTACKING
                position["x"] = self._lerp(position["x"], event_target["x"] - (5.0 if attacking_side is MatchViewerSide.HOME else -5.0), 0.52)
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
                position["x"] = self._lerp(position["x"], event_target["x"] - (2.5 if attacking_side is MatchViewerSide.HOME else -2.5), 0.38)
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
            return ball_frame(position=self._ball_near_player(positions.get(owner) or {"x": 50.0, "y": 50.0}), owner_player_id=owner, state="rolling")

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
                return ball_frame(position=self._ball_near_player(primary_pos or event_origin), owner_player_id=primary, state=self._ball_state_from_render(active_event, fallback="controlled"))
            if stage == "event":
                return ball_frame(position=event_target, owner_player_id=None, state=self._ball_state_from_render(active_event, fallback="shot"))
            return ball_frame(position={"x": event_target["x"], "y": event_target["y"]}, owner_player_id=None, state="in_goal")
        if viewer_type is MatchViewerEventType.SAVE:
            if stage == "pre":
                return ball_frame(position=self._ball_near_player(secondary_pos or primary_pos or event_origin), owner_player_id=secondary or primary, state=self._ball_state_from_render(active_event, fallback="controlled"))
            if stage == "event":
                return ball_frame(position=event_target, owner_player_id=None, state=self._ball_state_from_render(active_event, fallback="saved"))
            return ball_frame(position=self._ball_near_player(goalkeeper_target), owner_player_id=primary if primary_side is defending_side else secondary, state="held")
        if viewer_type is MatchViewerEventType.MISS:
            if stage == "pre":
                return ball_frame(position=self._ball_near_player(primary_pos or event_origin), owner_player_id=primary, state=self._ball_state_from_render(active_event, fallback="controlled"))
            resolved_miss_target = event_target if stage == "event" else wide_target
            return ball_frame(position=resolved_miss_target if stage == "event" else self._ball_near_player(resolved_miss_target), owner_player_id=None, state=self._ball_state_from_render(active_event, fallback="missed"))
        if viewer_type is MatchViewerEventType.FOUL:
            return ball_frame(position=self._ball_near_player(primary_pos or event_origin), owner_player_id=primary or default_owner, state="stopped")
        if viewer_type is MatchViewerEventType.OFFSIDE:
            return ball_frame(position=event_target if stage != "pre" else self._ball_near_player(primary_pos or event_origin), owner_player_id=primary, state="stopped")
        if viewer_type in {MatchViewerEventType.RED_CARD, MatchViewerEventType.HALFTIME, MatchViewerEventType.FULLTIME}:
            return ball_frame(position=self._ball_near_player(primary_pos or positions.get(default_owner) or {"x": 50.0, "y": 50.0}), owner_player_id=primary or default_owner, state="stopped")
        if viewer_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE, MatchViewerEventType.ATTACK}:
            if stage == "pre":
                return ball_frame(position=self._ball_near_player(primary_pos or event_origin), owner_player_id=primary or default_owner, state=self._ball_state_from_render(active_event, fallback="controlled"))
            if stage == "event":
                return ball_frame(position=event_target, owner_player_id=None, state=self._ball_state_from_render(active_event, fallback="traveling"))
        owner = primary or default_owner
        return ball_frame(position=self._ball_near_player(positions.get(owner) or event_target), owner_player_id=owner, state=self._ball_state_from_render(active_event, fallback="rolling"))

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
        if event_type in {MatchViewerEventType.GOAL, MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.RED_CARD, MatchViewerEventType.OFFSIDE}:
            return 2.2
        if event_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE}:
            return 1.8
        return 1.1

    def _settle_seconds(self, event_type: MatchViewerEventType) -> float:
        if event_type is MatchViewerEventType.GOAL:
            return 2.4
        if event_type in {MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.RED_CARD, MatchViewerEventType.FOUL}:
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
        position["x"] = self._lerp(position["x"], 50.0 + (attack_direction * (1.2 if highlighted else 5.0)), center_bias)
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
        target_x = 96.0 if attacks_right and viewer_type is MatchViewerEventType.GOAL else 90.0 if attacks_right else 4.0 if viewer_type is MatchViewerEventType.GOAL else 10.0
        if viewer_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.SET_PIECE}:
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
        attackers = [player_id for player_id in runtime.lineup if runtime.players_by_id[player_id].role is PlayerRole.FORWARD]
        midfielders = [player_id for player_id in runtime.lineup if runtime.players_by_id[player_id].role is PlayerRole.MIDFIELDER]
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
        if event_type in {MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.FOUL, MatchViewerEventType.OFFSIDE, MatchViewerEventType.PENALTY}:
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
