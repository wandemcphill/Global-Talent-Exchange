from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from typing import Any

from app.match_engine.schemas import MatchEventView, MatchReplayPayloadView, MatchTeamVisualIdentityView
from app.match_engine.simulation.models import MatchEventType, PlayerRole
from app.replay_archive.schemas import ReplayArchiveRecord, ReplayMomentView
from app.schemas.match_viewer import (
    MatchTimelineFrameView,
    MatchViewerBallFrameView,
    MatchViewerEventType,
    MatchViewerEventView,
    MatchViewerPhase,
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
            ),
            source_type=event.event_type.value,
            team_side=None,
            home_formation=self._optional_text(metadata.get("home_formation")),
            away_formation=self._optional_text(metadata.get("away_formation")),
            fallback_formation=self._optional_text(metadata.get("fallback_formation")),
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
            ),
            source_type=event.event_type,
            team_side=None,
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
        for index, event in enumerate(events):
            event.team_side = self._team_side_from_team_id(home_runtime, away_runtime, event.view.team_id)
            if event.team_side is not None:
                last_possession = event.team_side
            lead = self._lead_seconds(event.view.event_type)
            settle = self._settle_seconds(event.view.event_type)
            pre_time = max(last_time + 0.4, event.view.time_seconds - lead)

            if not frames:
                frames.append(
                    self._frame(
                        match_id=match_id,
                        home_runtime=home_runtime,
                        away_runtime=away_runtime,
                        time_seconds=0.0,
                        clock_minute=0.0,
                        home_score=0,
                        away_score=0,
                        active_event=None,
                        phase=MatchViewerPhase.KICKOFF,
                        stage="reset",
                        possession_side=MatchViewerSide.HOME,
                    )
                )
                last_time = 0.0

            if pre_time > last_time + 0.1:
                frames.append(
                    self._frame(
                        match_id=match_id,
                        home_runtime=home_runtime,
                        away_runtime=away_runtime,
                        time_seconds=pre_time,
                        clock_minute=max(0.0, self._pre_clock(frames[-1].clock_minute, event.view.minute)),
                        home_score=frames[-1].home_score,
                        away_score=frames[-1].away_score,
                        active_event=event,
                        phase=self._phase_for_event(event.view.event_type),
                        stage="pre",
                        possession_side=event.team_side or last_possession,
                    )
                )
                last_time = pre_time

            if event.view.event_type is MatchViewerEventType.SUBSTITUTION:
                self._apply_persistent_event(home_runtime, away_runtime, event)

            frames.append(
                self._frame(
                    match_id=match_id,
                    home_runtime=home_runtime,
                    away_runtime=away_runtime,
                    time_seconds=max(event.view.time_seconds, last_time + 0.1),
                    clock_minute=self._clock_value(event.view.minute, event.view.added_time),
                    home_score=event.view.home_score,
                    away_score=event.view.away_score,
                    active_event=event,
                    phase=self._phase_for_event(event.view.event_type),
                    stage="event",
                    possession_side=event.team_side or last_possession,
                )
            )
            last_time = frames[-1].time_seconds

            if event.view.event_type is not MatchViewerEventType.SUBSTITUTION:
                self._apply_persistent_event(home_runtime, away_runtime, event)

            post_time = min(duration_seconds + 4.0, max(last_time + 0.6, event.view.time_seconds + settle))
            if event.view.event_type is not MatchViewerEventType.FULLTIME:
                frames.append(
                    self._frame(
                        match_id=match_id,
                        home_runtime=home_runtime,
                        away_runtime=away_runtime,
                        time_seconds=post_time,
                        clock_minute=min(120.0, self._clock_value(event.view.minute, event.view.added_time) + 0.2),
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=self._phase_for_event(event.view.event_type),
                        stage="post",
                        possession_side=event.team_side or last_possession,
                    )
                )
                last_time = post_time

            if event.view.event_type is MatchViewerEventType.GOAL:
                reset_time = min(duration_seconds + 5.0, last_time + 1.8)
                frames.append(
                    self._frame(
                        match_id=match_id,
                        home_runtime=home_runtime,
                        away_runtime=away_runtime,
                        time_seconds=reset_time,
                        clock_minute=min(120.0, self._clock_value(event.view.minute, event.view.added_time) + 0.35),
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.KICKOFF,
                        stage="reset",
                        possession_side=self._restart_side_after_goal(event.view.home_score, event.view.away_score),
                    )
                )
                last_time = reset_time

            if event.view.event_type is MatchViewerEventType.HALFTIME:
                second_half_time = min(duration_seconds + 6.0, last_time + 1.4)
                frames.append(
                    self._frame(
                        match_id=match_id,
                        home_runtime=home_runtime,
                        away_runtime=away_runtime,
                        time_seconds=second_half_time,
                        clock_minute=45.1,
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.KICKOFF,
                        stage="reset",
                        possession_side=MatchViewerSide.AWAY,
                    )
                )
                last_time = second_half_time

            if event.view.event_type is MatchViewerEventType.FULLTIME:
                last_time = max(last_time, event.view.time_seconds)

            if index == len(events) - 1 and frames[-1].time_seconds < duration_seconds:
                frames.append(
                    self._frame(
                        match_id=match_id,
                        home_runtime=home_runtime,
                        away_runtime=away_runtime,
                        time_seconds=duration_seconds,
                        clock_minute=max(90.0, frames[-1].clock_minute),
                        home_score=event.view.home_score,
                        away_score=event.view.away_score,
                        active_event=event,
                        phase=MatchViewerPhase.FULLTIME,
                        stage="post",
                        possession_side=last_possession,
                    )
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
            active_event_id=active_event.view.event_id if active_event is not None else None,
            event_banner=active_event.view.banner_text if active_event is not None and stage in {"event", "post"} else None,
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
        event_target = self._target_zone(
            side=attacking_side or MatchViewerSide.HOME,
            home_attacks_right=home_attacks_right,
            event_id=active_event.view.event_id,
            viewer_type=viewer_type,
        )
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
                    position["x"] = self._lerp(position["x"], event_target["x"], 0.42)
                    position["y"] = self._lerp(position["y"], event_target["y"], 0.42)
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
                position["x"] = self._lerp(position["x"], event_target["x"], 0.66 if stage != "pre" else 0.38)
                position["y"] = self._lerp(position["y"], event_target["y"], 0.66 if stage != "pre" else 0.38)
                return position, state
            if viewer_type is MatchViewerEventType.GOAL and secondary_side is attacking_side:
                state = MatchViewerPlayerState.ATTACKING
                position["x"] = self._lerp(position["x"], event_target["x"] - (5.0 if attacking_side is MatchViewerSide.HOME else -5.0), 0.52)
                position["y"] = self._lerp(position["y"], event_target["y"] + 6.0, 0.52)
                return position, state

        if viewer_type in {MatchViewerEventType.GOAL, MatchViewerEventType.MISS, MatchViewerEventType.SAVE, MatchViewerEventType.ATTACK, MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE, MatchViewerEventType.OFFSIDE}:
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
        if stage == "reset":
            return {
                "position": {"x": 50.0, "y": 50.0},
                "owner_player_id": default_owner,
                "state": "placed",
            }
        if active_event is None:
            owner = default_owner
            return {
                "position": self._ball_near_player(positions.get(owner) or {"x": 50.0, "y": 50.0}),
                "owner_player_id": owner,
                "state": "rolling",
            }

        viewer_type = active_event.view.event_type
        primary = active_event.view.primary_player_id
        secondary = active_event.view.secondary_player_id
        primary_side = self._player_side_lookup(home_runtime, away_runtime, primary)
        secondary_side = self._player_side_lookup(home_runtime, away_runtime, secondary)
        attacking_side = active_event.team_side or secondary_side or primary_side or possession_side
        defending_side = self._opposite_side(attacking_side)
        event_target = self._target_zone(
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

        if viewer_type is MatchViewerEventType.GOAL:
            if stage == "pre":
                return {"position": self._ball_near_player(primary_pos or event_target), "owner_player_id": primary, "state": "controlled"}
            if stage == "event":
                return {"position": event_target, "owner_player_id": None, "state": "shot"}
            return {"position": {"x": event_target["x"], "y": event_target["y"]}, "owner_player_id": None, "state": "in_goal"}
        if viewer_type is MatchViewerEventType.SAVE:
            if stage == "pre":
                return {"position": self._ball_near_player(secondary_pos or primary_pos or event_target), "owner_player_id": secondary or primary, "state": "controlled"}
            if stage == "event":
                return {"position": goalkeeper_target, "owner_player_id": None, "state": "saved"}
            return {"position": self._ball_near_player(goalkeeper_target), "owner_player_id": primary if primary_side is defending_side else secondary, "state": "held"}
        if viewer_type is MatchViewerEventType.MISS:
            if stage == "pre":
                return {"position": self._ball_near_player(primary_pos or event_target), "owner_player_id": primary, "state": "controlled"}
            return {"position": wide_target if stage == "event" else self._ball_near_player(wide_target), "owner_player_id": None, "state": "missed"}
        if viewer_type is MatchViewerEventType.OFFSIDE:
            return {"position": event_target if stage != "pre" else self._ball_near_player(primary_pos or event_target), "owner_player_id": primary, "state": "stopped"}
        if viewer_type in {MatchViewerEventType.RED_CARD, MatchViewerEventType.HALFTIME, MatchViewerEventType.FULLTIME}:
            return {"position": self._ball_near_player(primary_pos or positions.get(default_owner) or {"x": 50.0, "y": 50.0}), "owner_player_id": primary or default_owner, "state": "stopped"}
        if viewer_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE, MatchViewerEventType.ATTACK}:
            if stage == "pre":
                return {"position": self._ball_near_player(primary_pos or event_target), "owner_player_id": primary or default_owner, "state": "controlled"}
            if stage == "event":
                return {"position": event_target, "owner_player_id": None, "state": "traveling"}
        owner = primary or default_owner
        return {
            "position": self._ball_near_player(positions.get(owner) or event_target),
            "owner_player_id": owner,
            "state": "rolling",
        }

    def _viewer_event_type_from_match_event(self, event: MatchEventView) -> MatchViewerEventType:
        mapping = {
            MatchEventType.KICKOFF: MatchViewerEventType.KICKOFF,
            MatchEventType.GOAL: MatchViewerEventType.GOAL,
            MatchEventType.PENALTY_SCORED: MatchViewerEventType.GOAL,
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

    def _lead_seconds(self, event_type: MatchViewerEventType) -> float:
        if event_type in {MatchViewerEventType.GOAL, MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.RED_CARD, MatchViewerEventType.OFFSIDE}:
            return 2.2
        if event_type in {MatchViewerEventType.PENALTY, MatchViewerEventType.SET_PIECE}:
            return 1.8
        return 1.1

    def _settle_seconds(self, event_type: MatchViewerEventType) -> float:
        if event_type is MatchViewerEventType.GOAL:
            return 2.4
        if event_type in {MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.RED_CARD}:
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
        if event_type in {MatchViewerEventType.SAVE, MatchViewerEventType.MISS, MatchViewerEventType.OFFSIDE, MatchViewerEventType.PENALTY}:
            return 2
        return 1

    def _optional_text(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _fraction(self, seed: str) -> float:
        digest = md5(seed.encode("utf-8")).hexdigest()[:8]
        return int(digest, 16) / 0xFFFFFFFF

    def _clamp(self, value: float) -> float:
        return max(0.0, min(100.0, round(value, 2)))

    def _lerp(self, start: float, end: float, t: float) -> float:
        return self._clamp(start + ((end - start) * t))
