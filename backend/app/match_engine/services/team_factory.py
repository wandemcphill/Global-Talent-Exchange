from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select

from backend.app.club_identity.jerseys.repository import InMemoryClubIdentityRepository
from backend.app.club_identity.jerseys.service import ClubIdentityService
from backend.app.club_identity.models.jersey_models import JerseyVariant
from backend.app.models.club_jersey_design import ClubJerseyDesign
from backend.app.models.club_profile import ClubProfile
from backend.app.common.enums.competition_type import CompetitionType
from backend.app.competition_engine.queue_contracts import MatchSimulationJob
from backend.app.ingestion.models import Player
from backend.app.match_engine.schemas import (
    MatchClubContextInput,
    MatchCompetitionContextInput,
    MatchKitIdentityInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    MatchTeamIdentityInput,
    TeamTacticalPlanInput,
)
from backend.app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle
from backend.app.models.manager_market import ManagerCatalogEntry, ManagerHolding, ManagerTeamAssignment
from backend.app.services.player_lifecycle_service import (
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)


@dataclass(slots=True)
class SyntheticSquadFactory:
    session_factory: sessionmaker[Session] | None = None
    identity_service: ClubIdentityService = field(
        default_factory=lambda: ClubIdentityService(InMemoryClubIdentityRepository())
    )

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
        session = lifecycle_service.session if lifecycle_service is not None else None
        manager_profile = self._manager_profile_for_team(session, team_id) if lifecycle_service is not None else None
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
            tactics=self._build_tactics(resolved_overall, manager_profile=manager_profile),
            manager_profile=manager_profile,
            club_context=self._build_club_context(resolved_overall, manager_profile=manager_profile),
            identity=self._resolve_team_identity(session, team_id=team_id, team_name=team_name),
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
        manager_profile = self._manager_profile_for_team(lifecycle_service.session if lifecycle_service is not None else None, team_id)
        return MatchTeamInput(
            team_id=team_id,
            team_name=team_name,
            formation="4-3-3",
            tactics=self._build_tactics(resolved_overall, manager_profile=manager_profile),
            manager_profile=manager_profile,
            club_context=self._build_managed_club_context(starters + bench, resolved_overall, manager_profile=manager_profile),
            identity=self._resolve_team_identity(lifecycle_service.session, team_id=team_id, team_name=team_name),
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

    def _build_tactics(self, resolved_overall: int, manager_profile: dict[str, object] | None = None) -> TeamTacticalPlanInput:
        style = TacticalStyle.ATTACKING if resolved_overall >= 84 else TacticalStyle.DEFENSIVE if resolved_overall <= 68 else TacticalStyle.BALANCED
        pressing = self._clamp(resolved_overall - 15)
        tempo = self._clamp(resolved_overall - 12)
        aggression = self._clamp(42 + ((resolved_overall - 60) // 2))
        substitution_windows = (60, 72, 82)
        tactical_quality = self._clamp(54 + ((resolved_overall - 55) // 2))
        adaptability = self._clamp(52 + ((resolved_overall - 55) // 3))
        game_management = self._clamp(55 + ((resolved_overall - 55) // 3))
        if manager_profile is not None:
            mentality = str(manager_profile.get('mentality', 'balanced'))
            tactics = set(manager_profile.get('tactics') or [])
            traits = set(manager_profile.get('traits') or [])
            if mentality in {'attacking', 'pressing'} or 'high_press_attack' in tactics:
                style = TacticalStyle.ATTACKING
                pressing = self._clamp(pressing + 10)
                tempo = self._clamp(tempo + 8)
            elif mentality in {'defensive', 'pragmatic'} or 'low_block_counter' in tactics or 'compact_midblock' in tactics:
                style = TacticalStyle.DEFENSIVE
                pressing = self._clamp(pressing - 6)
                aggression = self._clamp(aggression - 3)
            elif mentality in {'technical', 'possession'} or 'tiki_taka' in tactics or 'possession_control' in tactics:
                style = TacticalStyle.BALANCED
                tempo = self._clamp(tempo + 4)
            if 'quick_substitution' in traits:
                substitution_windows = (56, 67, 78)
                adaptability = self._clamp(adaptability + 8)
                game_management = self._clamp(game_management + 6)
            elif 'late_substitution' in traits:
                substitution_windows = (67, 78, 86)
                adaptability = self._clamp(adaptability - 3)
            if {'tactical_flexibility', 'in_game_adjustments'} & traits:
                tactical_quality = self._clamp(tactical_quality + 8)
                adaptability = self._clamp(adaptability + 10)
            if {'defensive_organization', 'strict_structure'} & traits:
                tactical_quality = self._clamp(tactical_quality + 5)
                game_management = self._clamp(game_management + 5)
            if {'great motivator', 'great_motivator'} & traits:
                game_management = self._clamp(game_management + 4)
        return TeamTacticalPlanInput(
            style=style,
            pressing=pressing,
            tempo=tempo,
            aggression=aggression,
            substitution_windows=substitution_windows,
            red_card_fallback_formation="4-4-1",
            injury_auto_substitution=True,
            yellow_card_substitution_minute=70,
            yellow_card_replacement_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
            max_substitutions=5,
            tactical_quality=tactical_quality,
            adaptability=adaptability,
            game_management=game_management,
        )

    def _manager_profile_for_team(self, session: Session | None, team_id: str) -> dict[str, object] | None:
        if session is None:
            return None
        assignment = session.scalar(select(ManagerTeamAssignment).where(ManagerTeamAssignment.user_id == team_id))
        if assignment is None or not assignment.main_manager_asset_id:
            return None
        holding = session.scalar(select(ManagerHolding).where(ManagerHolding.asset_id == assignment.main_manager_asset_id))
        if holding is None:
            return None
        manager = session.scalar(select(ManagerCatalogEntry).where(ManagerCatalogEntry.manager_id == holding.manager_id))
        if manager is None:
            return None
        return {
            'display_name': manager.display_name,
            'mentality': manager.mentality,
            'tactics': list(manager.tactics or []),
            'traits': list(manager.traits or []),
            'rarity': manager.rarity,
            'philosophy_summary': manager.philosophy_summary,
            'substitution_tendency': manager.substitution_tendency,
        }

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
                shirt_number=shirt_number if shirt_number <= 99 else None,
                display_name=f"K{shirt_number}",
                position_archetype="shot_stopper",
                pace=self._clamp(base_overall - 18 + variation),
                composure=self._clamp(base_overall + 4 + variation),
                decision_making=self._clamp(base_overall + 2 + variation),
                positioning=self._clamp(base_overall + 5 + variation),
                off_ball_movement=self._clamp(base_overall - 24 + variation),
                aerial_ability=self._clamp(base_overall + 7 + variation),
                technique=self._clamp(base_overall - 2 + variation),
                stamina_curve=self._clamp(fitness - 6),
                consistency=self._clamp(base_overall + 3 + variation),
                clutch_factor=self._clamp(base_overall + 2 + variation),
                big_match_temperament=self._clamp(base_overall + 1 + variation),
                recent_form=self._clamp(base_overall + variation),
                morale=self._clamp(60 + variation),
                motivation=self._clamp(62 + variation),
                fatigue_load=max(12, 32 - variation),
                injury_risk=18,
                leadership=self._clamp(base_overall + 5),
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
                shirt_number=shirt_number if shirt_number <= 99 else None,
                display_name=f"D{shirt_number}",
                position_archetype="ball_playing_defender" if shirt_number % 2 == 0 else "fullback",
                pace=self._clamp(base_overall - 2 + variation),
                composure=self._clamp(base_overall + 1 + variation),
                decision_making=self._clamp(base_overall + 1 + variation),
                positioning=self._clamp(base_overall + 7 + variation),
                off_ball_movement=self._clamp(base_overall - 8 + variation),
                aerial_ability=self._clamp(base_overall + 6 + variation),
                technique=self._clamp(base_overall - 1 + variation),
                stamina_curve=self._clamp(fitness - 2),
                consistency=self._clamp(base_overall + 2 + variation),
                clutch_factor=self._clamp(base_overall - 2 + variation),
                big_match_temperament=self._clamp(base_overall + 1 + variation),
                recent_form=self._clamp(base_overall + variation),
                morale=self._clamp(59 + variation),
                motivation=self._clamp(61 + variation),
                fatigue_load=max(18, 34 - variation),
                injury_risk=24,
                leadership=self._clamp(base_overall + 3),
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
                shirt_number=shirt_number if shirt_number <= 99 else None,
                display_name=f"M{shirt_number}",
                position_archetype="deep_playmaker" if shirt_number % 2 == 0 else "box_to_box",
                pace=self._clamp(base_overall - 1 + variation),
                composure=self._clamp(base_overall + 3 + variation),
                decision_making=self._clamp(base_overall + 6 + variation),
                positioning=self._clamp(base_overall + 4 + variation),
                off_ball_movement=self._clamp(base_overall + 4 + variation),
                aerial_ability=self._clamp(base_overall - 6 + variation),
                technique=self._clamp(base_overall + 7 + variation),
                stamina_curve=self._clamp(fitness + 1),
                consistency=self._clamp(base_overall + 4 + variation),
                clutch_factor=self._clamp(base_overall + 1 + variation),
                big_match_temperament=self._clamp(base_overall + 1 + variation),
                recent_form=self._clamp(base_overall + 1 + variation),
                morale=self._clamp(61 + variation),
                motivation=self._clamp(62 + variation),
                fatigue_load=max(20, 38 - variation),
                injury_risk=22,
                leadership=self._clamp(base_overall + 4),
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
            shirt_number=shirt_number if shirt_number <= 99 else None,
            display_name=f"F{shirt_number}",
            position_archetype="inside_forward" if shirt_number % 2 == 0 else "poacher",
            pace=self._clamp(base_overall + 6 + variation),
            composure=self._clamp(base_overall + 6 + variation),
            decision_making=self._clamp(base_overall + 1 + variation),
            positioning=self._clamp(base_overall + 4 + variation),
            off_ball_movement=self._clamp(base_overall + 8 + variation),
            aerial_ability=self._clamp(base_overall - 3 + variation),
            technique=self._clamp(base_overall + 3 + variation),
            stamina_curve=self._clamp(fitness - 3),
            consistency=self._clamp(base_overall + 1 + variation),
            clutch_factor=self._clamp(base_overall + 7 + variation),
            big_match_temperament=self._clamp(base_overall + 5 + variation),
            recent_form=self._clamp(base_overall + 2 + variation),
            morale=self._clamp(62 + variation),
            motivation=self._clamp(64 + variation),
            fatigue_load=max(22, 40 - variation),
            injury_risk=20,
            leadership=self._clamp(base_overall + 1),
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
            recent_form = self._managed_recent_form(player)
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
                shirt_number=self._normalize_shirt_number(player.shirt_number),
                display_name=self._shirt_name(player.full_name),
                position_archetype="shot_stopper",
                pace=self._clamp(overall - 18),
                composure=self._clamp(overall + 4),
                decision_making=self._clamp(overall + 3),
                positioning=self._clamp(overall + 5),
                off_ball_movement=self._clamp(overall - 24),
                aerial_ability=self._clamp(overall + 7),
                technique=self._clamp(overall - 2),
                stamina_curve=self._clamp(fitness - 6),
                consistency=self._clamp(overall + 2),
                clutch_factor=self._clamp(overall + 2),
                big_match_temperament=self._clamp(overall + 1),
                recent_form=recent_form,
                morale=self._clamp(58 + ((recent_form - 55) // 2)),
                motivation=self._clamp(60 + ((recent_form - 55) // 3)),
                fatigue_load=26,
                injury_risk=18,
                leadership=self._clamp(overall + 4),
            )
        if assigned_role is PlayerRole.DEFENDER:
            recent_form = self._managed_recent_form(player)
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
                shirt_number=self._normalize_shirt_number(player.shirt_number),
                display_name=self._shirt_name(player.full_name),
                position_archetype="ball_playing_defender" if "back" in (player.position or "").lower() else "center_back",
                pace=self._clamp(overall - 1),
                composure=self._clamp(overall + 1),
                decision_making=self._clamp(overall + 2),
                positioning=self._clamp(overall + 6),
                off_ball_movement=self._clamp(overall - 7),
                aerial_ability=self._clamp(overall + 5),
                technique=self._clamp(overall - 1),
                stamina_curve=self._clamp(fitness - 2),
                consistency=self._clamp(overall + 2),
                clutch_factor=self._clamp(overall - 2),
                big_match_temperament=self._clamp(overall + 1),
                recent_form=recent_form,
                morale=self._clamp(58 + ((recent_form - 55) // 2)),
                motivation=self._clamp(60 + ((recent_form - 55) // 3)),
                fatigue_load=30,
                injury_risk=24,
                leadership=self._clamp(overall + 3),
            )
        if assigned_role is PlayerRole.MIDFIELDER:
            recent_form = self._managed_recent_form(player)
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
                shirt_number=self._normalize_shirt_number(player.shirt_number),
                display_name=self._shirt_name(player.full_name),
                position_archetype="playmaker" if "am" in (player.normalized_position or "").lower() else "controller",
                pace=self._clamp(overall - 1),
                composure=self._clamp(overall + 3),
                decision_making=self._clamp(overall + 6),
                positioning=self._clamp(overall + 3),
                off_ball_movement=self._clamp(overall + 4),
                aerial_ability=self._clamp(overall - 6),
                technique=self._clamp(overall + 7),
                stamina_curve=self._clamp(fitness),
                consistency=self._clamp(overall + 4),
                clutch_factor=self._clamp(overall + 1),
                big_match_temperament=self._clamp(overall + 2),
                recent_form=recent_form,
                morale=self._clamp(59 + ((recent_form - 55) // 2)),
                motivation=self._clamp(61 + ((recent_form - 55) // 3)),
                fatigue_load=32,
                injury_risk=22,
                leadership=self._clamp(overall + 4),
            )
        recent_form = self._managed_recent_form(player)
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
            shirt_number=self._normalize_shirt_number(player.shirt_number),
            display_name=self._shirt_name(player.full_name),
            position_archetype="inside_forward" if "wing" in (player.normalized_position or "").lower() else "poacher",
            pace=self._clamp(overall + 6),
            composure=self._clamp(overall + 6),
            decision_making=self._clamp(overall + 1),
            positioning=self._clamp(overall + 4),
            off_ball_movement=self._clamp(overall + 8),
            aerial_ability=self._clamp(overall - 2),
            technique=self._clamp(overall + 3),
            stamina_curve=self._clamp(fitness - 3),
            consistency=self._clamp(overall + 2),
            clutch_factor=self._clamp(overall + 7),
            big_match_temperament=self._clamp(overall + 5),
            recent_form=recent_form,
            morale=self._clamp(61 + ((recent_form - 55) // 2)),
            motivation=self._clamp(63 + ((recent_form - 55) // 3)),
            fatigue_load=34,
            injury_risk=20,
            leadership=self._clamp(overall + 2),
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
        if required_role is PlayerRole.GOALKEEPER:
            return 3 if actual_role is PlayerRole.GOALKEEPER else 1
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

    def _managed_recent_form(self, player: Player) -> int:
        rating = max((stat.average_rating or 0.0 for stat in player.season_stats if stat.average_rating is not None), default=0.0)
        if rating <= 0:
            return 58
        return self._clamp(int(round(48 + (rating * 5.5))))

    def _normalize_shirt_number(self, value: int | None) -> int | None:
        if value is None:
            return None
        return value if 1 <= value <= 99 else None

    def _shirt_name(self, full_name: str) -> str:
        chunks = [chunk for chunk in full_name.split() if chunk]
        if not chunks:
            return full_name
        return chunks[-1][:16].upper()

    def _build_club_context(
        self,
        resolved_overall: int,
        *,
        manager_profile: dict[str, object] | None = None,
    ) -> MatchClubContextInput:
        traits = {str(item).strip().lower() for item in (manager_profile or {}).get("traits", [])}
        chemistry = self._clamp(58 + ((resolved_overall - 55) // 2) + (4 if {"great motivator", "great_motivator"} & traits else 0))
        return MatchClubContextInput(
            club_tier=self._clamp(resolved_overall),
            competition_tier=self._clamp(resolved_overall - 1),
            team_chemistry=chemistry,
            recent_form=self._clamp(56 + ((resolved_overall - 55) // 3)),
            morale=self._clamp(58 + ((resolved_overall - 55) // 3)),
            motivation=self._clamp(60 + ((resolved_overall - 55) // 4)),
            fatigue_load=max(18, 42 - ((resolved_overall - 50) // 2)),
            travel_load=28,
            rivalry_intensity=0,
            schedule_pressure=34,
        )

    def _build_managed_club_context(
        self,
        squad: list[tuple[Player, PlayerRole]],
        resolved_overall: int,
        *,
        manager_profile: dict[str, object] | None = None,
    ) -> MatchClubContextInput:
        form_values = [self._managed_recent_form(player) for player, _ in squad]
        base = self._build_club_context(resolved_overall, manager_profile=manager_profile)
        average_form = int(round(sum(form_values) / max(1, len(form_values))))
        return base.model_copy(
            update={
                "recent_form": self._clamp(average_form),
                "morale": self._clamp(base.morale + ((average_form - 58) // 3)),
                "motivation": self._clamp(base.motivation + ((average_form - 58) // 4)),
            }
        )

    def _resolve_team_identity(
        self,
        session: Session | None,
        *,
        team_id: str,
        team_name: str,
    ) -> MatchTeamIdentityInput:
        generated = self.identity_service.get_identity(team_id)
        club_profile = session.get(ClubProfile, team_id) if session is not None else None
        jerseys = self._load_jerseys(session, team_id) if session is not None else {}
        club_name = club_profile.club_name if club_profile is not None else generated.club_name or team_name
        short_name = club_profile.short_name if club_profile is not None else None
        short_code = ((short_name or generated.short_club_code or club_name[:3]).replace(" ", "")[:6]).upper()
        return MatchTeamIdentityInput(
            club_name=club_name,
            short_club_code=short_code,
            badge_url=(club_profile.crest_asset_ref if club_profile is not None else None) or generated.badge_profile.badge_url,
            badge_shape=generated.badge_profile.shape.value,
            badge_initials=generated.badge_profile.initials,
            badge_primary_color=(club_profile.primary_color if club_profile is not None else generated.badge_profile.primary_color),
            badge_secondary_color=(club_profile.secondary_color if club_profile is not None else generated.badge_profile.secondary_color),
            badge_accent_color=(club_profile.accent_color if club_profile is not None else generated.badge_profile.accent_color),
            home_kit=self._map_kit_identity(jerseys.get("home"), generated.jersey_set.home, slot="home"),
            away_kit=self._map_kit_identity(jerseys.get("away"), generated.jersey_set.away, slot="away"),
            goalkeeper_kit=self._map_kit_identity(jerseys.get("goalkeeper"), generated.jersey_set.goalkeeper, slot="goalkeeper"),
        )

    def _load_jerseys(self, session: Session | None, team_id: str) -> dict[str, ClubJerseyDesign]:
        if session is None:
            return {}
        rows = session.scalars(
            select(ClubJerseyDesign)
            .where(ClubJerseyDesign.club_id == team_id)
            .where(ClubJerseyDesign.is_active.is_(True))
        ).all()
        by_slot: dict[str, ClubJerseyDesign] = {}
        for row in rows:
            by_slot.setdefault(row.slot_type, row)
        return by_slot

    def _map_kit_identity(
        self,
        row: ClubJerseyDesign | None,
        fallback: JerseyVariant,
        *,
        slot: str,
    ) -> MatchKitIdentityInput:
        if row is None:
            return MatchKitIdentityInput(
                kit_type=slot,
                primary_color=fallback.primary_color,
                secondary_color=fallback.secondary_color,
                accent_color=fallback.accent_color,
                shorts_color=fallback.shorts_color,
                socks_color=fallback.socks_color,
                pattern_type=fallback.pattern_type.value,
                collar_style=fallback.collar_style.value,
                sleeve_style=fallback.sleeve_style.value,
                badge_placement=fallback.badge_placement.value,
                front_text=fallback.front_text,
            )
        metadata = row.metadata_json or {}
        return MatchKitIdentityInput(
            kit_type=slot,
            primary_color=row.primary_color,
            secondary_color=row.secondary_color,
            accent_color=row.trim_color,
            shorts_color=str(metadata.get("shorts_color") or row.primary_color),
            socks_color=str(metadata.get("socks_color") or row.secondary_color),
            pattern_type=str(metadata.get("pattern_type") or fallback.pattern_type.value),
            collar_style=str(metadata.get("collar_style") or fallback.collar_style.value),
            sleeve_style=str(row.sleeve_style or fallback.sleeve_style.value),
            badge_placement=row.crest_placement,
            front_text=row.motto_text or fallback.front_text,
        )
