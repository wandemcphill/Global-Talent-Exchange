from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from random import Random
from typing import Any, Iterable

from app.config.competition_constants import (
    HALFTIME_ANALYSIS_MAX_SECONDS,
    HALFTIME_ANALYSIS_MIN_SECONDS,
    HIGHLIGHT_DEFAULT_EXPIRY_SECONDS,
)
from app.match_engine.services.player_rating_engine import PositionAwarePlayerRatingEngine
from app.match_engine.schemas import (
    MatchAnalyticsRatioView,
    MatchBroadcastPresentationView,
    MatchCommentaryCueView,
    MatchCriticalSnapshotView,
    MatchCrowdStateView,
    MatchEntityHeatmapView,
    MatchExperienceLayerView,
    MatchHalftimeAnalyticsView,
    MatchHeatmapView,
    MatchHighlightAccessView,
    MatchHighlightClipView,
    MatchKeyMomentView,
    MatchMotionDirectionView,
    MatchMotionPredictionView,
    MatchMomentumPointView,
    MatchMomentumTimelinePointView,
    MatchPossessionZonesView,
    MatchPassMapEdgeView,
    MatchPerformanceSyncView,
    MatchPostMatchAnalyticsView,
    MatchPlayerRatingView,
    MatchRenderPointView,
    MatchRenderSyncEventView,
    MatchRenderSyncPayloadView,
    MatchReplayDownloadContractView,
    MatchReplayPayloadView,
    MatchSceneAssemblyContractView,
    MatchSpectatorSyncView,
    MatchShotMapItemView,
    MatchSpectatorPackageView,
    MatchSubstitutionLogView,
    MatchTacticalChangeLogView,
    MatchThirdControlView,
    MatchXgTimelinePointView,
)
from app.match_engine.simulation.models import MatchEventType, MatchHighlightProfile, MatchSpectatorMode, SimulationResult


@dataclass(frozen=True, slots=True)
class HighlightBundle:
    clips: list[MatchHighlightClipView]
    profile: MatchHighlightProfile
    runtime_seconds: int
    access: MatchHighlightAccessView
    key_moments: list[MatchKeyMomentView]


class MatchKeyMomentSelector:
    def select(self, result: SimulationResult, *, max_moments: int = 8) -> list[MatchKeyMomentView]:
        candidates = [event for event in result.events if event.event_type in _KEY_MOMENT_TYPES]
        if not candidates:
            candidates = list(result.events)[:2]
        scored = sorted(candidates, key=_key_moment_score, reverse=True)
        picked = sorted(scored[:max_moments], key=lambda event: (event.minute, event.sequence))
        moments: list[MatchKeyMomentView] = []
        cursor = 0
        for event in picked:
            duration = 18 if event.event_type in _TOP_MOMENT_TYPES else 12
            start_second = cursor
            end_second = cursor + duration
            cursor = end_second + 2
            moments.append(
                MatchKeyMomentView(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    start_second=start_second,
                    end_second=end_second,
                    importance=int(event.metadata.get("importance", 3)),
                    team_name=event.team_name,
                )
            )
        return moments


class MatchHighlightBuilder:
    def __init__(self, *, key_moment_selector: MatchKeyMomentSelector | None = None) -> None:
        self.key_moment_selector = key_moment_selector or MatchKeyMomentSelector()

    def build(self, result: SimulationResult) -> HighlightBundle:
        profile = _resolve_highlight_profile(result)
        rng = Random(result.seed + 77)
        target_min, target_max = _highlight_target_range(profile)
        target_duration = rng.randint(target_min, target_max)
        clips = self._build_clips(result, target_duration, profile)
        runtime = max(0, clips[-1].end_second if clips else 0)
        access = MatchHighlightAccessView(
            expires_after_seconds=None if _is_archive_mode(result) else HIGHLIGHT_DEFAULT_EXPIRY_SECONDS,
            archive_mode=_is_archive_mode(result),
            watermark_required=True,
            signed_url_required=True,
            audit_log_required=True,
            rate_limit_per_minute=6,
            policy_checks=["entitlement", "download_policy", "geo", "age_rating"],
        )
        return HighlightBundle(
            clips=clips,
            profile=profile,
            runtime_seconds=runtime,
            access=access,
            key_moments=self.key_moment_selector.select(result),
        )

    @staticmethod
    def _select_candidates(
        candidates: list,
        target_duration: int,
        profile: MatchHighlightProfile,
    ) -> list:
        """Pick which moments make the package, then restore chronological order.

        The clip loop below fills a fixed second budget and stops once it is spent. When
        candidates were fed in purely chronological order, a busy match spent that budget
        on early, low-importance moments and silently dropped the decisive ones — a
        90th-minute winner could be cut while a routine first-half save survived.

        Selection is therefore importance-first (goals and red cards before saves and
        substitutions, later moments before earlier ones at equal weight), and the chosen
        set is re-sorted by minute so playback still runs in match order.
        """
        budget = max(0, target_duration)
        if profile is MatchHighlightProfile.ELITE_FINAL:
            # Walkout and trophy bookends consume part of the budget.
            budget = max(0, budget - 60)

        ranked = sorted(
            candidates,
            key=lambda event: (
                -_highlight_weight(event),
                -int(event.metadata.get("importance", 3)),
                -event.minute,
                event.sequence,
            ),
        )

        chosen: list = []
        spent = 0
        for event in ranked:
            duration = _clip_duration_for_event(event.event_type) + 2
            if chosen and spent + duration > budget:
                continue
            chosen.append(event)
            spent += duration
        if not chosen:
            chosen = ranked[:1]
        return sorted(chosen, key=lambda event: (event.minute, event.sequence))

    def _build_clips(self, result: SimulationResult, target_duration: int, profile: MatchHighlightProfile) -> list[MatchHighlightClipView]:
        candidates = [event for event in result.events if event.event_type in _HIGHLIGHT_EVENT_TYPES]
        if not candidates:
            return [
                MatchHighlightClipView(
                    title="Match story package",
                    start_second=0,
                    end_second=max(90, min(target_duration, 240)),
                    importance=3,
                    event_type=MatchEventType.KICKOFF,
                )
            ]
        candidates = self._select_candidates(candidates, target_duration, profile)
        clips: list[MatchHighlightClipView] = []
        cursor = 0
        if profile is MatchHighlightProfile.ELITE_FINAL:
            clips.append(
                MatchHighlightClipView(
                    title="Final walkout and lineup",
                    start_second=cursor,
                    end_second=cursor + 30,
                    importance=3,
                    event_type=MatchEventType.KICKOFF,
                )
            )
            cursor = clips[-1].end_second + 2
        for event in candidates:
            duration = _clip_duration_for_event(event.event_type)
            if cursor + duration > target_duration and len(clips) >= 2:
                break
            start_second = cursor
            end_second = min(start_second + duration, target_duration)
            clips.append(
                MatchHighlightClipView(
                    title=_clip_title(event),
                    start_second=start_second,
                    end_second=end_second,
                    importance=int(event.metadata.get("importance", 3)),
                    event_type=event.event_type,
                    event_id=event.event_id,
                    team_name=event.team_name,
                )
            )
            cursor = end_second + 2
            if cursor >= target_duration:
                break
        if profile is MatchHighlightProfile.ELITE_FINAL and cursor < target_duration:
            clips.append(
                MatchHighlightClipView(
                    title="Trophy and medal presentation",
                    start_second=cursor,
                    end_second=min(target_duration, cursor + 28),
                    importance=3,
                    event_type=MatchEventType.FULLTIME,
                )
            )
            cursor = clips[-1].end_second + 2
        if clips and clips[-1].end_second < target_duration:
            clips.append(
                MatchHighlightClipView(
                    title="Match story package",
                    start_second=clips[-1].end_second,
                    end_second=target_duration,
                    importance=2,
                    event_type=MatchEventType.FULLTIME,
                )
            )
        return clips


class MatchHalftimeAnalyticsBuilder:
    def __init__(self, *, rating_engine: PositionAwarePlayerRatingEngine | None = None) -> None:
        self.rating_engine = rating_engine or PositionAwarePlayerRatingEngine()

    def build(self, result: SimulationResult, *, requested_duration_seconds: int | None = None) -> MatchHalftimeAnalyticsView:
        duration = self._resolve_duration(result, requested_duration_seconds)
        first_half_events = [event for event in result.events if event.minute <= 45]
        home_shots = sum(1 for event in first_half_events if event.team_id == result.home_team_id and event.event_type is MatchEventType.SHOT)
        away_shots = sum(1 for event in first_half_events if event.team_id == result.away_team_id and event.event_type is MatchEventType.SHOT)
        home_on_target = sum(
            1
            for event in first_half_events
            if event.team_id == result.home_team_id
            and event.event_type
            in {
                MatchEventType.SHOT_ON_TARGET,
                MatchEventType.GOAL,
                MatchEventType.GOALKEEPER_SAVE,
                MatchEventType.DOUBLE_SAVE,
                MatchEventType.PENALTY_SCORED,
                MatchEventType.PENALTY_MISSED,
            }
        )
        away_on_target = sum(
            1
            for event in first_half_events
            if event.team_id == result.away_team_id
            and event.event_type
            in {
                MatchEventType.SHOT_ON_TARGET,
                MatchEventType.GOAL,
                MatchEventType.GOALKEEPER_SAVE,
                MatchEventType.DOUBLE_SAVE,
                MatchEventType.PENALTY_SCORED,
                MatchEventType.PENALTY_MISSED,
            }
        )
        home_xg = round(_sum_xg(first_half_events, result.home_team_id), 2)
        away_xg = round(_sum_xg(first_half_events, result.away_team_id), 2)
        home_possession = _clamp_int(50 + (home_shots - away_shots) * 2 + int(result.home_strength.midfield - result.away_strength.midfield) // 2, 35, 65)
        away_possession = 100 - home_possession
        home_heatmap, away_heatmap = _heatmaps(result)
        home_pass_map, away_pass_map = _pass_maps(result)
        ratings = self.rating_engine.rate(result, events=first_half_events, limit=6)
        momentum_graph = _momentum_graph(first_half_events)
        cards_incidents = _cards_incidents(first_half_events)
        tactical_suggestions = _tactical_suggestions(result, home_possession, away_possession, home_shots, away_shots)
        key_stats = [
            f"Shots: {result.home_team_name} {home_shots}-{away_shots} {result.away_team_name}",
            f"On target: {home_on_target}-{away_on_target}",
            f"xG: {home_xg:.2f}-{away_xg:.2f}",
            f"Possession: {home_possession}% to {away_possession}%",
        ]
        tactical_insights = [
            f"{result.home_team_name} are controlling the ball better." if home_possession >= away_possession else f"{result.away_team_name} are controlling the ball better.",
            f"The midfield battle is leaning toward {result.home_team_name}." if result.home_strength.midfield >= result.away_strength.midfield else f"The midfield battle is leaning toward {result.away_team_name}.",
        ]
        return MatchHalftimeAnalyticsView(
            duration_seconds=duration,
            home_possession=home_possession,
            away_possession=away_possession,
            home_shots=home_shots,
            away_shots=away_shots,
            home_shots_on_target=home_on_target,
            away_shots_on_target=away_on_target,
            expected_goals_home=home_xg,
            expected_goals_away=away_xg,
            home_heatmap=home_heatmap,
            away_heatmap=away_heatmap,
            home_pass_map=home_pass_map,
            away_pass_map=away_pass_map,
            player_ratings=ratings,
            home_stamina=round(100 - result.home_strength.fatigue_load, 1),
            away_stamina=round(100 - result.away_strength.fatigue_load, 1),
            home_formation=result.home_stats.current_formation,
            away_formation=result.away_stats.current_formation,
            momentum_graph=momentum_graph,
            cards_incidents=cards_incidents,
            tactical_suggestions=tactical_suggestions,
            key_stats=key_stats,
            tactical_insights=tactical_insights,
            standout_players=ratings[:3],
        )

    def _resolve_duration(self, result: SimulationResult, requested_duration_seconds: int | None) -> int:
        if requested_duration_seconds is not None:
            return max(HALFTIME_ANALYSIS_MIN_SECONDS, min(HALFTIME_ANALYSIS_MAX_SECONDS, requested_duration_seconds))
        base = HALFTIME_ANALYSIS_MIN_SECONDS + min(40, len(result.events))
        if result.is_final:
            base += 10
        return max(HALFTIME_ANALYSIS_MIN_SECONDS, min(HALFTIME_ANALYSIS_MAX_SECONDS, base))


class MatchPresentationBuilder:
    def build_scene_contract(self, result: SimulationResult) -> MatchSceneAssemblyContractView:
        elite = _is_elite_presentation(result)
        scenes = ["walkout", "lineup", "replay_angles", "crowd_atmosphere"]
        if elite:
            scenes.extend(["trophy_presentation", "medal_presentation", "branded_backdrop"])
        return MatchSceneAssemblyContractView(
            scene_version="v2",
            enabled_scenes=scenes,
            replay_angle_set="elite" if elite else "standard",
            crowd_profile="finals" if elite else result.atmosphere_profile,
            branded_backdrop=elite,
            event_render_mode="event_driven",
            transition_style="blended_interpolation",
            camera_modes=["broadcast", "attack_zoom", "goal_camera"],
            replay_buffer_events=12,
            special_moment_effects=True,
            motion_runtime="onnx_runtime_blend_inference",
            commentary_runtime="llm_template_tts_stack",
            crowd_reactivity="event_weighted_pressure_feedback",
            spectator_sync_mode="deterministic_playback",
        )

    def build_broadcast_presentation(self, result: SimulationResult) -> MatchBroadcastPresentationView:
        elite = _is_elite_presentation(result)
        return MatchBroadcastPresentationView(
            overlay_style="gtex_final" if elite else "gtex_clean",
            scoreboard_style="premium" if elite else "compact",
            commentary_style="tactical",
            finals_package=elite,
            atmosphere_profile="elite" if elite else result.atmosphere_profile,
            live_stream_transport="websocket",
            async_match_mode="summary_only",
            tts_enabled=True,
            commentary_languages=["en", "fr"] if elite else ["en"],
            commentator_roles=["lead", "analyst", "banter"] if elite else ["lead", "analyst"],
        )

    def build_spectator_package(self, result: SimulationResult) -> MatchSpectatorPackageView:
        return MatchSpectatorPackageView(
            modes=[MatchSpectatorMode.FREE_2D_COMMENTARY, MatchSpectatorMode.PAID_LIVE_KEY_MOMENT_VIDEO],
            free_mode=MatchSpectatorMode.FREE_2D_COMMENTARY,
            paid_mode=MatchSpectatorMode.PAID_LIVE_KEY_MOMENT_VIDEO,
            can_pause=False,
            continuous_stream_available=True,
            key_moment_delivery="tick_batch",
            sync_strategy="deterministic_playback",
            watch_party_enabled=True,
            reactions_enabled=True,
            chat_enabled=True,
            replay_sync_enabled=True,
        )


class MatchReplayContractBuilder:
    def build_download_contract(self, result: SimulationResult) -> MatchReplayDownloadContractView:
        policy_checks = ["entitlement", "download_policy", "geo", "age_rating"]
        if _is_archive_mode(result):
            policy_checks.append("archive_access")
        return MatchReplayDownloadContractView(
            signed_url_required=True,
            watermark_required=True,
            audit_log_required=True,
            rate_limit_per_minute=6,
            policy_checks=policy_checks,
            signed_url_hook="replay.sign_url",
            watermark_hook="replay.apply_watermark",
            audit_log_hook="replay.audit_log",
        )

    def build_sync_contract(self, result: SimulationResult) -> MatchPerformanceSyncView:
        elite = _is_elite_presentation(result)
        return MatchPerformanceSyncView(
            tick_rate_hz=24 if elite else 20,
            max_latency_ms=280 if elite else 320,
            checkpoint_interval_seconds=12 if elite else 15,
            deterministic_seed=result.seed,
        )


class MatchRenderSyncBuilder:
    def build(self, replay_payload: MatchReplayPayloadView) -> MatchRenderSyncPayloadView:
        sync_contract = replay_payload.sync_contract or MatchPerformanceSyncView(deterministic_seed=replay_payload.seed)
        home_team_id = replay_payload.summary.home_stats.team_id
        away_team_id = replay_payload.summary.away_stats.team_id
        last_tick = -1
        events: list[MatchRenderSyncEventView] = []

        for event in replay_payload.timeline.events:
            render = _dict_value(event.metadata.get("render"))
            origin = _point_value(render.get("origin"))
            target = _point_value(render.get("target"), fallback=origin)
            actors = _dict_value(render.get("actors"))
            camera = _dict_value(render.get("camera"))
            ball = _dict_value(render.get("ball"))
            replay = _dict_value(render.get("replay"))
            team_side = _team_side_for_event(
                event,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                fallback=actors.get("team_side"),
            )
            tick = max(last_tick + 1, int(round(event.presentation_second * sync_contract.tick_rate_hz)))
            last_tick = tick
            meta: dict[str, Any] = {
                "render_type": render.get("type"),
                "chance_family": event.metadata.get("chance_family"),
                "importance": int(event.metadata.get("importance", 1) or 1),
                "pressure_level": event.metadata.get("pressure_level"),
                "build_up_pattern": event.metadata.get("build_up_pattern"),
                "xg": float(event.metadata.get("xg", event.metadata.get("chance_quality", 0.0)) or 0.0),
                "camera_mode": camera.get("mode"),
                "camera_blend": camera.get("blend"),
                "camera_slow_motion": bool(camera.get("slow_motion", False)),
                "camera_freeze_frame": bool(camera.get("freeze_frame", False)),
                "camera_shake": bool(camera.get("shake", False)),
                "ball_motion": ball.get("motion"),
                "ball_height": float(ball.get("height", 0.0) or 0.0),
                "ball_speed": float(ball.get("speed", 0.0) or 0.0),
                "replay_eligible": bool(replay.get("eligible", False)),
                "replay_speed": float(replay.get("speed", 0.0) or 0.0),
                "reviewable": bool(event.metadata.get("reviewable", False)),
                "review_decision": event.metadata.get("review_decision"),
                "score_commit": event.metadata.get("score_commit"),
                "commentary": event.commentary,
                "clock_label": event.clock_label,
            }
            if meta["ball_speed"] > 0:
                meta["shot_power"] = round(meta["ball_speed"], 2)
            if origin.y != target.y:
                meta["curve"] = round(abs(target.y - origin.y) / 100.0, 2)

            events.append(
                MatchRenderSyncEventView(
                    match_id=replay_payload.match_id,
                    event_id=event.event_id,
                    tick=tick,
                    minute=event.minute,
                    presentation_second=event.presentation_second,
                    event_type=event.event_type.value.upper(),
                    team=team_side,
                    team_id=home_team_id if team_side == "home" else away_team_id if team_side == "away" else event.team_id,
                    player_id=_actor_player_id(event=event, team_side=team_side, home_team_id=home_team_id, away_team_id=away_team_id),
                    secondary_player_id=_secondary_actor_id(event=event, team_side=team_side, home_team_id=home_team_id, away_team_id=away_team_id),
                    position=origin,
                    target_position=target,
                    meta=meta,
                    experience=_experience_layer_for_event(
                        replay_payload=replay_payload,
                        event=event,
                        tick=tick,
                        origin=origin,
                        target=target,
                        meta=meta,
                    ),
                )
            )

        return MatchRenderSyncPayloadView(
            match_id=replay_payload.match_id,
            seed=replay_payload.seed,
            tick_rate_hz=sync_contract.tick_rate_hz,
            max_latency_ms=sync_contract.max_latency_ms,
            deterministic=True,
            events=events,
        )


class MatchPostMatchAnalyticsBuilder:
    _SHOT_MAP_TYPES = {
        MatchEventType.SHOT,
        MatchEventType.SHOT_ON_TARGET,
        MatchEventType.MISSED_CHANCE,
        MatchEventType.MISSED_BIG_CHANCE,
        MatchEventType.GOAL,
        MatchEventType.GOALKEEPER_SAVE,
        MatchEventType.DOUBLE_SAVE,
        MatchEventType.WOODWORK,
        MatchEventType.PENALTY_SCORED,
        MatchEventType.PENALTY_MISSED,
    }

    _ON_TARGET_TYPES = {
        MatchEventType.SHOT_ON_TARGET,
        MatchEventType.GOAL,
        MatchEventType.GOALKEEPER_SAVE,
        MatchEventType.DOUBLE_SAVE,
        MatchEventType.PENALTY_SCORED,
        MatchEventType.PENALTY_MISSED,
    }

    def build(self, replay_payload: MatchReplayPayloadView) -> MatchPostMatchAnalyticsView:
        home_team_id = replay_payload.summary.home_stats.team_id
        away_team_id = replay_payload.summary.away_stats.team_id
        home_team_name = replay_payload.summary.home_stats.team_name
        away_team_name = replay_payload.summary.away_stats.team_name

        shot_map: list[MatchShotMapItemView] = []
        home_heatmap = [0] * 9
        away_heatmap = [0] * 9
        player_heatmaps: dict[tuple[str, str, str, str], list[int]] = defaultdict(lambda: [0] * 9)
        thirds = {
            "home": {"defensive": 0, "midfield": 0, "attacking": 0},
            "away": {"defensive": 0, "midfield": 0, "attacking": 0},
        }
        xg_home = 0.0
        xg_away = 0.0
        xg_timeline: list[MatchXgTimelinePointView] = []
        momentum_timeline: list[MatchMomentumTimelinePointView] = []

        for event in replay_payload.timeline.events:
            render = _dict_value(event.metadata.get("render"))
            origin = _point_value(render.get("origin"))
            camera = _dict_value(render.get("camera"))
            team_side = _team_side_for_event(
                event,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                fallback=_dict_value(render.get("actors")).get("team_side"),
            )
            if team_side not in {"home", "away"}:
                continue

            zone_index = _zone_index(origin)
            if team_side == "home":
                home_heatmap[zone_index] += 1
            else:
                away_heatmap[zone_index] += 1
            thirds[team_side][_attacking_third_label(origin.x, attacks_right=_attacks_right(render, team_side=team_side, minute=event.minute))] += 1

            actor_id = _actor_player_id(
                event=event,
                team_side=team_side,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            )
            actor_name = _actor_player_name(
                event=event,
                team_side=team_side,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            )
            if actor_id and actor_name:
                team_id = home_team_id if team_side == "home" else away_team_id
                team_name = home_team_name if team_side == "home" else away_team_name
                player_heatmaps[(actor_id, actor_name, team_id, team_name)][zone_index] += 1

            if event.event_type in self._SHOT_MAP_TYPES:
                team_id = home_team_id if team_side == "home" else away_team_id
                team_name = home_team_name if team_side == "home" else away_team_name
                xg = float(event.metadata.get("xg", event.metadata.get("chance_quality", 0.0)) or 0.0)
                if team_side == "home":
                    xg_home += xg
                else:
                    xg_away += xg
                shot_map.append(
                    MatchShotMapItemView(
                        event_id=event.event_id,
                        minute=event.minute,
                        team_id=team_id,
                        team_name=team_name,
                        player_id=actor_id,
                        player_name=actor_name,
                        x=origin.x,
                        y=origin.y,
                        xg=round(xg, 2),
                        goal=event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_SCORED},
                        on_target=event.event_type in self._ON_TARGET_TYPES,
                        replay_angle=str(camera.get("mode")) if camera.get("mode") is not None else None,
                    )
                )
                xg_timeline.append(
                    MatchXgTimelinePointView(
                        minute=event.minute,
                        home_xg=round(xg_home, 2),
                        away_xg=round(xg_away, 2),
                    )
                )

            swing = float(event.metadata.get("momentum_swing", 0.0) or 0.0)
            if swing > 0:
                momentum_timeline.append(
                    MatchMomentumTimelinePointView(
                        minute=event.minute,
                        home_pressure=round(swing, 2) if team_side == "home" else 0.0,
                        away_pressure=round(swing, 2) if team_side == "away" else 0.0,
                    )
                )

        team_heatmaps = [
            MatchEntityHeatmapView(
                entity_id=home_team_id,
                entity_name=home_team_name,
                team_id=home_team_id,
                team_name=home_team_name,
                zones=home_heatmap,
            ),
            MatchEntityHeatmapView(
                entity_id=away_team_id,
                entity_name=away_team_name,
                team_id=away_team_id,
                team_name=away_team_name,
                zones=away_heatmap,
            ),
        ]
        player_heatmap_views = [
            MatchEntityHeatmapView(
                entity_id=entity_id,
                entity_name=entity_name,
                team_id=team_id,
                team_name=team_name,
                zones=zones,
            )
            for (entity_id, entity_name, team_id, team_name), zones in sorted(
                player_heatmaps.items(),
                key=lambda item: (sum(item[1]), item[0][3], item[0][1]),
                reverse=True,
            )[:14]
        ]

        return MatchPostMatchAnalyticsView(
            match_id=replay_payload.match_id,
            seed=replay_payload.seed,
            score=f"{replay_payload.summary.home_score}-{replay_payload.summary.away_score}",
            xg=MatchAnalyticsRatioView(
                home=round(replay_payload.summary.expected_goals_home, 2),
                away=round(replay_payload.summary.expected_goals_away, 2),
            ),
            shots=MatchAnalyticsRatioView(
                home=float(replay_payload.summary.home_stats.shots),
                away=float(replay_payload.summary.away_stats.shots),
            ),
            shots_on_target=MatchAnalyticsRatioView(
                home=float(replay_payload.summary.home_stats.shots_on_target),
                away=float(replay_payload.summary.away_stats.shots_on_target),
            ),
            possession=MatchAnalyticsRatioView(
                home=float(replay_payload.summary.home_stats.possession),
                away=float(replay_payload.summary.away_stats.possession),
            ),
            possession_zones=MatchPossessionZonesView(
                home=MatchThirdControlView(**thirds["home"]),
                away=MatchThirdControlView(**thirds["away"]),
            ),
            shot_map=shot_map,
            team_heatmaps=team_heatmaps,
            player_heatmaps=player_heatmap_views,
            xg_timeline=_compact_xg_timeline(xg_timeline),
            momentum_timeline=_compact_momentum_timeline(momentum_timeline),
            tactical_changes=list(replay_payload.tactical_change_log),
            substitutions=list(replay_payload.substitution_log),
            summary_line=replay_payload.summary.summary_line,
        )


class MatchControlLogBuilder:
    def build_tactical_log(self, result: SimulationResult) -> list[MatchTacticalChangeLogView]:
        logs: list[MatchTacticalChangeLogView] = []
        for event in result.events:
            if event.event_type is not MatchEventType.TACTICAL_CHANGE:
                continue
            logs.append(
                MatchTacticalChangeLogView(
                    change_id=str(event.metadata.get("change_id", event.event_id)),
                    team_id=event.team_id or "",
                    team_name=event.team_name,
                    requested_minute=int(event.metadata.get("requested_minute", event.minute)),
                    requested_second=int(event.metadata.get("requested_second", 0)),
                    applied_minute=event.minute,
                    applied_second=0,
                    change_type="tactical_adjustment",
                    urgency=str(event.metadata.get("urgency", "normal")),
                    changes=dict(event.metadata.get("adjustments", {})),
                )
            )
        return logs

    def build_substitution_log(self, result: SimulationResult) -> list[MatchSubstitutionLogView]:
        logs: list[MatchSubstitutionLogView] = []
        for event in result.events:
            if event.event_type is not MatchEventType.SUBSTITUTION:
                continue
            logs.append(
                MatchSubstitutionLogView(
                    team_id=event.team_id or "",
                    team_name=event.team_name,
                    outgoing_player_id=event.secondary_player_id or "",
                    incoming_player_id=event.primary_player_id or "",
                    requested_minute=int(event.metadata.get("requested_minute", event.minute)),
                    applied_minute=event.minute,
                    reason=str(event.metadata.get("reason", "")) or None,
                    urgency=str(event.metadata.get("urgency", "")) or None,
                )
            )
        return logs

    def build_critical_snapshots(self, result: SimulationResult) -> list[MatchCriticalSnapshotView]:
        snapshots: list[MatchCriticalSnapshotView] = []
        for event in result.events:
            if event.event_type not in _CRITICAL_SNAPSHOT_TYPES:
                continue
            snapshots.append(
                MatchCriticalSnapshotView(
                    minute=event.minute,
                    event_type=event.event_type,
                    home_score=event.home_score,
                    away_score=event.away_score,
                    home_formation=str(event.metadata.get("home_formation", result.home_stats.current_formation)),
                    away_formation=str(event.metadata.get("away_formation", result.away_stats.current_formation)),
                    home_momentum=float(event.metadata.get("home_momentum", 0.0)),
                    away_momentum=float(event.metadata.get("away_momentum", 0.0)),
                )
            )
        return snapshots


def _dict_value(value: object | None) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _point_value(value: object | None, *, fallback: MatchRenderPointView | None = None) -> MatchRenderPointView:
    if isinstance(value, dict):
        return MatchRenderPointView(
            x=float(value.get("x", 50.0) or 50.0),
            y=float(value.get("y", 50.0) or 50.0),
        )
    return fallback or MatchRenderPointView(x=50.0, y=50.0)


def _team_side_for_event(event, *, home_team_id: str, away_team_id: str, fallback: object | None = None) -> str | None:
    if isinstance(fallback, str) and fallback in {"home", "away"}:
        return fallback
    if event.team_id == home_team_id:
        return "home"
    if event.team_id == away_team_id:
        return "away"
    if event.secondary_player is not None and event.event_type in {
        MatchEventType.GOALKEEPER_SAVE,
        MatchEventType.DOUBLE_SAVE,
        MatchEventType.PENALTY_MISSED,
    }:
        return "away" if event.team_id == home_team_id else "home" if event.team_id == away_team_id else None
    return None


def _actor_player_id(*, event, team_side: str | None, home_team_id: str, away_team_id: str) -> str | None:
    if team_side is None:
        return event.primary_player.player_id if event.primary_player is not None else None
    event_side = _team_side_for_event(event, home_team_id=home_team_id, away_team_id=away_team_id)
    if event_side == team_side:
        return event.primary_player.player_id if event.primary_player is not None else None
    return event.secondary_player.player_id if event.secondary_player is not None else event.primary_player.player_id if event.primary_player is not None else None


def _secondary_actor_id(*, event, team_side: str | None, home_team_id: str, away_team_id: str) -> str | None:
    if team_side is None:
        return event.secondary_player.player_id if event.secondary_player is not None else None
    event_side = _team_side_for_event(event, home_team_id=home_team_id, away_team_id=away_team_id)
    if event_side == team_side:
        return event.secondary_player.player_id if event.secondary_player is not None else None
    return event.primary_player.player_id if event.primary_player is not None else None


def _actor_player_name(*, event, team_side: str | None, home_team_id: str, away_team_id: str) -> str | None:
    if team_side is None:
        return event.primary_player.player_name if event.primary_player is not None else None
    event_side = _team_side_for_event(event, home_team_id=home_team_id, away_team_id=away_team_id)
    if event_side == team_side:
        return event.primary_player.player_name if event.primary_player is not None else None
    return event.secondary_player.player_name if event.secondary_player is not None else event.primary_player.player_name if event.primary_player is not None else None


def _zone_index(point: MatchRenderPointView) -> int:
    column = min(2, max(0, int(point.x // 33.34)))
    row = min(2, max(0, int(point.y // 33.34)))
    return (row * 3) + column


def _attacks_right(render: dict[str, Any], *, team_side: str, minute: int) -> bool:
    target = _point_value(render.get("target"))
    origin = _point_value(render.get("origin"))
    if target.x != origin.x:
        return target.x >= origin.x
    return team_side == ("home" if minute < 45 else "away")


def _attacking_third_label(x: float, *, attacks_right: bool) -> str:
    if attacks_right:
        if x < 33.34:
            return "defensive"
        if x < 66.67:
            return "midfield"
        return "attacking"
    if x > 66.67:
        return "defensive"
    if x > 33.34:
        return "midfield"
    return "attacking"


def _compact_xg_timeline(points: list[MatchXgTimelinePointView]) -> list[MatchXgTimelinePointView]:
    latest_by_minute: dict[int, MatchXgTimelinePointView] = {}
    for point in points:
        latest_by_minute[point.minute] = point
    return [latest_by_minute[minute] for minute in sorted(latest_by_minute)]


def _compact_momentum_timeline(points: list[MatchMomentumTimelinePointView]) -> list[MatchMomentumTimelinePointView]:
    accumulated: dict[int, dict[str, float]] = defaultdict(lambda: {"home": 0.0, "away": 0.0})
    for point in points:
        accumulated[point.minute]["home"] += point.home_pressure
        accumulated[point.minute]["away"] += point.away_pressure
    return [
        MatchMomentumTimelinePointView(
            minute=minute,
            home_pressure=round(payload["home"], 2),
            away_pressure=round(payload["away"], 2),
        )
        for minute, payload in sorted(accumulated.items())
    ]


_KEY_MOMENT_TYPES = {
    MatchEventType.GOAL,
    MatchEventType.PENALTY_GOAL,
    MatchEventType.PENALTY_MISS,
    MatchEventType.PENALTY_SCORED,
    MatchEventType.PENALTY_MISSED,
    MatchEventType.RED_CARD,
    MatchEventType.WOODWORK,
    MatchEventType.DOUBLE_SAVE,
    MatchEventType.GOALKEEPER_SAVE,
    MatchEventType.TACTICAL_CHANGE,
    MatchEventType.TACTICAL_SWING,
    MatchEventType.SUBSTITUTION_IMPACT,
    MatchEventType.MISSED_BIG_CHANCE,
}

_TOP_MOMENT_TYPES = {
    MatchEventType.GOAL,
    MatchEventType.PENALTY_GOAL,
    MatchEventType.PENALTY_SCORED,
    MatchEventType.RED_CARD,
    MatchEventType.WOODWORK,
    MatchEventType.DOUBLE_SAVE,
}

_HIGHLIGHT_EVENT_TYPES = {
    MatchEventType.GOAL,
    MatchEventType.PENALTY_GOAL,
    MatchEventType.PENALTY_MISS,
    MatchEventType.PENALTY_SCORED,
    MatchEventType.PENALTY_MISSED,
    MatchEventType.RED_CARD,
    MatchEventType.YELLOW_CARD,
    MatchEventType.INJURY,
    MatchEventType.WOODWORK,
    MatchEventType.DOUBLE_SAVE,
    MatchEventType.GOALKEEPER_SAVE,
    MatchEventType.TACTICAL_CHANGE,
    MatchEventType.TACTICAL_SWING,
    MatchEventType.SUBSTITUTION,
    MatchEventType.SUBSTITUTION_IMPACT,
    MatchEventType.MISSED_BIG_CHANCE,
}

#: Relative pull of each moment when the highlight budget cannot hold everything.
#: Higher wins. Goals and dismissals must never be displaced by filler.
_HIGHLIGHT_WEIGHTS: dict[MatchEventType, int] = {
    MatchEventType.GOAL: 100,
    MatchEventType.PENALTY_GOAL: 100,
    MatchEventType.PENALTY_SCORED: 100,
    MatchEventType.PENALTY_MISS: 90,
    MatchEventType.PENALTY_MISSED: 90,
    MatchEventType.RED_CARD: 80,
    MatchEventType.MISSED_BIG_CHANCE: 60,
    MatchEventType.WOODWORK: 55,
    MatchEventType.DOUBLE_SAVE: 50,
    MatchEventType.GOALKEEPER_SAVE: 40,
    MatchEventType.INJURY: 35,
    MatchEventType.TACTICAL_SWING: 30,
    MatchEventType.TACTICAL_CHANGE: 30,
    MatchEventType.SUBSTITUTION_IMPACT: 25,
    MatchEventType.YELLOW_CARD: 20,
    MatchEventType.SUBSTITUTION: 15,
}


def _highlight_weight(event) -> int:
    return _HIGHLIGHT_WEIGHTS.get(event.event_type, 10)


_CRITICAL_SNAPSHOT_TYPES = {
    MatchEventType.GOAL,
    MatchEventType.PENALTY_SCORED,
    MatchEventType.PENALTY_MISSED,
    MatchEventType.RED_CARD,
    MatchEventType.HALFTIME,
    MatchEventType.FULLTIME,
    MatchEventType.TACTICAL_CHANGE,
}


def _resolve_highlight_profile(result: SimulationResult) -> MatchHighlightProfile:
    if _is_elite_presentation(result):
        return MatchHighlightProfile.ELITE_FINAL
    total_goals = result.home_score + result.away_score
    red_cards = result.home_stats.red_cards + result.away_stats.red_cards
    penalties = any(
        event.event_type
        in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS, MatchEventType.PENALTY_SCORED, MatchEventType.PENALTY_MISSED}
        for event in result.events
    )
    lead_changes = _lead_change_count(result.events)
    if result.home_score == result.away_score and total_goals <= 1 and red_cards == 0 and not penalties:
        return MatchHighlightProfile.BORING_DRAW
    if total_goals >= 4 or red_cards >= 1 or penalties or lead_changes >= 2:
        return MatchHighlightProfile.HIGH_DRAMA
    return MatchHighlightProfile.NORMAL


def _highlight_target_range(profile: MatchHighlightProfile) -> tuple[int, int]:
    if profile is MatchHighlightProfile.BORING_DRAW:
        return 90, 180
    if profile is MatchHighlightProfile.HIGH_DRAMA:
        return 300, 390
    if profile is MatchHighlightProfile.ELITE_FINAL:
        return 420, 600
    return 180, 300


def _clip_duration_for_event(event_type: MatchEventType) -> int:
    if event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_SCORED}:
        return 28
    if event_type in {MatchEventType.RED_CARD, MatchEventType.WOODWORK, MatchEventType.DOUBLE_SAVE}:
        return 20
    if event_type in {MatchEventType.GOALKEEPER_SAVE, MatchEventType.PENALTY_MISSED}:
        return 18
    if event_type in {MatchEventType.TACTICAL_CHANGE, MatchEventType.TACTICAL_SWING, MatchEventType.SUBSTITUTION_IMPACT}:
        return 14
    if event_type in {MatchEventType.YELLOW_CARD, MatchEventType.SUBSTITUTION}:
        return 10
    return 16


def _clip_title(event) -> str:
    actor = event.primary_player_name or event.team_name or "Key moment"
    return f"{actor} - {event.event_type.value.replace('_', ' ')}"


def _key_moment_score(event) -> float:
    base = 1.0
    if event.event_type in _TOP_MOMENT_TYPES:
        base += 2.5
    if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_SCORED}:
        base += 1.5
    base += float(event.metadata.get("importance", 1)) * 0.4
    base += float(event.metadata.get("momentum_swing", 0.0)) * 0.15
    return base


def _sum_xg(events: Iterable, team_id: str) -> float:
    return sum(float(event.metadata.get("chance_quality", 0.0)) for event in events if event.team_id == team_id)


def _heatmaps(result: SimulationResult) -> tuple[MatchHeatmapView, MatchHeatmapView]:
    rng = Random(result.seed + 45)
    home = [rng.randint(10, 95) for _ in range(9)]
    away = [rng.randint(10, 95) for _ in range(9)]
    return MatchHeatmapView(zones=home), MatchHeatmapView(zones=away)


def _pass_maps(result: SimulationResult) -> tuple[list[MatchPassMapEdgeView], list[MatchPassMapEdgeView]]:
    rng = Random(result.seed + 61)
    home_map = [
        MatchPassMapEdgeView(source_zone=rng.randint(0, 8), target_zone=rng.randint(0, 8), count=rng.randint(4, 18))
        for _ in range(6)
    ]
    away_map = [
        MatchPassMapEdgeView(source_zone=rng.randint(0, 8), target_zone=rng.randint(0, 8), count=rng.randint(4, 18))
        for _ in range(6)
    ]
    return home_map, away_map


def _player_ratings(events: Iterable, result: SimulationResult) -> list[MatchPlayerRatingView]:
    return PositionAwarePlayerRatingEngine().rate(result, events=list(events), limit=6)


def _momentum_graph(events: Iterable) -> list[MatchMomentumPointView]:
    points: list[MatchMomentumPointView] = []
    for event in events:
        swing = float(event.metadata.get("momentum_swing", 0.0))
        if swing <= 0:
            continue
        points.append(MatchMomentumPointView(minute=event.minute, value=round(swing, 2)))
    return points[:6]


def _cards_incidents(events: Iterable) -> list[str]:
    incidents: list[str] = []
    for event in events:
        if event.event_type in {MatchEventType.YELLOW_CARD, MatchEventType.RED_CARD, MatchEventType.INJURY, MatchEventType.TACTICAL_FOUL}:
            label = event.event_type.value.replace("_", " ")
            name = event.primary_player_name or event.team_name or "Match"
            incidents.append(f"{event.minute}' {name} - {label}")
    return incidents[:6]


def _tactical_suggestions(
    result: SimulationResult,
    home_possession: int,
    away_possession: int,
    home_shots: int,
    away_shots: int,
) -> list[str]:
    suggestions: list[str] = []
    if result.home_score < result.away_score and home_shots < away_shots:
        suggestions.append("Home: raise tempo and add an extra runner between the lines.")
    if result.away_score < result.home_score and away_shots < home_shots:
        suggestions.append("Away: increase pressing and push the defensive line a step.")
    if home_possession < 45:
        suggestions.append("Home: tighten midfield spacing and slow the opposition build-up.")
    if away_possession < 45:
        suggestions.append("Away: compact the middle and look for direct transitions.")
    return suggestions[:4]


def _lead_change_count(events: Iterable) -> int:
    lead_changes = 0
    home = 0
    away = 0
    leader: str | None = None
    for event in events:
        if event.event_type not in {MatchEventType.GOAL, MatchEventType.PENALTY_SCORED}:
            continue
        home = event.home_score
        away = event.away_score
        current = "home" if home > away else "away" if away > home else None
        if current and leader and current != leader:
            lead_changes += 1
        leader = current
    return lead_changes


def _is_elite_presentation(result: SimulationResult) -> bool:
    stage = (result.stage or "").lower()
    return result.is_final or "elite" in stage or "final" in stage or "world" in stage


def _is_archive_mode(result: SimulationResult) -> bool:
    stage = (result.stage or "").lower()
    return result.is_final or "historic" in stage


def _experience_layer_for_event(
    *,
    replay_payload: MatchReplayPayloadView,
    event,
    tick: int,
    origin: MatchRenderPointView,
    target: MatchRenderPointView,
    meta: dict[str, Any],
) -> MatchExperienceLayerView:
    sync_contract = replay_payload.sync_contract or MatchPerformanceSyncView(deterministic_seed=replay_payload.seed)
    spectator_package = replay_payload.spectator_package or MatchSpectatorPackageView()
    return MatchExperienceLayerView(
        motion=_motion_prediction_for_event(event=event, origin=origin, target=target, meta=meta),
        commentary=_commentary_cue_for_event(event=event, meta=meta),
        crowd=_crowd_state_for_event(
            replay_payload=replay_payload,
            event=event,
            meta=meta,
        ),
        spectator_sync=MatchSpectatorSyncView(
            room_id=f"match_{replay_payload.match_id}",
            sync_strategy=spectator_package.sync_strategy,
            shared_clock_second=event.presentation_second,
            tick=tick,
            max_latency_ms=sync_contract.max_latency_ms,
            checkpoint_interval_seconds=sync_contract.checkpoint_interval_seconds,
            pause_replay_enabled=spectator_package.can_pause,
            reactions_enabled=spectator_package.reactions_enabled,
        ),
    )


def _motion_prediction_for_event(
    *,
    event,
    origin: MatchRenderPointView,
    target: MatchRenderPointView,
    meta: dict[str, Any],
) -> MatchMotionPredictionView:
    render_type = str(meta.get("render_type") or "").lower()
    event_type = event.event_type.value
    pressure = _pressure_value(event.metadata.get("pressure_level"))
    speed = _clamp_float(float(meta.get("ball_speed", 0.0) or 0.0) / 36.0, 0.0, 1.0)

    shoot_score = 0.72 if event_type in {"goal", "penalty_scored", "penalty_goal"} else 0.52 if render_type in {"goal", "shot"} else 0.10
    sprint_score = 0.22 + (pressure * 0.40) + (speed * 0.25)
    run_score = 0.30 + ((1.0 - pressure) * 0.18) + (0.10 if render_type in {"attack", "transition"} else 0.0)
    total = max(run_score + sprint_score + shoot_score, 0.0001)

    direction_x = float(target.x - origin.x)
    direction_y = float(target.y - origin.y)
    magnitude = max((direction_x**2 + direction_y**2) ** 0.5, 0.0001)

    return MatchMotionPredictionView(
        model_key="gtex_motion_blend_v1",
        run_weight=round(run_score / total, 3),
        sprint_weight=round(sprint_score / total, 3),
        shoot_weight=round(shoot_score / total, 3),
        direction=MatchMotionDirectionView(
            x=round(direction_x / magnitude, 3),
            y=round(direction_y / magnitude, 3),
        ),
        pressure=round(pressure, 3),
        ball_distance=round(abs(float(event.metadata.get("chance_quality", 0.0) or 0.0) - 0.5) * 30.0, 2),
        nearest_defender_distance=round(max(1.5, (1.0 - pressure) * 18.0), 2),
        fatigue_load=round(_float_value(event.metadata.get("fatigue_pressure"), default=0.0), 3),
        role_encoding=_role_encoding_for_event(event),
    )


def _commentary_cue_for_event(*, event, meta: dict[str, Any]) -> MatchCommentaryCueView:
    intensity = _clamp_float(((int(meta.get("importance", 1) or 1) - 1) / 4.0) + (0.25 if event.event_type in _TOP_MOMENT_TYPES else 0.0), 0.18, 1.0)
    return MatchCommentaryCueView(
        line=event.commentary,
        tone="hype" if event.event_type in _TOP_MOMENT_TYPES else "tactical",
        commentator="lead" if event.event_type in _TOP_MOMENT_TYPES else "analyst",
        language="en",
        intensity=round(intensity, 3),
        tts_ready=bool(event.commentary.strip()),
        banter_layer=event.secondary_player is not None and event.event_type in _TOP_MOMENT_TYPES,
        audio_channel="headline" if event.event_type in _TOP_MOMENT_TYPES else "match_bed",
    )


def _crowd_state_for_event(
    *,
    replay_payload: MatchReplayPayloadView,
    event,
    meta: dict[str, Any],
) -> MatchCrowdStateView:
    home = _clamp_float(float(event.metadata.get("crowd_home", replay_payload.home_crowd_intensity) or replay_payload.home_crowd_intensity), 0.0, 1.0)
    away = _clamp_float(float(event.metadata.get("crowd_away", replay_payload.away_crowd_intensity) or replay_payload.away_crowd_intensity), 0.0, 1.0)
    dominant_side = "home" if home >= away else "away"
    spike = event.event_type in _TOP_MOMENT_TYPES or bool(meta.get("camera_freeze_frame", False))
    return MatchCrowdStateView(
        profile=replay_payload.atmosphere_profile or "standard",
        home_intensity=round(home, 3),
        away_intensity=round(away, 3),
        dominant_side=dominant_side,
        chant_level=round(max(home, away), 3),
        hostility=round(_clamp_float(abs(home - away) + (0.12 if spike else 0.0), 0.0, 1.0), 3),
        spike=spike,
    )


def _role_encoding_for_event(event) -> str | None:
    metadata_role = event.metadata.get("outgoing_role") or event.metadata.get("role")
    if isinstance(metadata_role, str) and metadata_role.strip():
        return metadata_role.strip().lower()
    if event.primary_player is None:
        return None
    return "featured_actor"


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


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
