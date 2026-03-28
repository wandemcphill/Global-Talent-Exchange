from __future__ import annotations

from dataclasses import dataclass
from random import Random

from app.match_engine.simulation.models import InternalPlayer, PlayerRole, TeamRuntimeState


@dataclass(frozen=True, slots=True)
class PlayerDecisionScore:
    action_type: str
    score: float
    success_probability: float


@dataclass(frozen=True, slots=True)
class PlayerDecisionOutcome:
    actor: InternalPlayer
    shooter: InternalPlayer
    creator: InternalPlayer | None
    target: InternalPlayer | None
    action_type: str
    chance_family: str
    score: float
    pressure: float
    quality_modifier: float
    on_target_modifier: float
    goal_modifier: float
    offside_modifier: float
    personality: dict[str, float]
    options: tuple[PlayerDecisionScore, ...]


class PlayerDecisionAI:
    def decide_attacking_action(
        self,
        *,
        attacking: TeamRuntimeState,
        defending: TeamRuntimeState,
        minute: int,
        base_family: str,
        rng: Random,
    ) -> PlayerDecisionOutcome | None:
        candidates = attacking.active_outfielders()
        if not candidates:
            return None

        actor = self._weighted_choice(
            items=candidates,
            weights=[
                max(
                    1.0,
                    (player.control_value() * 0.54)
                    + (player.attacking_value() * 0.28)
                    + (player.off_ball_movement * 0.18)
                    + (10.0 if player.role is PlayerRole.MIDFIELDER else 6.0 if player.role is PlayerRole.FORWARD else 0.0),
                )
                for player in candidates
            ],
            rng=rng,
        )
        if actor is None:
            return None

        personality = self._personality(actor)
        teammates = [player for player in candidates if player.player_id != actor.player_id]
        target = self._weighted_choice(
            items=teammates,
            weights=[
                max(
                    1.0,
                    (player.off_ball_movement * 0.42)
                    + (player.pace * 0.20)
                    + (player.attacking_value() * 0.26)
                    + (10.0 if player.role is PlayerRole.FORWARD else 0.0),
                )
                for player in teammates
            ],
            rng=rng,
        )
        pressure = self._pressure(actor=actor, defending=defending, minute=minute, base_family=base_family)
        options = self._score_actions(
            actor=actor,
            target=target,
            pressure=pressure,
            personality=personality,
            base_family=base_family,
        )
        if not options:
            return None
        ranked = sorted(options, key=lambda item: item.score, reverse=True)
        best = ranked[0]

        creator: InternalPlayer | None = None
        shooter = actor
        family = base_family
        quality_modifier = 0.0
        on_target_modifier = 0.0
        goal_modifier = 0.0
        offside_modifier = 0.0

        if best.action_type == "pass" and target is not None:
            creator = actor
            shooter = target
            family = "cutback" if target.role is PlayerRole.FORWARD and base_family != "long_range_effort" else "near_post_finish"
            quality_modifier = 0.04 + ((best.success_probability - 0.5) * 0.08)
            on_target_modifier = 0.03
            goal_modifier = 0.01
        elif best.action_type == "run_into_space" and target is not None:
            creator = actor
            shooter = target
            family = "through_ball_one_on_one"
            quality_modifier = 0.06 + ((best.success_probability - 0.5) * 0.10)
            on_target_modifier = 0.02
            goal_modifier = 0.02
            offside_modifier = 0.03 + (personality["risk_taking"] * 0.02)
        elif best.action_type == "dribble":
            family = "near_post_finish" if actor.role is PlayerRole.FORWARD else "penalty_box_scramble"
            quality_modifier = 0.03 + (best.success_probability * 0.03)
            on_target_modifier = -0.01 + (personality["composure"] * 0.03)
            goal_modifier = 0.01 + (personality["risk_taking"] * 0.01)
        elif best.action_type == "hold":
            family = "long_range_effort" if actor.role is not PlayerRole.FORWARD else "penalty_box_scramble"
            quality_modifier = -0.05 + (personality["composure"] * 0.02)
            on_target_modifier = -0.03
            goal_modifier = -0.02
        else:
            family = "long_range_effort" if base_family == "long_range_effort" else base_family
            quality_modifier = 0.01 + (personality["selfishness"] * 0.02)
            on_target_modifier = 0.02 + (personality["composure"] * 0.02)
            goal_modifier = 0.02 + (personality["selfishness"] * 0.02)

        return PlayerDecisionOutcome(
            actor=actor,
            shooter=shooter,
            creator=creator,
            target=target,
            action_type=best.action_type,
            chance_family=family,
            score=round(best.score, 3),
            pressure=round(pressure, 3),
            quality_modifier=round(quality_modifier, 3),
            on_target_modifier=round(on_target_modifier, 3),
            goal_modifier=round(goal_modifier, 3),
            offside_modifier=round(offside_modifier, 3),
            personality=personality,
            options=tuple(ranked[:4]),
        )

    def _score_actions(
        self,
        *,
        actor: InternalPlayer,
        target: InternalPlayer | None,
        pressure: float,
        personality: dict[str, float],
        base_family: str,
    ) -> list[PlayerDecisionScore]:
        receiver_value = (
            ((target.off_ball_movement / 100.0) * 0.45)
            + ((target.pace / 100.0) * 0.20)
            + ((target.attacking_value() / 100.0) * 0.35)
            if target is not None
            else 0.0
        )
        shoot_success = self._clamp(
            0.26
            + ((actor.finishing + actor.composure + actor.technique) / 320.0)
            - (pressure * 0.20)
            + (0.04 if actor.role is PlayerRole.FORWARD else 0.0),
            0.08,
            0.88,
        )
        pass_success = self._clamp(
            0.32
            + ((actor.control_value() + actor.creativity) / 280.0)
            + (receiver_value * 0.18)
            - (pressure * 0.18),
            0.10,
            0.94,
        )
        dribble_success = self._clamp(
            0.24
            + ((actor.technique + actor.pace + actor.composure) / 340.0)
            - (pressure * 0.22),
            0.08,
            0.86,
        )
        hold_success = self._clamp(
            0.36
            + ((actor.decision_making + actor.composure) / 300.0)
            - (pressure * 0.10),
            0.16,
            0.90,
        )
        run_success = self._clamp(
            0.28
            + ((actor.creativity + actor.technique) / 330.0)
            + (receiver_value * 0.20)
            - (pressure * 0.20)
            + (0.04 if base_family in {"counterattack", "through_ball_one_on_one"} else 0.0),
            0.10,
            0.90,
        )

        scores = [
            PlayerDecisionScore(
                action_type="shoot",
                score=round(
                    shoot_success
                    * (0.76 + (actor.finishing / 180.0))
                    * (1.0 + (personality["selfishness"] * 0.28)),
                    3,
                ),
                success_probability=round(shoot_success, 3),
            ),
            PlayerDecisionScore(
                action_type="pass",
                score=round(
                    pass_success
                    * (0.72 + (actor.creativity / 190.0))
                    * (1.0 + ((1.0 - personality["selfishness"]) * 0.22)),
                    3,
                ),
                success_probability=round(pass_success, 3),
            ),
            PlayerDecisionScore(
                action_type="dribble",
                score=round(
                    dribble_success
                    * (0.70 + (actor.technique / 210.0))
                    * (1.0 + (personality["risk_taking"] * 0.18)),
                    3,
                ),
                success_probability=round(dribble_success, 3),
            ),
            PlayerDecisionScore(
                action_type="hold",
                score=round(
                    hold_success
                    * (0.66 + (actor.decision_making / 230.0))
                    * (1.0 + ((1.0 - personality["risk_taking"]) * 0.16)),
                    3,
                ),
                success_probability=round(hold_success, 3),
            ),
            PlayerDecisionScore(
                action_type="run_into_space",
                score=round(
                    run_success
                    * (0.68 + ((actor.creativity + actor.technique) / 280.0))
                    * (1.0 + (personality["risk_taking"] * 0.24)),
                    3,
                ),
                success_probability=round(run_success, 3),
            ),
        ]
        if target is None:
            return [score for score in scores if score.action_type not in {"pass", "run_into_space"}]
        return scores

    def _personality(self, player: InternalPlayer) -> dict[str, float]:
        selfishness = self._clamp(
            0.28
            + ((player.finishing - player.creativity) / 180.0)
            + (0.16 if player.role is PlayerRole.FORWARD else -0.04 if player.role is PlayerRole.DEFENDER else 0.0),
            0.10,
            0.92,
        )
        risk_taking = self._clamp(
            0.26
            + ((player.creativity + player.technique - player.discipline) / 220.0)
            + (0.06 if player.role in {PlayerRole.MIDFIELDER, PlayerRole.FORWARD} else 0.0),
            0.08,
            0.94,
        )
        composure = self._clamp((player.composure / 100.0) + ((player.clutch_factor - 50.0) / 250.0), 0.12, 0.98)
        return {
            "selfishness": round(selfishness, 3),
            "risk_taking": round(risk_taking, 3),
            "composure": round(composure, 3),
        }

    def _pressure(
        self,
        *,
        actor: InternalPlayer,
        defending: TeamRuntimeState,
        minute: int,
        base_family: str,
    ) -> float:
        family_bonus = 0.10 if base_family in {"counterattack", "through_ball_one_on_one"} else 0.0
        return self._clamp(
            ((defending.strength.defense - actor.control_value()) / 120.0)
            + (defending.tactics.pressing / 125.0)
            + max(0.0, minute - 68) / 130.0
            - family_bonus,
            0.0,
            1.0,
        )

    def _weighted_choice(
        self,
        *,
        items: list[InternalPlayer],
        weights: list[float],
        rng: Random,
    ) -> InternalPlayer | None:
        if not items:
            return None
        total = sum(max(0.0, weight) for weight in weights)
        if total <= 0.0:
            return items[0]
        threshold = rng.random() * total
        cursor = 0.0
        for item, weight in zip(items, weights, strict=True):
            cursor += max(0.0, weight)
            if cursor >= threshold:
                return item
        return items[-1]

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
