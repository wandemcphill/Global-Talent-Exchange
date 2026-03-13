from __future__ import annotations

from backend.app.match_engine.commentary.timeline import MatchCommentaryTimelineGenerator
from backend.app.match_engine.schemas import (
    MatchFinalSummaryView,
    MatchHighlightClipView,
    MatchInjuryReportView,
    MatchPlayerReferenceView,
    MatchPlayerStatsView,
    MatchReplayPayloadView,
    MatchSimulationRequest,
    MatchTeamStatsView,
    MatchTeamStrengthView,
    PenaltyAttemptView,
    PenaltyShootoutView,
)
from backend.app.match_engine.services.replay_builder import ReplayEventLogBuilder
from backend.app.match_engine.simulation.event_generator import MatchEventGenerator
from backend.app.match_engine.simulation.models import MatchEventType, SimulationResult


class MatchSimulationService:
    def __init__(
        self,
        *,
        event_generator: MatchEventGenerator | None = None,
        commentary_generator: MatchCommentaryTimelineGenerator | None = None,
        replay_builder: ReplayEventLogBuilder | None = None,
    ) -> None:
        self.event_generator = event_generator or MatchEventGenerator()
        self.commentary_generator = commentary_generator or MatchCommentaryTimelineGenerator()
        self.replay_builder = replay_builder or ReplayEventLogBuilder()

    def build_replay_payload(self, request: MatchSimulationRequest) -> MatchReplayPayloadView:
        result = self.event_generator.simulate(request)
        timeline = self.commentary_generator.build(result)
        summary = self._build_summary(result, presentation_duration_seconds=timeline.presentation_duration_seconds)
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
            manager_influence_notes=summary.manager_influence_notes,
            injury_report=summary.injury_report,
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
        return self._build_summary(result, presentation_duration_seconds=timeline.presentation_duration_seconds)

    def _build_summary(self, result: SimulationResult, *, presentation_duration_seconds: int) -> MatchFinalSummaryView:
        home_prob, draw_prob, away_prob = self._probability_triplet(result)
        home_xg, away_xg = self._expected_goals(result)
        return MatchFinalSummaryView(
            match_id=result.match_id,
            seed=result.seed,
            win_probability_home=home_prob,
            win_probability_draw=draw_prob,
            win_probability_away=away_prob,
            expected_goals_home=home_xg,
            expected_goals_away=away_xg,
            key_highlights=self._key_highlights(result),
            highlight_package=self._highlight_package(result),
            manager_influence_notes=self._manager_influence_notes(result),
            injury_report=self._injury_report(result),
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
            ),
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
                MatchEventType.RED_CARD,
                MatchEventType.INJURY,
                MatchEventType.SUBSTITUTION,
            }:
                minute = f"{event.minute}+{event.added_time}" if event.added_time else str(event.minute)
                actor = event.primary_player_name or event.team_name or 'Match event'
                notable.append(f"{minute}' {actor}: {event.event_type.value.replace('_', ' ')}")
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
            }:
                continue
            start_second = min(cursor, max(0, result.seed % 5 + event.minute * 2))
            duration = 24 if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL} else 16
            title_actor = event.primary_player_name or event.team_name or 'Key moment'
            clips.append(
                MatchHighlightClipView(
                    title=f"{title_actor} · {event.event_type.value.replace('_', ' ')}",
                    start_second=start_second,
                    end_second=start_second + duration,
                    importance=5 if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_GOAL} else 4,
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

    def _manager_influence_notes(self, result: SimulationResult) -> list[str]:
        notes: list[str] = []
        if result.home_strength.depth - result.away_strength.depth >= 6:
            notes.append(f"{result.home_team_name} carried the stronger bench depth, which helped sustain the tempo.")
        elif result.away_strength.depth - result.home_strength.depth >= 6:
            notes.append(f"{result.away_team_name} carried the stronger bench depth, which helped sustain the tempo.")
        if result.home_strength.fitness - result.away_strength.fitness >= 6:
            notes.append(f"{result.home_team_name} looked fresher in key phases and managed the game state better.")
        elif result.away_strength.fitness - result.home_strength.fitness >= 6:
            notes.append(f"{result.away_team_name} looked fresher in key phases and managed the game state better.")
        if result.home_strength.attack - result.away_strength.defense >= 8:
            notes.append(f"{result.home_team_name} found attacking lanes that the opposition could not fully seal.")
        if result.away_strength.attack - result.home_strength.defense >= 8:
            notes.append(f"{result.away_team_name} repeatedly threatened in transition and stretched the back line.")
        if result.home_stats.injuries or result.away_stats.injuries:
            notes.append('Injuries changed the tactical texture and substitution sequence of the match.')
        return notes[:5]
