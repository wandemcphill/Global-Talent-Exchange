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
        context = team.club_context or {}

        attack = self._weighted_line_strength(starters, selector="attack")
        midfield = self._weighted_line_strength(starters, selector="midfield")
        defense = self._weighted_line_strength(starters, selector="defense")
        goalkeeping = max((player.goalkeeping_value() for player in starters if player.role is PlayerRole.GOALKEEPER), default=40.0)
        depth = self._depth_value(starters, bench)
        discipline = fmean(player.discipline for player in starters)
        fitness = fmean(player.fitness for player in starters)
        chemistry = self._chemistry(team)
        recent_form = self._blend_context(
            fmean(player.recent_form for player in starters),
            float(context.get("recent_form", 58)),
            weight=0.72,
        )
        morale = self._blend_context(
            fmean(player.morale for player in starters),
            float(context.get("morale", 60)),
            weight=0.74,
        )
        motivation = self._blend_context(
            fmean(player.motivation for player in starters),
            float(context.get("motivation", 60)),
            weight=0.72,
        )
        fatigue_load = self._fatigue_load(team)
        coach_quality, tactical_quality, adaptability = self._coach_and_tactical_quality(team)
        tactical_cohesion = self._tactical_cohesion(team, chemistry, tactical_quality, adaptability)

        style_attack, style_midfield, style_defense = self._style_adjustments(team.tactics.style)
        squad_balance = self._squad_balance_bonus(team)
        manager_attack, manager_midfield, manager_defense, manager_depth, manager_fitness = self._manager_adjustments(team)
        context_attack = (float(context.get("competition_tier", 60)) - 60.0) * 0.04
        context_defense = (float(context.get("club_tier", 60)) - 60.0) * 0.04
        base_home_edge = 0.85 if is_home else 0.0

        fatigue_drag = max(0.0, (fatigue_load - 45.0) * 0.10)
        form_boost = (recent_form - 55.0) * 0.12
        morale_boost = (morale - 55.0) * 0.08
        tactical_boost = (tactical_cohesion - 60.0) * 0.08

        attack = self._clamp(
            attack
            + style_attack
            + ((team.tactics.tempo - 50) * 0.08)
            + ((team.tactics.pressing - 50) * 0.05)
            + squad_balance
            + manager_attack
            + context_attack
            + form_boost
            + morale_boost
            + tactical_boost
            + base_home_edge,
            20.0,
            99.0,
        )
        midfield = self._clamp(
            midfield
            + style_midfield
            + ((team.tactics.pressing - 50) * 0.07)
            + (chemistry - 60.0) * 0.09
            + (coach_quality - 60.0) * 0.05
            + manager_midfield
            + (base_home_edge * 0.7),
            20.0,
            99.0,
        )
        defense = self._clamp(
            defense
            + style_defense
            - ((team.tactics.aggression - 50) * 0.04)
            + manager_defense
            + context_defense
            + (chemistry - 60.0) * 0.06
            + (coach_quality - 60.0) * 0.05
            + ((adaptability - 60.0) * 0.04),
            20.0,
            99.0,
        )
        depth = self._clamp(depth + manager_depth + ((coach_quality - 60.0) * 0.06), 20.0, 99.0)
        fitness = self._clamp(fitness + manager_fitness - fatigue_drag + ((morale - 55.0) * 0.04), 20.0, 99.0)
        chemistry = self._clamp(chemistry + squad_balance + ((coach_quality - 60.0) * 0.05), 20.0, 99.0)
        tactical_cohesion = self._clamp(tactical_cohesion + ((chemistry - 60.0) * 0.05), 20.0, 99.0)
        coach_quality = self._clamp(coach_quality, 20.0, 99.0)
        tactical_quality = self._clamp(tactical_quality, 20.0, 99.0)
        adaptability = self._clamp(adaptability, 20.0, 99.0)
        recent_form = self._clamp(recent_form, 20.0, 99.0)
        morale = self._clamp(morale, 20.0, 99.0)
        motivation = self._clamp(motivation + (base_home_edge * 2.0), 20.0, 99.0)
        fatigue_load = self._clamp(fatigue_load, 5.0, 99.0)

        upset_resistance = self._clamp(
            (coach_quality * 0.28)
            + (tactical_cohesion * 0.20)
            + (morale * 0.16)
            + (chemistry * 0.16)
            + (goalkeeping * 0.10)
            + (depth * 0.10),
            20.0,
            99.0,
        )
        upset_punch = self._clamp(
            (attack * 0.26)
            + (goalkeeping * 0.18)
            + (motivation * 0.16)
            + (recent_form * 0.16)
            + (tactical_quality * 0.14)
            + ((100.0 - fatigue_load) * 0.10),
            20.0,
            99.0,
        )
        overall = self._clamp(
            (attack * 0.22)
            + (midfield * 0.16)
            + (defense * 0.16)
            + (goalkeeping * 0.10)
            + (depth * 0.08)
            + (chemistry * 0.08)
            + (tactical_cohesion * 0.06)
            + (recent_form * 0.04)
            + (morale * 0.03)
            + (coach_quality * 0.04)
            + (tactical_quality * 0.03),
            20.0,
            99.0,
        )
        return TeamStrengthSnapshot(
            overall=round(overall, 2),
            attack=round(attack, 2),
            midfield=round(midfield, 2),
            defense=round(defense, 2),
            goalkeeping=round(goalkeeping, 2),
            depth=round(depth, 2),
            discipline=round(discipline, 2),
            fitness=round(fitness, 2),
            chemistry=round(chemistry, 2),
            tactical_cohesion=round(tactical_cohesion, 2),
            recent_form=round(recent_form, 2),
            morale=round(morale, 2),
            motivation=round(motivation, 2),
            fatigue_load=round(fatigue_load, 2),
            coach_quality=round(coach_quality, 2),
            tactical_quality=round(tactical_quality, 2),
            adaptability=round(adaptability, 2),
            upset_resistance=round(upset_resistance, 2),
            upset_punch=round(upset_punch, 2),
        )

    def _weighted_line_strength(self, starters, *, selector: str) -> float:
        values: list[float] = []
        for player in starters:
            if selector == "attack":
                base = player.attacking_value()
                multiplier = {
                    PlayerRole.GOALKEEPER: 0.25,
                    PlayerRole.DEFENDER: 0.72,
                    PlayerRole.MIDFIELDER: 1.02,
                    PlayerRole.FORWARD: 1.18,
                }[player.role]
            elif selector == "midfield":
                base = player.control_value()
                multiplier = {
                    PlayerRole.GOALKEEPER: 0.18,
                    PlayerRole.DEFENDER: 0.82,
                    PlayerRole.MIDFIELDER: 1.20,
                    PlayerRole.FORWARD: 0.74,
                }[player.role]
            else:
                base = player.defensive_value()
                multiplier = {
                    PlayerRole.GOALKEEPER: 0.38,
                    PlayerRole.DEFENDER: 1.20,
                    PlayerRole.MIDFIELDER: 0.92,
                    PlayerRole.FORWARD: 0.48,
                }[player.role]
            values.append(base * multiplier)
        return fmean(values) if values else 40.0

    def _depth_value(self, starters, bench) -> float:
        if not bench:
            return fmean(player.overall for player in starters)
        bench_scores = sorted(
            (
                (player.overall * 0.62)
                + (player.consistency * 0.12)
                + (player.recent_form * 0.12)
                + (player.fitness * 0.14)
            )
            for player in bench
        )
        return fmean(bench_scores[-5:])

    def _chemistry(self, team: MatchTeamProfile) -> float:
        context = team.club_context or {}
        starter_values = (
            (player.consistency * 0.22)
            + (player.decision_making * 0.22)
            + (player.morale * 0.18)
            + (player.leadership * 0.12)
            + (player.discipline * 0.12)
            + (player.recent_form * 0.14)
            for player in team.starters
        )
        base = fmean(starter_values)
        return self._blend_context(base, float(context.get("team_chemistry", 62)), weight=0.74)

    def _tactical_cohesion(
        self,
        team: MatchTeamProfile,
        chemistry: float,
        tactical_quality: float,
        adaptability: float,
    ) -> float:
        decision_layer = fmean(player.decision_making for player in team.starters)
        consistency_layer = fmean(player.consistency for player in team.starters)
        style_fit = {
            TacticalStyle.ATTACKING: 1.6,
            TacticalStyle.BALANCED: 1.0,
            TacticalStyle.DEFENSIVE: 1.3,
        }[team.tactics.style]
        return self._clamp(
            (decision_layer * 0.28)
            + (consistency_layer * 0.20)
            + (chemistry * 0.20)
            + (tactical_quality * 0.20)
            + (adaptability * 0.10)
            + (team.tactics.game_management * 0.02)
            + style_fit,
            20.0,
            99.0,
        )

    def _fatigue_load(self, team: MatchTeamProfile) -> float:
        context = team.club_context or {}
        player_load = fmean(
            (player.fatigue_load * 0.60) + ((100.0 - player.stamina_curve) * 0.18) + ((100.0 - player.fitness) * 0.22)
            for player in team.starters
        )
        tactical_load = max(0.0, ((team.tactics.tempo - 50.0) * 0.18) + ((team.tactics.pressing - 50.0) * 0.14))
        context_load = (float(context.get("travel_load", 28)) * 0.35) + (float(context.get("schedule_pressure", 34)) * 0.30)
        return player_load + tactical_load + context_load

    def _coach_and_tactical_quality(self, team: MatchTeamProfile) -> tuple[float, float, float]:
        profile = team.manager_profile or {}
        rarity = str(profile.get("rarity", "standard")).strip().lower()
        substitution_tendency = str(profile.get("substitution_tendency", "balanced")).strip().lower()
        traits = {str(item).strip().lower() for item in (profile.get("traits") or [])}
        tactics = {str(item).strip().lower() for item in (profile.get("tactics") or [])}

        rarity_bonus = {
            "icon": 8.0,
            "legendary": 7.0,
            "epic": 5.0,
            "rare": 3.0,
            "standard": 0.0,
        }.get(rarity, 0.0)
        coach_quality = 56.0 + rarity_bonus
        tactical_quality = float(team.tactics.tactical_quality)
        adaptability = float(team.tactics.adaptability)

        if substitution_tendency == "proactive":
            coach_quality += 2.5
            adaptability += 2.0
        elif substitution_tendency == "late":
            coach_quality -= 1.0
            adaptability -= 1.5

        if {"great_motivator", "man_management", "develops_young_players"} & traits:
            coach_quality += 2.2
        if {"defensive_organization", "strict_structure"} & traits:
            tactical_quality += 2.4
        if {"tactical_flexibility", "in_game_adjustments"} & traits:
            tactical_quality += 2.0
            adaptability += 4.0
        if {"high_press_attack", "gegenpress", "tiki_taka", "possession_control"} & tactics:
            tactical_quality += 1.2
        if {"low_block_counter", "compact_midblock", "park_the_bus"} & tactics:
            adaptability += 1.2

        return coach_quality, tactical_quality, adaptability

    def _style_adjustments(self, style: TacticalStyle) -> tuple[float, float, float]:
        if style is TacticalStyle.ATTACKING:
            return 3.5, 1.8, -2.1
        if style is TacticalStyle.DEFENSIVE:
            return -2.6, 0.9, 3.8
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
            balance += 0.8
        else:
            balance -= min(abs(role_counts[PlayerRole.GOALKEEPER] - 1) * 1.4, 2.8)

        for role, minimum, maximum, reward in (
            (PlayerRole.DEFENDER, 3, 5, 0.7),
            (PlayerRole.MIDFIELDER, 2, 5, 0.7),
            (PlayerRole.FORWARD, 1, 3, 0.55),
        ):
            count = role_counts[role]
            if minimum <= count <= maximum:
                balance += reward
            else:
                deficit = minimum - count if count < minimum else count - maximum
                balance -= min(deficit * 0.7, 1.8)

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
            balance -= (outfield_gap - 3) * 0.3
        return self._clamp(balance, -3.0, 3.0)

    def _manager_adjustments(self, team: MatchTeamProfile) -> tuple[float, float, float, float, float]:
        profile = team.manager_profile or {}
        if not profile:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        mentality = str(profile.get("mentality", "balanced")).strip().lower()
        tactics = {str(item).strip().lower() for item in (profile.get("tactics") or [])}
        traits = {str(item).strip().lower() for item in (profile.get("traits") or [])}

        attack = midfield = defense = depth = fitness = 0.0
        if mentality in {"attacking", "pressing"}:
            attack += 0.9
            midfield += 0.4
            defense -= 0.15
        elif mentality in {"defensive", "pragmatic"}:
            defense += 0.9
            midfield += 0.3
        elif mentality in {"technical", "possession"}:
            midfield += 0.95
            attack += 0.3
        elif mentality == "balanced":
            defense += 0.15
            midfield += 0.15

        if {"high_press_attack", "gegenpress"} & tactics:
            attack += 0.5
            midfield += 0.35
            fitness -= 0.12
        if {"compact_midblock", "low_block_counter", "park_the_bus"} & tactics:
            defense += 0.65
        if "counter_attack" in tactics:
            attack += 0.4
            defense += 0.1
        if {"tiki_taka", "possession_control", "technical_build_up"} & tactics:
            midfield += 0.55
            attack += 0.2
        if "set_piece_focus" in tactics or "uses set piece" in traits:
            attack += 0.28
            defense += 0.16

        if {"technical_coaching", "expressive_freedom"} & traits:
            attack += 0.32
            midfield += 0.4
        if {"defensive_organization", "strict_structure"} & traits:
            defense += 0.7
        if {"develops_young_players", "academy_promotion_bias", "uses young players"} & traits:
            depth += 0.55
        if "quick_substitution" in traits:
            depth += 0.75
            fitness += 0.45
        if "late_substitution" in traits:
            depth -= 0.1
            fitness -= 0.18
        if {"great motivator", "great_motivator"} & traits:
            fitness += 0.22
            midfield += 0.15

        return (
            self._clamp(attack, -2.0, 2.0),
            self._clamp(midfield, -2.0, 2.0),
            self._clamp(defense, -2.0, 2.0),
            self._clamp(depth, -1.5, 1.5),
            self._clamp(fitness, -1.5, 1.5),
        )

    def _blend_context(self, player_value: float, context_value: float, *, weight: float) -> float:
        return (player_value * weight) + (context_value * (1.0 - weight))

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
