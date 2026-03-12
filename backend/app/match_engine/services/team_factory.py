from __future__ import annotations

from dataclasses import dataclass

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.competition_engine.queue_contracts import MatchSimulationJob
from backend.app.match_engine.schemas import (
    MatchCompetitionContextInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    TeamTacticalPlanInput,
)
from backend.app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle


@dataclass(slots=True)
class SyntheticSquadFactory:
    def build_request(self, job: MatchSimulationJob) -> MatchSimulationRequest:
        return MatchSimulationRequest(
            match_id=job.fixture_id,
            seed=job.simulation_seed,
            kickoff_at=job.scheduled_kickoff_at,
            competition=MatchCompetitionContextInput(
                competition_type=self._competition_type(job),
                stage=job.stage_name or ("final" if job.is_final else "regular"),
                is_final=job.is_final,
                requires_winner=job.is_cup_match or job.is_final,
            ),
            home_team=self.build_team(
                team_id=job.home_club_id or "home",
                team_name=job.home_club_name or job.home_club_id or "Home Club",
                base_overall=job.home_strength_rating or 75,
            ),
            away_team=self.build_team(
                team_id=job.away_club_id or "away",
                team_name=job.away_club_name or job.away_club_id or "Away Club",
                base_overall=job.away_strength_rating or 75,
            ),
        )

    def build_team(
        self,
        *,
        team_id: str,
        team_name: str,
        base_overall: int,
    ) -> MatchTeamInput:
        resolved_overall = max(50, min(96, base_overall))
        style = TacticalStyle.ATTACKING if resolved_overall >= 84 else TacticalStyle.DEFENSIVE if resolved_overall <= 68 else TacticalStyle.BALANCED
        tactics = TeamTacticalPlanInput(
            style=style,
            pressing=self._clamp(resolved_overall - 15),
            tempo=self._clamp(resolved_overall - 12),
            aggression=self._clamp(42 + ((resolved_overall - 60) // 2)),
            substitution_windows=(60, 72, 82),
            red_card_fallback_formation="4-4-1",
            injury_auto_substitution=True,
            yellow_card_substitution_minute=70,
            yellow_card_replacement_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
            max_substitutions=5,
        )
        discipline = self._clamp(58 + ((resolved_overall - 55) // 2))
        fitness = self._clamp(62 + ((resolved_overall - 55) // 2))
        starters = [
            self._build_player(
                team_id=team_id,
                shirt_number=index + 1,
                role=role,
                base_overall=resolved_overall,
                discipline=discipline,
                fitness=fitness,
            )
            for index, role in enumerate(self._starter_roles("4-3-3"))
        ]
        bench_roles = (
            PlayerRole.GOALKEEPER,
            PlayerRole.DEFENDER,
            PlayerRole.DEFENDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.FORWARD,
            PlayerRole.FORWARD,
        )
        bench = [
            self._build_player(
                team_id=team_id,
                shirt_number=index + 101,
                role=role,
                base_overall=max(45, resolved_overall - 4),
                discipline=min(99, discipline + 2),
                fitness=min(99, fitness + 4),
            )
            for index, role in enumerate(bench_roles)
        ]
        return MatchTeamInput(
            team_id=team_id,
            team_name=team_name,
            formation="4-3-3",
            tactics=tactics,
            starters=starters,
            bench=bench,
        )

    @staticmethod
    def _competition_type(job: MatchSimulationJob) -> MatchCompetitionType:
        if job.competition_type in {
            CompetitionType.CHAMPIONS_LEAGUE,
            CompetitionType.WORLD_SUPER_CUP,
            CompetitionType.FAST_CUP,
        } or job.is_cup_match:
            return MatchCompetitionType.CUP
        return MatchCompetitionType.LEAGUE

    @staticmethod
    def _starter_roles(formation: str) -> list[PlayerRole]:
        lines = [int(part) for part in formation.split("-")]
        return [PlayerRole.GOALKEEPER] + ([PlayerRole.DEFENDER] * lines[0]) + ([PlayerRole.MIDFIELDER] * sum(lines[1:-1])) + ([PlayerRole.FORWARD] * lines[-1])

    def _build_player(
        self,
        *,
        team_id: str,
        shirt_number: int,
        role: PlayerRole,
        base_overall: int,
        discipline: int,
        fitness: int,
    ) -> MatchPlayerInput:
        variation = (shirt_number % 3) - 1
        resolved_overall = self._clamp(base_overall + variation)
        if role is PlayerRole.GOALKEEPER:
            return MatchPlayerInput(
                player_id=f"{team_id}-p{shirt_number}",
                player_name=f"{team_id.title()} Keeper {shirt_number}",
                role=role,
                overall=self._clamp(resolved_overall - 2),
                finishing=10,
                creativity=34,
                defending=56,
                goalkeeping=self._clamp(base_overall + 10 + variation),
                discipline=discipline,
                fitness=fitness,
            )
        if role is PlayerRole.DEFENDER:
            return MatchPlayerInput(
                player_id=f"{team_id}-p{shirt_number}",
                player_name=f"{team_id.title()} Defender {shirt_number}",
                role=role,
                overall=resolved_overall,
                finishing=self._clamp(base_overall - 16 + variation),
                creativity=self._clamp(base_overall - 4 + variation),
                defending=self._clamp(base_overall + 8 + variation),
                goalkeeping=5,
                discipline=discipline,
                fitness=fitness,
            )
        if role is PlayerRole.MIDFIELDER:
            return MatchPlayerInput(
                player_id=f"{team_id}-p{shirt_number}",
                player_name=f"{team_id.title()} Midfielder {shirt_number}",
                role=role,
                overall=self._clamp(resolved_overall + 1),
                finishing=self._clamp(base_overall - 2 + variation),
                creativity=self._clamp(base_overall + 8 + variation),
                defending=self._clamp(base_overall - 5 + variation),
                goalkeeping=5,
                discipline=discipline,
                fitness=fitness,
            )
        return MatchPlayerInput(
            player_id=f"{team_id}-p{shirt_number}",
            player_name=f"{team_id.title()} Forward {shirt_number}",
            role=role,
            overall=self._clamp(resolved_overall + 2),
            finishing=self._clamp(base_overall + 10 + variation),
            creativity=self._clamp(base_overall + 2 + variation),
            defending=self._clamp(base_overall - 18 + variation),
            goalkeeping=5,
            discipline=discipline,
            fitness=fitness,
        )

    @staticmethod
    def _clamp(value: int) -> int:
        return max(1, min(99, value))
