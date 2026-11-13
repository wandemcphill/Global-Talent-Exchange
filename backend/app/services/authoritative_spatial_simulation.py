from __future__ import annotations

from hashlib import md5
from math import cos, hypot, sin, tau
from typing import Any

from app.match_engine.simulation.models import PlayerRole
from app.schemas.match_viewer import MatchViewerAnimationState, MatchViewerPlayerState, MatchViewerSide

_LINE_Y = {
    1: (50.0,),
    2: (34.0, 66.0),
    3: (22.0, 50.0, 78.0),
    4: (18.0, 39.0, 61.0, 82.0),
    5: (14.0, 32.0, 50.0, 68.0, 86.0),
}
_LINE_X = {3: (24.0, 50.0, 76.0), 4: (20.0, 38.0, 62.0, 80.0)}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _smoothstep(value: float) -> float:
    value = _clamp(value, 0.0, 1.0)
    return value * value * (3.0 - (2.0 * value))


def _hash_phase(player_id: str) -> tuple[float, float]:
    digest = md5(player_id.encode("utf-8"), usedforsecurity=False).digest()
    return (
        (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) * tau,
        (int.from_bytes(digest[4:8], "big") / 0xFFFFFFFF) * tau,
    )


def _line_sizes(runtime: Any) -> list[int]:
    outfield = runtime.lineup[1:]
    total = len(outfield)
    if total <= 0:
        return []

    try:
        values = [max(0, int(part)) for part in str(runtime.current_formation).split("-")]
    except ValueError:
        values = []
    if values and sum(values) == total and all(value > 0 for value in values):
        return values

    defenders = sum(runtime.players_by_id[item].role is PlayerRole.DEFENDER for item in outfield)
    midfielders = sum(runtime.players_by_id[item].role is PlayerRole.MIDFIELDER for item in outfield)
    forwards = sum(runtime.players_by_id[item].role is PlayerRole.FORWARD for item in outfield)
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
    defensive_line = float(getattr(runtime, "defensive_line", 50.0) or 50.0)
    width = float(getattr(runtime, "width", 50.0) or 50.0)
    line_shift = (defensive_line - 50.0) * 0.28
    adjusted_x = []
    for i, x in enumerate(base_x):
        if i == 0:
            shift = line_shift
        elif i == len(base_x) - 1:
            shift = line_shift * 0.35
        else:
            shift = line_shift * 0.65
        adjusted_x.append(_clamp(x + shift, 14.0, 86.0))
    base_x = tuple(adjusted_x)
    if not attacks_right:
        base_x = tuple(100.0 - value for value in base_x)
    result = {runtime.lineup[0]: {"x": 8.0 if attacks_right else 92.0, "y": 50.0}}
    cursor = 0
    outfield = runtime.lineup[1:]
    width_factor = 1.0 + ((width - 50.0) * 0.008)
    for group_index, size in enumerate(sizes):
        ys = _LINE_Y.get(size, tuple(10.0 + ((i + 1) * (80.0 / (size + 1))) for i in range(size)))
        if width_factor != 1.0:
            ys = tuple(_clamp(50.0 + (y - 50.0) * width_factor, 8.0, 92.0) for y in ys)
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
    if (
        isinstance(value, dict)
        and isinstance(value.get("x"), (int, float))
        and isinstance(value.get("y"), (int, float))
    ):
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


def _sample_trajectory(
    trajectory: list[dict[str, float]], local: float
) -> tuple[dict[str, float], dict[str, float], float]:
    if not trajectory:
        raise ValueError("trajectory must contain at least one sample")
    if local <= trajectory[0]["t"]:
        point = trajectory[0]
        return (
            {"x": point["x"], "y": point["y"], "z": max(0.0, point["z"])},
            {"x": 0.0, "y": 0.0, "z": 0.0},
            trajectory[-1]["t"],
        )
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
    return (
        {"x": point["x"], "y": point["y"], "z": max(0.0, point["z"])},
        {"x": 0.0, "y": 0.0, "z": 0.0},
        trajectory[-1]["t"],
    )


def _ball_from_depth(attacks_right: bool, depth: float) -> dict[str, float]:
    depth = _clamp(depth, 0.08, 0.92)
    lane = 50.0 + sin(depth * 9.0) * 14.0
    x = (20.0 + depth * 70.0) if attacks_right else (80.0 - depth * 70.0)
    return {"x": _clamp(x), "y": _clamp(lane, 16.0, 84.0)}


def _instruction(runtime: Any, name: str, default: float = 50.0) -> float:
    return float(getattr(runtime, name, default) or default)


def _shift_toward_block(
    position: dict[str, float],
    anchor: dict[str, float],
    line: str,
    *,
    ball: dict[str, float],
    direction: float,
    in_possession: bool,
    blend: float,
    defensive_line: float = 50.0,
    press: float = 50.0,
    width: float = 50.0,
) -> None:
    """Slide a whole line with the ball, the way a 2D match keeps its shape."""
    if blend <= 0.0:
        return
    if line == "goalkeeper":
        position["y"] += (ball["y"] - position["y"]) * min(0.1, blend * 0.12)
        return
    line_bias = _clamp((defensive_line - 50.0) / 50.0, -1.0, 1.0)
    press_bias = _clamp((press - 50.0) / 50.0, -1.0, 1.0)
    width_bias = _clamp((width - 50.0) / 50.0, -1.0, 1.0)
    if in_possession:
        along = {"defense": -15.0, "midfield": -5.0, "attack": 8.0}.get(line, -4.0)
        if line == "defense":
            along += 6.0 * line_bias
            if abs(anchor["y"] - 50.0) > 18.0:
                along += 5.0 + (4.0 * width_bias)
        elif line == "midfield":
            along += 3.0 * line_bias
    else:
        along = {"defense": 11.0, "midfield": 3.0, "attack": -7.0}.get(line, 2.0)
        if line == "defense":
            along -= (6.0 * press_bias) + (3.0 * line_bias)
        elif line == "midfield":
            along -= 4.0 * press_bias
    desired_x = ball["x"] + along * direction
    offside_gap = 4.5 - (1.4 * line_bias)
    if in_possession and line == "defense":
        if direction > 0:
            desired_x = min(desired_x, ball["x"] - offside_gap)
        else:
            desired_x = max(desired_x, ball["x"] + offside_gap)
    elif not in_possession and line == "defense":
        if direction > 0:
            desired_x = max(desired_x, ball["x"] + offside_gap)
        else:
            desired_x = min(desired_x, ball["x"] - offside_gap)
    desired_x = _clamp(desired_x, 8.0, 92.0)
    lane_y = anchor["y"] * 0.74 + ball["y"] * 0.26
    if not in_possession and line in {"defense", "midfield"}:
        compact = 0.84 + (0.12 * width_bias)
        lane_y = 50.0 + (lane_y - 50.0) * compact
    elif in_possession and line in {"defense", "attack"}:
        spread = 1.0 + (0.16 * width_bias)
        lane_y = 50.0 + (lane_y - 50.0) * spread
    position["x"] += (desired_x - position["x"]) * blend
    position["y"] += (_clamp(lane_y, 8.0, 92.0) - position["y"]) * blend


def _carrier_id(runtime: Any, attacks_right: bool, phase_depth: float) -> str | None:
    if not runtime.lineup:
        return None
    sizes = _line_sizes(runtime)
    outfield = runtime.lineup[1:]
    if not sizes or not outfield:
        return runtime.lineup[0]
    if phase_depth < 0.34:
        line_index = 0
    elif phase_depth < 0.62:
        line_index = (len(sizes) - 1) // 2
        if line_index == 0 and len(sizes) > 1:
            line_index = 1
    else:
        line_index = len(sizes) - 1
    cursor = 0
    group: list[str] = []
    for index, size in enumerate(sizes):
        chunk = list(outfield[cursor : cursor + size])
        if index == line_index:
            group = chunk
            break
        cursor += size
    if not group:
        group = list(outfield)
    anchors = _anchors(runtime, attacks_right)
    lane = 50.0 + sin(phase_depth * 9.0) * 14.0
    return min(group, key=lambda player_id: abs(anchors[player_id]["y"] - lane))


def _player_position(
    runtime: Any,
    player: Any,
    *,
    time_seconds: float,
    active_event: Any,
    stage: str,
    clock_minute: float,
    possession_side: MatchViewerSide,
    home_attacks_right: bool,
    phase_depth: float | None = None,
) -> tuple[dict[str, float], MatchViewerPlayerState, bool]:
    attacks_right = _side_attacks_right(runtime.view.side, home_attacks_right)
    anchor = _anchors(runtime, attacks_right)[player.player_id]
    position = dict(anchor)
    line = _line(runtime, player.player_id)
    highlighted = bool(active_event is not None and player.player_id in active_event.view.highlighted_player_ids)
    state = MatchViewerPlayerState.IDLE
    event_side = getattr(active_event, "team_side", None) if active_event is not None else None
    attacking_side = event_side or possession_side
    direction = 1.0 if _side_attacks_right(attacking_side, home_attacks_right) else -1.0
    in_possession = runtime.view.side is possession_side
    if in_possession:
        push = {"goalkeeper": 0.8, "defense": 5.5, "midfield": 8.5, "attack": 12.0}.get(line, 6.0)
        if line == "defense":
            push += 3.2 * min(1.0, abs(anchor["y"] - 50.0) / 28.0)
        position["x"] += push * direction
        state = (
            MatchViewerPlayerState.IDLE
            if line == "goalkeeper"
            else MatchViewerPlayerState.ATTACKING
            if line == "attack"
            else MatchViewerPlayerState.MOVING
        )
    else:
        tuck = {"goalkeeper": 0.0, "defense": 3.8, "midfield": 1.4, "attack": -2.8}.get(line, 0.0)
        position["x"] += tuck * direction
        if line in {"defense", "midfield"}:
            position["y"] = 50.0 + (position["y"] - 50.0) * 0.86
        state = MatchViewerPlayerState.DEFENDING
        press_intensity = float(getattr(runtime, "press_intensity", 50.0) or 50.0)
        if active_event is not None:
            target_pt = _event_point(active_event, "origin") or _event_point(active_event, "target")
            if target_pt is not None:
                dx = target_pt["x"] - position["x"]
                dy = target_pt["y"] - position["y"]
                dist = hypot(dx, dy)
                press_radius = 18.0 + (press_intensity * 0.16)
                if 0.5 < dist < press_radius:
                    pull = ((press_radius - dist) / press_radius) * (press_intensity / 100.0) * 0.22
                    position["x"] += dx * pull
                    position["y"] += dy * pull
                    if line != "goalkeeper" and dist < 14.0:
                        state = MatchViewerPlayerState.PRESSING
    event_weight = 0.0
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
            strike = _smoothstep((local + 0.05) / 1.15)
            desired = {
                "x": origin["x"] + ((target["x"] - origin["x"]) * strike),
                "y": origin["y"] + ((target["y"] - origin["y"]) * strike),
            }
            blend = 0.72 * event_weight
            position["x"] += (desired["x"] - position["x"]) * blend
            position["y"] += (desired["y"] - position["y"]) * blend
            if active_event.view.event_type.value in {"goal", "shot", "miss", "save", "penalty"} and abs(local) < 0.55:
                state = (
                    MatchViewerPlayerState.ATTACKING
                    if runtime.view.side is attacking_side
                    else MatchViewerPlayerState.DEFENDING
                )
        elif player.player_id == active_event.view.secondary_player_id:
            blend = 0.58 * event_weight
            position["x"] += (target["x"] - position["x"]) * blend
            position["y"] += (target["y"] - position["y"]) * blend
            state = (
                MatchViewerPlayerState.MOVING
                if runtime.view.side is possession_side
                else MatchViewerPlayerState.DEFENDING
            )
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
    actor = active_event is not None and player.player_id in {
        active_event.view.primary_player_id,
        active_event.view.secondary_player_id,
    }
    ball_point = None
    block_blend = 0.0
    if not actor and phase_depth is not None and active_event is None:
        ball_point = _ball_from_depth(_side_attacks_right(possession_side, home_attacks_right), phase_depth)
        block_blend = 0.82
    elif not actor and active_event is not None:
        origin = _event_point(active_event, "origin") or dict(anchor)
        target = _event_target(active_event, possession_side, home_attacks_right)
        ball_point = {
            "x": origin["x"] + ((target["x"] - origin["x"]) * event_weight),
            "y": origin["y"] + ((target["y"] - origin["y"]) * event_weight),
        }
        block_blend = 0.34 * event_weight
    if ball_point is not None:
        _shift_toward_block(
            position,
            anchor,
            line,
            ball=ball_point,
            direction=direction,
            in_possession=in_possession,
            blend=block_blend,
            defensive_line=_instruction(runtime, "defensive_line"),
            press=_instruction(runtime, "press_intensity"),
            width=_instruction(runtime, "width"),
        )
    _drop_when_tired(position, line=line, attacks_right=attacks_right, clock_minute=clock_minute, player=player)
    state = _engage_around_the_ball(
        position,
        runtime,
        player,
        line=line,
        state=state,
        ball_point=ball_point,
        direction=direction,
        in_possession=in_possession,
        attacks_right=attacks_right,
        phase_depth=phase_depth,
        active_event=active_event,
    )
    _apply_restart(
        position,
        anchor,
        line=line,
        player=player,
        active_event=active_event,
        event_weight=event_weight,
        in_possession=in_possession,
        direction=direction,
    )
    return {"x": _clamp(position["x"]), "y": _clamp(position["y"])}, state, highlighted


def _nearest_on_line(runtime: Any, attacks_right: bool, ball: dict[str, float], lines: set[str], exclude: str | None) -> str | None:
    anchors = _anchors(runtime, attacks_right)
    ranked: list[tuple[float, str]] = []
    for player_id in runtime.lineup:
        if player_id == exclude or _line(runtime, player_id) not in lines:
            continue
        anchor = anchors[player_id]
        channel_y = anchor["y"] * 0.74 + ball["y"] * 0.26
        channel_y = 50.0 + (channel_y - 50.0) * 0.84
        ranked.append((hypot(anchor["x"] - ball["x"], channel_y - ball["y"]), player_id))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][1]


def _support_id(runtime: Any, attacks_right: bool, ball: dict[str, float], direction: float, carrier_id: str | None) -> str | None:
    anchors = _anchors(runtime, attacks_right)
    attackers = [player_id for player_id in runtime.lineup if _line(runtime, player_id) == "attack" and player_id != carrier_id]
    pool = attackers or [
        player_id for player_id in runtime.lineup if _line(runtime, player_id) == "midfield" and player_id != carrier_id
    ]
    if not pool:
        return None

    def score(player_id: str) -> tuple[float, float]:
        anchor = anchors[player_id]
        ahead = (anchor["x"] - ball["x"]) * direction
        return (ahead, -abs(anchor["y"] - ball["y"]))

    return max(pool, key=score)


def _engage_around_the_ball(
    position: dict[str, float],
    runtime: Any,
    player: Any,
    *,
    line: str,
    state: MatchViewerPlayerState,
    ball_point: dict[str, float] | None,
    direction: float,
    in_possession: bool,
    attacks_right: bool,
    phase_depth: float | None,
    active_event: Any,
) -> MatchViewerPlayerState:
    """Put the carrier on the ball, send one runner, and step one opponent out."""
    if ball_point is None or phase_depth is None or active_event is not None:
        return state
    carrier_id = _carrier_id(runtime, attacks_right, phase_depth) if in_possession else None
    if in_possession and player.player_id == carrier_id:
        position["x"] = ball_point["x"]
        position["y"] = ball_point["y"]
        return state
    if in_possession:
        support_id = _support_id(runtime, attacks_right, ball_point, direction, carrier_id)
        if player.player_id == support_id:
            position["x"] += 6.2 * direction
            position["y"] += (ball_point["y"] - position["y"]) * 0.38
            return MatchViewerPlayerState.ATTACKING if line == "attack" else MatchViewerPlayerState.MOVING
        return state
    if line == "goalkeeper":
        position["y"] += (ball_point["y"] - position["y"]) * 0.4
        return state
    presser_id = _nearest_on_line(runtime, attacks_right, ball_point, {"midfield"}, None) or _nearest_on_line(
        runtime, attacks_right, ball_point, {"attack"}, None
    )
    if player.player_id != presser_id:
        return state
    dx = ball_point["x"] - position["x"]
    dy = ball_point["y"] - position["y"]
    dist = hypot(dx, dy)
    stop = 4.6
    if dist > stop:
        press = _clamp((_instruction(runtime, "press_intensity") - 50.0) / 50.0, -1.0, 1.0)
        gain = 0.4 + (0.22 * press)
        scale = (dist - stop) / dist
        position["x"] += dx * scale * gain
        position["y"] += dy * scale * gain
    return MatchViewerPlayerState.PRESSING


def _drop_when_tired(
    position: dict[str, float],
    *,
    line: str,
    attacks_right: bool,
    clock_minute: float,
    player: Any,
) -> None:
    if line == "goalkeeper":
        return
    late = _clamp((clock_minute - 65.0) / 25.0, 0.0, 1.0)
    if late <= 0.0:
        return
    stamina = float(getattr(player, "base_stamina_pct", None) or 100.0)
    tired = late * (1.15 if stamina < 72.0 else 0.55)
    drop = tired * (4.8 if line == "attack" else 2.6 if line == "midfield" else 1.6)
    position["x"] -= drop if attacks_right else -drop


def _restart_kind(active_event: Any) -> str | None:
    if active_event is None:
        return None
    event_type = str(getattr(getattr(active_event, "view", None), "event_type", "") or "")
    event_type = event_type.split(".")[-1].lower()
    metadata = getattr(active_event, "metadata", None) or {}
    raw = str(metadata.get("set_piece_kind") or metadata.get("restart") or "").lower()
    if event_type == "penalty" or raw == "penalty":
        return "penalty"
    if raw in {"corner", "free_kick", "throw_in", "throw"}:
        return "throw_in" if raw == "throw" else raw
    if event_type == "set_piece":
        return "corner" if "corner" in raw else "free_kick"
    if event_type == "foul":
        return "free_kick"
    if str(metadata.get("possession_route") or "") == "set_piece" and event_type in {"goal", "shot", "miss", "save"}:
        return "free_kick"
    return None


def _apply_restart(
    position: dict[str, float],
    anchor: dict[str, float],
    *,
    line: str,
    player: Any,
    active_event: Any,
    event_weight: float,
    in_possession: bool,
    direction: float,
) -> None:
    kind = _restart_kind(active_event)
    if kind is None or event_weight <= 0.0:
        return
    origin = _event_point(active_event, "origin") or {"x": 70.0 if direction > 0 else 30.0, "y": 50.0}
    blend = min(0.9, event_weight * 1.7)
    is_taker = player.player_id == active_event.view.primary_player_id
    spot_x = 88.0 if direction > 0 else 12.0
    if kind == "penalty":
        if is_taker and in_possession:
            desired = {"x": spot_x, "y": 50.0}
        elif line == "goalkeeper" and not in_possession:
            desired = {"x": 94.0 if direction > 0 else 6.0, "y": 50.0}
        elif in_possession:
            desired = {"x": 70.0 if direction > 0 else 30.0, "y": anchor["y"]}
        else:
            desired = {"x": 78.0 if direction > 0 else 22.0, "y": anchor["y"]}
    elif kind == "corner":
        corner_y = 8.0 if origin["y"] < 50.0 else 92.0
        corner_x = 98.0 if direction > 0 else 2.0
        if is_taker and in_possession:
            desired = {"x": corner_x, "y": corner_y}
        elif in_possession and line == "attack":
            desired = {"x": 84.0 if direction > 0 else 16.0, "y": anchor["y"]}
        elif not in_possession and line == "defense":
            desired = {"x": 88.0 if direction > 0 else 12.0, "y": anchor["y"]}
        elif not in_possession and line == "goalkeeper":
            desired = {"x": 94.0 if direction > 0 else 6.0, "y": 50.0 + ((corner_y - 50.0) * 0.15)}
        else:
            desired = {"x": 62.0 if direction > 0 else 38.0, "y": anchor["y"]}
    elif kind == "throw_in":
        touch_y = 6.0 if origin["y"] < 50.0 else 94.0
        if is_taker and in_possession:
            desired = {"x": origin["x"], "y": touch_y}
        elif in_possession:
            desired = {"x": origin["x"] + (6.0 * direction), "y": anchor["y"]}
        else:
            desired = {"x": origin["x"] + (10.0 * direction), "y": anchor["y"]}
    else:
        wall_x = origin["x"] + (9.0 * direction)
        if is_taker and in_possession:
            desired = {"x": origin["x"], "y": origin["y"]}
        elif not in_possession and line == "defense" and abs(anchor["y"] - origin["y"]) < 22.0:
            desired = {"x": wall_x, "y": origin["y"] + ((anchor["y"] - 50.0) * 0.18)}
        elif in_possession and line == "attack":
            desired = {"x": origin["x"] + (14.0 * direction), "y": anchor["y"]}
        elif not in_possession and line == "goalkeeper":
            desired = {"x": 92.0 if direction > 0 else 8.0, "y": 50.0}
        else:
            desired = {"x": origin["x"] - (8.0 * direction), "y": anchor["y"]}
    position["x"] += (_clamp(desired["x"], 2.0, 98.0) - position["x"]) * blend
    position["y"] += (_clamp(desired["y"], 4.0, 96.0) - position["y"]) * blend


def _velocity_for_player(runtime: Any, player: Any, **kwargs: Any) -> tuple[float, float]:
    now = kwargs["time_seconds"]
    current, _, _ = _player_position(runtime, player, **kwargs)
    previous_kwargs = dict(kwargs)
    previous_kwargs["time_seconds"] = max(0.0, now - 0.08)
    previous, _, _ = _player_position(runtime, player, **previous_kwargs)
    return ((current["x"] - previous["x"]) / 0.08, (current["y"] - previous["y"]) / 0.08)


def _animation_for_player(
    player: Any, line: str, state: MatchViewerPlayerState, speed_ratio: float, event: Any, time_seconds: float
) -> MatchViewerAnimationState:
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


def build_player_payloads(
    *,
    home_runtime: Any,
    away_runtime: Any,
    home_attacks_right: bool,
    active_event: Any,
    stage: str,
    clock_minute: float,
    possession_side: MatchViewerSide,
    time_seconds: float,
    phase_depth: float | None = None,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for runtime in (home_runtime, away_runtime):
        attacks_right = _side_attacks_right(runtime.view.side, home_attacks_right)
        anchors = _anchors(runtime, attacks_right)
        carrier_id = None
        if phase_depth is not None and active_event is None and runtime.view.side is possession_side:
            carrier_id = _carrier_id(runtime, attacks_right, phase_depth)
        direction = 1.0 if _side_attacks_right(possession_side, home_attacks_right) else -1.0
        for player_id in runtime.lineup:
            player = runtime.players_by_id[player_id]
            position, state, highlighted = _player_position(
                runtime,
                player,
                time_seconds=time_seconds,
                active_event=active_event,
                stage=stage,
                clock_minute=clock_minute,
                possession_side=possession_side,
                home_attacks_right=home_attacks_right,
                phase_depth=phase_depth,
            )
            vx, vy = _velocity_for_player(
                runtime,
                player,
                time_seconds=time_seconds,
                active_event=active_event,
                stage=stage,
                clock_minute=clock_minute,
                possession_side=possession_side,
                home_attacks_right=home_attacks_right,
                phase_depth=phase_depth,
            )
            line = _line(runtime, player_id)
            if phase_depth is not None and active_event is None and line != "goalkeeper" and hypot(vx, vy) < 0.2:
                moving = 1.4 if runtime.view.side is possession_side else -0.7
                vx = moving * direction
                vy = 0.0
            speed_ratio = _clamp(hypot(vx, vy) / 8.5, 0.0, 1.0)
            payloads.append(
                {
                    "player_id": player.player_id,
                    "team_id": player.team_id,
                    "side": player.side,
                    "shirt_number": player.shirt_number,
                    "label": player.label,
                    "role": player.role,
                    "line": _line(runtime, player_id),
                    "state": state,
                    "active": True,
                    "highlighted": highlighted,
                    "position": position,
                    "anchor_position": anchors[player_id],
                    "animation_state": _animation_for_player(
                        player, _line(runtime, player_id), state, speed_ratio, active_event, time_seconds
                    ),
                    "speed_ratio": speed_ratio,
                    "blend_factor": _smoothstep(speed_ratio),
                    "stamina_pct": float(player.base_stamina_pct if player.base_stamina_pct is not None else 100.0),
                    "has_possession": bool(
                        player.player_id == carrier_id
                        or (
                            active_event is not None
                            and player.player_id == active_event.view.primary_player_id
                            and runtime.view.side is possession_side
                        )
                    ),
                    "facing": {"x": 1.0 if vx >= 0 else -1.0, "y": 0.0},
                    "velocity": {"x": round(vx, 3), "y": round(vy, 3)},
                }
            )
    return payloads


def build_ball_payload(
    *,
    player_payloads: list[dict[str, Any]],
    home_runtime: Any,
    away_runtime: Any,
    home_attacks_right: bool,
    active_event: Any,
    stage: str,
    possession_side: MatchViewerSide,
    time_seconds: float,
) -> dict[str, Any]:
    if time_seconds <= 0.0:
        return {
            "position": {"x": 50.0, "y": 50.0},
            "height": 0.05,
            "owner_player_id": None,
            "state": "rolling",
            "spin": None,
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
        }
    owner_id = None
    if active_event is not None:
        owner_id = (
            active_event.view.primary_player_id
            if possession_side is active_event.team_side
            else active_event.view.secondary_player_id
        )
    if not owner_id:
        for player in player_payloads:
            if player.get("has_possession"):
                owner_id = player["player_id"]
                break
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
            handoff_id = (
                active_event.view.secondary_player_id
                if active_event is not None and event_type in post_flight_handoff_types
                else None
            )
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
    elif event_type in flight_types and local < -0.15:
        approach = _smoothstep((local + 2.0) / 1.85)
        x = 50.0 + ((origin["x"] - 50.0) * approach)
        y = 50.0 + ((origin["y"] - 50.0) * approach)
        height = 0.05
        state = "rolling"
        previous_approach = _smoothstep((max(-2.0, local - 0.05) + 2.0) / 1.85)
        velocity_x = (
            (50.0 + ((origin["x"] - 50.0) * approach))
            - (50.0 + ((origin["x"] - 50.0) * previous_approach))
        ) / 0.05
        velocity_y = (
            (50.0 + ((origin["y"] - 50.0) * approach))
            - (50.0 + ((origin["y"] - 50.0) * previous_approach))
        ) / 0.05
        velocity_z = 0.0
    elif event_type in flight_types and -0.15 <= local <= 2.8:
        distance = hypot(target["x"] - origin["x"], target["y"] - origin["y"])
        duration = max(0.42, min(2.4, 0.42 + (distance / 32.0)))
        phase = _smoothstep((local + 0.08) / duration)
        x = origin["x"] + ((target["x"] - origin["x"]) * phase)
        y = origin["y"] + ((target["y"] - origin["y"]) * phase)
        height = (
            0.05 + (0.18 * sin(phase * 3.14159265))
            if event_type in {"shot", "goal", "save", "miss", "penalty"}
            else 0.03 + (0.10 * sin(phase * 3.14159265))
        )
        state = "in_flight"
        previous_phase = _smoothstep((max(0.0, local - 0.05) + 0.08) / duration)
        velocity_x = (
            (origin["x"] + ((target["x"] - origin["x"]) * phase))
            - (origin["x"] + ((target["x"] - origin["x"]) * previous_phase))
        ) / 0.05
        velocity_y = (
            (origin["y"] + ((target["y"] - origin["y"]) * phase))
            - (origin["y"] + ((target["y"] - origin["y"]) * previous_phase))
        ) / 0.05
        velocity_z = height / 0.05
    else:
        owned = owner_position or {"x": 50.0, "y": 50.0}
        x, y = owned["x"], owned["y"]
        height = 0.05
        state = "controlled" if owner_position else "rolling"
        velocity_x = velocity_y = velocity_z = 0.0
        if state == "controlled" and active_event is None:
            lead = 0.8 if _side_attacks_right(possession_side, home_attacks_right) else -0.8
            x += lead
            velocity_x = lead / 0.2

    spin = (
        trajectory_spin
        if state == "in_flight" and trajectory_spin is not None
        else ({"x": 0.0, "y": 0.35, "z": 0.8} if state == "in_flight" else None)
    )
    return {
        "position": {"x": round(_clamp(x), 3), "y": round(_clamp(y), 3)},
        "height": round(max(0.0, height), 3),
        "owner_player_id": owner_id if state == "controlled" else None,
        "state": state,
        "spin": spin,
        "velocity": {"x": round(velocity_x, 3), "y": round(velocity_z, 3), "z": round(velocity_y, 3)},
    }
