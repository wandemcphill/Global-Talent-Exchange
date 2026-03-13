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

        squad_balance = self._squad_balance_bonus(team)
        manager_attack, manager_midfield, manager_defense, manager_depth, manager_fitness = self._manager_adjustments(team)
        home_edge = 1.35 if is_home else 0.0

        attack = self._clamp(attack + squad_balance + manager_attack + home_edge, 20.0, 99.0)
        midfield = self._clamp(midfield + (squad_balance * 0.8) + manager_midfield + (0.65 if is_home else 0.0), 20.0, 99.0)
        defense = self._clamp(defense + (squad_balance * 0.55) + manager_defense, 20.0, 99.0)
        depth = self._clamp(depth + manager_depth, 20.0, 99.0)
        fitness = self._clamp(fitness + manager_fitness, 20.0, 99.0)
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

    def _squad_balance_bonus(self, team: MatchTeamProfile) -> float:
        role_counts = {
            PlayerRole.GOALKEEPER: 0,
            PlayerRole.DEFENDER: 0,
            PlayerRole.MIDFIELDER: 0,
            PlayerRole.FORWARD: 0,
        }
        for player in team.starters:
            role_counts[player.role] += 1

        balance = 0.0
        if role_counts[PlayerRole.GOALKEEPER] == 1:
            balance += 0.75
        else:
            balance -= min(abs(role_counts[PlayerRole.GOALKEEPER] - 1) * 1.2, 2.4)

        for role, minimum, maximum, reward in (
            (PlayerRole.DEFENDER, 3, 5, 0.65),
            (PlayerRole.MIDFIELDER, 2, 5, 0.65),
            (PlayerRole.FORWARD, 1, 3, 0.55),
        ):
            count = role_counts[role]
            if minimum <= count <= maximum:
                balance += reward
            else:
                deficit = minimum - count if count < minimum else count - maximum
                balance -= min(deficit * 0.6, 1.5)

        outfield_gap = max(
            role_counts[PlayerRole.DEFENDER],
            role_counts[PlayerRole.MIDFIELDER],
            role_counts[PlayerRole.FORWARD],
        ) - min(
            role_counts[PlayerRole.DEFENDER],
            role_counts[PlayerRole.MIDFIELDER],
            role_counts[PlayerRole.FORWARD],
        )
        if outfield_gap > 3:
            balance -= (outfield_gap - 3) * 0.25
        return self._clamp(balance, -2.5, 2.5)

    def _manager_adjustments(self, team: MatchTeamProfile) -> tuple[float, float, float, float, float]:
        profile = team.manager_profile or {}
        if not profile:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        mentality = str(profile.get("mentality", "balanced")).strip().lower()
        tactics = {str(item).strip().lower() for item in (profile.get("tactics") or [])}
        traits = {str(item).strip().lower() for item in (profile.get("traits") or [])}

        attack = midfield = defense = depth = fitness = 0.0

        if mentality in {"attacking", "pressing"}:
            attack += 1.0
            midfield += 0.35
            defense -= 0.2
        elif mentality in {"defensive", "pragmatic"}:
            defense += 0.95
            midfield += 0.3
            attack -= 0.15
        elif mentality in {"technical", "possession"}:
            midfield += 1.0
            attack += 0.35
        elif mentality == "physical":
            attack += 0.45
            defense += 0.3
            fitness += 0.8

        if {"high_press_attack", "gegenpress"} & tactics:
            attack += 0.65
            midfield += 0.45
            fitness -= 0.15
        if {"compact_midblock", "low_block_counter", "park_the_bus"} & tactics:
            defense += 0.7
        if "counter_attack" in tactics:
            attack += 0.45
            defense += 0.15
        if {"tiki_taka", "possession_control", "technical_build_up"} & tactics:
            midfield += 0.55
            attack += 0.25
        if "set_piece_focus" in tactics:
            attack += 0.25
            defense += 0.15

        if {"technical_coaching", "expressive_freedom"} & traits:
            attack += 0.35
            midfield += 0.45
        if {"defensive_organization", "strict_structure"} & traits:
            defense += 0.75
        if {"develops_young_players", "academy_promotion_bias"} & traits:
            depth += 0.45
        if "tactical_flexibility" in traits:
            midfield += 0.35
            defense += 0.2
        if "quick_substitution" in traits:
            depth += 0.85
            fitness += 0.55
        if "late_substitution" in traits:
            depth -= 0.15
            fitness -= 0.2
        if "boosts_physicality_focus" in traits:
            fitness += 0.8
            defense += 0.15

        return (
            self._clamp(attack, -2.0, 2.0),
            self._clamp(midfield, -2.0, 2.0),
            self._clamp(defense, -2.0, 2.0),
            self._clamp(depth, -1.5, 1.5),
            self._clamp(fitness, -1.5, 1.5),
        )

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
