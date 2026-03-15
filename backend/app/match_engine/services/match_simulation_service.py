from __future__ import annotations

from backend.app.match_engine.commentary.timeline import MatchCommentaryTimelineGenerator
from backend.app.match_engine.schemas import (
    MatchBadgeVisualView,
    MatchFinalSummaryView,
    MatchHighlightClipView,
    MatchInjuryReportView,
    MatchKitVisualView,
    MatchPlayerReferenceView,
    MatchPlayerStatsView,
    MatchPlayerVisualView,
    MatchReplayPayloadView,
    MatchSimulationRequest,
    MatchTeamStatsView,
    MatchTeamStrengthView,
    MatchTeamVisualIdentityView,
    MatchVisualIdentityView,
    PenaltyAttemptView,
    PenaltyShootoutView,
)
from backend.app.match_engine.services.replay_builder import ReplayEventLogBuilder
from backend.app.match_engine.services.experience_layers import (
    MatchControlLogBuilder,
    MatchHalftimeAnalyticsBuilder,
    MatchHighlightBuilder,
    MatchPresentationBuilder,
    MatchReplayContractBuilder,
    HighlightBundle,
)
from backend.app.match_engine.simulation.event_generator import MatchEventGenerator
from backend.app.match_engine.simulation.models import MatchEventType, SimulationResult


class MatchSimulationService:
    def __init__(
        self,
        *,
        event_generator: MatchEventGenerator | None = None,
        commentary_generator: MatchCommentaryTimelineGenerator | None = None,
        replay_builder: ReplayEventLogBuilder | None = None,
        highlight_builder: MatchHighlightBuilder | None = None,
        halftime_builder: MatchHalftimeAnalyticsBuilder | None = None,
        presentation_builder: MatchPresentationBuilder | None = None,
        replay_contract_builder: MatchReplayContractBuilder | None = None,
        control_log_builder: MatchControlLogBuilder | None = None,
    ) -> None:
        self.event_generator = event_generator or MatchEventGenerator()
        self.commentary_generator = commentary_generator or MatchCommentaryTimelineGenerator()
        self.replay_builder = replay_builder or ReplayEventLogBuilder()
        self.highlight_builder = highlight_builder or MatchHighlightBuilder()
        self.halftime_builder = halftime_builder or MatchHalftimeAnalyticsBuilder()
        self.presentation_builder = presentation_builder or MatchPresentationBuilder()
        self.replay_contract_builder = replay_contract_builder or MatchReplayContractBuilder()
        self.control_log_builder = control_log_builder or MatchControlLogBuilder()

    def build_replay_payload(self, request: MatchSimulationRequest) -> MatchReplayPayloadView:
        result = self.event_generator.simulate(request)
        timeline = self.commentary_generator.build(result)
        highlight_bundle = self.highlight_builder.build(result)
        halftime_analytics = self.halftime_builder.build(
            result,
            requested_duration_seconds=request.competition.halftime_duration_seconds,
        )
        spectator_package = self.presentation_builder.build_spectator_package(result)
        scene_contract = self.presentation_builder.build_scene_contract(result)
        broadcast_presentation = self.presentation_builder.build_broadcast_presentation(result)
        replay_download = self.replay_contract_builder.build_download_contract(result)
        sync_contract = self.replay_contract_builder.build_sync_contract(result)
        tactical_log = self.control_log_builder.build_tactical_log(result)
        substitution_log = self.control_log_builder.build_substitution_log(result)
        critical_snapshots = self.control_log_builder.build_critical_snapshots(result)
        summary = self._build_summary(
            result,
            presentation_duration_seconds=timeline.presentation_duration_seconds,
            highlight_bundle=highlight_bundle,
        )
        replay_log = self.replay_builder.build(result)
        return MatchReplayPayloadView(
            match_id=result.match_id,
            seed=result.seed,
            win_probability_home=summary.win_probability_home,
            win_probability_draw=summary.win_probability_draw,
            win_probability_away=summary.win_probability_away,
            expected_goals_home=summary.expected_goals_home,
            expected_goals_away=summary.expected_goals_away,
            key_highlights=summary.key_highlights,
            highlight_package=summary.highlight_package,
            highlight_profile=summary.highlight_profile,
            highlight_runtime_seconds=summary.highlight_runtime_seconds,
            highlight_access=summary.highlight_access,
            key_moments=highlight_bundle.key_moments,
            manager_influence_notes=summary.manager_influence_notes,
            injury_report=summary.injury_report,
            halftime_analytics=halftime_analytics,
            spectator_package=spectator_package,
            scene_assembly=scene_contract,
            broadcast_presentation=broadcast_presentation,
            replay_download=replay_download,
            sync_contract=sync_contract,
            tactical_change_log=tactical_log,
            substitution_log=substitution_log,
            critical_snapshots=critical_snapshots,
            visual_identity=self._build_visual_identity(result),
            status=result.status,
            summary=summary,
            timeline=timeline,
            replay_log=replay_log,
        )

    def build_timeline(self, request: MatchSimulationRequest):
        result = self.event_generator.simulate(request)
        return self.commentary_generator.build(result)

    def build_summary(self, request: MatchSimulationRequest) -> MatchFinalSummaryView:
        result = self.event_generator.simulate(request)
        timeline = self.commentary_generator.build(result)
        highlight_bundle = self.highlight_builder.build(result)
        return self._build_summary(
            result,
            presentation_duration_seconds=timeline.presentation_duration_seconds,
            highlight_bundle=highlight_bundle,
        )

    def _build_summary(
        self,
        result: SimulationResult,
        *,
        presentation_duration_seconds: int,
        highlight_bundle: HighlightBundle | None = None,
    ) -> MatchFinalSummaryView:
        home_prob, draw_prob, away_prob = self._probability_triplet(result)
        home_xg, away_xg = self._expected_goals(result)
        bundle = highlight_bundle or self.highlight_builder.build(result)
        return MatchFinalSummaryView(
            match_id=result.match_id,
            seed=result.seed,
            win_probability_home=home_prob,
            win_probability_draw=draw_prob,
            win_probability_away=away_prob,
            expected_goals_home=home_xg,
            expected_goals_away=away_xg,
            key_highlights=self._key_highlights(result),
            highlight_package=bundle.clips,
            highlight_profile=bundle.profile,
            highlight_runtime_seconds=bundle.runtime_seconds,
            highlight_access=bundle.access,
            manager_influence_notes=list(result.manager_influence_notes),
            injury_report=self._injury_report(result),
            upset_probability=result.upset_probability,
            upset_reason_codes=list(result.upset_reason_codes),
            home_advantage_note=result.home_advantage_note,
            manager_influence_score_home=round(result.home_stats.tactical_swings + (result.home_strength.coach_quality / 20.0), 2),
            manager_influence_score_away=round(result.away_stats.tactical_swings + (result.away_strength.coach_quality / 20.0), 2),
            tactical_battle_summary=result.tactical_battle_summary,
            form_motivation_summary=result.form_motivation_summary,
            momentum_swings=list(result.momentum_swings),
            turning_points=list(result.turning_points),
            key_matchups=list(result.key_matchups),
            tactical_impact_notes=list(result.tactical_impact_notes),
            status=result.status,
            competition_type=result.competition_type,
            stage=result.stage,
            is_final=result.is_final,
            requires_winner=result.requires_winner,
            winner_team_id=result.winner_team_id,
            winner_team_name=result.winner_team_name,
            home_score=result.home_score,
            away_score=result.away_score,
            decided_by_penalties=result.decided_by_penalties,
            home_penalty_score=result.home_penalty_score,
            away_penalty_score=result.away_penalty_score,
            upset=result.upset,
            presentation_duration_seconds=presentation_duration_seconds,
            summary_line=result.summary_line,
            home_stats=self._build_team_stats(result.home_stats, result.home_strength),
            away_stats=self._build_team_stats(result.away_stats, result.away_strength),
            player_stats=[
                MatchPlayerStatsView(
                    player_id=player.player_id,
                    player_name=player.player_name,
                    team_id=player.team_id,
                    team_name=player.team_name,
                    role=player.role,
                    started=player.started,
                    minutes_played=player.minutes_played,
                    goals=player.goals,
                    assists=player.assists,
                    saves=player.saves,
                    missed_chances=player.missed_chances,
                    yellow_cards=player.yellow_cards,
                    red_card=player.red_card,
                    injured=player.injured,
                    substituted_in_minute=player.substituted_in_minute,
                    substituted_out_minute=player.substituted_out_minute,
                )
                for player in result.player_stats
                if player.started or player.is_notable()
            ],
            shootout=self._build_shootout(result),
        )

    def _build_team_stats(self, team_stats, strength) -> MatchTeamStatsView:
        return MatchTeamStatsView(
            team_id=team_stats.team_id,
            team_name=team_stats.team_name,
            started_formation=team_stats.started_formation,
            current_formation=team_stats.current_formation,
            goals=team_stats.goals,
            shots=team_stats.shots,
            shots_on_target=team_stats.shots_on_target,
            saves=team_stats.saves,
            missed_chances=team_stats.missed_chances,
            yellow_cards=team_stats.yellow_cards,
            red_cards=team_stats.red_cards,
            injuries=team_stats.injuries,
            substitutions=team_stats.substitutions,
            possession=team_stats.possession,
            strength=MatchTeamStrengthView(
                overall=strength.overall,
                attack=strength.attack,
                midfield=strength.midfield,
                defense=strength.defense,
                goalkeeping=strength.goalkeeping,
                depth=strength.depth,
                discipline=strength.discipline,
                fitness=strength.fitness,
                chemistry=strength.chemistry,
                tactical_cohesion=strength.tactical_cohesion,
                recent_form=strength.recent_form,
                morale=strength.morale,
                motivation=strength.motivation,
                fatigue_load=strength.fatigue_load,
                coach_quality=strength.coach_quality,
                tactical_quality=strength.tactical_quality,
                adaptability=strength.adaptability,
                upset_resistance=strength.upset_resistance,
                upset_punch=strength.upset_punch,
            ),
            big_chances=team_stats.big_chances,
            woodwork=team_stats.woodwork,
            tactical_swings=team_stats.tactical_swings,
        )

    def _build_shootout(self, result: SimulationResult) -> PenaltyShootoutView | None:
        if result.shootout is None:
            return None
        return PenaltyShootoutView(
            winner_team_id=result.shootout.winner_team_id,
            winner_team_name=result.shootout.winner_team_name,
            home_penalties=result.shootout.home_penalties,
            away_penalties=result.shootout.away_penalties,
            attempts=[
                PenaltyAttemptView(
                    order=attempt.order,
                    team_id=attempt.team_id,
                    team_name=attempt.team_name,
                    taker=MatchPlayerReferenceView(player_id=attempt.taker_id, player_name=attempt.taker_name),
                    goalkeeper=(
                        MatchPlayerReferenceView(player_id=attempt.goalkeeper_id, player_name=attempt.goalkeeper_name)
                        if attempt.goalkeeper_id is not None and attempt.goalkeeper_name is not None
                        else None
                    ),
                    scored=attempt.scored,
                    home_penalties=attempt.home_penalties,
                    away_penalties=attempt.away_penalties,
                )
                for attempt in result.shootout.attempts
            ],
        )

    def _probability_triplet(self, result: SimulationResult) -> tuple[int, int, int]:
        home_edge = (
            (result.home_strength.overall + result.home_strength.depth * 0.12 + result.home_strength.fitness * 0.08)
            - (result.away_strength.overall + result.away_strength.depth * 0.12 + result.away_strength.fitness * 0.08)
        )
        draw_bias = 19 if abs(home_edge) <= 2.5 else 16 if abs(home_edge) <= 6 else 13
        home = max(14, min(76, int(round(44 + (home_edge * 0.78)))))
        away = max(12, min(72, int(round(37 - (home_edge * 0.72)))))
        draw = max(10, min(30, draw_bias))
        total = home + draw + away
        if total > 100:
            overflow = total - 100
            if home >= away:
                home -= overflow
            else:
                away -= overflow
        elif total < 100:
            draw += 100 - total
        return home, draw, away

    def _expected_goals(self, result: SimulationResult) -> tuple[float, float]:
        home_xg = round(
            max(
                0.35,
                (result.home_stats.shots_on_target * 0.24)
                + (result.home_strength.attack / 70.0)
                + (result.home_strength.midfield / 210.0)
                - (result.away_strength.defense / 240.0),
            ),
            2,
        )
        away_xg = round(
            max(
                0.30,
                (result.away_stats.shots_on_target * 0.24)
                + (result.away_strength.attack / 70.0)
                + (result.away_strength.midfield / 210.0)
                - (result.home_strength.defense / 240.0),
            ),
            2,
        )
        return home_xg, away_xg

    def _key_highlights(self, result: SimulationResult) -> list[str]:
        notable: list[str] = []
        for event in result.events:
            if event.event_type in {
                MatchEventType.GOAL,
                MatchEventType.PENALTY_GOAL,
                MatchEventType.PENALTY_SCORED,
                MatchEventType.PENALTY_MISSED,
                MatchEventType.RED_CARD,
                MatchEventType.INJURY,
                MatchEventType.SUBSTITUTION,
                MatchEventType.DOUBLE_SAVE,
                MatchEventType.GOALKEEPER_SAVE,
                MatchEventType.TACTICAL_SWING,
                MatchEventType.TACTICAL_CHANGE,
                MatchEventType.SUBSTITUTION_IMPACT,
                MatchEventType.WOODWORK,
                MatchEventType.MISSED_BIG_CHANCE,
            }:
                minute = f"{event.minute}+{event.added_time}" if event.added_time else str(event.minute)
                actor = event.primary_player_name or event.team_name or 'Match event'
                family = event.metadata.get("chance_family")
                suffix = f" - {family}" if isinstance(family, str) else ""
                notable.append(f"{minute}' {actor}: {event.event_type.value.replace('_', ' ')}{suffix}")
            if len(notable) >= 6:
                break
        if not notable:
            notable.append(result.summary_line)
        return notable

    def _highlight_package(self, result: SimulationResult) -> list[MatchHighlightClipView]:
        clips: list[MatchHighlightClipView] = []
        cursor = 0
        for event in result.events:
            if event.event_type not in {
                MatchEventType.GOAL,
                MatchEventType.PENALTY_GOAL,
                MatchEventType.RED_CARD,
                MatchEventType.INJURY,
                MatchEventType.SUBSTITUTION,
                MatchEventType.DOUBLE_SAVE,
                MatchEventType.TACTICAL_SWING,
                MatchEventType.WOODWORK,
            }:
                continue
            start_second = min(cursor, max(0, result.seed % 5 + event.minute * 2))
            duration = 24 if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.DOUBLE_SAVE} else 16
            title_actor = event.primary_player_name or event.team_name or 'Key moment'
            family = event.metadata.get("chance_family")
            suffix = f" - {family}" if isinstance(family, str) else ""
            clips.append(
                MatchHighlightClipView(
                    title=f"{title_actor} - {event.event_type.value.replace('_', ' ')}{suffix}",
                    start_second=start_second,
                    end_second=start_second + duration,
                    importance=5 if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL, MatchEventType.DOUBLE_SAVE} else 4,
                    event_type=event.event_type,
                    team_name=event.team_name,
                )
            )
            cursor += duration
            if cursor >= 280 or len(clips) >= 10:
                break
        if not clips:
            clips.append(
                MatchHighlightClipView(
                    title='Match story package',
                    start_second=0,
                    end_second=min(180, max(90, result.home_score + result.away_score + 120)),
                    importance=3,
                    event_type=MatchEventType.KICKOFF,
                    team_name=None,
                )
            )
        return clips

    def _injury_report(self, result: SimulationResult) -> list[MatchInjuryReportView]:
        reports: list[MatchInjuryReportView] = []
        for event in result.events:
            if event.event_type is not MatchEventType.INJURY:
                continue
            reports.append(
                MatchInjuryReportView(
                    minute=event.minute,
                    team_name=event.team_name or 'Unknown team',
                    player_name=event.primary_player_name or 'Unknown player',
                    severity='high' if event.minute < 35 else 'medium' if event.minute < 70 else 'monitor',
                    tactical_impact='Forced shape change and bench response.' if event.minute < 70 else 'Late disruption to the closing phase.',
                )
            )
        return reports[:4]

    def _build_visual_identity(self, result: SimulationResult) -> MatchVisualIdentityView:
        def map_team(team) -> MatchTeamVisualIdentityView:
            return MatchTeamVisualIdentityView(
                team_id=team.team_id,
                team_name=team.team_name,
                short_club_code=team.short_club_code,
                badge=MatchBadgeVisualView(
                    badge_url=team.badge.badge_url,
                    shape=team.badge.shape,
                    initials=team.badge.initials,
                    primary_color=team.badge.primary_color,
                    secondary_color=team.badge.secondary_color,
                    accent_color=team.badge.accent_color,
                ),
                selected_kit=MatchKitVisualView(
                    kit_type=team.selected_kit.kit_type,
                    primary_color=team.selected_kit.primary_color,
                    secondary_color=team.selected_kit.secondary_color,
                    accent_color=team.selected_kit.accent_color,
                    shorts_color=team.selected_kit.shorts_color,
                    socks_color=team.selected_kit.socks_color,
                    pattern_type=team.selected_kit.pattern_type,
                    collar_style=team.selected_kit.collar_style,
                    sleeve_style=team.selected_kit.sleeve_style,
                    badge_placement=team.selected_kit.badge_placement,
                    front_text=team.selected_kit.front_text,
                ),
                alternate_kit=MatchKitVisualView(
                    kit_type=team.alternate_kit.kit_type,
                    primary_color=team.alternate_kit.primary_color,
                    secondary_color=team.alternate_kit.secondary_color,
                    accent_color=team.alternate_kit.accent_color,
                    shorts_color=team.alternate_kit.shorts_color,
                    socks_color=team.alternate_kit.socks_color,
                    pattern_type=team.alternate_kit.pattern_type,
                    collar_style=team.alternate_kit.collar_style,
                    sleeve_style=team.alternate_kit.sleeve_style,
                    badge_placement=team.alternate_kit.badge_placement,
                    front_text=team.alternate_kit.front_text,
                ),
                third_kit=(
                    MatchKitVisualView(
                        kit_type=team.third_kit.kit_type,
                        primary_color=team.third_kit.primary_color,
                        secondary_color=team.third_kit.secondary_color,
                        accent_color=team.third_kit.accent_color,
                        shorts_color=team.third_kit.shorts_color,
                        socks_color=team.third_kit.socks_color,
                        pattern_type=team.third_kit.pattern_type,
                        collar_style=team.third_kit.collar_style,
                        sleeve_style=team.third_kit.sleeve_style,
                        badge_placement=team.third_kit.badge_placement,
                        front_text=team.third_kit.front_text,
                    )
                    if team.third_kit is not None
                    else None
                ),
                goalkeeper_kit=MatchKitVisualView(
                    kit_type=team.goalkeeper_kit.kit_type,
                    primary_color=team.goalkeeper_kit.primary_color,
                    secondary_color=team.goalkeeper_kit.secondary_color,
                    accent_color=team.goalkeeper_kit.accent_color,
                    shorts_color=team.goalkeeper_kit.shorts_color,
                    socks_color=team.goalkeeper_kit.socks_color,
                    pattern_type=team.goalkeeper_kit.pattern_type,
                    collar_style=team.goalkeeper_kit.collar_style,
                    sleeve_style=team.goalkeeper_kit.sleeve_style,
                    badge_placement=team.goalkeeper_kit.badge_placement,
                    front_text=team.goalkeeper_kit.front_text,
                ),
                player_visuals=[
                    MatchPlayerVisualView(
                        player_id=player.player_id,
                        display_name=player.display_name,
                        shirt_name=player.shirt_name,
                        shirt_number=player.shirt_number,
                        role=player.role,
                    )
                    for player in team.player_visuals
                ],
                clash_adjusted=team.clash_adjusted,
            )

        return MatchVisualIdentityView(
            home_team=map_team(result.visual_identity.home_team),
            away_team=map_team(result.visual_identity.away_team),
            clash_resolved=result.visual_identity.clash_resolved,
        )

