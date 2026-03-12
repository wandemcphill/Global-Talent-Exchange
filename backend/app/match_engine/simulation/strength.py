from __future__ import annotations

from statistics import fmean
from typing import Protocol

from backend.app.match_engine.simulation.models import MatchTeamProfile, PlayerRole, TacticalStyle, TeamStrengthSnapshot


class TeamStrengthCalculator(Protocol):
    def calculate(self, team: MatchTeamProfile, *, is_home: bool) -> TeamStrengthSnapshot:
        ...


class DefaultTeamStrengthCalculator:
    def calculate(self, team: MatchTeamProfile, *, is_home: bool) -> TeamStrengthSnapshot:
        starters = team.starters
        bench = team.bench
        attack = fmean(self._attack_impact(player) for player in starters)
        midfield = fmean(self._midfield_impact(player) for player in starters)
        defense = fmean(self._defense_impact(player) for player in starters)
        goalkeeping = max((player.goalkeeping_value() for player in starters if player.role is PlayerRole.GOALKEEPER), default=40.0)
        depth = fmean(sorted((player.overall for player in bench), reverse=True)[:5]) if bench else fmean(player.overall for player in starters)
        discipline = fmean(player.discipline for player in starters)
        fitness = fmean(player.fitness for player in starters)

        style_attack, style_midfield, style_defense = self._style_adjustments(team.tactics.style)
        attack = self._clamp(attack + style_attack + ((team.tactics.tempo - 50) * 0.10) + ((team.tactics.pressing - 50) * 0.05), 20.0, 99.0)
        midfield = self._clamp(midfield + style_midfield + ((team.tactics.pressing - 50) * 0.08), 20.0, 99.0)
        defense = self._clamp(defense + style_defense - ((team.tactics.aggression - 50) * 0.05), 20.0, 99.0)
        overall = self._clamp((attack * 0.34) + (midfield * 0.24) + (defense * 0.24) + (goalkeeping * 0.08) + (depth * 0.10), 20.0, 99.0)
        return TeamStrengthSnapshot(
            overall=round(overall, 2),
            attack=round(attack, 2),
            midfield=round(midfield, 2),
            defense=round(defense, 2),
            goalkeeping=round(goalkeeping, 2),
            depth=round(depth, 2),
            discipline=round(discipline, 2),
            fitness=round(fitness, 2),
        )

    def _attack_impact(self, player) -> float:
        return player.attacking_value()

    def _midfield_impact(self, player) -> float:
        return player.control_value()

    def _defense_impact(self, player) -> float:
        return player.defensive_value()

    def _style_adjustments(self, style: TacticalStyle) -> tuple[float, float, float]:
        if style is TacticalStyle.ATTACKING:
            return 4.0, 2.0, -2.5
        if style is TacticalStyle.DEFENSIVE:
            return -3.5, 1.0, 4.5
        return 0.0, 0.0, 0.0

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
