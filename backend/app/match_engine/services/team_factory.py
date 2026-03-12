from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.competition_engine.queue_contracts import MatchSimulationJob
from backend.app.ingestion.models import Player
from backend.app.match_engine.schemas import (
    MatchCompetitionContextInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    TeamTacticalPlanInput,
)
from backend.app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle
from backend.app.services.player_lifecycle_service import (
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)


@dataclass(slots=True)
class SyntheticSquadFactory:
    session_factory: sessionmaker[Session] | None = None

    def build_request(self, job: MatchSimulationJob) -> MatchSimulationRequest:
        home_team: MatchTeamInput
        away_team: MatchTeamInput
        if self.session_factory is not None:
            session = self.session_factory()
            try:
                lifecycle_service = PlayerLifecycleService(session)
                home_team = self.build_team(
                    team_id=job.home_club_id or "home",
                    team_name=job.home_club_name or job.home_club_id or "Home Club",
                    base_overall=job.home_strength_rating or 75,
                    match_date=job.match_date,
                    lifecycle_service=lifecycle_service,
                )
                away_team = self.build_team(
                    team_id=job.away_club_id or "away",
                    team_name=job.away_club_name or job.away_club_id or "Away Club",
                    base_overall=job.away_strength_rating or 75,
                    match_date=job.match_date,
                    lifecycle_service=lifecycle_service,
                )
            finally:
                session.close()
        else:
            home_team = self.build_team(
                team_id=job.home_club_id or "home",
                team_name=job.home_club_name or job.home_club_id or "Home Club",
                base_overall=job.home_strength_rating or 75,
            )
            away_team = self.build_team(
                team_id=job.away_club_id or "away",
                team_name=job.away_club_name or job.away_club_id or "Away Club",
                base_overall=job.away_strength_rating or 75,
            )
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
            home_team=home_team,
            away_team=away_team,
        )

    def build_team(
        self,
        *,
        team_id: str,
        team_name: str,
        base_overall: int,
        match_date: date | None = None,
        lifecycle_service: PlayerLifecycleService | None = None,
    ) -> MatchTeamInput:
        if lifecycle_service is not None and match_date is not None:
            managed_team = self._build_managed_team(
                lifecycle_service=lifecycle_service,
                team_id=team_id,
                team_name=team_name,
                base_overall=base_overall,
                match_date=match_date,
            )
            if managed_team is not None:
                return managed_team

        resolved_overall = max(50, min(96, base_overall))
        discipline = self._clamp(58 + ((resolved_overall - 55) // 2))
        fitness = self._clamp(62 + ((resolved_overall - 55) // 2))
        starters = [
            self._build_synthetic_player(
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
            self._build_synthetic_player(
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
            tactics=self._build_tactics(resolved_overall),
            starters=starters,
            bench=bench,
        )

    def _build_managed_team(
        self,
        *,
        lifecycle_service: PlayerLifecycleService,
        team_id: str,
        team_name: str,
        base_overall: int,
        match_date: date,
    ) -> MatchTeamInput | None:
        squad_status = lifecycle_service.list_club_squad_status(team_id, on_date=match_date)
        if not squad_status:
            return None

        eligible = [record.player for record in squad_status if record.available]
        if len(eligible) < 11:
            blocked = ", ".join(
                f"{record.player.full_name} ({record.reason})"
                for record in squad_status
                if not record.available
            )
            raise PlayerLifecycleValidationError(
                f"{team_name} cannot field an eligible squad on {match_date.isoformat()}: "
                f"{len(eligible)} players available under active contract."
                + (f" Blocked players: {blocked}" if blocked else "")
            )

        starters, bench = self._select_managed_squad(eligible)
        resolved_overall = max(50, min(96, base_overall))
        return MatchTeamInput(
            team_id=team_id,
            team_name=team_name,
            formation="4-3-3",
            tactics=self._build_tactics(resolved_overall),
            starters=[
                self._build_managed_player(player, assigned_role=role, base_overall=resolved_overall)
                for player, role in starters
            ],
            bench=[
                self._build_managed_player(player, assigned_role=role, base_overall=max(45, resolved_overall - 3))
                for player, role in bench
            ],
        )

    def _select_managed_squad(
        self,
        players: list[Player],
    ) -> tuple[list[tuple[Player, PlayerRole]], list[tuple[Player, PlayerRole]]]:
        remaining = list(players)
        starters: list[tuple[Player, PlayerRole]] = []
        for role in self._starter_roles("4-3-3"):
            candidate = self._select_best_candidate(remaining, role)
            if candidate is None:
                raise PlayerLifecycleValidationError("Managed squad cannot satisfy formation role requirements")
            starters.append((candidate, role))
            remaining.remove(candidate)
        bench = [
            (player, self._resolve_player_role(player))
            for player in sorted(remaining, key=self._managed_player_sort_key, reverse=True)[:7]
        ]
        return starters, bench

    def _select_best_candidate(self, players: list[Player], required_role: PlayerRole) -> Player | None:
        if not players:
            return None
        ranked = sorted(
            players,
            key=lambda player: (
                self._role_fit_score(player, required_role),
                *self._managed_player_sort_key(player),
            ),
            reverse=True,
        )
        best = ranked[0]
        if required_role is PlayerRole.GOALKEEPER and self._role_fit_score(best, required_role) <= 0:
            return None
        if required_role is not PlayerRole.GOALKEEPER and self._role_fit_score(best, required_role) <= 0:
            return None
        return best

    def _build_tactics(self, resolved_overall: int) -> TeamTacticalPlanInput:
        style = TacticalStyle.ATTACKING if resolved_overall >= 84 else TacticalStyle.DEFENSIVE if resolved_overall <= 68 else TacticalStyle.BALANCED
        return TeamTacticalPlanInput(
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

    def _build_synthetic_player(
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

    def _build_managed_player(
        self,
        player: Player,
        *,
        assigned_role: PlayerRole,
        base_overall: int,
    ) -> MatchPlayerInput:
        overall = self._estimate_player_overall(player, base_overall=base_overall)
        discipline = self._clamp(70)
        fitness = self._clamp(78)
        if assigned_role is PlayerRole.GOALKEEPER:
            return MatchPlayerInput(
                player_id=player.id,
                player_name=player.full_name,
                role=assigned_role,
                overall=self._clamp(overall - 2),
                finishing=10,
                creativity=36,
                defending=54,
                goalkeeping=self._clamp(overall + 10),
                discipline=discipline,
                fitness=fitness,
            )
        if assigned_role is PlayerRole.DEFENDER:
            return MatchPlayerInput(
                player_id=player.id,
                player_name=player.full_name,
                role=assigned_role,
                overall=overall,
                finishing=self._clamp(overall - 18),
                creativity=self._clamp(overall - 3),
                defending=self._clamp(overall + 8),
                goalkeeping=5,
                discipline=discipline,
                fitness=fitness,
            )
        if assigned_role is PlayerRole.MIDFIELDER:
            return MatchPlayerInput(
                player_id=player.id,
                player_name=player.full_name,
                role=assigned_role,
                overall=self._clamp(overall + 1),
                finishing=self._clamp(overall - 2),
                creativity=self._clamp(overall + 7),
                defending=self._clamp(overall - 4),
                goalkeeping=5,
                discipline=discipline,
                fitness=fitness,
            )
        return MatchPlayerInput(
            player_id=player.id,
            player_name=player.full_name,
            role=assigned_role,
            overall=self._clamp(overall + 2),
            finishing=self._clamp(overall + 8),
            creativity=self._clamp(overall + 1),
            defending=self._clamp(overall - 16),
            goalkeeping=5,
            discipline=discipline,
            fitness=fitness,
        )

    def _estimate_player_overall(self, player: Player, *, base_overall: int) -> int:
        ratings = [stat.average_rating or 0.0 for stat in player.season_stats if stat.average_rating is not None]
        best_rating = max(ratings, default=0.0)
        output = max(((stat.goals or 0) + (stat.assists or 0) for stat in player.season_stats), default=0)
        rating_bonus = round((best_rating - 6.5) * 5) if best_rating else 0
        market_bonus = min(10, int((player.market_value_eur or 0.0) / 12_000_000))
        output_bonus = min(6, output // 5)
        anchor = 58 + rating_bonus + market_bonus + output_bonus
        return self._clamp(int(round((base_overall * 0.6) + (anchor * 0.4))))

    def _managed_player_sort_key(self, player: Player) -> tuple[int, float, float]:
        return (
            self._estimate_player_overall(player, base_overall=75),
            float(player.market_value_eur or 0.0),
            max((stat.average_rating or 0.0 for stat in player.season_stats if stat.average_rating is not None), default=0.0),
        )

    def _role_fit_score(self, player: Player, required_role: PlayerRole) -> int:
        actual_role = self._resolve_player_role(player)
        if actual_role is required_role:
            return 3
        if required_role is PlayerRole.DEFENDER and actual_role is PlayerRole.MIDFIELDER:
            return 1
        if required_role is PlayerRole.MIDFIELDER and actual_role in {PlayerRole.DEFENDER, PlayerRole.FORWARD}:
            return 1
        if required_role is PlayerRole.FORWARD and actual_role is PlayerRole.MIDFIELDER:
            return 1
        return 0

    def _resolve_player_role(self, player: Player) -> PlayerRole:
        position = (player.normalized_position or player.position or "").lower()
        if "goal" in position or position in {"gk", "goalkeeper"}:
            return PlayerRole.GOALKEEPER
        if any(token in position for token in ("back", "def", "cb", "lb", "rb", "wb")):
            return PlayerRole.DEFENDER
        if any(token in position for token in ("mid", "wing", "dm", "cm", "am")):
            return PlayerRole.MIDFIELDER
        return PlayerRole.FORWARD

    @staticmethod
    def _clamp(value: int) -> int:
        return max(1, min(99, value))
