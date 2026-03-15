from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable

from backend.app.config.competition_constants import (
    HALFTIME_ANALYSIS_MAX_SECONDS,
    HALFTIME_ANALYSIS_MIN_SECONDS,
    HIGHLIGHT_DEFAULT_EXPIRY_SECONDS,
)
from backend.app.match_engine.schemas import (
    MatchBroadcastPresentationView,
    MatchCriticalSnapshotView,
    MatchHalftimeAnalyticsView,
    MatchHeatmapView,
    MatchHighlightAccessView,
    MatchHighlightClipView,
    MatchKeyMomentView,
    MatchMomentumPointView,
    MatchPassMapEdgeView,
    MatchPerformanceSyncView,
    MatchPlayerRatingView,
    MatchReplayDownloadContractView,
    MatchSceneAssemblyContractView,
    MatchSpectatorPackageView,
    MatchSubstitutionLogView,
    MatchTacticalChangeLogView,
)
from backend.app.match_engine.simulation.models import MatchEventType, MatchHighlightProfile, MatchSpectatorMode, SimulationResult


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
        candidates = sorted(candidates, key=lambda event: (event.minute, event.sequence))
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
        ratings = _player_ratings(first_half_events, result)
        momentum_graph = _momentum_graph(first_half_events)
        cards_incidents = _cards_incidents(first_half_events)
        tactical_suggestions = _tactical_suggestions(result, home_possession, away_possession, home_shots, away_shots)
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
            scene_version="v1",
            enabled_scenes=scenes,
            replay_angle_set="elite" if elite else "standard",
            crowd_profile="finals" if elite else "regular",
            branded_backdrop=elite,
        )

    def build_broadcast_presentation(self, result: SimulationResult) -> MatchBroadcastPresentationView:
        elite = _is_elite_presentation(result)
        return MatchBroadcastPresentationView(
            overlay_style="gtex_final" if elite else "gtex_clean",
            scoreboard_style="premium" if elite else "compact",
            commentary_style="tactical",
            finals_package=elite,
            atmosphere_profile="elite" if elite else "standard",
        )

    def build_spectator_package(self, result: SimulationResult) -> MatchSpectatorPackageView:
        return MatchSpectatorPackageView(
            modes=[MatchSpectatorMode.FREE_2D_COMMENTARY, MatchSpectatorMode.PAID_LIVE_KEY_MOMENT_VIDEO],
            free_mode=MatchSpectatorMode.FREE_2D_COMMENTARY,
            paid_mode=MatchSpectatorMode.PAID_LIVE_KEY_MOMENT_VIDEO,
            can_pause=False,
            continuous_stream_available=False,
            key_moment_delivery="event_triggered",
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
    MatchEventType.INJURY,
    MatchEventType.WOODWORK,
    MatchEventType.DOUBLE_SAVE,
    MatchEventType.GOALKEEPER_SAVE,
    MatchEventType.TACTICAL_CHANGE,
    MatchEventType.TACTICAL_SWING,
    MatchEventType.SUBSTITUTION_IMPACT,
    MatchEventType.MISSED_BIG_CHANCE,
}

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
    ratings: dict[str, float] = {}
    roster = {player.player_id: player for player in result.player_stats}
    for event in events:
        player_id = event.primary_player_id
        if not player_id or player_id not in roster:
            continue
        ratings.setdefault(player_id, 6.0)
        if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_SCORED}:
            ratings[player_id] += 0.8
        if event.event_type in {MatchEventType.MISSED_BIG_CHANCE, MatchEventType.PENALTY_MISSED}:
            ratings[player_id] -= 0.4
        if event.event_type in {MatchEventType.GOALKEEPER_SAVE, MatchEventType.DOUBLE_SAVE}:
            ratings[player_id] += 0.4
        if event.event_type is MatchEventType.YELLOW_CARD:
            ratings[player_id] -= 0.2
        if event.event_type is MatchEventType.RED_CARD:
            ratings[player_id] -= 1.0
    rated = sorted(ratings.items(), key=lambda item: item[1], reverse=True)[:6]
    views: list[MatchPlayerRatingView] = []
    for player_id, score in rated:
        player = roster[player_id]
        views.append(
            MatchPlayerRatingView(
                player_id=player.player_id,
                player_name=player.player_name,
                team_id=player.team_id,
                team_name=player.team_name,
                rating=round(max(4.0, min(9.8, score)), 2),
                summary=None,
            )
        )
    return views


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


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
