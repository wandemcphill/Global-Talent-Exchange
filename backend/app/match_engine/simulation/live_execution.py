from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
from itertools import count
from random import Random
from typing import Any

from app.common.enums.match_status import MatchStatus
from app.match_engine.schemas import (
    MatchSimulationRequest,
    MatchSubstitutionRequestInput,
    MatchTacticalAdjustmentInput,
)
from app.match_engine.simulation.event_generator import (
    MatchEventGenerator,
    MatchNarrativeContext,
    ScheduledItem,
)
from app.match_engine.simulation.models import (
    MatchEvent,
    MatchEventType,
    MatchVisualIdentityPayload,
    PenaltyAttempt,
    PenaltyShootout,
    PlayerMatchStats,
    PlayerRole,
    SimulationResult,
    TacticalPlan,
    TacticalStyle,
    TeamMatchStats,
    TeamRuntimeState,
    TeamStrengthSnapshot,
)
from app.match_engine.simulation.offside_var import resolve_match_broadcast_category

_REGULAR_TIME_END_MINUTE = 90
_EXTRA_TIME_END_MINUTE = 120
_EXTRA_TIME_SCHEDULE: tuple[tuple[int, str], ...] = (
    (93, "home"),
    (99, "away"),
    (105, "home"),
    (111, "away"),
    (117, "home"),
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _serialize_rng_state(state: tuple[Any, ...]) -> list[Any]:
    version, internal, gauss_next = state
    return [int(version), [int(item) for item in internal], gauss_next]


def _deserialize_rng_state(payload: list[Any]) -> tuple[Any, ...]:
    return (int(payload[0]), tuple(int(item) for item in payload[1]), payload[2])


def _serialize_tactical_plan(plan: TacticalPlan) -> dict[str, Any]:
    return {
        "style": plan.style.value,
        "pressing": int(plan.pressing),
        "tempo": int(plan.tempo),
        "aggression": int(plan.aggression),
        "substitution_windows": list(plan.substitution_windows),
        "red_card_fallback_formation": str(plan.red_card_fallback_formation),
        "injury_auto_substitution": bool(plan.injury_auto_substitution),
        "yellow_card_substitution_minute": int(plan.yellow_card_substitution_minute),
        "yellow_card_replacement_roles": [role.value for role in plan.yellow_card_replacement_roles],
        "max_substitutions": int(plan.max_substitutions),
        "allow_substitutions": bool(plan.allow_substitutions),
        "allow_tactical_changes": bool(plan.allow_tactical_changes),
        "defensive_line": int(plan.defensive_line),
        "width": int(plan.width),
        "mentality": plan.mentality.value,
        "set_piece_emphasis": int(plan.set_piece_emphasis),
        "player_instructions": deepcopy(plan.player_instructions),
        "game_state_adjustments": deepcopy(plan.game_state_adjustments),
        "tactical_quality": int(plan.tactical_quality),
        "adaptability": int(plan.adaptability),
        "game_management": int(plan.game_management),
    }


def _deserialize_tactical_plan(payload: dict[str, Any]) -> TacticalPlan:
    return TacticalPlan(
        style=TacticalStyle(str(payload["style"])),
        pressing=int(payload["pressing"]),
        tempo=int(payload["tempo"]),
        aggression=int(payload["aggression"]),
        substitution_windows=tuple(int(item) for item in payload["substitution_windows"]),
        red_card_fallback_formation=str(payload["red_card_fallback_formation"]),
        injury_auto_substitution=bool(payload["injury_auto_substitution"]),
        yellow_card_substitution_minute=int(payload["yellow_card_substitution_minute"]),
        yellow_card_replacement_roles=tuple(
            PlayerRole(str(role)) for role in payload["yellow_card_replacement_roles"]
        ),
        max_substitutions=int(payload["max_substitutions"]),
        allow_substitutions=bool(payload.get("allow_substitutions", True)),
        allow_tactical_changes=bool(payload.get("allow_tactical_changes", True)),
        defensive_line=int(payload.get("defensive_line", 50)),
        width=int(payload.get("width", 50)),
        mentality=TacticalStyle(str(payload.get("mentality", payload["style"]))),
        set_piece_emphasis=int(payload.get("set_piece_emphasis", 50)),
        player_instructions=deepcopy(payload.get("player_instructions")),
        game_state_adjustments=deepcopy(payload.get("game_state_adjustments")),
        tactical_quality=int(payload.get("tactical_quality", 60)),
        adaptability=int(payload.get("adaptability", 60)),
        game_management=int(payload.get("game_management", 60)),
    )


def _serialize_strength(snapshot: TeamStrengthSnapshot) -> dict[str, Any]:
    return {
        "overall": float(snapshot.overall),
        "attack": float(snapshot.attack),
        "midfield": float(snapshot.midfield),
        "defense": float(snapshot.defense),
        "goalkeeping": float(snapshot.goalkeeping),
        "depth": float(snapshot.depth),
        "discipline": float(snapshot.discipline),
        "fitness": float(snapshot.fitness),
        "chemistry": float(snapshot.chemistry),
        "tactical_cohesion": float(snapshot.tactical_cohesion),
        "recent_form": float(snapshot.recent_form),
        "morale": float(snapshot.morale),
        "motivation": float(snapshot.motivation),
        "fatigue_load": float(snapshot.fatigue_load),
        "coach_quality": float(snapshot.coach_quality),
        "tactical_quality": float(snapshot.tactical_quality),
        "adaptability": float(snapshot.adaptability),
        "upset_resistance": float(snapshot.upset_resistance),
        "upset_punch": float(snapshot.upset_punch),
    }


def _deserialize_strength(payload: dict[str, Any]) -> TeamStrengthSnapshot:
    return TeamStrengthSnapshot(**{key: float(value) for key, value in payload.items()})


def _serialize_team_stats(stats: TeamMatchStats) -> dict[str, Any]:
    return {
        "team_id": stats.team_id,
        "team_name": stats.team_name,
        "started_formation": stats.started_formation,
        "current_formation": stats.current_formation,
        "goals": int(stats.goals),
        "shots": int(stats.shots),
        "shots_on_target": int(stats.shots_on_target),
        "saves": int(stats.saves),
        "missed_chances": int(stats.missed_chances),
        "yellow_cards": int(stats.yellow_cards),
        "red_cards": int(stats.red_cards),
        "injuries": int(stats.injuries),
        "substitutions": int(stats.substitutions),
        "possession": int(stats.possession),
        "big_chances": int(stats.big_chances),
        "woodwork": int(stats.woodwork),
        "tactical_swings": int(stats.tactical_swings),
    }


def _deserialize_team_stats(payload: dict[str, Any]) -> TeamMatchStats:
    return TeamMatchStats(
        team_id=str(payload["team_id"]),
        team_name=str(payload["team_name"]),
        started_formation=str(payload["started_formation"]),
        current_formation=str(payload["current_formation"]),
        goals=int(payload.get("goals", 0)),
        shots=int(payload.get("shots", 0)),
        shots_on_target=int(payload.get("shots_on_target", 0)),
        saves=int(payload.get("saves", 0)),
        missed_chances=int(payload.get("missed_chances", 0)),
        yellow_cards=int(payload.get("yellow_cards", 0)),
        red_cards=int(payload.get("red_cards", 0)),
        injuries=int(payload.get("injuries", 0)),
        substitutions=int(payload.get("substitutions", 0)),
        possession=int(payload.get("possession", 50)),
        big_chances=int(payload.get("big_chances", 0)),
        woodwork=int(payload.get("woodwork", 0)),
        tactical_swings=int(payload.get("tactical_swings", 0)),
    )


def _serialize_team_state(state: TeamRuntimeState) -> dict[str, Any]:
    return {
        "current_formation": state.current_formation,
        "current_shape": list(state.current_shape),
        "tactics": _serialize_tactical_plan(state.tactics),
        "strength": _serialize_strength(state.strength),
        "active_player_ids": list(state.active_player_ids),
        "bench_player_ids": list(state.bench_player_ids),
        "stats": _serialize_team_stats(state.stats),
        "yellow_carded_ids": sorted(state.yellow_carded_ids),
        "red_carded_ids": sorted(state.red_carded_ids),
        "injured_ids": sorted(state.injured_ids),
        "substitutions_used": int(state.substitutions_used),
        "shape_attack_adjustment": float(state.shape_attack_adjustment),
        "shape_defense_adjustment": float(state.shape_defense_adjustment),
        "dynamic_morale": float(state.dynamic_morale),
        "dynamic_motivation": float(state.dynamic_motivation),
        "fatigue_level": float(state.fatigue_level),
        "momentum": float(state.momentum),
        "live_upset_momentum": float(state.live_upset_momentum),
        "manager_influence_score": float(state.manager_influence_score),
        "tactical_mismatch_edge": float(state.tactical_mismatch_edge),
        "home_advantage_score": float(state.home_advantage_score),
        "upset_potential": float(state.upset_potential),
        "crowd_intensity": float(state.crowd_intensity),
    }


def _restore_team_state(base: TeamRuntimeState, payload: dict[str, Any]) -> TeamRuntimeState:
    return TeamRuntimeState(
        team_id=base.team_id,
        team_name=base.team_name,
        is_home=base.is_home,
        starting_formation=base.starting_formation,
        current_formation=str(payload["current_formation"]),
        starting_shape=base.starting_shape,
        current_shape=tuple(int(part) for part in payload["current_shape"]),
        tactics=_deserialize_tactical_plan(payload["tactics"]),
        strength=_deserialize_strength(payload["strength"]),
        players_by_id=base.players_by_id,
        active_player_ids=[str(pid) for pid in payload["active_player_ids"]],
        bench_player_ids=[str(pid) for pid in payload["bench_player_ids"]],
        stats=_deserialize_team_stats(payload["stats"]),
        visual_identity=base.visual_identity,
        yellow_carded_ids={str(pid) for pid in payload.get("yellow_carded_ids", [])},
        red_carded_ids={str(pid) for pid in payload.get("red_carded_ids", [])},
        injured_ids={str(pid) for pid in payload.get("injured_ids", [])},
        substitutions_used=int(payload.get("substitutions_used", 0)),
        shape_attack_adjustment=float(payload.get("shape_attack_adjustment", 0.0)),
        shape_defense_adjustment=float(payload.get("shape_defense_adjustment", 0.0)),
        dynamic_morale=float(payload.get("dynamic_morale", base.dynamic_morale)),
        dynamic_motivation=float(payload.get("dynamic_motivation", base.dynamic_motivation)),
        fatigue_level=float(payload.get("fatigue_level", base.fatigue_level)),
        momentum=float(payload.get("momentum", 0.0)),
        live_upset_momentum=float(payload.get("live_upset_momentum", 0.0)),
        manager_influence_score=float(payload.get("manager_influence_score", 0.0)),
        tactical_mismatch_edge=float(payload.get("tactical_mismatch_edge", 0.0)),
        home_advantage_score=float(payload.get("home_advantage_score", 0.0)),
        upset_potential=float(payload.get("upset_potential", 0.0)),
        crowd_intensity=float(payload.get("crowd_intensity", base.crowd_intensity)),
    )


def _serialize_player_stats(stats: dict[str, PlayerMatchStats]) -> dict[str, dict[str, Any]]:
    serialized: dict[str, dict[str, Any]] = {}
    for player_id, item in stats.items():
        serialized[player_id] = {
            "player_id": item.player_id,
            "player_name": item.player_name,
            "team_id": item.team_id,
            "team_name": item.team_name,
            "role": item.role.value,
            "started": bool(item.started),
            "minutes_played": int(item.minutes_played),
            "goals": int(item.goals),
            "assists": int(item.assists),
            "saves": int(item.saves),
            "shots_on_target": int(item.shots_on_target),
            "missed_chances": int(item.missed_chances),
            "big_chances_missed": int(item.big_chances_missed),
            "yellow_cards": int(item.yellow_cards),
            "red_card": bool(item.red_card),
            "injured": bool(item.injured),
            "substituted_in_minute": item.substituted_in_minute,
            "substituted_out_minute": item.substituted_out_minute,
            "key_passes": int(item.key_passes),
            "tackles_won": int(item.tackles_won),
            "interceptions": int(item.interceptions),
            "xg": float(item.xg),
            "xg_faced": float(item.xg_faced),
        }
    return serialized


def _deserialize_player_stats(payload: dict[str, dict[str, Any]]) -> dict[str, PlayerMatchStats]:
    restored: dict[str, PlayerMatchStats] = {}
    for player_id, item in payload.items():
        restored[player_id] = PlayerMatchStats(
            player_id=str(item["player_id"]),
            player_name=str(item["player_name"]),
            team_id=str(item["team_id"]),
            team_name=str(item["team_name"]),
            role=PlayerRole(str(item["role"])),
            started=bool(item["started"]),
            minutes_played=int(item.get("minutes_played", 0)),
            goals=int(item.get("goals", 0)),
            assists=int(item.get("assists", 0)),
            saves=int(item.get("saves", 0)),
            shots_on_target=int(item.get("shots_on_target", 0)),
            missed_chances=int(item.get("missed_chances", 0)),
            big_chances_missed=int(item.get("big_chances_missed", 0)),
            yellow_cards=int(item.get("yellow_cards", 0)),
            red_card=bool(item.get("red_card", False)),
            injured=bool(item.get("injured", False)),
            substituted_in_minute=item.get("substituted_in_minute"),
            substituted_out_minute=item.get("substituted_out_minute"),
            key_passes=int(item.get("key_passes", 0)),
            tackles_won=int(item.get("tackles_won", 0)),
            interceptions=int(item.get("interceptions", 0)),
            xg=float(item.get("xg", 0.0)),
            xg_faced=float(item.get("xg_faced", 0.0)),
        )
    return restored


def serialize_match_event(event: MatchEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "sequence": int(event.sequence),
        "event_type": event.event_type.value,
        "minute": int(event.minute),
        "added_time": int(event.added_time),
        "home_score": int(event.home_score),
        "away_score": int(event.away_score),
        "team_id": event.team_id,
        "team_name": event.team_name,
        "primary_player_id": event.primary_player_id,
        "primary_player_name": event.primary_player_name,
        "secondary_player_id": event.secondary_player_id,
        "secondary_player_name": event.secondary_player_name,
        "metadata": deepcopy(event.metadata),
    }


def deserialize_match_event(payload: dict[str, Any]) -> MatchEvent:
    return MatchEvent(
        event_id=str(payload["event_id"]),
        sequence=int(payload["sequence"]),
        event_type=MatchEventType(str(payload["event_type"])),
        minute=int(payload["minute"]),
        added_time=int(payload.get("added_time", 0)),
        home_score=int(payload.get("home_score", 0)),
        away_score=int(payload.get("away_score", 0)),
        team_id=payload.get("team_id"),
        team_name=payload.get("team_name"),
        primary_player_id=payload.get("primary_player_id"),
        primary_player_name=payload.get("primary_player_name"),
        secondary_player_id=payload.get("secondary_player_id"),
        secondary_player_name=payload.get("secondary_player_name"),
        metadata=deepcopy(payload.get("metadata") or {}),
    )


def _serialize_schedule_item(item: ScheduledItem) -> dict[str, Any]:
    payload: dict[str, Any] | None = None
    if item.payload is not None:
        payload = {}
        for key, value in item.payload.items():
            if isinstance(value, MatchTacticalAdjustmentInput):
                payload[key] = {"__schema__": "MatchTacticalAdjustmentInput", "data": value.model_dump(mode="json")}
            elif isinstance(value, MatchSubstitutionRequestInput):
                payload[key] = {"__schema__": "MatchSubstitutionRequestInput", "data": value.model_dump(mode="json")}
            else:
                payload[key] = deepcopy(value)
    return {
        "minute": int(item.minute),
        "priority": int(item.priority),
        "kind": str(item.kind),
        "team_side": item.team_side,
        "index": int(item.index),
        "payload": payload,
    }


def _deserialize_schedule_item(item: dict[str, Any]) -> ScheduledItem:
    raw_payload = item.get("payload")
    payload: dict[str, Any] | None = None
    if raw_payload is not None:
        payload = {}
        for key, value in raw_payload.items():
            if isinstance(value, dict) and value.get("__schema__") == "MatchTacticalAdjustmentInput":
                payload[key] = MatchTacticalAdjustmentInput.model_validate(value["data"])
            elif isinstance(value, dict) and value.get("__schema__") == "MatchSubstitutionRequestInput":
                payload[key] = MatchSubstitutionRequestInput.model_validate(value["data"])
            else:
                payload[key] = deepcopy(value)
    return ScheduledItem(
        minute=int(item["minute"]),
        priority=int(item["priority"]),
        kind=str(item["kind"]),
        team_side=item.get("team_side"),
        index=int(item["index"]),
        payload=payload,
    )


def _serialize_shootout(shootout: PenaltyShootout | None) -> dict[str, Any] | None:
    if shootout is None:
        return None
    return {
        "winner_team_id": shootout.winner_team_id,
        "winner_team_name": shootout.winner_team_name,
        "home_penalties": int(shootout.home_penalties),
        "away_penalties": int(shootout.away_penalties),
        "attempts": [
            {
                "order": int(attempt.order),
                "team_id": attempt.team_id,
                "team_name": attempt.team_name,
                "taker_id": attempt.taker_id,
                "taker_name": attempt.taker_name,
                "goalkeeper_id": attempt.goalkeeper_id,
                "goalkeeper_name": attempt.goalkeeper_name,
                "scored": bool(attempt.scored),
                "home_penalties": int(attempt.home_penalties),
                "away_penalties": int(attempt.away_penalties),
            }
            for attempt in shootout.attempts
        ],
    }


def _deserialize_shootout(payload: dict[str, Any] | None) -> PenaltyShootout | None:
    if payload is None:
        return None
    return PenaltyShootout(
        winner_team_id=str(payload["winner_team_id"]),
        winner_team_name=str(payload["winner_team_name"]),
        home_penalties=int(payload["home_penalties"]),
        away_penalties=int(payload["away_penalties"]),
        attempts=tuple(
            PenaltyAttempt(
                order=int(attempt["order"]),
                team_id=str(attempt["team_id"]),
                team_name=str(attempt["team_name"]),
                taker_id=str(attempt["taker_id"]),
                taker_name=str(attempt["taker_name"]),
                goalkeeper_id=attempt.get("goalkeeper_id"),
                goalkeeper_name=attempt.get("goalkeeper_name"),
                scored=bool(attempt["scored"]),
                home_penalties=int(attempt["home_penalties"]),
                away_penalties=int(attempt["away_penalties"]),
            )
            for attempt in payload.get("attempts", [])
        ),
    )


def _serialize_narrative(narrative: MatchNarrativeContext) -> dict[str, Any]:
    return {
        "favorite_side": narrative.favorite_side,
        "upset_probability": float(narrative.upset_probability),
        "stage_pressure": float(narrative.stage_pressure),
        "rivalry_intensity": float(narrative.rivalry_intensity),
        "home_advantage_note": narrative.home_advantage_note,
        "clash_resolved": bool(narrative.clash_resolved),
        "competition_allows_corner_var": bool(narrative.competition_allows_corner_var),
    }


def _deserialize_narrative(payload: dict[str, Any]) -> MatchNarrativeContext:
    return MatchNarrativeContext(
        favorite_side=str(payload["favorite_side"]),
        upset_probability=float(payload["upset_probability"]),
        stage_pressure=float(payload["stage_pressure"]),
        rivalry_intensity=float(payload["rivalry_intensity"]),
        home_advantage_note=str(payload["home_advantage_note"]),
        clash_resolved=bool(payload["clash_resolved"]),
        competition_allows_corner_var=bool(payload.get("competition_allows_corner_var", False)),
    )


@dataclass(slots=True)
class MatchExecutionCheckpoint:
    match_id: str
    seed: int
    requires_winner: bool
    execution_revision: int
    current_minute: int
    target_end_minute: int
    clock_phase: str
    next_event_sequence: int
    halftime_processed: bool
    fulltime_processed: bool
    extra_time_active: bool
    rng_state: list[Any]
    narrative: MatchNarrativeContext
    home_state: TeamRuntimeState
    away_state: TeamRuntimeState
    player_stats: dict[str, PlayerMatchStats]
    future_schedule: list[ScheduledItem]
    committed_events: list[MatchEvent]
    shootout: PenaltyShootout | None = None
    applied_command_ids: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "seed": int(self.seed),
            "requires_winner": bool(self.requires_winner),
            "execution_revision": int(self.execution_revision),
            "current_minute": int(self.current_minute),
            "target_end_minute": int(self.target_end_minute),
            "clock_phase": str(self.clock_phase),
            "next_event_sequence": int(self.next_event_sequence),
            "halftime_processed": bool(self.halftime_processed),
            "fulltime_processed": bool(self.fulltime_processed),
            "extra_time_active": bool(self.extra_time_active),
            "rng_state": list(self.rng_state),
            "narrative": _serialize_narrative(self.narrative),
            "home_state": _serialize_team_state(self.home_state),
            "away_state": _serialize_team_state(self.away_state),
            "player_stats": _serialize_player_stats(self.player_stats),
            "future_schedule": [_serialize_schedule_item(item) for item in self.future_schedule],
            "committed_events": [serialize_match_event(event) for event in self.committed_events],
            "shootout": _serialize_shootout(self.shootout),
            "applied_command_ids": list(self.applied_command_ids or []),
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        *,
        generator: MatchEventGenerator,
        request: MatchSimulationRequest,
    ) -> "MatchExecutionCheckpoint":
        home_profile = generator._build_team_profile(request.home_team)
        away_profile = generator._build_team_profile(request.away_team)
        home_strength = generator.strength_calculator.calculate(home_profile, is_home=True)
        away_strength = generator.strength_calculator.calculate(away_profile, is_home=False)
        home_visual, away_visual, _ = generator._resolve_visual_identities(
            home_profile.visual_identity, away_profile.visual_identity
        )
        base_home = generator._build_runtime_state(
            home_profile, home_strength, is_home=True, visual_identity=home_visual
        )
        base_away = generator._build_runtime_state(
            away_profile, away_strength, is_home=False, visual_identity=away_visual
        )
        return cls(
            match_id=str(payload["match_id"]),
            seed=int(payload["seed"]),
            requires_winner=bool(payload["requires_winner"]),
            execution_revision=int(payload.get("execution_revision", 1)),
            current_minute=int(payload.get("current_minute", 0)),
            target_end_minute=int(payload.get("target_end_minute", _REGULAR_TIME_END_MINUTE)),
            clock_phase=str(payload.get("clock_phase", "first_half")),
            next_event_sequence=int(payload.get("next_event_sequence", 1)),
            halftime_processed=bool(payload.get("halftime_processed", False)),
            fulltime_processed=bool(payload.get("fulltime_processed", False)),
            extra_time_active=bool(payload.get("extra_time_active", False)),
            rng_state=list(payload["rng_state"]),
            narrative=_deserialize_narrative(payload["narrative"]),
            home_state=_restore_team_state(base_home, payload["home_state"]),
            away_state=_restore_team_state(base_away, payload["away_state"]),
            player_stats=_deserialize_player_stats(payload["player_stats"]),
            future_schedule=[_deserialize_schedule_item(item) for item in payload.get("future_schedule", [])],
            committed_events=[deserialize_match_event(item) for item in payload.get("committed_events", [])],
            shootout=_deserialize_shootout(payload.get("shootout")),
            applied_command_ids=[str(cid) for cid in payload.get("applied_command_ids", [])],
        )


def _apply_substitution_strength_adjustment(
    state: TeamRuntimeState,
    outgoing: Any,
    incoming: Any,
) -> None:
    """Update TeamStrengthSnapshot incrementally when a live substitution changes active personnel."""

    active_count = max(1, len(state.active_player_ids))
    attack_delta = (incoming.attacking_value() - outgoing.attacking_value()) / active_count * 1.4
    defense_delta = (incoming.defensive_value() - outgoing.defensive_value()) / active_count * 1.4
    midfield_delta = (incoming.control_value() - outgoing.control_value()) / active_count * 1.4
    overall_delta = (float(incoming.overall) - float(outgoing.overall)) / active_count * 1.2
    fitness_delta = (float(incoming.fitness) - float(outgoing.fitness)) / active_count * 1.0
    gk_val = (
        incoming.goalkeeping_value()
        if incoming.role is PlayerRole.GOALKEEPER
        else state.strength.goalkeeping
    )
    state.strength = TeamStrengthSnapshot(
        overall=_clamp(state.strength.overall + overall_delta, 25.0, 99.0),
        attack=_clamp(state.strength.attack + attack_delta, 25.0, 99.0),
        midfield=_clamp(state.strength.midfield + midfield_delta, 25.0, 99.0),
        defense=_clamp(state.strength.defense + defense_delta, 25.0, 99.0),
        goalkeeping=float(gk_val),
        depth=state.strength.depth,
        discipline=state.strength.discipline,
        fitness=_clamp(state.strength.fitness + fitness_delta, 25.0, 99.0),
        chemistry=state.strength.chemistry,
        tactical_cohesion=state.strength.tactical_cohesion,
        recent_form=state.strength.recent_form,
        morale=state.strength.morale,
        motivation=state.strength.motivation,
        fatigue_load=state.strength.fatigue_load,
        coach_quality=state.strength.coach_quality,
        tactical_quality=state.strength.tactical_quality,
        adaptability=state.strength.adaptability,
        upset_resistance=state.strength.upset_resistance,
        upset_punch=state.strength.upset_punch,
    )


def initialize_execution(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    *,
    revision: int = 1,
) -> MatchExecutionCheckpoint:
    seed = generator._resolve_seed(request)
    rng = Random(seed)
    requires_winner = generator._resolve_requires_winner(request)
    home_profile = generator._build_team_profile(request.home_team)
    away_profile = generator._build_team_profile(request.away_team)
    home_strength = generator.strength_calculator.calculate(home_profile, is_home=True)
    away_strength = generator.strength_calculator.calculate(away_profile, is_home=False)
    home_visual, away_visual, clash_resolved = generator._resolve_visual_identities(
        home_profile.visual_identity,
        away_profile.visual_identity,
    )
    home_state = generator._build_runtime_state(home_profile, home_strength, is_home=True, visual_identity=home_visual)
    away_state = generator._build_runtime_state(away_profile, away_strength, is_home=False, visual_identity=away_visual)
    narrative = generator._prepare_match_context(request, home_state, away_state, clash_resolved=clash_resolved)
    player_stats = generator._initialize_player_stats(home_state, away_state)

    committed_events: list[MatchEvent] = []
    event_counter = count(1)

    def record(entry: MatchEvent | list[MatchEvent] | tuple[MatchEvent, ...] | None) -> None:
        if entry is None:
            return
        if isinstance(entry, list | tuple):
            for nested in entry:
                record(nested)
            return
        meta = dict(entry.metadata or {})
        meta.setdefault("execution_revision", int(revision))
        stamped = replace(entry, metadata=meta)
        committed_events.append(stamped)
        generator.crowd_engine.react(event=stamped, home_state=home_state, away_state=away_state)

    record(
        generator._make_event(
            match_id=request.match_id,
            event_counter=event_counter,
            event_type=MatchEventType.KICKOFF,
            minute=0,
            home_state=home_state,
            away_state=away_state,
            metadata={
                "stage": request.competition.stage,
                "competition_type": request.competition.competition_type.value,
                "approved_shorter_presentation": bool(
                    getattr(request.competition, "approved_shorter_presentation", False)
                ),
                "designated_major_knockout": bool(
                    getattr(request.competition, "designated_major_knockout", False)
                ),
                "competition_allows_corner_var": bool(
                    getattr(request.competition, "competition_allows_corner_var", False)
                ),
                "competition_category": resolve_match_broadcast_category(
                    is_final=request.competition.is_final,
                    stage=request.competition.stage,
                    competition_type=request.competition.competition_type.value,
                    approved_shorter_presentation=bool(
                        getattr(request.competition, "approved_shorter_presentation", False)
                    ),
                    metadata={
                        "designated_major_knockout": bool(
                            getattr(request.competition, "designated_major_knockout", False)
                        )
                    },
                ).value,
                "upset_probability": round(narrative.upset_probability, 3),
                "home_tactics": generator._shape_instructions(home_state),
                "away_tactics": generator._shape_instructions(away_state),
            },
        )
    )
    schedule = generator._build_schedule(
        home_state,
        away_state,
        rng,
        is_final=request.competition.is_final,
        narrative=narrative,
    )
    schedule = generator._merge_tactical_changes(schedule, request, home_state, away_state)

    return MatchExecutionCheckpoint(
        match_id=request.match_id,
        seed=seed,
        requires_winner=requires_winner,
        execution_revision=int(revision),
        current_minute=0,
        target_end_minute=_REGULAR_TIME_END_MINUTE,
        clock_phase="first_half",
        next_event_sequence=next(event_counter),
        halftime_processed=False,
        fulltime_processed=False,
        extra_time_active=False,
        rng_state=_serialize_rng_state(rng.getstate()),
        narrative=narrative,
        home_state=home_state,
        away_state=away_state,
        player_stats=player_stats,
        future_schedule=list(schedule),
        committed_events=committed_events,
        shootout=None,
        applied_command_ids=[],
    )


def resume_from_halftime(checkpoint: MatchExecutionCheckpoint) -> MatchExecutionCheckpoint:
    if checkpoint.clock_phase == "halftime":
        checkpoint.clock_phase = "second_half"
    return checkpoint


def advance_checkpoint(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
    *,
    until_minute: int,
    stop_at_halftime: bool = True,
) -> tuple[MatchExecutionCheckpoint, list[MatchEvent]]:
    """Advance an execution checkpoint deterministically through `until_minute`."""

    rng = Random()
    rng.setstate(_deserialize_rng_state(checkpoint.rng_state))
    home_state = checkpoint.home_state
    away_state = checkpoint.away_state
    player_stats = checkpoint.player_stats
    narrative = checkpoint.narrative
    schedule = list(checkpoint.future_schedule)
    committed = list(checkpoint.committed_events)
    newly_emitted: list[MatchEvent] = []
    event_counter = count(checkpoint.next_event_sequence)
    phase_stamp: dict[str, str | None] = {"value": "extra_time" if checkpoint.extra_time_active else None}

    def record(entry: MatchEvent | list[MatchEvent] | tuple[MatchEvent, ...] | None) -> None:
        if entry is None:
            return
        if isinstance(entry, list | tuple):
            for nested in entry:
                record(nested)
            return
        meta = dict(entry.metadata or {})
        meta.setdefault("execution_revision", int(checkpoint.execution_revision))
        if phase_stamp["value"]:
            meta["match_phase"] = phase_stamp["value"]
        stamped = replace(entry, metadata=meta)
        committed.append(stamped)
        newly_emitted.append(stamped)
        generator.crowd_engine.react(event=stamped, home_state=home_state, away_state=away_state)

    if checkpoint.clock_phase == "completed":
        return checkpoint, []

    halftime_processed = bool(checkpoint.halftime_processed)
    fulltime_processed = bool(checkpoint.fulltime_processed)
    extra_time_active = bool(checkpoint.extra_time_active)
    target_end_minute = int(checkpoint.target_end_minute)
    shootout = checkpoint.shootout
    halftime_halt = False
    remaining_schedule: list[ScheduledItem] = []

    requested_target = max(int(checkpoint.current_minute), int(until_minute))
    step_limit = min(requested_target, target_end_minute)

    idx = 0
    while idx < len(schedule):
        item = schedule[idx]
        if item.minute > step_limit:
            remaining_schedule = schedule[idx:]
            break
        if not halftime_processed and item.minute >= 45:
            halftime_processed = True
            generator._apply_halftime_reset(home_state, away_state)
            record(
                generator._make_event(
                    match_id=request.match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.HALFTIME,
                    minute=45,
                    home_state=home_state,
                    away_state=away_state,
                )
            )
            if stop_at_halftime:
                remaining_schedule = schedule[idx:]
                halftime_halt = True
                break
        generator._execute_scheduled_item(
            request=request,
            item=item,
            home_state=home_state,
            away_state=away_state,
            player_stats=player_stats,
            rng=rng,
            narrative=narrative,
            event_counter=event_counter,
            record=record,
        )
        if item.kind in {"tactical_change", "tactical_substitution"} and item.payload:
            cmd_id = item.payload.get("change_id")
            if cmd_id and cmd_id not in (checkpoint.applied_command_ids or []):
                checkpoint.applied_command_ids = [*(checkpoint.applied_command_ids or []), str(cmd_id)]
        idx += 1
    else:
        remaining_schedule = []

    if halftime_halt:
        checkpoint.current_minute = 45
        checkpoint.clock_phase = "halftime"
        checkpoint.halftime_processed = True
        checkpoint.future_schedule = remaining_schedule
        checkpoint.committed_events = committed
        checkpoint.next_event_sequence = next(event_counter)
        checkpoint.rng_state = _serialize_rng_state(rng.getstate())
        return checkpoint, newly_emitted

    if not halftime_processed and step_limit >= 45:
        halftime_processed = True
        generator._apply_halftime_reset(home_state, away_state)
        record(
            generator._make_event(
                match_id=request.match_id,
                event_counter=event_counter,
                event_type=MatchEventType.HALFTIME,
                minute=45,
                home_state=home_state,
                away_state=away_state,
            )
        )
        if stop_at_halftime:
            checkpoint.current_minute = 45
            checkpoint.clock_phase = "halftime"
            checkpoint.halftime_processed = True
            checkpoint.future_schedule = remaining_schedule
            checkpoint.committed_events = committed
            checkpoint.next_event_sequence = next(event_counter)
            checkpoint.rng_state = _serialize_rng_state(rng.getstate())
            return checkpoint, newly_emitted

    new_minute = step_limit
    new_phase = checkpoint.clock_phase
    if not fulltime_processed:
        new_phase = "second_half" if halftime_processed else "first_half"

    if not fulltime_processed and step_limit >= _REGULAR_TIME_END_MINUTE:
        level_at_full_time = home_state.stats.goals == away_state.stats.goals
        play_extra_time = (
            bool(getattr(request.competition, "extra_time", False))
            and checkpoint.requires_winner
            and level_at_full_time
        )
        record(
            generator._make_event(
                match_id=request.match_id,
                event_counter=event_counter,
                event_type=MatchEventType.FULLTIME,
                minute=_REGULAR_TIME_END_MINUTE,
                home_state=home_state,
                away_state=away_state,
                metadata={
                    "match_phase": "full_time",
                    "goes_to_extra_time": play_extra_time,
                    "goes_to_penalties": bool(
                        checkpoint.requires_winner and level_at_full_time and not play_extra_time
                    ),
                },
            )
        )
        fulltime_processed = True
        if play_extra_time:
            extra_time_active = True
            target_end_minute = _EXTRA_TIME_END_MINUTE
            new_phase = "extra_time"
            phase_stamp["value"] = "extra_time"
            next_index = max((item.index for item in remaining_schedule), default=1000)
            for et_minute, et_side in _EXTRA_TIME_SCHEDULE:
                next_index += 1
                remaining_schedule.append(
                    ScheduledItem(
                        minute=et_minute,
                        priority=20,
                        kind="chance",
                        team_side=et_side,
                        index=next_index,
                    )
                )
            remaining_schedule.sort(key=lambda entry: (entry.minute, entry.priority, entry.index))
            if requested_target > _REGULAR_TIME_END_MINUTE:
                et_limit = min(requested_target, target_end_minute)
                et_consumed = 0
                for et_idx, item in enumerate(remaining_schedule):
                    if item.minute > et_limit:
                        remaining_schedule = remaining_schedule[et_idx:]
                        break
                    et_consumed = et_idx + 1
                    generator._execute_scheduled_item(
                        request=request,
                        item=item,
                        home_state=home_state,
                        away_state=away_state,
                        player_stats=player_stats,
                        rng=rng,
                        narrative=narrative,
                        event_counter=event_counter,
                        record=record,
                    )
                else:
                    if et_consumed == len(remaining_schedule):
                        remaining_schedule = []
                new_minute = et_limit

    if fulltime_processed and (not extra_time_active or new_minute >= _EXTRA_TIME_END_MINUTE):
        phase_stamp["value"] = None
        still_level = home_state.stats.goals == away_state.stats.goals
        if checkpoint.requires_winner and still_level and shootout is None:
            phase_stamp["value"] = "penalty_shootout"
            shootout = generator.penalty_generator.generate(home_state, away_state, rng)
            penalty_origin = 121 if extra_time_active else 90
            for offset, attempt in enumerate(shootout.attempts, start=1):
                record(
                    generator._make_event(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        event_type=MatchEventType.PENALTY_GOAL if attempt.scored else MatchEventType.PENALTY_MISS,
                        minute=penalty_origin + offset,
                        home_state=home_state,
                        away_state=away_state,
                        team_id=attempt.team_id,
                        team_name=attempt.team_name,
                        primary_player_id=attempt.taker_id,
                        primary_player_name=attempt.taker_name,
                        secondary_player_id=attempt.goalkeeper_id,
                        secondary_player_name=attempt.goalkeeper_name,
                        metadata={
                            "shootout_round": attempt.order,
                            "home_penalties": attempt.home_penalties,
                            "away_penalties": attempt.away_penalties,
                            "importance": 5,
                            "pressure_level": "shootout",
                            "match_phase": "penalty_shootout",
                        },
                    )
                )
            phase_stamp["value"] = None
        new_phase = "completed"

    checkpoint.current_minute = new_minute
    checkpoint.target_end_minute = target_end_minute
    checkpoint.clock_phase = new_phase
    checkpoint.halftime_processed = halftime_processed
    checkpoint.fulltime_processed = fulltime_processed
    checkpoint.extra_time_active = extra_time_active
    checkpoint.shootout = shootout
    checkpoint.future_schedule = remaining_schedule
    checkpoint.committed_events = committed
    checkpoint.next_event_sequence = next(event_counter)
    checkpoint.rng_state = _serialize_rng_state(rng.getstate())
    return checkpoint, newly_emitted


def rebuild_remaining_schedule(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
    *,
    from_minute: int,
    new_revision: int,
    command_salt: str,
    effective_home_state: TeamRuntimeState | None = None,
    effective_away_state: TeamRuntimeState | None = None,
) -> MatchExecutionCheckpoint:
    """Regenerate unplayed events strictly after `checkpoint.current_minute` using updated team states."""

    home_eff = effective_home_state or checkpoint.home_state
    away_eff = effective_away_state or checkpoint.away_state
    salt_int = int(sha256(f"{command_salt}:{new_revision}".encode("utf-8")).hexdigest()[:12], 16)
    fork_seed = (int(checkpoint.seed) ^ int(new_revision) ^ int(from_minute) ^ salt_int) & 0xFFFFFFFFFFFF
    rng = Random(fork_seed)

    # Preserve pending explicit tactical changes, tactical substitutions, and sub windows not yet executed.
    preserved = [
        item
        for item in checkpoint.future_schedule
        if item.kind in {"tactical_change", "tactical_substitution", "window"}
    ]
    next_index = max((item.index for item in preserved), default=0)

    if checkpoint.extra_time_active or checkpoint.fulltime_processed:
        start_et = max(91, int(from_minute))
        # Re-weight remaining ET chances against the revised live ratings.
        home_attack = generator._live_attack_rating(
            home_eff, away_eff, start_et, narrative=checkpoint.narrative
        )
        away_attack = generator._live_attack_rating(
            away_eff, home_eff, start_et, narrative=checkpoint.narrative
        )
        home_def = max(10.0, generator._live_defense_rating(home_eff, away_eff, start_et, narrative=checkpoint.narrative))
        away_def = max(10.0, generator._live_defense_rating(away_eff, home_eff, start_et, narrative=checkpoint.narrative))
        home_share = _clamp((home_attack / away_def) / max(0.01, (home_attack / away_def) + (away_attack / home_def)), 0.25, 0.75)
        for item in checkpoint.future_schedule:
            if item.kind == "chance" and item.minute >= start_et:
                next_index += 1
                preserved.append(
                    ScheduledItem(
                        minute=item.minute,
                        priority=item.priority,
                        kind="chance",
                        team_side="home" if rng.random() < home_share else "away",
                        index=next_index,
                    )
                )
        preserved.sort(key=lambda item: (item.minute, item.priority, item.index))
        checkpoint.future_schedule = preserved
        checkpoint.execution_revision = int(new_revision)
        checkpoint.rng_state = _serialize_rng_state(rng.getstate())
        return checkpoint

    min_minute = max(1, int(from_minute))
    max_minute = 89
    if min_minute > max_minute:
        preserved.sort(key=lambda item: (item.minute, item.priority, item.index))
        checkpoint.future_schedule = preserved
        checkpoint.execution_revision = int(new_revision)
        checkpoint.rng_state = _serialize_rng_state(rng.getstate())
        return checkpoint

    remaining_fraction = max(0.05, (90 - min_minute + 1) / 90.0)

    def _draw_minute(lo: int, hi: int) -> int:
        bounded_lo = max(min_minute, lo)
        bounded_hi = min(max_minute, hi)
        if bounded_lo > bounded_hi:
            return min(max_minute, max(min_minute, bounded_hi))
        return generator._incident_minute(rng, bounded_lo, bounded_hi)

    for state, side in ((home_eff, "home"), (away_eff, "away")):
        yellow_budget = max(0, round(generator._yellow_card_count(state, rng, narrative=checkpoint.narrative) * remaining_fraction))
        for _ in range(yellow_budget):
            next_index += 1
            preserved.append(
                ScheduledItem(
                    minute=_draw_minute(12, 88),
                    priority=10,
                    kind="yellow",
                    team_side=side,
                    index=next_index,
                )
            )
        if not state.red_carded_ids and rng.random() < remaining_fraction:
            for _ in range(generator._red_card_count(state, rng, narrative=checkpoint.narrative)):
                next_index += 1
                preserved.append(
                    ScheduledItem(
                        minute=_draw_minute(24, 84),
                        priority=11,
                        kind="red",
                        team_side=side,
                        index=next_index,
                    )
                )
        if rng.random() < remaining_fraction:
            for _ in range(generator._injury_count(state, rng)):
                next_index += 1
                preserved.append(
                    ScheduledItem(
                        minute=_draw_minute(18, 84),
                        priority=12,
                        kind="injury",
                        team_side=side,
                        index=next_index,
                    )
                )
        foul_budget = max(0, round(generator._tactical_foul_count(state, rng, narrative=checkpoint.narrative) * remaining_fraction))
        for _ in range(foul_budget):
            next_index += 1
            preserved.append(
                ScheduledItem(
                    minute=_draw_minute(14, 88),
                    priority=13,
                    kind="foul",
                    team_side=side,
                    index=next_index,
                )
            )
        if min_minute <= 86 and generator._fatigue_event_count(state, rng):
            next_index += 1
            preserved.append(
                ScheduledItem(
                    minute=_draw_minute(52, 86),
                    priority=14,
                    kind="fatigue",
                    team_side=side,
                    index=next_index,
                )
            )
        if min_minute <= 80 and (state.strength.tactical_quality >= 62 or state.strength.adaptability >= 64):
            next_index += 1
            preserved.append(
                ScheduledItem(
                    minute=_draw_minute(54, 80),
                    priority=18,
                    kind="tactical",
                    team_side=side,
                    index=next_index,
                )
            )

    full_chances = generator._chance_count(
        home_eff,
        away_eff,
        rng,
        is_final=request.competition.is_final,
        narrative=checkpoint.narrative,
    )
    remaining_chances = max(1 if (90 - min_minute) >= 6 else 0, round(full_chances * remaining_fraction))

    sample_minute = min(85, max(min_minute, 45))
    home_attack = generator._live_attack_rating(
        home_eff, away_eff, sample_minute, narrative=checkpoint.narrative
    )
    away_attack = generator._live_attack_rating(
        away_eff, home_eff, sample_minute, narrative=checkpoint.narrative
    )
    home_defense = max(
        10.0, generator._live_defense_rating(home_eff, away_eff, sample_minute, narrative=checkpoint.narrative)
    )
    away_defense = max(
        10.0, generator._live_defense_rating(away_eff, home_eff, sample_minute, narrative=checkpoint.narrative)
    )
    base_share = generator._chance_share(home_eff, away_eff)
    live_pressure_home = home_attack / away_defense
    live_pressure_away = away_attack / home_defense
    live_share = live_pressure_home / max(0.01, live_pressure_home + live_pressure_away)
    home_share = _clamp((base_share * 0.4) + (live_share * 0.6), 0.22, 0.78)

    mode = min(max_minute, max(min_minute, round(min_minute + ((max_minute - min_minute) * 0.58))))
    for _ in range(remaining_chances):
        next_index += 1
        chance_minute = generator._clamp_minute(
            int(round(rng.triangular(min_minute, max_minute, mode)))
        )
        chance_minute = max(min_minute, min(max_minute, chance_minute))
        preserved.append(
            ScheduledItem(
                minute=chance_minute,
                priority=20,
                kind="chance",
                team_side="home" if rng.random() < home_share else "away",
                index=next_index,
            )
        )

    preserved.sort(key=lambda item: (item.minute, item.priority, item.index))
    checkpoint.future_schedule = preserved
    checkpoint.execution_revision = int(new_revision)
    checkpoint.rng_state = _serialize_rng_state(rng.getstate())
    return checkpoint


def apply_live_tactical_revision(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
    *,
    side: str,
    command_id: str,
    effective_minute: int,
    new_revision: int,
    adjustment: MatchTacticalAdjustmentInput | None = None,
    substitutions: list[MatchSubstitutionRequestInput] | None = None,
) -> tuple[MatchExecutionCheckpoint, list[MatchEvent]]:
    """Apply manager tactics/substitutions at `effective_minute` and regenerate future play."""

    normalized_side = "home" if str(side).strip().lower() == "home" else "away"
    state = checkpoint.home_state if normalized_side == "home" else checkpoint.away_state
    opponent = checkpoint.away_state if normalized_side == "home" else checkpoint.home_state
    emitted: list[MatchEvent] = []
    event_counter = count(checkpoint.next_event_sequence)

    def record(entry: MatchEvent | list[MatchEvent] | tuple[MatchEvent, ...] | None) -> None:
        if entry is None:
            return
        if isinstance(entry, list | tuple):
            for nested in entry:
                record(nested)
            return
        meta = dict(entry.metadata or {})
        meta["execution_revision"] = int(new_revision)
        stamped = replace(entry, metadata=meta)
        checkpoint.committed_events.append(stamped)
        emitted.append(stamped)
        generator.crowd_engine.react(event=stamped, home_state=checkpoint.home_state, away_state=checkpoint.away_state)

    apply_immediately = effective_minute <= checkpoint.current_minute or checkpoint.clock_phase == "halftime"
    next_idx = max((item.index for item in checkpoint.future_schedule), default=100)

    if apply_immediately:
        target_minute = max(int(checkpoint.current_minute), int(effective_minute))
        if adjustment is not None:
            ev = generator._apply_tactical_change(
                match_id=request.match_id,
                event_counter=event_counter,
                state=state,
                opponent=opponent,
                minute=target_minute,
                payload={
                    "adjustment": adjustment,
                    "change_id": command_id,
                    "requested_minute": target_minute,
                    "requested_second": 0,
                    "urgency": "normal",
                },
            )
            record(ev)
        for sub_idx, sub in enumerate(substitutions or []):
            outgoing = state.players_by_id.get(sub.outgoing_player_id)
            incoming = state.players_by_id.get(sub.incoming_player_id)
            events = generator._apply_tactical_substitution(
                match_id=request.match_id,
                event_counter=event_counter,
                state=state,
                opponent=opponent,
                minute=target_minute,
                payload={
                    "substitution": sub,
                    "change_id": f"{command_id}:sub:{sub_idx}",
                    "requested_minute": target_minute,
                    "requested_second": 0,
                    "urgency": "urgent",
                },
                player_stats=checkpoint.player_stats,
            )
            record(events)
            if events and outgoing is not None and incoming is not None:
                _apply_substitution_strength_adjustment(state, outgoing, incoming)
        checkpoint.next_event_sequence = next(event_counter)
        if command_id not in (checkpoint.applied_command_ids or []):
            checkpoint.applied_command_ids = [*(checkpoint.applied_command_ids or []), command_id]
        rebuild_remaining_schedule(
            generator,
            request,
            checkpoint,
            from_minute=max(1, target_minute + (0 if checkpoint.clock_phase == "halftime" else 1)),
            new_revision=new_revision,
            command_salt=command_id,
        )
        return checkpoint, emitted

    # Scheduled for future open-play minute (> current_minute):
    # Do NOT touch committed history or stats at <= current_minute; project all pending
    # + new changes onto disposable preview states so future chance mix reflects all active orders.
    preview_home = deepcopy(checkpoint.home_state)
    preview_away = deepcopy(checkpoint.away_state)
    dummy_counter = count(1)
    dummy_stats = deepcopy(checkpoint.player_stats)

    for queued in checkpoint.future_schedule:
        if queued.kind not in {"tactical_change", "tactical_substitution"} or not queued.payload:
            continue
        q_state = preview_home if queued.team_side == "home" else preview_away
        q_opp = preview_away if queued.team_side == "home" else preview_home
        if queued.kind == "tactical_change":
            generator._apply_tactical_change(
                match_id=request.match_id,
                event_counter=dummy_counter,
                state=q_state,
                opponent=q_opp,
                minute=int(queued.minute),
                payload=queued.payload,
            )
        elif queued.kind == "tactical_substitution":
            sub_item = queued.payload.get("substitution")
            q_out = q_state.players_by_id.get(sub_item.outgoing_player_id) if sub_item is not None else None
            q_in = q_state.players_by_id.get(sub_item.incoming_player_id) if sub_item is not None else None
            q_events = generator._apply_tactical_substitution(
                match_id=request.match_id,
                event_counter=dummy_counter,
                state=q_state,
                opponent=q_opp,
                minute=int(queued.minute),
                payload=queued.payload,
                player_stats=dummy_stats,
            )
            if q_events and q_out is not None and q_in is not None:
                _apply_substitution_strength_adjustment(q_state, q_out, q_in)

    eff_state = preview_home if normalized_side == "home" else preview_away
    eff_opp = preview_away if normalized_side == "home" else preview_home

    if adjustment is not None:
        next_idx += 1
        checkpoint.future_schedule.append(
            ScheduledItem(
                minute=int(effective_minute),
                priority=5,
                kind="tactical_change",
                team_side=normalized_side,
                index=next_idx,
                payload={
                    "adjustment": adjustment,
                    "change_id": command_id,
                    "requested_minute": int(effective_minute),
                    "requested_second": 0,
                    "urgency": "normal",
                },
            )
        )
        generator._apply_tactical_change(
            match_id=request.match_id,
            event_counter=dummy_counter,
            state=eff_state,
            opponent=eff_opp,
            minute=int(effective_minute),
            payload={"adjustment": adjustment, "change_id": command_id},
        )
    for sub_idx, sub in enumerate(substitutions or []):
        outgoing = eff_state.players_by_id.get(sub.outgoing_player_id)
        incoming = eff_state.players_by_id.get(sub.incoming_player_id)
        next_idx += 1
        checkpoint.future_schedule.append(
            ScheduledItem(
                minute=int(effective_minute),
                priority=6,
                kind="tactical_substitution",
                team_side=normalized_side,
                index=next_idx,
                payload={
                    "substitution": sub,
                    "change_id": f"{command_id}:sub:{sub_idx}",
                    "requested_minute": int(effective_minute),
                    "requested_second": 0,
                    "urgency": "urgent",
                },
            )
        )
        events = generator._apply_tactical_substitution(
            match_id=request.match_id,
            event_counter=dummy_counter,
            state=eff_state,
            opponent=eff_opp,
            minute=int(effective_minute),
            payload={"substitution": sub, "change_id": f"{command_id}:sub:{sub_idx}"},
            player_stats=dummy_stats,
        )
        if events and outgoing is not None and incoming is not None:
            _apply_substitution_strength_adjustment(eff_state, outgoing, incoming)

    rebuild_remaining_schedule(
        generator,
        request,
        checkpoint,
        from_minute=int(effective_minute),
        new_revision=new_revision,
        command_salt=command_id,
        effective_home_state=preview_home,
        effective_away_state=preview_away,
    )
    return checkpoint, []


def _assemble_simulation_result(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
    *,
    home_state: TeamRuntimeState,
    away_state: TeamRuntimeState,
    player_stats: dict[str, PlayerMatchStats],
    status: MatchStatus,
    finalize_minutes: bool,
) -> SimulationResult:
    events = list(checkpoint.committed_events)
    narrative = checkpoint.narrative
    shootout = checkpoint.shootout

    generator._resolve_possession(home_state, away_state, narrative=narrative)
    if finalize_minutes:
        generator._finalize_player_minutes(player_stats)
    winner_team_id, winner_team_name = generator._resolve_winner(home_state, away_state, shootout)
    upset = generator._resolve_upset(home_state, away_state, winner_team_id)
    ordered_player_stats = tuple(
        sorted(
            player_stats.values(),
            key=lambda line: (
                line.team_id,
                -line.goals,
                -line.assists,
                -line.saves,
                -line.missed_chances,
                line.player_name,
            ),
        )
    )
    return SimulationResult(
        match_id=request.match_id,
        seed=checkpoint.seed,
        status=status,
        competition_type=request.competition.competition_type,
        stage=request.competition.stage,
        is_final=request.competition.is_final,
        requires_winner=checkpoint.requires_winner,
        home_team_id=home_state.team_id,
        home_team_name=home_state.team_name,
        away_team_id=away_state.team_id,
        away_team_name=away_state.team_name,
        winner_team_id=winner_team_id,
        winner_team_name=winner_team_name,
        home_score=home_state.stats.goals,
        away_score=away_state.stats.goals,
        decided_by_penalties=shootout is not None,
        home_penalty_score=shootout.home_penalties if shootout is not None else None,
        away_penalty_score=shootout.away_penalties if shootout is not None else None,
        upset=upset,
        upset_probability=narrative.upset_probability,
        upset_reason_codes=generator._upset_reason_codes(
            upset=upset,
            winner_team_id=winner_team_id,
            home_state=home_state,
            away_state=away_state,
            events=events,
        ),
        home_advantage_note=narrative.home_advantage_note,
        summary_line=generator._build_summary_line(home_state, away_state, shootout, upset=upset),
        home_strength=home_state.strength,
        away_strength=away_state.strength,
        home_stats=home_state.stats,
        away_stats=away_state.stats,
        player_stats=ordered_player_stats,
        events=tuple(events),
        manager_influence_notes=generator._manager_influence_notes(home_state, away_state, events),
        tactical_battle_summary=generator._tactical_battle_summary(home_state, away_state),
        form_motivation_summary=generator._form_motivation_summary(home_state, away_state),
        momentum_swings=generator._momentum_swings(events),
        turning_points=generator._turning_points(events),
        key_matchups=generator._key_matchups(ordered_player_stats),
        tactical_impact_notes=generator._tactical_impact_notes(events),
        visual_identity=MatchVisualIdentityPayload(
            home_team=home_state.visual_identity,
            away_team=away_state.visual_identity,
            clash_resolved=narrative.clash_resolved,
        ),
        shootout=shootout,
        home_crowd_intensity=round(home_state.crowd_intensity, 3),
        away_crowd_intensity=round(away_state.crowd_intensity, 3),
        atmosphere_profile=generator.crowd_engine.profile(
            home_state=home_state,
            away_state=away_state,
            is_final=request.competition.is_final,
        ),
        atmosphere_summary=generator._atmosphere_summary(home_state, away_state, narrative=narrative),
    )


def build_partial_simulation_result(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
) -> SimulationResult:
    """Build a non-mutating SimulationResult containing strictly committed events up to current_minute."""

    status = MatchStatus.PAUSED if checkpoint.clock_phase == "halftime" else MatchStatus.IN_PROGRESS
    return _assemble_simulation_result(
        generator,
        request,
        checkpoint,
        home_state=deepcopy(checkpoint.home_state),
        away_state=deepcopy(checkpoint.away_state),
        player_stats=deepcopy(checkpoint.player_stats),
        status=status,
        finalize_minutes=False,
    )


def finalize_checkpoint(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
) -> SimulationResult:
    """Complete any remaining play and emit the canonical SimulationResult."""

    if checkpoint.clock_phase != "completed":
        advance_checkpoint(
            generator,
            request,
            checkpoint,
            until_minute=_EXTRA_TIME_END_MINUTE,
            stop_at_halftime=False,
        )

    return _assemble_simulation_result(
        generator,
        request,
        checkpoint,
        home_state=checkpoint.home_state,
        away_state=checkpoint.away_state,
        player_stats=checkpoint.player_stats,
        status=MatchStatus.COMPLETED,
        finalize_minutes=True,
    )


def project_remaining_from_checkpoint(
    generator: MatchEventGenerator,
    request: MatchSimulationRequest,
    checkpoint: MatchExecutionCheckpoint,
) -> SimulationResult:
    """Return a non-mutating full SimulationResult projection from the current checkpoint."""

    rehydrated = MatchExecutionCheckpoint.from_dict(
        checkpoint.to_dict(),
        generator=generator,
        request=request,
    )
    return finalize_checkpoint(generator, request, rehydrated)


__all__ = [
    "MatchExecutionCheckpoint",
    "advance_checkpoint",
    "apply_live_tactical_revision",
    "build_partial_simulation_result",
    "deserialize_match_event",
    "finalize_checkpoint",
    "initialize_execution",
    "project_remaining_from_checkpoint",
    "rebuild_remaining_schedule",
    "resume_from_halftime",
    "serialize_match_event",
]
