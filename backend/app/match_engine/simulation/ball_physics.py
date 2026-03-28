from __future__ import annotations

import math
from dataclasses import dataclass
from hashlib import sha256

from app.match_engine.simulation.models import InternalPlayer

GRAVITY = -9.81
AIR_DRAG = 0.992
GROUND_DRAG = 0.88
SPIN_FACTOR = 0.0014
BOUNCE_DAMPING = 0.68
FIELD_LENGTH_METERS = 105.0
FIELD_WIDTH_METERS = 68.0


@dataclass(slots=True)
class _BallState:
    time: float
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float


class BallPhysicsEngine:
    def build_shot_profile(
        self,
        *,
        shooter: InternalPlayer,
        creator: InternalPlayer | None,
        chance_family: str,
        action_type: str,
        pressure: float,
    ) -> dict[str, object]:
        technique = shooter.technique / 100.0
        composure = shooter.composure / 100.0
        finishing = shooter.finishing / 100.0
        creator_technique = (creator.technique / 100.0) if creator is not None else technique
        motion = self._motion_for_family(chance_family=chance_family, action_type=action_type)
        spin_sign = self._spin_sign(f"{shooter.player_id}:{chance_family}:{action_type}")

        power = self._clamp(
            0.78
            + (finishing * 0.34)
            + (technique * 0.22)
            + (0.06 if action_type in {"shoot", "dribble"} else 0.02 if action_type == "run_into_space" else -0.03)
            - (pressure * 0.08),
            0.68,
            1.42,
        )
        elevation = self._clamp(
            {
                "counterattack": 0.24,
                "through_ball_one_on_one": 0.18,
                "cutback": 0.16,
                "set_piece_header": 0.54,
                "back_post_header": 0.50,
                "penalty_box_scramble": 0.14,
                "long_range_effort": 0.32,
                "near_post_finish": 0.18,
                "late_siege": 0.22,
                "defensive_error": 0.18,
            }.get(chance_family, 0.20)
            + (0.18 if motion in {"cross", "lob"} else 0.0)
            + ((creator_technique - 0.5) * 0.10),
            0.08,
            0.82,
        )
        sidespin = round(
            spin_sign
            * self._clamp(
                0.55
                + (technique * 2.8)
                + (0.85 if chance_family in {"long_range_effort", "cutback"} else 0.0)
                + (0.35 if action_type == "pass" else 0.0),
                0.45,
                4.8,
            ),
            3,
        )
        topspin = round(
            self._clamp(
                0.45
                + (composure * 1.9)
                + (0.90 if chance_family == "long_range_effort" else 0.25)
                - (0.35 if motion == "cross" else 0.0),
                -1.5,
                4.2,
            ),
            3,
        )
        lift_spin = round(
            self._clamp(
                -0.25
                + (creator_technique * 1.6)
                + (0.65 if motion in {"cross", "lob"} else 0.0),
                -1.8,
                2.8,
            ),
            3,
        )
        curve = self._clamp(abs(sidespin) / 4.6, 0.0, 1.0)
        dip = self._clamp(max(0.0, topspin) / 4.0, 0.0, 1.0)
        control = self._clamp((technique * 0.55) + (composure * 0.45) - (pressure * 0.12), 0.0, 1.0)
        deception = self._clamp((curve * 0.35) + (dip * 0.30) + (control * 0.35), 0.0, 1.0)

        return {
            "motion": motion,
            "power": round(power, 3),
            "elevation": round(elevation, 3),
            "curve": round(curve, 3),
            "dip": round(dip, 3),
            "control": round(control, 3),
            "deception": round(deception, 3),
            "spin": {"x": lift_spin, "y": topspin, "z": sidespin},
        }

    def default_profile(self, *, render_type: str, chance_family: str) -> dict[str, object]:
        motion = self._motion_for_render_type(render_type=render_type, chance_family=chance_family)
        elevation = 0.30 if motion in {"cross", "lob"} else 0.18 if motion == "shot" else 0.08
        power = 1.08 if motion == "shot" else 0.94
        return {
            "motion": motion,
            "power": round(power, 3),
            "elevation": round(elevation, 3),
            "curve": 0.32 if motion in {"shot", "cross"} else 0.12,
            "dip": 0.26 if motion == "shot" else 0.10,
            "control": 0.62,
            "deception": 0.40 if motion == "shot" else 0.22,
            "spin": {"x": 0.4 if motion == "lob" else 0.1, "y": 0.8 if motion == "shot" else 0.2, "z": 1.2 if motion == "shot" else 0.4},
        }

    def render_payload(
        self,
        *,
        origin: dict[str, float],
        target: dict[str, float],
        profile: dict[str, object],
        render_type: str,
        outcome: str,
    ) -> dict[str, object]:
        motion = str(profile.get("motion") or self._motion_for_render_type(render_type=render_type, chance_family="default"))
        power = float(profile.get("power", 1.0) or 1.0)
        elevation = float(profile.get("elevation", 0.18) or 0.18)
        spin = profile.get("spin")
        spin_vector = self._spin_vector(spin)
        samples = self._simulate_path(
            origin=origin,
            target=target,
            power=power,
            elevation=elevation,
            spin=spin_vector,
            outcome=outcome,
        )
        if not samples:
            samples = [self._state(0.0, origin["x"], origin["y"], 0.0, 0.0, 0.0, 0.0)]

        collisions = self._collisions(samples=samples, outcome=outcome)
        trajectory = [
            {
                "t": round(state.time, 3),
                "x": round(self._meters_to_norm_x(state.x), 2),
                "y": round(self._meters_to_norm_y(state.y), 2),
                "z": round(max(0.0, state.z), 2),
            }
            for state in self._sample_states(samples, target_points=7)
        ]
        max_height = max(state.z for state in samples)
        launch = samples[0]
        return {
            "motion": motion,
            "height": round(self._clamp(max_height / 4.0, 0.04, 1.25), 2),
            "speed": round(power, 2),
            "spin": {axis: round(value, 3) for axis, value in spin_vector.items()},
            "velocity": {
                "x": round(launch.vx, 3),
                "y": round(launch.vy, 3),
                "z": round(launch.vz, 3),
            },
            "curve": round(float(profile.get("curve", 0.0) or 0.0), 3),
            "dip": round(float(profile.get("dip", 0.0) or 0.0), 3),
            "control": round(float(profile.get("control", 0.0) or 0.0), 3),
            "deception": round(float(profile.get("deception", 0.0) or 0.0), 3),
            "max_height": round(max_height, 2),
            "hang_time": round(samples[-1].time, 3),
            "bounces": sum(1 for item in collisions if item["type"] == "ground"),
            "collisions": collisions,
            "trajectory": trajectory,
        }

    def _simulate_path(
        self,
        *,
        origin: dict[str, float],
        target: dict[str, float],
        power: float,
        elevation: float,
        spin: dict[str, float],
        outcome: str,
    ) -> list[_BallState]:
        origin_x = self._norm_to_meters_x(origin["x"])
        origin_y = self._norm_to_meters_y(origin["y"])
        target_x = self._norm_to_meters_x(target["x"])
        target_y = self._norm_to_meters_y(target["y"])
        dx = target_x - origin_x
        dy = target_y - origin_y
        distance = max(1.0, math.hypot(dx, dy))
        speed = max(14.0, min(34.0, 18.0 + (power * 12.0)))
        direction_x = dx / distance
        direction_y = dy / distance
        vx = direction_x * speed
        vy = direction_y * speed
        vz = max(0.8, (1.4 + (elevation * 8.0)) * (0.78 if outcome == "save" else 1.0))
        duration = self._clamp((distance / speed) * (1.0 + (elevation * 0.22)), 0.45, 2.8)
        states: list[_BallState] = []
        dt = 0.05
        time = 0.0
        position_x = origin_x
        position_y = origin_y
        position_z = 0.12
        save_triggered = False
        post_triggered = False

        while time <= duration + 0.001:
            states.append(self._state(time, position_x, position_y, position_z, vx, vy, vz))

            ax = SPIN_FACTOR * ((spin["y"] * vz) - (spin["z"] * vy))
            ay = SPIN_FACTOR * ((spin["z"] * vx) - (spin["x"] * vz))
            az = SPIN_FACTOR * ((spin["x"] * vy) - (spin["y"] * vx))

            vz += (GRAVITY + az) * dt
            vx = (vx + (ax * dt)) * AIR_DRAG
            vy = (vy + (ay * dt)) * AIR_DRAG

            position_x += vx * dt
            position_y += vy * dt
            position_z += vz * dt

            if position_z <= 0.0:
                position_z = 0.0
                if abs(vz) < 1.0:
                    vz = 0.0
                    vx *= GROUND_DRAG
                    vy *= GROUND_DRAG
                else:
                    vz = abs(vz) * BOUNCE_DAMPING
                    vx *= GROUND_DRAG
                    vy *= GROUND_DRAG

            if not save_triggered and outcome == "save" and time >= (duration * 0.62):
                vx *= -0.42
                vy *= -0.36
                vz = max(1.0, abs(vz) * 0.74)
                save_triggered = True
            if not post_triggered and outcome == "post" and time >= (duration * 0.82):
                vx *= -0.48
                vy *= 0.72
                vz = max(0.6, abs(vz) * 0.64)
                post_triggered = True

            time += dt

        final_z = 0.0 if outcome in {"goal", "miss", "post"} else min(1.4, max(0.0, position_z))
        states.append(self._state(duration, target_x, target_y, final_z, vx, vy, vz))
        return states

    def _collisions(self, *, samples: list[_BallState], outcome: str) -> list[dict[str, object]]:
        collisions: list[dict[str, object]] = []
        for previous, current in zip(samples, samples[1:], strict=False):
            if previous.z > 0.0 and current.z == 0.0:
                collisions.append({"type": "ground", "time": round(current.time, 3)})
        if outcome == "save":
            collisions.append({"type": "goalkeeper", "time": round(samples[-1].time * 0.62, 3)})
        if outcome == "post":
            collisions.append({"type": "woodwork", "time": round(samples[-1].time * 0.82, 3)})
        return collisions

    def _sample_states(self, samples: list[_BallState], *, target_points: int) -> list[_BallState]:
        if len(samples) <= target_points:
            return samples
        stride = max(1, len(samples) // max(1, target_points - 1))
        picked = [samples[index] for index in range(0, len(samples), stride)]
        if picked[-1] is not samples[-1]:
            picked.append(samples[-1])
        return picked[: target_points - 1] + [samples[-1]]

    def _motion_for_family(self, *, chance_family: str, action_type: str) -> str:
        if chance_family in {"set_piece_header", "back_post_header"}:
            return "cross"
        if chance_family == "long_range_effort":
            return "lob" if action_type == "hold" else "shot"
        if action_type == "pass":
            return "pass"
        return "shot"

    def _motion_for_render_type(self, *, render_type: str, chance_family: str) -> str:
        if render_type == "corner":
            return "cross"
        if render_type in {"free_kick", "foul"}:
            return "lob"
        if render_type == "pass":
            return "cross" if chance_family in {"set_piece_header", "back_post_header"} else "pass"
        return "shot"

    def _spin_vector(self, value: object) -> dict[str, float]:
        if not isinstance(value, dict):
            return {"x": 0.1, "y": 0.3, "z": 0.8}
        return {
            "x": float(value.get("x", 0.1) or 0.1),
            "y": float(value.get("y", 0.3) or 0.3),
            "z": float(value.get("z", 0.8) or 0.8),
        }

    def _spin_sign(self, seed: str) -> float:
        digest = sha256(seed.encode("utf-8")).hexdigest()[:8]
        return -1.0 if int(digest, 16) % 2 == 0 else 1.0

    def _norm_to_meters_x(self, value: float) -> float:
        return (value / 100.0) * FIELD_LENGTH_METERS

    def _norm_to_meters_y(self, value: float) -> float:
        return (value / 100.0) * FIELD_WIDTH_METERS

    def _meters_to_norm_x(self, value: float) -> float:
        return self._clamp((value / FIELD_LENGTH_METERS) * 100.0, 0.0, 100.0)

    def _meters_to_norm_y(self, value: float) -> float:
        return self._clamp((value / FIELD_WIDTH_METERS) * 100.0, 0.0, 100.0)

    def _state(self, time: float, x: float, y: float, z: float, vx: float, vy: float, vz: float) -> _BallState:
        return _BallState(time=time, x=x, y=y, z=max(0.0, z), vx=vx, vy=vy, vz=vz)

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
