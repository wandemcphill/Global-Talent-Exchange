from __future__ import annotations

from backend.app.match_engine.schemas import (
    MatchCompetitionContextInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    TeamTacticalPlanInput,
)
from backend.app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle


def build_request(
    *,
    seed: int,
    match_id: str = "match-001",
    competition_type: MatchCompetitionType = MatchCompetitionType.LEAGUE,
    is_final: bool = False,
    requires_winner: bool | None = None,
    stage: str | None = None,
    home_team: MatchTeamInput | None = None,
    away_team: MatchTeamInput | None = None,
) -> MatchSimulationRequest:
    resolved_stage = stage or ("final" if is_final else "knockout" if competition_type is MatchCompetitionType.CUP else "regular")
    return MatchSimulationRequest(
        match_id=match_id,
        seed=seed,
        competition=MatchCompetitionContextInput(
            competition_type=competition_type,
            stage=resolved_stage,
            is_final=is_final,
            requires_winner=requires_winner,
        ),
        home_team=home_team or build_team("home", "North City", 82),
        away_team=away_team or build_team("away", "South Town", 78),
    )


def build_team(
    team_id: str,
    team_name: str,
    base_overall: int,
    *,
    formation: str = "4-3-3",
    style: TacticalStyle = TacticalStyle.BALANCED,
    pressing: int = 55,
    tempo: int = 55,
    aggression: int = 50,
    discipline: int = 72,
    fitness: int = 74,
    substitution_windows: tuple[int, ...] = (60, 72, 82),
    red_card_fallback_formation: str = "4-4-1",
    yellow_card_substitution_minute: int = 70,
    yellow_card_replacement_roles: tuple[PlayerRole, ...] = (PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
    max_substitutions: int = 5,
) -> MatchTeamInput:
    starter_roles = _starter_roles_from_formation(formation)
    bench_roles = (
        PlayerRole.GOALKEEPER,
        PlayerRole.DEFENDER,
        PlayerRole.DEFENDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.FORWARD,
        PlayerRole.FORWARD,
    )
    tactics = TeamTacticalPlanInput(
        style=style,
        pressing=pressing,
        tempo=tempo,
        aggression=aggression,
        substitution_windows=substitution_windows,
        red_card_fallback_formation=red_card_fallback_formation,
        injury_auto_substitution=True,
        yellow_card_substitution_minute=yellow_card_substitution_minute,
        yellow_card_replacement_roles=yellow_card_replacement_roles,
        max_substitutions=max_substitutions,
    )
    starters = [
        _build_player(team_id, index + 1, role, base_overall, discipline=discipline, fitness=fitness)
        for index, role in enumerate(starter_roles)
    ]
    bench = [
        _build_player(team_id, index + 101, role, base_overall - 3, discipline=discipline, fitness=fitness + 4)
        for index, role in enumerate(bench_roles)
    ]
    return MatchTeamInput(
        team_id=team_id,
        team_name=team_name,
        formation=formation,
        tactics=tactics,
        starters=starters,
        bench=bench,
    )


def _starter_roles_from_formation(formation: str) -> list[PlayerRole]:
    lines = [int(part) for part in formation.split("-")]
    midfielders = sum(lines[1:-1])
    forwards = lines[-1]
    defenders = lines[0]
    return [PlayerRole.GOALKEEPER] + ([PlayerRole.DEFENDER] * defenders) + ([PlayerRole.MIDFIELDER] * midfielders) + ([PlayerRole.FORWARD] * forwards)


def _build_player(
    team_id: str,
    shirt_number: int,
    role: PlayerRole,
    base_overall: int,
    *,
    discipline: int,
    fitness: int,
) -> MatchPlayerInput:
    variation = (shirt_number % 3) - 1
    resolved_overall = _clamp(base_overall + variation)
    resolved_shirt_number = shirt_number if 1 <= shirt_number <= 99 else None
    display_name = f"{team_id[:1].upper()}{shirt_number}" if resolved_shirt_number is not None else None
    if role is PlayerRole.GOALKEEPER:
        return MatchPlayerInput(
            player_id=f"{team_id}-p{shirt_number}",
            player_name=f"{team_id.title()} Keeper {shirt_number}",
            role=role,
            overall=_clamp(resolved_overall - 2),
            finishing=10,
            creativity=34,
            defending=56,
            goalkeeping=_clamp(base_overall + 10 + variation),
            discipline=_clamp(discipline),
            fitness=_clamp(fitness),
            shirt_number=resolved_shirt_number,
            display_name=display_name,
        )
    if role is PlayerRole.DEFENDER:
        return MatchPlayerInput(
            player_id=f"{team_id}-p{shirt_number}",
            player_name=f"{team_id.title()} Defender {shirt_number}",
            role=role,
            overall=resolved_overall,
            finishing=_clamp(base_overall - 16 + variation),
            creativity=_clamp(base_overall - 4 + variation),
            defending=_clamp(base_overall + 8 + variation),
            goalkeeping=5,
            discipline=_clamp(discipline),
            fitness=_clamp(fitness),
            shirt_number=resolved_shirt_number,
            display_name=display_name,
        )
    if role is PlayerRole.MIDFIELDER:
        return MatchPlayerInput(
            player_id=f"{team_id}-p{shirt_number}",
            player_name=f"{team_id.title()} Midfielder {shirt_number}",
            role=role,
            overall=_clamp(resolved_overall + 1),
            finishing=_clamp(base_overall - 2 + variation),
            creativity=_clamp(base_overall + 8 + variation),
            defending=_clamp(base_overall - 5 + variation),
            goalkeeping=5,
            discipline=_clamp(discipline),
            fitness=_clamp(fitness),
            shirt_number=resolved_shirt_number,
            display_name=display_name,
        )
    return MatchPlayerInput(
        player_id=f"{team_id}-p{shirt_number}",
        player_name=f"{team_id.title()} Forward {shirt_number}",
        role=role,
        overall=_clamp(resolved_overall + 2),
        finishing=_clamp(base_overall + 10 + variation),
        creativity=_clamp(base_overall + 2 + variation),
        defending=_clamp(base_overall - 18 + variation),
        goalkeeping=5,
        discipline=_clamp(discipline),
        fitness=_clamp(fitness),
        shirt_number=resolved_shirt_number,
        display_name=display_name,
    )


def _clamp(value: int) -> int:
    return max(1, min(99, value))
