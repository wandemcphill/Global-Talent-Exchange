from __future__ import annotations

from dataclasses import dataclass
from random import Random

from app.match_engine.reality_engine.match_state import MatchState
from app.match_engine.reality_engine.roles import resolve_role_profile
from app.match_engine.reality_engine.tactics import TacticalContext
from app.match_engine.simulation.models import InternalPlayer, PlayerRole


@dataclass(frozen=True, slots=True)
class PossessionProgress:
    final_third_entry: bool
    route: str
    progression_score: float
    turnover_risk: float
    pressure: float
    chance_family: str


@dataclass(frozen=True, slots=True)
class ShotProfile:
    shot_type: str
    route: str
    distance: float
    angle: float
    pressure: float
    defender_proximity: float
    goalkeeper_positioning: float
    transition_speed: float
    body_part: str
    is_set_piece: bool
    assisted: bool


class EventEngine:
    def progress_possession(
        self,
        state: MatchState,
        tactical_context: TacticalContext,
        rng: Random,
    ) -> PossessionProgress:
        attacking = state.attacking_team()
        defending = state.defending_team()
        attacking_context = tactical_context.for_side(state.possession_side)
        defending_context = tactical_context.for_side("away" if state.possession_side == "home" else "home")
        progression_score = self._clamp(
            0.44
            + ((attacking_context.midfield_control - defending_context.midfield_control) / 280.0)
            + ((attacking_context.press_resistance - defending_context.press_intensity) / 320.0)
            + ((attacking_context.progression_bias - 1.0) * 0.42)
            + (attacking_context.game_state_aggression * 0.22)
            + rng.uniform(-0.06, 0.06),
            0.12,
            0.92,
        )
        final_third_entry = rng.random() < progression_score
        pressure = self._clamp(
            (defending_context.press_intensity / 100.0)
            - ((attacking_context.press_resistance - 60.0) / 200.0)
            + rng.uniform(-0.04, 0.04),
            0.08,
            0.94,
        )
        turnover_risk = self._clamp(
            0.22
            + (pressure * 0.32)
            - ((attacking_context.progression_bias - 1.0) * 0.14)
            + (0.04 if not final_third_entry else -0.02),
            0.10,
            0.70,
        )
        route = self._weighted_choice(
            [
                ("transition", 1.00 + ((tactical_context.transition_intensity - 0.40) * 1.4)),
                ("central_combine", 1.05 + ((attacking_context.midfield_control - 60.0) / 90.0)),
                ("wide_overlap", 0.90 + (attacking_context.width * 0.70)),
                ("set_piece", 0.55 + (attacking_context.set_piece_threat * 0.80)),
                ("press_break", 0.75 + ((attacking_context.press_resistance - defending_context.press_intensity) / 120.0)),
            ],
            rng,
        )
        chance_family = self._chance_family(
            route=route,
            attacking=attacking,
            defending=defending,
            minute=state.minute,
            final_third_entry=final_third_entry,
            rng=rng,
        )
        return PossessionProgress(
            final_third_entry=final_third_entry,
            route=route,
            progression_score=progression_score,
            turnover_risk=turnover_risk,
            pressure=pressure,
            chance_family=chance_family,
        )

    def generate_shot(
        self,
        *,
        state: MatchState,
        tactical_context: TacticalContext,
        shooter: InternalPlayer,
        keeper_positioning: float,
        possession: PossessionProgress,
        assisted: bool,
        rng: Random,
    ) -> ShotProfile:
        attacking_context = tactical_context.for_side(state.possession_side)
        body_part = self._body_part_for_chance(shooter=shooter, chance_family=possession.chance_family, rng=rng)
        shot_type = possession.chance_family
        if possession.chance_family == "through_ball_one_on_one":
            distance = rng.uniform(8.0, 15.0)
            angle = rng.uniform(0.55, 0.96)
        elif possession.chance_family == "cutback":
            distance = rng.uniform(10.0, 16.0)
            angle = rng.uniform(0.45, 0.82)
        elif possession.chance_family in {"set_piece_header", "back_post_header"}:
            distance = rng.uniform(6.0, 13.5)
            angle = rng.uniform(0.22, 0.68)
        elif possession.chance_family == "long_range_effort":
            distance = rng.uniform(18.0, 30.0)
            angle = rng.uniform(0.08, 0.42)
        elif possession.chance_family == "defensive_error":
            distance = rng.uniform(9.0, 16.0)
            angle = rng.uniform(0.42, 0.86)
        elif possession.chance_family == "counterattack":
            distance = rng.uniform(11.0, 20.0)
            angle = rng.uniform(0.38, 0.80)
        elif possession.chance_family == "late_siege":
            distance = rng.uniform(11.0, 19.0)
            angle = rng.uniform(0.30, 0.70)
        else:
            distance = rng.uniform(10.0, 22.0)
            angle = rng.uniform(0.20, 0.72)

        role_profile = resolve_role_profile(shooter)
        pressure = self._clamp(
            possession.pressure
            + (possession.turnover_risk * 0.22)
            - ((role_profile.shot_quality - 1.0) * 0.18)
            - ((shooter.composure - 60.0) / 240.0),
            0.06,
            0.94,
        )
        defender_proximity = self._clamp(
            0.26
            + (pressure * 0.36)
            + ((tactical_context.for_side("away" if state.possession_side == "home" else "home").defensive_compactness - 60.0) / 220.0)
            - ((role_profile.transition - 1.0) * 0.12)
            + rng.uniform(-0.06, 0.06),
            0.08,
            0.96,
        )
        transition_speed = self._clamp(
            (possession.progression_score * 0.58)
            + ((attacking_context.progression_bias - 1.0) * 0.65)
            + ((shooter.pace - 50.0) / 100.0)
            + ((role_profile.transition - 1.0) * 0.28),
            0.08,
            0.98,
        )
        return ShotProfile(
            shot_type=shot_type,
            route=possession.route,
            distance=distance,
            angle=angle,
            pressure=pressure,
            defender_proximity=defender_proximity,
            goalkeeper_positioning=self._clamp(keeper_positioning / 100.0, 0.18, 0.95),
            transition_speed=transition_speed,
            body_part=body_part,
            is_set_piece=possession.route == "set_piece",
            assisted=assisted,
        )

    def on_target_probability(self, shot: ShotProfile, shooter: InternalPlayer) -> float:
        role_profile = resolve_role_profile(shooter)
        body_part_adjustment = {
            "header": -0.08,
            "foot": 0.0,
            "volley": -0.03,
            "weak_foot": -0.10,
        }.get(shot.body_part, 0.0)
        return self._clamp(
            0.28
            + ((shooter.finishing - 55.0) / 160.0)
            + ((shooter.technique - 55.0) / 250.0)
            + ((role_profile.shot_quality - 1.0) * 0.18)
            - (shot.pressure * 0.22)
            - max(0.0, shot.distance - 18.0) / 90.0
            + body_part_adjustment,
            0.12,
            0.88,
        )

    def _chance_family(
        self,
        *,
        route: str,
        attacking,
        defending,
        minute: int,
        final_third_entry: bool,
        rng: Random,
    ) -> str:
        if route == "set_piece":
            return "set_piece_header" if rng.random() < 0.58 else "back_post_header"
        if not final_third_entry:
            return "long_range_effort"
        score_delta = attacking.stats.goals - defending.stats.goals
        options = [
            ("through_ball_one_on_one", 1.02 + (attacking.strength.attack / 180.0)),
            ("cutback", 0.98 + (attacking.tactics.width / 180.0)),
            ("penalty_box_scramble", 0.80 + (0.20 if minute >= 70 else 0.0)),
            ("counterattack", 0.88 + (0.18 if route in {"transition", "press_break"} else 0.0)),
            ("near_post_finish", 0.72 + (attacking.tactics.tempo / 240.0)),
        ]
        if minute >= 78 and score_delta <= 0 and attacking.is_home:
            options.append(("late_siege", 0.96 + attacking.home_advantage_score / 10.0))
        if defending.fatigue_level >= 48 or defending.stats.red_cards > 0:
            options.append(("defensive_error", 0.78 + defending.fatigue_level / 200.0))
        return self._weighted_choice(options, rng)

    def _body_part_for_chance(self, *, shooter: InternalPlayer, chance_family: str, rng: Random) -> str:
        if chance_family in {"set_piece_header", "back_post_header"}:
            return "header"
        if shooter.role is PlayerRole.FORWARD and rng.random() < 0.10:
            return "volley"
        if shooter.technique < 62 and rng.random() < 0.12:
            return "weak_foot"
        return "foot"

    @staticmethod
    def _weighted_choice(options: list[tuple[str, float]], rng: Random) -> str:
        total = sum(max(weight, 0.01) for _, weight in options)
        cursor = rng.uniform(0.0, total)
        running = 0.0
        for value, weight in options:
            running += max(weight, 0.01)
            if running >= cursor:
                return value
        return options[-1][0]

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
