from __future__ import annotations

import math

from app.match_engine.reality_engine.event_engine import ShotProfile
from app.match_engine.reality_engine.roles import resolve_role_profile
from app.match_engine.simulation.models import InternalPlayer


class XGModel:
    def calculate_xg(
        self,
        shot: ShotProfile,
        *,
        shooter: InternalPlayer,
        keeper: InternalPlayer | None,
    ) -> float:
        role_profile = resolve_role_profile(shooter)
        shot_type_bias = {
            "through_ball_one_on_one": 1.02,
            "cutback": 0.82,
            "counterattack": 0.46,
            "near_post_finish": 0.36,
            "penalty_box_scramble": 0.24,
            "defensive_error": 0.56,
            "late_siege": 0.34,
            "set_piece_header": 0.12,
            "back_post_header": 0.18,
            "long_range_effort": -0.68,
        }.get(shot.shot_type, 0.18)
        body_part_bias = {
            "foot": 0.08,
            "header": -0.22,
            "volley": -0.06,
            "weak_foot": -0.18,
        }.get(shot.body_part, 0.0)
        keeper_drag = 0.0
        if keeper is not None:
            keeper_profile = resolve_role_profile(keeper)
            keeper_drag = ((keeper.goalkeeping_value() - 52.0) / 210.0) * keeper_profile.goalkeeping
        z = (
            (1.55 * shot.angle)
            - (0.098 * shot.distance)
            - (0.62 * shot.pressure)
            - (0.54 * shot.defender_proximity)
            - (0.34 * shot.goalkeeper_positioning)
            - keeper_drag
            + shot_type_bias
            + body_part_bias
            + ((shot.transition_speed - 0.50) * 0.34)
            + ((shooter.composure - 58.0) / 95.0)
            + ((shooter.technique - 58.0) / 130.0)
            + ((role_profile.shot_quality - 1.0) * 0.60)
        )
        xg = 1.0 / (1.0 + math.exp(-z))
        finishing_multiplier = self._clamp((shooter.finishing / 80.0) * (0.94 + ((role_profile.shot_quality - 1.0) * 0.35)), 0.78, 1.24)
        xg *= finishing_multiplier
        if shot.assisted:
            xg *= 1.04
        if shot.is_set_piece and shot.body_part == "header":
            xg *= 0.94
        return self._clamp(xg, 0.02, 0.88)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
