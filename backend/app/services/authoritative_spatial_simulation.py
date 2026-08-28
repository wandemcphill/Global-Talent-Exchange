from __future__ import annotations

from hashlib import md5
from math import cos, hypot, sin, tau
from typing import Any

from app.match_engine.simulation.models import PlayerRole
from app.schemas.match_viewer import MatchViewerAnimationState, MatchViewerPlayerState, MatchViewerSide

_LINE_Y = {1: (50.0,), 2: (34.0, 66.0), 3: (22.0, 50.0, 78.0), 4: (18.0, 39.0, 61.0, 82.0), 5: (14.0, 32.0, 50.0, 68.0, 86.0)}
_LINE_X = {3: (24.0, 50.0, 76.0), 4: (20.0, 38.0, 62.0, 80.0)}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _smoothstep(value: float) -> float:
    value = _clamp(value, 0.0, 1.0)
    return value * value * (3.0 - (2.0 * value))


def _hash_phase(player_id: str) -> tuple[float, float]:
    digest = md5(player_id.encode("utf-8")).digest()
    return ((int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) * tau, (int.from_bytes(digest[4:8], "big") / 0xFFFFFFFF) * tau)


def _line_sizes(runtime: Any) -> list[int]:
    outfield = runtime.lineup[1:]
    total = len(outfield)
    if total <= 0:
        return []

    try:
        values = [
            max(0, int(part))
            for part in str(runtime.current_formation).split("-")
        ]
    except ValueError:
        values = []
    if values and sum(values) == total and all(value > 0 for value in values):
        return values

    defenders = sum(
        runtime.players_by_id[item].role is PlayerRole.DEFENDER
        for item in outfield
    )
    midfielders = sum(
        runtime.players_by_id[item].role is PlayerRole.MIDFIELDER
        for item in outfield
    )
    forwards = sum(
        runtime.players_by_id[item].role is PlayerRole.FORWARD
        for item in outfield
    )
    role_sizes = [size for size in (defenders, midfielders, forwards) if size > 0]
    if role_sizes and sum(role_sizes) == total:
        return role_sizes

    defaults = {
        1: [1],
        2: [1, 1],
        3: [1, 1, 1],
        4: [2, 1, 1],
        5: [2, 2, 1],
        6: [3, 2, 1],
        7: [3, 2, 2],
        8: [3, 3, 2],
        9: [4, 3, 2],
        10: [4, 3, 3],
        11: [4, 4, 3],
    }
    if total in defaults:
        return defaults[total]

    if total == 1:
        return [1]
    defenders = min(4, max(1, total - 2))
    forwards = min(3, max(1, total - defenders - 1))
    midfielders = total - defenders - forwards
    if midfielders < 1:
        midfielders = 1
        defenders = max(1, total - forwards - midfielders)
    return [defenders, midfielders, forwards]
def _anchors(runtime: Any, attacks_right: bool) -> dict[str, dict[str, float]]:
    if not runtime.lineup:
        return {}
    sizes = _line_sizes(runtime)
    base_x = _LINE_X.get(len(sizes))
    if base_x is None:
        gap = 58.0 / max(1, len(sizes) - 1)
        base_x = tuple(21.0 + (gap * index) for index in range(len(sizes)))
    if not attacks_right:
        base_x = tuple(100.0 - value for value in base_x)
    result = {runtime.lineup[0]: {"x": 8.0 if attacks_right else 92.0, "y": 50.0}}
    cursor = 0
    outfield = runtime.lineup[1:]
    for group_index, size in enumerate(sizes):
        ys = _LINE_Y.get(size, tuple(10.0 + ((i + 1) * (80.0 / (size + 1))) for i in range(size)))
        for local_index in range(size):
            result[outfield[cursor + local_index]] = {"x": float(base_x[group_index]), "y": float(ys[local_index])}
        cursor += size
    return result


def _line(runtime: Any, player_id: str) -> str:
    if runtime.lineup and runtime.lineup[0] == player_id:
        return "goalkeeper"
    outfield = runtime.lineup[1:]
    cursor = 0
    sizes = _line_sizes(runtime)
    for index, size in enumerate(sizes):
        if player_id in outfield[cursor : cursor + size]:
            if index == 0:
                return "defense"
            if index == len(sizes) - 1:
                return "attack"
            return "midfield"
        cursor += size
    return "midfield"


def _side_attacks_right(side: MatchViewerSide, home_attacks_right: bool) -> bool:
    return home_attacks_right if side is MatchViewerSide.HOME else not home_attacks_right


def _event_point(event: Any, key: str) -> dict[str, float] | None:
    contract = getattr(event, "render_contract", None) or {}
    value = contract.get(key) if isinstance(contract, dict) else None
    if isinstance(value, dict) and isinstance(value.get("x"), (int, float)) and isinstance(value.get("y"), (int, float)):
        return {"x": _clamp(float(value["x"])), "y": _clamp(float(value["y"]))}
    return None


def _event_target(event: Any, possession_side: MatchViewerSide, home_attacks_right: bool) -> dict[str, float]:
    point = _event_point(event, "target") if event is not None else None
    if point is not None:
        return point
    attacks_right = _side_attacks_right(possession_side, home_attacks_right)
    return {"x": 84.0 if attacks_right else 16.0, "y": 50.0}


def _trajectory_contract(event: Any) -> tuple[list[dict[str, float]], dict[str, float] | None]:
    contract = getattr(event, "render_contract", None) or {}
    ball = contract.get("ball") if isinstance(contract, dict) else None
    if not isinstance(ball, dict):
        return [], None
    raw_trajectory = ball.get("trajectory")
    if not isinstance(raw_trajectory, list):
        return [], None
    trajectory: list[dict[str, float]] = []
    for item in raw_trajectory:
        if not isinstance(item, dict):
            continue
        values = {key: item.get(key) for key in ("t", "x", "y", "z")}
        if not all(isinstance(values[key], (int, float)) for key in values):
            continue
        trajectory.append({key: float(values[key]) for key in values})
    trajectory.sort(key=lambda item: item["t"])
    spin = ball.get("spin")
    resolved_spin = None
    if isinstance(spin, dict) and all(isinstance(spin.get(axis), (int, float)) for axis in ("x", "y", "z")):
        resolved_spin = {axis: float(spin[axis]) for axis in ("x", "y", "z")}
    return trajectory, resolved_spin


def _sample_trajectory(trajectory: list[dict[str, float]], local: float) -> tuple[dict[str, float], dict[str, float], float]:
    if not trajectory:
        raise ValueError("trajectory must contain at least one sample")
    if local <= trajectory[0]["t"]:
        point = trajectory[0]
        return {"x": point["x"], "y": point["y"], "z": max(0.0, point["z"])}, {"x": 0.0, "y": 0.0, "z": 0.0}, trajectory[-1]["t"]
    if local >= trajectory[-1]["t"]:
        point = trajectory[-1]
        if len(trajectory) >= 2:
            previous = trajectory[-2]
            dt = max(0.001, point["t"] - previous["t"])
            velocity = {
                "x": (point["x"] - previous["x"]) / dt,
                "y": (point["y"] - previous["y"]) / dt,
                "z": (point["z"] - previous["z"]) / dt,
            }
        else:
            velocity = {"x": 0.0, "y": 0.0, "z": 0.0}
        return {"x": point["x"], "y": point["y"], "z": max(0.0, point["z"])}, velocity, trajectory[-1]["t"]

    for left, right in zip(trajectory, trajectory[1:]):
        if left["t"] <= local <= right["t"]:
            dt = max(0.001, right["t"] - left["t"])
            alpha = _clamp((local - left["t"]) / dt, 0.0, 1.0)
            point = {
                "x": left["x"] + ((right["x"] - left["x"]) * alpha),
                "y": left["y"] + ((right["y"] - left["y"]) * alpha),
                "z": max(0.0, left["z"] + ((right["z"] - left["z"]) * alpha)),
            }
            velocity = {
                "x": (right["x"] - left["x"]) / dt,
                "y": (right["y"] - left["y"]) / dt,
                "z": (right["z"] - left["z"]) / dt,
            }
            return point, velocity, trajectory[-1]["t"]
    point = trajectory[-1]
    return {"x": point["x"], "y": point["y"], "z": max(0.0, point["z"])}, {"x": 0.0, "y": 0.0, "z": 0.0}, trajectory[-1]["t"]


def _player_position(runtime: Any, player: Any, *, time_seconds: float, active_event: Any, stage: str, clock_minute: float, possession_side: MatchViewerSide, home_attacks_right: bool) -> tuple[dict[str, float], MatchViewerPlayerState, bool]:
    attacks_right = _side_attacks_right(runtime.view.side, home_attacks_right)
    anchor = _anchors(runtime, attacks_right)[player.player_id]
    position = dict(anchor)
    line = _line(runtime, player.player_id)
    highlighted = bool(active_event is not None and player.player_id in active_event.view.highlighted_player_ids)
    state = MatchViewerPlayerState.IDLE
    event_side = getattr(active_event, "team_side", None) if active_event is not None else None
    attacking_side = event_side or possession_side
    direction = 1.0 if _side_attacks_right(attacking_side, home_attacks_right) else -1.0
    if runtime.view.side is possession_side:
        position["x"] += 3.5 * direction
        position["x"] += 2.0 * direction if line == "attack" else 0.0
        state = MatchViewerPlayerState.ATTACKING if line == "attack" else MatchViewerPlayerState.MOVING
    else:
        position["x"] -= 2.0 * direction
        state = MatchViewerPlayerState.DEFENDING
    if active_event is not None:
        event_time = float(active_event.view.time_seconds)
        duration = max(0.5, float(active_event.view.duration_ms) / 1000.0)
        local = time_seconds - event_time
        influence = _smoothstep((local + 1.4) / (duration + 2.0))
        release = 1.0 - _smoothstep((local - duration) / 1.8)
        event_weight = influence * max(0.0, release)
        target = _event_target(active_event, possession_side, home_attacks_right)
        origin = _event_point(active_event, "origin") or dict(anchor)
        if player.player_id == active_event.view.primary_player_id:
            desired = origin if local < 0.15 else target
            blend = 0.72 * event_weight
            position["x"] += (desired["x"] - position["x"]) * blend
            position["y"] += (desired["y"] - position["y"]) * blend
            if active_event.view.event_type.value in {"goal", "shot", "miss", "save", "penalty"} and abs(local) < 0.55:
                state = MatchViewerPlayerState.ATTACKING if runtime.view.side is attacking_side else MatchViewerPlayerState.DEFENDING
        elif player.player_id == active_event.view.secondary_player_id:
            blend = 0.58 * event_weight
            position["x"] += (target["x"] - position["x"]) * blend
            position["y"] += (target["y"] - position["y"]) * blend
            state = MatchViewerPlayerState.MOVING if runtime.view.side is possession_side else MatchViewerPlayerState.DEFENDING
        elif runtime.view.side is attacking_side and line in {"attack", "midfield"}:
            lane, depth = _hash_phase(player.player_id)
            lane_offset = sin((clock_minute * 0.55) + lane) * (7.0 if line == "attack" else 5.0)
            depth_offset = cos((clock_minute * 0.41) + depth) * (4.0 if line == "attack" else 3.0)
            position["x"] += (target["x"] - position["x"]) * (0.16 * event_weight) + depth_offset * direction * 0.18
            position["y"] += (target["y"] - position["y"]) * (0.12 * event_weight) + lane_offset * 0.18
            state = MatchViewerPlayerState.ATTACKING if line == "attack" else MatchViewerPlayerState.MOVING
        elif runtime.view.side is not attacking_side and line in {"defense", "midfield"}:
            position["x"] += (target["x"] - position["x"]) * (0.08 * event_weight)
            position["y"] += (target["y"] - position["y"]) * (0.06 * event_weight)
            state = MatchViewerPlayerState.PRESSING if event_weight > 0.25 else MatchViewerPlayerState.DEFENDING
    return {"x": _clamp(position["x"]), "y": _clamp(position["y"])}, state, highlighted


def _velocity_for_player(runtime: Any, player: Any, **kwargs: Any) -> tuple[float, float]:
    now = kwargs["time_seconds"]
    current, _, _ = _player_position(runtime, player, **kwargs)
    previous_kwargs = dict(kwargs)
    previous_kwargs["time_seconds"] = max(0.0, now - 0.08)
    previous, _, _ = _player_position(runtime, player, **previous_kwargs)
    return ((current["x"] - previous["x"]) / 0.08, (current["y"] - previous["y"]) / 0.08)


def _animation_for_player(player: Any, line: str, state: MatchViewerPlayerState, speed_ratio: float, event: Any, time_seconds: float) -> MatchViewerAnimationState:
    if event is not None:
        local = time_seconds - float(event.view.time_seconds)
        if player.player_id == event.view.primary_player_id and abs(local) <= 0.45:
            if event.view.event_type.value in {"goal", "shot", "miss", "penalty"}:
                return MatchViewerAnimationState.SHOOT
            if event.view.event_type.value in {"attack", "pass", "set_piece"}:
                return MatchViewerAnimationState.PASS
        if player.player_id == event.view.secondary_player_id and abs(local) <= 0.55:
            return MatchViewerAnimationState.RUN
    if state is MatchViewerPlayerState.PRESSING:
        return MatchViewerAnimationState.PRESS
    if speed_ratio > 0.82:
        return MatchViewerAnimationState.SPRINT
    if speed_ratio > 0.42:
        return MatchViewerAnimationState.RUN
    if speed_ratio > 0.12:
        return MatchViewerAnimationState.JOG
    return MatchViewerAnimationState.IDLE


def build_player_payloads(*, home_runtime: Any, away_runtime: Any, home_attacks_right: bool, active_event: Any, stage: str, clock_minute: float, possession_side: MatchViewerSide, time_seconds: float) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for runtime in (home_runtime, away_runtime):
        anchors = _anchors(runtime, _side_attacks_right(runtime.view.side, home_attacks_right))
        for player_id in runtime.lineup:
            player = runtime.players_by_id[player_id]
            position, state, highlighted = _player_position(runtime, player, time_seconds=time_seconds, active_event=active_event, stage=stage, clock_minute=clock_minute, possession_side=possession_side, home_attacks_right=home_attacks_right)
            vx, vy = _velocity_for_player(runtime, player, time_seconds=time_seconds, active_event=active_event, stage=stage, clock_minute=clock_minute, possession_side=possession_side, home_attacks_right=home_attacks_right)
            speed_ratio = _clamp(hypot(vx, vy) / 8.5, 0.0, 1.0)
            payloads.append({"player_id": player.player_id, "team_id": player.team_id, "side": player.side, "shirt_number": player.shirt_number, "label": player.label, "role": player.role, "line": _line(runtime, player_id), "state": state, "active": True, "highlighted": highlighted, "position": position, "anchor_position": anchors[player_id], "animation_state": _animation_for_player(player, _line(runtime, player_id), state, speed_ratio, active_event, time_seconds), "speed_ratio": speed_ratio, "blend_factor": _smoothstep(speed_ratio), "stamina_pct": float(player.base_stamina_pct if player.base_stamina_pct is not None else 100.0), "has_possession": bool(active_event is not None and player.player_id == active_event.view.primary_player_id and runtime.view.side is possession_side), "facing": {"x": 1.0 if vx >= 0 else -1.0, "y": 0.0}, "velocity": {"x": round(vx, 3), "y": round(vy, 3)}})
    return payloads


def build_ball_payload(*, player_payloads: list[dict[str, Any]], home_runtime: Any, away_runtime: Any, home_attacks_right: bool, active_event: Any, stage: str, possession_side: MatchViewerSide, time_seconds: float) -> dict[str, Any]:
    if time_seconds <= 0.0:
        return {"position": {"x": 50.0, "y": 50.0}, "height": 0.05, "owner_player_id": None, "state": "rolling", "spin": None, "velocity": {"x": 0.0, "y": 0.0, "z": 0.0}}
    owner_id = None
    if active_event is not None:
        owner_id = active_event.view.primary_player_id if possession_side is active_event.team_side else active_event.view.secondary_player_id
    if not owner_id:
        for player in player_payloads:
            if player["side"] is possession_side and player["role"] is not PlayerRole.GOALKEEPER:
                owner_id = player["player_id"]
                break
    player_by_id = {item["player_id"]: item for item in player_payloads}
    owner_position = player_by_id.get(owner_id, {}).get("position") if owner_id else None
    origin = _event_point(active_event, "origin") if active_event is not None else None
    target = _event_point(active_event, "target") if active_event is not None else None
    event_time = float(active_event.view.time_seconds) if active_event is not None else time_seconds
    local = time_seconds - event_time
    event_type = active_event.view.event_type.value if active_event is not None else "neutral"
    flight_types = {"attack", "pass", "shot", "goal", "miss", "save", "penalty", "set_piece"}
    origin = origin or dict(owner_position or {"x": 50.0, "y": 50.0})
    if target is None:
        direction = 1.0 if _side_attacks_right(possession_side, home_attacks_right) else -1.0
        target = {"x": _clamp(origin["x"] + 10.0 * direction), "y": origin["y"]}

    trajectory, trajectory_spin = _trajectory_contract(active_event)
    post_flight_handoff_types = {"pass", "attack", "set_piece", "save"}
    if trajectory and local >= 0.0:
        point, sampled_velocity, trajectory_duration = _sample_trajectory(trajectory, local)
        if local <= trajectory_duration:
            state = "in_flight"
            x, y = point["x"], point["y"]
            height = point["z"]
            velocity_x = sampled_velocity["x"]
            velocity_y = sampled_velocity["y"]
            velocity_z = sampled_velocity["z"]
        else:
            handoff_id = active_event.view.secondary_player_id if active_event is not None and event_type in post_flight_handoff_types else None
            if handoff_id and handoff_id in player_by_id:
                owner_id = handoff_id
                owner_position = player_by_id[handoff_id]["position"]
                x, y = owner_position["x"], owner_position["y"]
                height = 0.05
                state = "controlled"
                velocity_x = velocity_y = velocity_z = 0.0
            else:
                x, y = point["x"], point["y"]
                height = point["z"]
                state = "rolling"
                velocity_x = sampled_velocity["x"]
                velocity_y = sampled_velocity["y"]
                velocity_z = sampled_velocity["z"]
    elif event_type in flight_types and -0.15 <= local <= 2.8:
        distance = hypot(target["x"] - origin["x"], target["y"] - origin["y"])
        duration = max(0.42, min(2.4, 0.42 + (distance / 32.0)))
        phase = _smoothstep((local + 0.08) / duration)
        x = origin["x"] + ((target["x"] - origin["x"]) * phase)
        y = origin["y"] + ((target["y"] - origin["y"]) * phase)
        height = 0.05 + (0.18 * sin(phase * 3.14159265)) if event_type in {"shot", "goal", "save", "miss", "penalty"} else 0.03 + (0.10 * sin(phase * 3.14159265))
        state = "in_flight"
        previous_phase = _smoothstep((max(0.0, local - 0.05) + 0.08) / duration)
        velocity_x = ((origin["x"] + ((target["x"] - origin["x"]) * phase)) - (origin["x"] + ((target["x"] - origin["x"]) * previous_phase))) / 0.05
        velocity_y = ((origin["y"] + ((target["y"] - origin["y"]) * phase)) - (origin["y"] + ((target["y"] - origin["y"]) * previous_phase))) / 0.05
        velocity_z = height / 0.05
    else:
        x, y = (owner_position or {"x": 50.0, "y": 50.0}).values()
        height = 0.05
        state = "controlled" if owner_position else "rolling"
        velocity_x = velocity_y = velocity_z = 0.0

    spin = trajectory_spin if state == "in_flight" and trajectory_spin is not None else ({"x": 0.0, "y": 0.35, "z": 0.8} if state == "in_flight" else None)
    return {
        "position": {"x": round(_clamp(x), 3), "y": round(_clamp(y), 3)},
        "height": round(max(0.0, height), 3),
        "owner_player_id": owner_id if state == "controlled" else None,
        "state": state,
        "spin": spin,
        "velocity": {"x": round(velocity_x, 3), "y": round(velocity_z, 3), "z": round(velocity_y, 3)},
    }
