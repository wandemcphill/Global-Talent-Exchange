from __future__ import annotations

from backend.app.match_engine.commentary.timeline import MatchCommentaryTimelineGenerator
from backend.app.match_engine.schemas import (
    MatchFinalSummaryView,
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
from backend.app.match_engine.simulation.models import SimulationResult


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
        return MatchFinalSummaryView(
            match_id=result.match_id,
            seed=result.seed,
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
