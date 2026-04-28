from __future__ import annotations

from app.schemas.match_viewer import (
    MatchMode,
    MatchTimelineFrameView,
    MatchViewerBallFrameView,
    MatchViewerEventType,
    MatchViewerEventView,
    MatchViewerPhase,
    MatchViewerPlaybackStage,
    MatchViewerPlayerFrameView,
    MatchViewerPointView,
    MatchViewerVector2View,
    MatchViewStateView,
)

_PRESENTATION_ONLY_FLAG = "presentation_only"
_SYNTHETIC_CINEMATIC_FLAG = "synthetic_cinematic"
_MODE_WINDOWS = {
    MatchMode.QUICK: (180, 300),
    MatchMode.STANDARD: (420, 600),
    MatchMode.CINEMATIC: (600, 900),
}
_BUILDUP_TYPES = {
    MatchViewerEventType.ATTACK,
    MatchViewerEventType.PASS,
    MatchViewerEventType.GOAL,
    MatchViewerEventType.MISS,
    MatchViewerEventType.PENALTY,
    MatchViewerEventType.SAVE,
    MatchViewerEventType.SET_PIECE,
}
_MISS_ELIGIBLE_TYPES = {
    MatchViewerEventType.ATTACK,
    MatchViewerEventType.PASS,
    MatchViewerEventType.GOAL,
    MatchViewerEventType.PENALTY,
    MatchViewerEventType.SET_PIECE,
}
_QUICK_POST_TYPES = {
    MatchViewerEventType.FULLTIME,
    MatchViewerEventType.GOAL,
    MatchViewerEventType.HALFTIME,
    MatchViewerEventType.RED_CARD,
}
_QUICK_PRE_TYPES = {
    MatchViewerEventType.FULLTIME,
    MatchViewerEventType.GOAL,
    MatchViewerEventType.HALFTIME,
    MatchViewerEventType.KICKOFF,
}


class MatchViewerScalingService:
    def transform(
        self,
        view_state: MatchViewStateView,
        mode: MatchMode = MatchMode.STANDARD,
    ) -> MatchViewStateView:
        authoritative_events = [event for event in view_state.events if not self._is_presentation_only(event)]
        event_ids = {event.event_id for event in authoritative_events}
        base_frames = [
            frame for frame in view_state.frames if frame.active_event_id is None or frame.active_event_id in event_ids
        ]
        base_duration = self._base_duration(view_state)
        target_duration = self._target_duration(authoritative_events, frame_count=len(base_frames), mode=mode)
        scaled_events = self._scale_authoritative_events(
            authoritative_events,
            base_duration=base_duration,
            target_duration=target_duration,
            mode=mode,
        )
        events = (
            scaled_events
            if mode is not MatchMode.CINEMATIC
            else self._with_cinematic_events(scaled_events, target_duration)
        )
        event_lookup = {event.event_id: event for event in events}
        frames = self._scale_frames(
            base_frames,
            match_id=view_state.match_id,
            base_duration=base_duration,
            target_duration=target_duration,
            mode=mode,
            event_lookup=event_lookup,
        )
        if mode is MatchMode.CINEMATIC:
            frames = self._with_cinematic_frames(
                frames,
                events=events,
                target_duration=target_duration,
                match_id=view_state.match_id,
            )
        frames = self._normalize_frames(
            frames,
            match_id=view_state.match_id,
            target_duration=target_duration,
            event_lookup=event_lookup,
        )
        return view_state.model_copy(
            update={
                "match_mode": mode,
                "duration_seconds": target_duration,
                "events": events,
                "frames": frames,
            }
        )

    def _base_duration(self, view_state: MatchViewStateView) -> float:
        maxima = [float(max(1, view_state.duration_seconds))]
        if view_state.events:
            maxima.append(max(event.time_seconds for event in view_state.events))
        if view_state.frames:
            maxima.append(max(frame.time_seconds for frame in view_state.frames))
        return max(maxima)

    def _target_duration(
        self,
        events: list[MatchViewerEventView],
        *,
        frame_count: int,
        mode: MatchMode,
    ) -> int:
        minimum, maximum = _MODE_WINDOWS[mode]
        richness = self._richness_score(events, frame_count)
        normalized = min(1.0, max(0.0, (richness - 6.0) / 10.0))
        return int(round(minimum + ((maximum - minimum) * normalized)))

    def _richness_score(self, events: list[MatchViewerEventView], frame_count: int) -> float:
        score = min(frame_count / 80.0, 1.0)
        weights = {
            MatchViewerEventType.KICKOFF: 0.1,
            MatchViewerEventType.GOAL: 1.4,
            MatchViewerEventType.SAVE: 1.1,
            MatchViewerEventType.MISS: 1.1,
            MatchViewerEventType.FOUL: 0.7,
            MatchViewerEventType.OFFSIDE: 0.8,
            MatchViewerEventType.RED_CARD: 1.2,
            MatchViewerEventType.YELLOW_CARD: 0.6,
            MatchViewerEventType.SUBSTITUTION: 0.55,
            MatchViewerEventType.INJURY: 0.75,
            MatchViewerEventType.HALFTIME: 0.15,
            MatchViewerEventType.FULLTIME: 0.15,
            MatchViewerEventType.ATTACK: 0.85,
            MatchViewerEventType.PASS: 0.5,
            MatchViewerEventType.SET_PIECE: 0.95,
            MatchViewerEventType.PENALTY: 1.15,
            MatchViewerEventType.NEUTRAL: 0.45,
        }
        for event in events:
            score += 0.2 + weights.get(event.event_type, 0.5) + (max(0, event.emphasis_level - 1) * 0.15)
        return score

    def _scale_authoritative_events(
        self,
        events: list[MatchViewerEventView],
        *,
        base_duration: float,
        target_duration: int,
        mode: MatchMode,
    ) -> list[MatchViewerEventView]:
        minimum_gap = {
            MatchMode.QUICK: 0.35,
            MatchMode.STANDARD: 0.45,
            MatchMode.CINEMATIC: 0.6,
        }[mode]
        scaled: list[MatchViewerEventView] = []
        previous_time = -minimum_gap
        for index, event in enumerate(events):
            if event.event_type is MatchViewerEventType.KICKOFF:
                time_seconds = 0.0
            elif event.event_type is MatchViewerEventType.FULLTIME:
                time_seconds = float(target_duration)
            else:
                time_seconds = self._scaled_time(event.time_seconds, base_duration, target_duration)
            if time_seconds <= previous_time:
                time_seconds = round(previous_time + minimum_gap, 2)
            if index == len(events) - 1:
                time_seconds = min(float(target_duration), time_seconds)
            scaled.append(event.model_copy(update={"time_seconds": round(time_seconds, 2)}))
            previous_time = scaled[-1].time_seconds
        return scaled

    def _with_cinematic_events(
        self,
        events: list[MatchViewerEventView],
        target_duration: int,
    ) -> list[MatchViewerEventView]:
        extras: list[MatchViewerEventView] = []
        attack_limit = max(2, min(6, len(events) // 3 + 2))
        miss_limit = max(1, min(4, len(events) // 4 + 1))
        attack_count = 0
        miss_count = 0
        for index, event in enumerate(events):
            if index == 0:
                continue
            previous = events[index - 1]
            gap_before = max(0.0, event.time_seconds - previous.time_seconds)
            if gap_before < 14.0:
                continue
            minute = self._interpolated_minute(
                previous, event, event.time_seconds - min(max(gap_before * 0.45, 7.0), 18.0)
            )
            team_name = event.team_name or "Match"
            if attack_count < attack_limit and event.event_type in _BUILDUP_TYPES:
                attack_time = max(
                    previous.time_seconds + 3.0, event.time_seconds - min(max(gap_before * 0.45, 7.0), 18.0)
                )
                if attack_time < event.time_seconds - 2.0:
                    extras.append(
                        MatchViewerEventView(
                            event_id=f"{event.event_id}:presentation:attack",
                            sequence=event.sequence,
                            event_type=MatchViewerEventType.ATTACK,
                            minute=minute,
                            added_time=0,
                            clock_label=f"{minute}'",
                            time_seconds=round(attack_time, 2),
                            team_id=event.team_id,
                            team_name=event.team_name,
                            primary_player_id=event.primary_player_id,
                            primary_player_name=event.primary_player_name,
                            secondary_player_id=event.secondary_player_id,
                            secondary_player_name=event.secondary_player_name,
                            home_score=previous.home_score,
                            away_score=previous.away_score,
                            banner_text=f"{team_name} build-up",
                            commentary=f"{team_name} slow the tempo, recycle possession, and build pressure.",
                            emphasis_level=max(1, min(2, event.emphasis_level)),
                            highlighted_player_ids=list(event.highlighted_player_ids),
                            flags=[_PRESENTATION_ONLY_FLAG, _SYNTHETIC_CINEMATIC_FLAG],
                            playback_profile="buildup",
                        )
                    )
                    attack_count += 1
            if (
                miss_count < miss_limit
                and event.event_type in _MISS_ELIGIBLE_TYPES
                and gap_before > 28.0
                and not self._has_real_miss_between(events, previous.time_seconds, event.time_seconds)
            ):
                miss_time = max(
                    previous.time_seconds + 6.0, event.time_seconds - min(max(gap_before * 0.22, 4.0), 10.0)
                )
                if miss_time < event.time_seconds - 1.5:
                    miss_minute = self._interpolated_minute(previous, event, miss_time)
                    extras.append(
                        MatchViewerEventView(
                            event_id=f"{event.event_id}:presentation:miss",
                            sequence=event.sequence,
                            event_type=MatchViewerEventType.MISS,
                            minute=miss_minute,
                            added_time=0,
                            clock_label=f"{miss_minute}'",
                            time_seconds=round(miss_time, 2),
                            team_id=event.team_id,
                            team_name=event.team_name,
                            primary_player_id=event.primary_player_id,
                            primary_player_name=event.primary_player_name,
                            secondary_player_id=event.secondary_player_id,
                            secondary_player_name=event.secondary_player_name,
                            home_score=previous.home_score,
                            away_score=previous.away_score,
                            banner_text=f"{team_name} chance goes wide",
                            commentary=f"{team_name} open the defense, but the final effort drifts away from goal.",
                            emphasis_level=2,
                            highlighted_player_ids=list(event.highlighted_player_ids),
                            flags=[_PRESENTATION_ONLY_FLAG, _SYNTHETIC_CINEMATIC_FLAG],
                            playback_profile="miss",
                            miss_variant="wide",
                        )
                    )
                    miss_count += 1
        ordered = [*events, *extras]
        ordered.sort(key=lambda item: (item.time_seconds, item.sequence, item.event_id))
        capped: list[MatchViewerEventView] = []
        previous_time = -0.35
        for event in ordered:
            time_seconds = min(float(target_duration), max(0.0, event.time_seconds))
            if time_seconds <= previous_time:
                time_seconds = round(previous_time + 0.35, 2)
            capped.append(event.model_copy(update={"time_seconds": round(time_seconds, 2)}))
            previous_time = capped[-1].time_seconds
        return capped

    def _has_real_miss_between(self, events: list[MatchViewerEventView], start: float, end: float) -> bool:
        return any(
            event.event_type is MatchViewerEventType.MISS
            and not self._is_presentation_only(event)
            and start < event.time_seconds < end
            for event in events
        )

    def _interpolated_minute(
        self,
        previous: MatchViewerEventView,
        event: MatchViewerEventView,
        time_seconds: float,
    ) -> int:
        span = max(0.01, event.time_seconds - previous.time_seconds)
        ratio = min(1.0, max(0.0, (time_seconds - previous.time_seconds) / span))
        return max(0, min(120, int(round(previous.minute + ((event.minute - previous.minute) * ratio)))))

    def _scale_frames(
        self,
        frames: list[MatchTimelineFrameView],
        *,
        match_id: str,
        base_duration: float,
        target_duration: int,
        mode: MatchMode,
        event_lookup: dict[str, MatchViewerEventView],
    ) -> list[MatchTimelineFrameView]:
        scaled: list[MatchTimelineFrameView] = []
        for frame in frames:
            if mode is MatchMode.QUICK and not self._keep_quick_frame(frame, event_lookup):
                continue
            active_event_id = frame.active_event_id if frame.active_event_id in event_lookup else None
            time_seconds = self._scaled_time(frame.time_seconds, base_duration, target_duration)
            stage = self._frame_stage(frame)
            scaled.append(
                frame.model_copy(
                    update={
                        "frame_id": self._frame_id(match_id, time_seconds, stage),
                        "time_seconds": round(time_seconds, 2),
                        "active_event_id": active_event_id,
                        "event_banner": frame.event_banner if active_event_id is not None else None,
                        "stage": stage,
                    }
                )
            )
        return scaled

    def _keep_quick_frame(
        self,
        frame: MatchTimelineFrameView,
        event_lookup: dict[str, MatchViewerEventView],
    ) -> bool:
        stage = self._frame_stage(frame)
        if stage in {MatchViewerPlaybackStage.EVENT, MatchViewerPlaybackStage.RESET}:
            return True
        event = event_lookup.get(frame.active_event_id or "")
        if stage is MatchViewerPlaybackStage.POST:
            return event is not None and event.event_type in _QUICK_POST_TYPES
        if stage is MatchViewerPlaybackStage.PRE:
            return event is not None and event.event_type in _QUICK_PRE_TYPES
        return False

    def _with_cinematic_frames(
        self,
        frames: list[MatchTimelineFrameView],
        *,
        events: list[MatchViewerEventView],
        target_duration: int,
        match_id: str,
    ) -> list[MatchTimelineFrameView]:
        if not frames:
            return frames
        extras: list[MatchTimelineFrameView] = []
        event_lookup = {event.event_id: event for event in events}
        for index in range(len(frames) - 1):
            left = frames[index]
            right = frames[index + 1]
            gap = right.time_seconds - left.time_seconds
            if gap < 3.0:
                continue
            split_points = (0.5,) if gap < 6.0 else (0.35, 0.68)
            active_event = event_lookup.get(right.active_event_id or left.active_event_id or "")
            for t in split_points:
                time_seconds = round(left.time_seconds + (gap * t), 2)
                stage = MatchViewerPlaybackStage.HOLD if active_event is not None else self._frame_stage(right)
                extras.append(
                    self._interpolate_frame(
                        left,
                        right,
                        match_id=match_id,
                        time_seconds=time_seconds,
                        t=t,
                        active_event=active_event,
                        stage=stage,
                        home_score=active_event.home_score if active_event is not None else None,
                        away_score=active_event.away_score if active_event is not None else None,
                    )
                )
        for event in events:
            if not self._is_presentation_only(event):
                continue
            left, right, t = self._frame_window(frames, event.time_seconds)
            base_frame = self._interpolate_frame(
                left,
                right,
                match_id=match_id,
                time_seconds=event.time_seconds,
                t=t,
                active_event=event,
                stage=MatchViewerPlaybackStage.EVENT,
                home_score=event.home_score,
                away_score=event.away_score,
            )
            extras.append(base_frame)
            linger_time = min(float(target_duration), round(event.time_seconds + 1.8, 2))
            if linger_time + 0.4 < self._next_frame_time(frames, event.time_seconds):
                extras.append(
                    base_frame.model_copy(
                        update={
                            "frame_id": self._frame_id(match_id, linger_time, MatchViewerPlaybackStage.POST),
                            "time_seconds": linger_time,
                            "stage": MatchViewerPlaybackStage.POST,
                        }
                    )
                )
        return [*frames, *extras]

    def _frame_window(
        self,
        frames: list[MatchTimelineFrameView],
        time_seconds: float,
    ) -> tuple[MatchTimelineFrameView, MatchTimelineFrameView, float]:
        if len(frames) == 1 or time_seconds <= frames[0].time_seconds:
            return frames[0], frames[0], 0.0
        for index in range(len(frames) - 1):
            left = frames[index]
            right = frames[index + 1]
            if time_seconds <= right.time_seconds:
                span = max(0.01, right.time_seconds - left.time_seconds)
                return left, right, min(1.0, max(0.0, (time_seconds - left.time_seconds) / span))
        return frames[-1], frames[-1], 0.0

    def _next_frame_time(self, frames: list[MatchTimelineFrameView], after: float) -> float:
        for frame in frames:
            if frame.time_seconds > after:
                return frame.time_seconds
        return float("inf")

    def _interpolate_frame(
        self,
        left: MatchTimelineFrameView,
        right: MatchTimelineFrameView,
        *,
        match_id: str,
        time_seconds: float,
        t: float,
        active_event: MatchViewerEventView | None,
        stage: MatchViewerPlaybackStage,
        home_score: int | None,
        away_score: int | None,
    ) -> MatchTimelineFrameView:
        blend_left = t < 0.5
        phase = (
            self._phase_for_event(active_event.event_type)
            if active_event is not None
            else (left.phase if blend_left else right.phase)
        )
        return MatchTimelineFrameView(
            frame_id=self._frame_id(match_id, time_seconds, stage),
            time_seconds=round(time_seconds, 2),
            clock_minute=round(left.clock_minute + ((right.clock_minute - left.clock_minute) * t), 2),
            phase=phase,
            home_score=(
                left.home_score
                if home_score is None and blend_left
                else (right.home_score if home_score is None else home_score)
            ),
            away_score=(
                left.away_score
                if away_score is None and blend_left
                else (right.away_score if away_score is None else away_score)
            ),
            home_attacks_right=left.home_attacks_right if blend_left else right.home_attacks_right,
            possession_side=left.possession_side if blend_left else right.possession_side,
            active_event_id=(
                active_event.event_id
                if active_event is not None
                else (left.active_event_id if blend_left else right.active_event_id)
            ),
            event_banner=(
                active_event.banner_text
                if active_event is not None
                else (left.event_banner if blend_left else right.event_banner)
            ),
            stage=stage,
            camera_preset=left.camera_preset if blend_left else right.camera_preset,
            overlay_text=left.overlay_text if blend_left else right.overlay_text,
            pause_playback=left.pause_playback if blend_left else right.pause_playback,
            playback_rate=left.playback_rate if blend_left else right.playback_rate,
            flag_animation=left.flag_animation if blend_left else right.flag_animation,
            celebration_team_id=left.celebration_team_id if blend_left else right.celebration_team_id,
            possession_phase=left.possession_phase if blend_left else right.possession_phase,
            transition_state=left.transition_state if blend_left else right.transition_state,
            danger_zone=left.danger_zone if blend_left else right.danger_zone,
            pressure_index=round(left.pressure_index + ((right.pressure_index - left.pressure_index) * t), 3),
            compactness_home=round(left.compactness_home + ((right.compactness_home - left.compactness_home) * t), 3),
            compactness_away=round(left.compactness_away + ((right.compactness_away - left.compactness_away) * t), 3),
            frame_tags=list(left.frame_tags if blend_left else right.frame_tags),
            players=self._interpolated_players(left.players, right.players, t),
            ball=self._interpolated_ball(left.ball, right.ball, t),
        )

    def _interpolated_players(
        self,
        left_players: list[MatchViewerPlayerFrameView],
        right_players: list[MatchViewerPlayerFrameView],
        t: float,
    ) -> list[MatchViewerPlayerFrameView]:
        left_by_id = {player.player_id: player for player in left_players}
        right_by_id = {player.player_id: player for player in right_players}
        ordered_ids = [
            *[player.player_id for player in left_players],
            *[player.player_id for player in right_players if player.player_id not in left_by_id],
        ]
        players: list[MatchViewerPlayerFrameView] = []
        for player_id in ordered_ids:
            left = left_by_id.get(player_id)
            right = right_by_id.get(player_id)
            if left is None and right is not None:
                players.append(right)
                continue
            if right is None and left is not None:
                players.append(left)
                continue
            if left is None or right is None:
                continue
            blend_left = t < 0.5
            players.append(
                MatchViewerPlayerFrameView(
                    player_id=left.player_id,
                    team_id=left.team_id,
                    side=left.side if blend_left else right.side,
                    shirt_number=left.shirt_number if blend_left else right.shirt_number,
                    label=left.label if blend_left else right.label,
                    role=left.role if blend_left else right.role,
                    line=left.line if blend_left else right.line,
                    state=left.state if blend_left else right.state,
                    active=left.active if blend_left else right.active,
                    highlighted=left.highlighted if blend_left else right.highlighted,
                    position=self._lerp_point(left.position, right.position, t),
                    anchor_position=self._lerp_point(left.anchor_position, right.anchor_position, t),
                    animation_state=left.animation_state if blend_left else right.animation_state,
                    speed_ratio=round(left.speed_ratio + ((right.speed_ratio - left.speed_ratio) * t), 3),
                    blend_factor=round(left.blend_factor + ((right.blend_factor - left.blend_factor) * t), 3),
                    stamina_pct=round(left.stamina_pct + ((right.stamina_pct - left.stamina_pct) * t), 1),
                    has_possession=left.has_possession if blend_left else right.has_possession,
                    facing=self._lerp_vector2(left.facing, right.facing, t),
                    velocity=self._lerp_vector2(left.velocity, right.velocity, t),
                )
            )
        return players

    def _interpolated_ball(
        self,
        left: MatchViewerBallFrameView,
        right: MatchViewerBallFrameView,
        t: float,
    ) -> MatchViewerBallFrameView:
        return MatchViewerBallFrameView(
            position=self._lerp_point(left.position, right.position, t),
            height=round(left.height + ((right.height - left.height) * t), 3),
            owner_player_id=left.owner_player_id if t < 0.5 else right.owner_player_id,
            state=left.state if t < 0.5 else right.state,
            spin=self._lerp_vector(left.spin, right.spin, t),
            velocity=self._lerp_vector(left.velocity, right.velocity, t),
        )

    def _lerp_point(
        self,
        left: MatchViewerPointView,
        right: MatchViewerPointView,
        t: float,
    ) -> MatchViewerPointView:
        return MatchViewerPointView(
            x=round(left.x + ((right.x - left.x) * t), 3),
            y=round(left.y + ((right.y - left.y) * t), 3),
        )

    def _lerp_vector(self, left, right, t: float):
        if left is None and right is None:
            return None
        if left is None:
            return right
        if right is None:
            return left
        return left.__class__(
            x=round(left.x + ((right.x - left.x) * t), 3),
            y=round(left.y + ((right.y - left.y) * t), 3),
            z=round(left.z + ((right.z - left.z) * t), 3),
        )

    def _lerp_vector2(
        self,
        left: MatchViewerVector2View,
        right: MatchViewerVector2View,
        t: float,
    ) -> MatchViewerVector2View:
        return MatchViewerVector2View(
            x=round(left.x + ((right.x - left.x) * t), 3),
            y=round(left.y + ((right.y - left.y) * t), 3),
        )

    def _normalize_frames(
        self,
        frames: list[MatchTimelineFrameView],
        *,
        match_id: str,
        target_duration: int,
        event_lookup: dict[str, MatchViewerEventView],
    ) -> list[MatchTimelineFrameView]:
        if not frames:
            return frames
        ordered = sorted(frames, key=lambda item: (item.time_seconds, item.clock_minute, item.frame_id))
        normalized: list[MatchTimelineFrameView] = []
        for frame in ordered:
            time_seconds = min(float(target_duration), max(0.0, frame.time_seconds))
            if normalized and time_seconds <= normalized[-1].time_seconds:
                time_seconds = min(float(target_duration), round(normalized[-1].time_seconds + 0.05, 2))
            active_event_id = frame.active_event_id if frame.active_event_id in event_lookup else None
            stage = self._frame_stage(frame)
            normalized.append(
                frame.model_copy(
                    update={
                        "frame_id": self._frame_id(match_id, time_seconds, stage),
                        "time_seconds": round(time_seconds, 2),
                        "active_event_id": active_event_id,
                        "event_banner": frame.event_banner if active_event_id is not None else None,
                        "stage": stage,
                    }
                )
            )
        if normalized[0].time_seconds > 0.0:
            normalized.insert(
                0,
                normalized[0].model_copy(
                    update={
                        "frame_id": self._frame_id(match_id, 0.0, MatchViewerPlaybackStage.RESET),
                        "time_seconds": 0.0,
                        "stage": MatchViewerPlaybackStage.RESET,
                    }
                ),
            )
        last = normalized[-1]
        if last.time_seconds < target_duration:
            normalized.append(
                last.model_copy(
                    update={
                        "frame_id": self._frame_id(match_id, float(target_duration), MatchViewerPlaybackStage.POST),
                        "time_seconds": float(target_duration),
                        "phase": (
                            MatchViewerPhase.FULLTIME if last.phase is not MatchViewerPhase.FULLTIME else last.phase
                        ),
                        "stage": MatchViewerPlaybackStage.POST,
                    }
                )
            )
        elif last.time_seconds > target_duration:
            normalized[-1] = last.model_copy(
                update={
                    "frame_id": self._frame_id(match_id, float(target_duration), self._frame_stage(last)),
                    "time_seconds": float(target_duration),
                }
            )
        return normalized

    def _scaled_time(self, value: float, base_duration: float, target_duration: int) -> float:
        if base_duration <= 0:
            return 0.0
        return round(min(float(target_duration), max(0.0, (value / base_duration) * target_duration)), 2)

    def _frame_id(self, match_id: str, time_seconds: float, stage: MatchViewerPlaybackStage) -> str:
        return f"{match_id}:{int(round(time_seconds * 100))}:{stage.value}"

    def _frame_stage(self, frame: MatchTimelineFrameView) -> MatchViewerPlaybackStage:
        mapping = {
            "decision": MatchViewerPlaybackStage.DECISION,
            "event": MatchViewerPlaybackStage.EVENT,
            "hold": MatchViewerPlaybackStage.HOLD,
            "post": MatchViewerPlaybackStage.POST,
            "pre": MatchViewerPlaybackStage.PRE,
            "reset": MatchViewerPlaybackStage.RESET,
            "review": MatchViewerPlaybackStage.REVIEW,
        }
        suffix = frame.frame_id.rsplit(":", 1)[-1].strip().lower()
        return mapping.get(suffix, frame.stage)

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

    def _is_presentation_only(self, event: MatchViewerEventView) -> bool:
        return _PRESENTATION_ONLY_FLAG in event.flags


__all__ = ["MatchViewerScalingService"]
