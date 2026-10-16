from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from app.match_engine.reality_engine.match_state import MatchState
from app.match_engine.reality_engine.roles import resolve_role_profile
from app.match_engine.simulation.models import PlayerRole, TeamRuntimeState


@dataclass(frozen=True, slots=True)
class TeamTacticalContext:
    side: str
    midfield_control: float
    press_resistance: float
    progression_bias: float
    press_intensity: float
    defensive_compactness: float
    chance_suppression: float
    width: float
    line_height: float
    game_state_aggression: float
    set_piece_threat: float


@dataclass(frozen=True, slots=True)
class TacticalContext:
    home: TeamTacticalContext
    away: TeamTacticalContext
    average_tempo: float
    transition_intensity: float

    def for_side(self, side: str) -> TeamTacticalContext:
        return self.home if side == "home" else self.away


class TacticalEngine:
    def resolve(self, state: MatchState) -> TacticalContext:
        home = self._team_context(state, side="home")
        away = self._team_context(state, side="away")
        average_tempo = (state.home.tactics.tempo + state.away.tactics.tempo) / 200.0
        transition_intensity = self._clamp(
            0.40
            + ((home.progression_bias + away.progression_bias - 2.0) * 0.24)
            + ((state.home.tactics.tempo + state.away.tactics.tempo - 100.0) / 260.0)
            + ((state.home.tactics.pressing + state.away.tactics.pressing - 100.0) / 320.0),
            0.18,
            0.92,
        )
        return TacticalContext(
            home=home,
            away=away,
            average_tempo=average_tempo,
            transition_intensity=transition_intensity,
        )

    def possession_share(self, state: MatchState, tactical_context: TacticalContext) -> float:
        home = tactical_context.home
        away = tactical_context.away
        home_pressure = (
            (home.midfield_control * 0.56)
            + (home.press_resistance * 0.18)
            + (home.progression_bias * 18.0)
            + (home.game_state_aggression * 8.0)
            - (away.press_intensity * 0.08)
            + (1.4 if state.home.is_home else 0.0)
        )
        away_pressure = (
            (away.midfield_control * 0.56)
            + (away.press_resistance * 0.18)
            + (away.progression_bias * 18.0)
            + (away.game_state_aggression * 8.0)
            - (home.press_intensity * 0.08)
        )
        total = max(1.0, home_pressure + away_pressure)
        return self._clamp(home_pressure / total, 0.30, 0.70)

    def _team_context(self, state: MatchState, *, side: str) -> TeamTacticalContext:
        team = state.team(side)
        opponent = state.opponent(side)
        score_delta = state.score_delta(side)
        outfielders = team.active_outfielders()
        if outfielders:
            buildup_layer = fmean(
                player.control_value() * resolve_role_profile(player).buildup
                for player in outfielders
            )
            press_resistance = fmean(
                (
                    (player.control_value() * 0.48)
                    + (player.technique * 0.24)
                    + (player.decision_making * 0.18)
                    + (player.composure * 0.10)
                )
                * resolve_role_profile(player).buildup
                for player in outfielders
            )
            pressing_layer = fmean(
                player.pressing_value() * resolve_role_profile(player).pressing
                for player in outfielders
            )
            recovery_layer = fmean(
                player.defensive_value() * resolve_role_profile(player).recovery
                for player in outfielders
            )
            set_piece_threat = fmean(
                ((player.aerial_ability * 0.58) + (player.attacking_value() * 0.42))
                * resolve_role_profile(player).aerial
                for player in outfielders
            )
            width_profile = fmean(resolve_role_profile(player).width for player in outfielders)
        else:
            buildup_layer = team.strength.midfield
            press_resistance = team.strength.midfield
            pressing_layer = team.strength.midfield
            recovery_layer = team.strength.defense
            set_piece_threat = team.strength.attack
            width_profile = 1.0

        game_state_aggression = self._game_state_aggression(
            minute=state.minute,
            score_delta=score_delta,
            team=team,
            stage_pressure=state.stage_pressure,
        )
        fatigue_multiplier = self._fatigue_multiplier(team=team, minute=state.minute)
        midfield_control = self._clamp(
            (team.strength.midfield * 0.62)
            + (buildup_layer * 0.38)
            + ((team.tactics.width - 50.0) * 0.04)
            + (game_state_aggression * 12.0)
            - (len(team.red_carded_ids) * 2.2),
            24.0,
            110.0,
        )
        press_intensity = self._clamp(
            (
                ((team.tactics.pressing * 0.52) + (pressing_layer * 0.48))
                * fatigue_multiplier
                * (1.0 + game_state_aggression * 0.18)
            ),
            18.0,
            110.0,
        )
        press_resistance = self._clamp(
            (press_resistance * fatigue_multiplier) + (team.strength.chemistry * 0.08),
            22.0,
            110.0,
        )
        defensive_compactness = self._clamp(
            (
                (team.strength.defense * 0.58)
                + (recovery_layer * 0.24)
                + (team.strength.goalkeeping * 0.12)
                + (opponent.strength.attack * -0.06)
                + ((60.0 - abs(team.tactics.width - 50.0)) * 0.05)
            )
            * fatigue_multiplier
            * (1.0 + max(0.0, score_delta) * 0.04),
            20.0,
            115.0,
        )
        chance_suppression = self._clamp(
            (defensive_compactness * 0.72)
            + (team.strength.goalkeeping * 0.20)
            + (press_intensity * 0.08),
            18.0,
            115.0,
        )
        progression_bias = self._clamp(
            1.0
            + ((team.tactics.tempo - 50.0) / 170.0)
            + ((team.tactics.width - 50.0) / 240.0)
            + ((team.tactics.defensive_line - 50.0) / 280.0)
            + ((buildup_layer - opponent.strength.midfield) / 400.0)
            + ((width_profile - 1.0) * 0.26)
            + (game_state_aggression * 0.22),
            0.72,
            1.38,
        )
        return TeamTacticalContext(
            side=side,
            midfield_control=midfield_control,
            press_resistance=press_resistance,
            progression_bias=progression_bias,
            press_intensity=press_intensity,
            defensive_compactness=defensive_compactness,
            chance_suppression=chance_suppression,
            width=self._clamp((team.tactics.width / 100.0) * width_profile, 0.30, 1.25),
            line_height=self._clamp(team.tactics.defensive_line / 100.0, 0.18, 0.90),
            game_state_aggression=game_state_aggression,
            set_piece_threat=self._clamp(set_piece_threat / 100.0, 0.35, 1.25),
        )

    def _game_state_aggression(
        self,
        *,
        minute: int,
        score_delta: int,
        team: TeamRuntimeState,
        stage_pressure: float,
    ) -> float:
        aggression = 0.0
        if score_delta < 0:
            aggression += 0.12 + (0.04 * abs(score_delta))
            if minute >= 58:
                aggression += 0.08
        elif score_delta > 0 and minute >= 72:
            aggression -= 0.08
        if score_delta == 0 and minute >= 78 and stage_pressure >= 0.40:
            aggression += 0.05
        if team.tactics.mentality.value == "attacking":
            aggression += 0.04
        elif team.tactics.mentality.value == "defensive":
            aggression -= 0.04
        return self._clamp(aggression, -0.18, 0.34)

    def _fatigue_multiplier(self, *, team: TeamRuntimeState, minute: int) -> float:
        return self._clamp(
            1.02
            - max(0.0, (team.fatigue_level - 42.0) / 180.0)
            - max(0, minute - 68) / 600.0,
            0.72,
            1.04,
        )

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
