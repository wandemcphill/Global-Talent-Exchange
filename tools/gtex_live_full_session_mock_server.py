from __future__ import annotations

import argparse
import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketState

ACCESS_TOKEN = "live-full-session-access-token"  # pragma: allowlist secret
REFRESH_TOKEN = "live-full-session-refresh-token"  # pragma: allowlist secret
MATCH_ID = "live-full-session-test"
LOGGER = logging.getLogger("gtex_live_full_session_mock_server")

FIRST_HALF_MINUTE_LIMIT = 45.0
SECOND_HALF_START_MINUTE = 46.0
FULLTIME_MINUTE = 90.0
FRAME_MINUTE_STEP = 0.1
FULLTIME_SEQUENCE = int(FULLTIME_MINUTE / FRAME_MINUTE_STEP)
WEBSOCKET_FRAME_INTERVAL_SECONDS = 1.0
SEND_TIMEOUT_SECONDS = 3.0
CLIENT_IDLE_GRACE_SECONDS = 45.0
PLAYABLE_X_MIN = 7.5
PLAYABLE_X_MAX = 97.5
PLAYABLE_Z_MIN = 8.5
PLAYABLE_Z_MAX = 56.5
HOLDER_WINDOW_MINUTES = 4.5
HOLDER_CYCLE = (
    "home-8",
    "home-10",
    "home-9",
    "home-11",
    "away-6",
    "away-8",
    "away-9",
    "away-10",
    "home-7",
    "home-8",
    "home-10",
    "away-4",
)
BALL_LANE_PATTERN = (-10.0, -4.0, 8.0, 13.0, 6.0, -8.0, -12.0, 4.0, 11.0, -6.0, 2.0, 9.0)


@dataclass
class SessionState:
    http_requests: int = 0
    websocket_connections: int = 0
    frames_served: int = 0
    final_frame_sent: bool = False
    minutes: list[float] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    scores: list[str] = field(default_factory=list)
    camera_presets: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.http_requests = 0
        self.websocket_connections = 0
        self.frames_served = 0
        self.final_frame_sent = False
        self.minutes.clear()
        self.phases.clear()
        self.scores.clear()
        self.camera_presets.clear()

    @property
    def next_sequence(self) -> int:
        return max(0, min(FULLTIME_SEQUENCE, self.frames_served))

    def record_payload(self, payload: dict[str, Any]) -> None:
        self.frames_served += 1

        minute = float(payload.get("clockMinute") or 0.0)
        phase = str(payload.get("phase") or "")
        score = f"{int(payload.get('homeScore') or 0)}-{int(payload.get('awayScore') or 0)}"
        camera_preset = str(payload.get("cameraPreset") or "")

        self.minutes.append(minute)
        self.phases.append(phase)
        self.scores.append(score)
        self.camera_presets.append(camera_preset)

        if phase == "fulltime":
            self.final_frame_sent = True

    def build_summary(self) -> dict[str, Any]:
        def unique_ordered(values: list[str]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []
            for value in values:
                if value in seen:
                    continue
                seen.add(value)
                result.append(value)
            return result

        return {
            "match_id": MATCH_ID,
            "http_requests": self.http_requests,
            "websocket_connections": self.websocket_connections,
            "frames_served": self.frames_served,
            "final_frame_sent": self.final_frame_sent,
            "first_minute": self.minutes[0] if self.minutes else None,
            "last_minute": self.minutes[-1] if self.minutes else None,
            "phase_sequence": unique_ordered(self.phases),
            "score_timeline": unique_ordered(self.scores),
            "camera_presets_seen": unique_ordered(self.camera_presets),
        }


STATE = SessionState()
app = FastAPI()


def _score_for_minute(minute: float) -> tuple[int, int]:
    if minute < 28.0:
        return (0, 0)
    if minute < 63.0:
        return (1, 0)
    if minute < 84.0:
        return (1, 1)
    return (2, 1)


def _minute_for_sequence(seq: int) -> float:
    normalized = max(0, min(FULLTIME_SEQUENCE, seq))
    if normalized >= FULLTIME_SEQUENCE:
        return FULLTIME_MINUTE

    return round(normalized * FRAME_MINUTE_STEP, 1)


def _phase_for_sequence(seq: int) -> str:
    minute = _minute_for_sequence(seq)
    if minute >= FULLTIME_MINUTE:
        return "fulltime"
    if minute >= SECOND_HALF_START_MINUTE:
        return "second_half"
    if minute >= FIRST_HALF_MINUTE_LIMIT:
        return "halftime"
    return "first_half"


def _holder_window_index(minute: float) -> int:
    if minute >= FULLTIME_MINUTE:
        return max(0, len(HOLDER_CYCLE) - 1)

    return int(max(0.0, minute) // HOLDER_WINDOW_MINUTES)


def _holder_window_progress(minute: float) -> float:
    if minute >= FULLTIME_MINUTE:
        return 1.0

    return (max(0.0, minute) % HOLDER_WINDOW_MINUTES) / HOLDER_WINDOW_MINUTES


def _holder_for_minute(minute: float) -> str:
    return HOLDER_CYCLE[_holder_window_index(minute) % len(HOLDER_CYCLE)]


def _next_holder_for_minute(minute: float) -> str:
    if minute >= FULLTIME_MINUTE:
        return ""

    next_index = (_holder_window_index(minute) + 1) % len(HOLDER_CYCLE)
    return HOLDER_CYCLE[next_index]


def _previous_holder_for_minute(minute: float) -> str:
    if minute <= 0.0:
        return HOLDER_CYCLE[0]

    previous_index = (_holder_window_index(minute) - 1) % len(HOLDER_CYCLE)
    return HOLDER_CYCLE[previous_index]


def _team_token(player_id: str) -> str:
    if not player_id:
        return ""

    return player_id.split("-", 1)[0]


def _holder_for_sequence(seq: int) -> str:
    return _holder_for_minute(_minute_for_sequence(seq))


def _next_holder_for_sequence(seq: int) -> str:
    return _next_holder_for_minute(_minute_for_sequence(seq))


def _ball_state_for_minute(minute: float, holder_id: str) -> tuple[float, float, bool]:
    if minute >= FULLTIME_MINUTE:
        return (52.5, 34.0, True)

    attacking_home = holder_id.startswith("home")
    previous_holder_id = _previous_holder_for_minute(minute)
    next_holder_id = _next_holder_for_minute(minute)
    previous_same_team = _team_token(previous_holder_id) == _team_token(holder_id)
    next_same_team = _team_token(next_holder_id) == _team_token(holder_id)
    progress = _holder_window_progress(minute)
    eased = 0.5 - (0.5 * math.cos(progress * math.pi))
    lane_center = 34.0 + BALL_LANE_PATTERN[_holder_window_index(minute) % len(BALL_LANE_PATTERN)]
    lane_curve = math.sin(progress * math.pi) * (2.4 if (_holder_window_index(minute) % 2 == 0) else -2.4)
    if attacking_home:
        start_x = 48.0 if not previous_same_team else 66.0
        end_x = 92.0 if next_same_team else 74.0
    else:
        start_x = 57.0 if not previous_same_team else 39.0
        end_x = 13.0 if next_same_team else 31.0
    ball_x = start_x + ((end_x - start_x) * eased)
    ball_x = max(PLAYABLE_X_MIN + 3.0, min(PLAYABLE_X_MAX - 3.0, ball_x))
    ball_z = _clamp_pitch_z(lane_center + lane_curve)
    return (round(ball_x, 3), round(ball_z, 3), attacking_home)


def _camera_preset_for_state(minute: float, ball_x: float) -> str:
    if minute >= FULLTIME_MINUTE:
        return "broadcast"
    if ball_x >= 84.0 or ball_x <= 21.0:
        return "box_zoom"
    if abs(ball_x - 52.5) >= 16.0:
        return "attack_push"
    return "wide_reset"


def _lane_sign(index: int, base_z: float) -> float:
    if abs(base_z - 34.0) <= 1.0:
        return -1.0 if (index % 2 == 0) else 1.0
    return -1.0 if base_z < 34.0 else 1.0


def _clamp_pitch_z(value: float) -> float:
    return max(PLAYABLE_Z_MIN, min(PLAYABLE_Z_MAX, value))


def _clamp_pitch_x(value: float) -> float:
    return max(PLAYABLE_X_MIN, min(PLAYABLE_X_MAX, value))


def _resolve_facing(velocity_x: float, velocity_z: float, default_x: float) -> tuple[float, float]:
    planar_mag = math.hypot(velocity_x, velocity_z)
    if planar_mag > 0.02:
        return (round(velocity_x / planar_mag, 3), round(velocity_z / planar_mag, 3))
    return (default_x, 0.0)


def _team_meta_for_holder(holder_id: str) -> tuple[str, str]:
    if holder_id.startswith("away"):
        return ("away-team", "Full Session Away")

    return ("home-team", "Full Session Home")


def _live_play_event_for_sequence(
    seq: int,
    minute: float,
    holder_id: str,
    home_score: int,
    away_score: int,
) -> dict[str, Any]:
    next_holder_id = _next_holder_for_sequence(seq)
    team_id, team_name = _team_meta_for_holder(holder_id)
    event_type = "attack"
    banner_text = "Carrier drive"
    commentary = "The carrier advances with controlled support around the ball."
    secondary_player_id = ""
    window_progress = _holder_window_progress(minute)

    if holder_id and next_holder_id and window_progress >= 0.72:
        same_team_transition = holder_id.split("-", 1)[0] == next_holder_id.split("-", 1)[0]
        if same_team_transition and holder_id != next_holder_id:
            style_index = _holder_window_index(minute) % 3
            if style_index == 1:
                event_type = "through_pass"
                banner_text = "Through pass"
                commentary = "The carrier shapes an intentional through pass into the runner."
            elif style_index == 2:
                event_type = "cross"
                banner_text = "Cross-field ball"
                commentary = "A lofted service is sent toward the far-side runner."
            else:
                event_type = "pass"
                banner_text = "Measured pass"
                commentary = "Possession is recycled with a deliberate receiver-led pass."

            secondary_player_id = next_holder_id
        elif holder_id != next_holder_id:
            event_type = "turnover"
            banner_text = "Turnover"
            commentary = "The defending side forces a turnover and breaks the phase."

    event: dict[str, Any] = {
        "id": f"full-session-live-play-{seq}",
        "type": event_type,
        "sequence": 20 + int(minute),
        "minute": int(minute),
        "clockLabel": f"{int(minute)}'",
        "timeSeconds": round(minute * 60.0, 2),
        "teamId": team_id,
        "teamName": team_name,
        "primaryPlayerId": holder_id,
        "homeScore": home_score,
        "awayScore": away_score,
        "bannerText": banner_text,
        "commentary": commentary,
    }

    if secondary_player_id:
        event["secondaryPlayerId"] = secondary_player_id

    return event


def _home_player(
    index: int, *, minute: float, holder_id: str, ball_x: float, ball_z: float, attacking_home: bool
) -> dict[str, Any]:
    drift = minute / FULLTIME_MINUTE
    wave = ((int(minute) + index) % 5) - 2
    base_x = [8.0, 22.0, 24.0, 24.0, 22.0, 44.0, 48.0, 46.0, 67.0, 77.0, 85.0][index - 1]
    base_z = [34.0, 10.0, 24.0, 44.0, 58.0, 14.0, 34.0, 54.0, 16.0, 34.0, 52.0][index - 1]
    role = "GK" if index == 1 else "DF" if index <= 5 else "MF" if index <= 8 else "FW"
    line = "goalkeeper" if index == 1 else "defense" if index <= 5 else "midfield" if index <= 8 else "attack"
    has_possession = holder_id == f"home-{index}"
    next_holder_id = _next_holder_for_minute(minute)
    transition_phase = _holder_window_progress(minute)
    is_receiver = (
        not has_possession
        and transition_phase >= 0.58
        and next_holder_id == f"home-{index}"
        and next_holder_id.startswith("home")
    )
    box_defense = not attacking_home and ball_x <= 22.0
    box_support = attacking_home and ball_x >= 76.0
    lane_sign = _lane_sign(index, base_z)
    ball_proximity = abs(base_x - ball_x) + (abs(base_z - ball_z) * 0.6)
    primary_support = (
        not has_possession
        and not is_receiver
        and attacking_home
        and role != "GK"
        and ball_proximity < (12.5 if role == "FW" else 14.0 if role == "MF" else 9.25)
    )
    secondary_support = (
        not has_possession
        and not is_receiver
        and attacking_home
        and role != "GK"
        and not primary_support
        and ball_proximity < (18.0 if role == "FW" else 16.0 if role == "MF" else 11.5)
    )
    primary_press = not attacking_home and role != "GK" and ball_proximity < (9.5 if role != "FW" else 8.0)
    secondary_press = not attacking_home and role != "GK" and not primary_press and ball_proximity < 14.0
    box_runner = box_support and role == "FW" and index == 9
    box_width = box_support and role == "FW" and index == 11
    box_cutback = box_support and role == "MF" and index == 8
    box_marker = box_defense and role == "DF" and index in (3, 4)
    box_cover = box_defense and role == "MF" and index == 7
    role_pull = 0.04 if role == "GK" else 0.12 if role == "DF" else 0.22 if role == "MF" else 0.28
    team_compaction = max(0.0, ball_x - 52.5) * role_pull if attacking_home else min(0.0, ball_x - 52.5) * 0.08
    x = base_x + team_compaction + (wave * 0.08) + (drift * 0.04)
    z = 34.0 + (base_z - 34.0) * (0.88 if attacking_home else 0.96)
    speed_ratio = 0.0
    animation_state = "idle"
    state = "holding"
    if role == "GK":
        x = _clamp_pitch_x(5.8 + max(0.0, ball_x - 18.0) * 0.028)
        z = _clamp_pitch_z(34.0 + (ball_z - 34.0) * 0.18)
        lateral_delta = abs(ball_z - z)
        speed_ratio = 0.22 if lateral_delta > 4.5 else 0.14 if lateral_delta > 2.0 else 0.04
        animation_state = "jog" if speed_ratio > 0.01 else "idle"
        state = "set-position"
    elif has_possession:
        x = ball_x - 0.08
        z = ball_z
        speed_ratio = 0.88 if ball_x >= 74.0 else 0.74
        animation_state = "sprint" if ball_x >= 74.0 else "run"
        state = "carrying"
    elif is_receiver:
        x = ball_x + (3.0 if role == "FW" else 2.35 if role == "MF" else 1.65)
        z = _clamp_pitch_z(ball_z + lane_sign * (2.1 if role == "FW" else 1.45 if role == "MF" else 0.95))
        speed_ratio = 0.72 if role != "DF" else 0.5
        animation_state = "run"
        state = "receiving"
    elif box_marker:
        x = max(base_x, ball_x - 6.2)
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.82)
        speed_ratio = 0.34
        animation_state = "mark"
        state = "marking"
    elif box_cover:
        x = base_x + (ball_x - base_x) * 0.42
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.58)
        speed_ratio = 0.22
        animation_state = "jog"
        state = "covering"
    elif box_runner:
        x = base_x + (ball_x - base_x) * 0.9
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.76 - 0.6)
        speed_ratio = 0.52
        animation_state = "run"
        state = "support"
    elif box_width:
        x = base_x + (ball_x - base_x) * 0.78
        z = _clamp_pitch_z(base_z + lane_sign * 2.3)
        speed_ratio = 0.32
        animation_state = "jog"
        state = "width"
    elif box_cutback:
        x = base_x + (ball_x - base_x) * 0.62
        z = _clamp_pitch_z(base_z + lane_sign * 1.15)
        speed_ratio = 0.24
        animation_state = "jog"
        state = "supporting"
    elif primary_support:
        x = base_x + (ball_x - base_x) * (0.82 if role == "FW" else 0.74 if role == "MF" else 0.58)
        z = _clamp_pitch_z(
            base_z + (ball_z - base_z) * 0.76 + lane_sign * (2.2 if role == "FW" else 1.7 if role == "MF" else 1.1)
        )
        speed_ratio = 0.46 if role == "FW" else 0.34 if role == "MF" else 0.22
        animation_state = "run"
        state = "support"
    elif secondary_support:
        x = base_x + (ball_x - base_x) * (0.56 if role == "FW" else 0.44 if role == "MF" else 0.28)
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.5 + lane_sign * (1.5 if role != "DF" else 0.9))
        speed_ratio = 0.16 if role != "DF" else 0.08
        animation_state = "jog"
        state = "supporting"
    elif primary_press:
        x = base_x + (ball_x - base_x) * (0.74 if role == "MF" else 0.66)
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.68 - lane_sign * 0.9)
        speed_ratio = 0.4 if role == "MF" else 0.28
        animation_state = "press"
        state = "pressing"
    elif secondary_press:
        x = base_x + (ball_x - base_x) * 0.36
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.34 - lane_sign * 0.55)
        speed_ratio = 0.1
        animation_state = "jog"
        state = "covering"
    else:
        speed_ratio = 0.0
        animation_state = "idle"
        state = "shape"

    if minute >= FULLTIME_MINUTE:
        speed_ratio = 0.0
        animation_state = "idle"
        state = "finished"

    x = _clamp_pitch_x(x)
    z = _clamp_pitch_z(z)
    velocity_x = 0.0
    velocity_z = 0.0
    if minute < FULLTIME_MINUTE and speed_ratio > 0.001:
        if role == "GK":
            velocity_x = 0.08
            velocity_z = round((ball_z - z) * 0.025, 3)
        elif has_possession:
            velocity_x = 1.45 if ball_x >= 74.0 else 1.05
            velocity_z = round((ball_z - z) * 0.05, 3)
        elif is_receiver:
            velocity_x = 1.2 if role == "FW" else 0.96
            velocity_z = round((ball_z - z) * 0.08, 3)
        elif primary_support:
            velocity_x = 0.78 if role == "FW" else 0.58 if role == "MF" else 0.32
            velocity_z = round((ball_z - z) * 0.09, 3)
        elif secondary_support:
            velocity_x = 0.38 if role != "DF" else 0.2
            velocity_z = round((ball_z - z) * 0.06, 3)
        elif primary_press:
            velocity_x = 0.14
            velocity_z = round((ball_z - z) * 0.11, 3)
        elif secondary_press:
            velocity_x = 0.08
            velocity_z = round((ball_z - z) * 0.05, 3)
    facing_x, facing_z = _resolve_facing(velocity_x, velocity_z, 1.0)
    return {
        "entityId": f"home-{index}",
        "playerId": f"home-{index}",
        "teamId": "home-team",
        "teamSide": "home",
        "label": str(index),
        "role": role,
        "line": line,
        "shirtNumber": index,
        "active": True,
        "highlighted": has_possession or is_receiver or primary_support,
        "hasPossession": has_possession,
        "animationState": animation_state,
        "speedRatio": speed_ratio,
        "state": state,
        "x": round(x, 3),
        "y": 0.0,
        "z": round(z, 3),
        "velocityX": 0.0 if minute >= FULLTIME_MINUTE else round(velocity_x, 3),
        "velocityY": 0.0,
        "velocityZ": 0.0 if minute >= FULLTIME_MINUTE else round(velocity_z, 3),
        "facingX": facing_x,
        "facingZ": facing_z,
    }


def _away_player(
    index: int, *, minute: float, holder_id: str, ball_x: float, ball_z: float, attacking_home: bool
) -> dict[str, Any]:
    drift = minute / FULLTIME_MINUTE
    wave = (((int(minute) * 2) + index) % 5) - 2
    base_x = [97.0, 83.0, 81.0, 81.0, 83.0, 60.0, 56.0, 58.0, 39.0, 28.0, 20.0][index - 1]
    base_z = [34.0, 10.0, 24.0, 44.0, 58.0, 14.0, 34.0, 54.0, 16.0, 34.0, 52.0][index - 1]
    role = "GK" if index == 1 else "DF" if index <= 5 else "MF" if index <= 8 else "FW"
    line = "goalkeeper" if index == 1 else "defense" if index <= 5 else "midfield" if index <= 8 else "attack"
    attacking = not attacking_home
    has_possession = holder_id == f"away-{index}"
    next_holder_id = _next_holder_for_minute(minute)
    transition_phase = _holder_window_progress(minute)
    is_receiver = (
        not has_possession
        and transition_phase >= 0.58
        and next_holder_id == f"away-{index}"
        and next_holder_id.startswith("away")
    )
    box_defense = attacking_home and ball_x >= 83.0
    box_support = attacking and ball_x <= 29.0
    lane_sign = _lane_sign(index, base_z)
    ball_proximity = abs(base_x - ball_x) + (abs(base_z - ball_z) * 0.6)
    primary_support = (
        not has_possession
        and not is_receiver
        and attacking
        and role != "GK"
        and ball_proximity < (12.5 if role == "FW" else 14.0 if role == "MF" else 9.25)
    )
    secondary_support = (
        not has_possession
        and not is_receiver
        and attacking
        and role != "GK"
        and not primary_support
        and ball_proximity < (18.0 if role == "FW" else 16.0 if role == "MF" else 11.5)
    )
    primary_press = not attacking and role != "GK" and ball_proximity < (9.5 if role != "FW" else 8.0)
    secondary_press = not attacking and role != "GK" and not primary_press and ball_proximity < 14.0
    box_runner = box_support and role == "FW" and index == 9
    box_width = box_support and role == "FW" and index == 11
    box_cutback = box_support and role == "MF" and index == 8
    box_marker = box_defense and role == "DF" and index in (3, 4)
    box_cover = box_defense and role == "MF" and index == 7
    role_pull = 0.04 if role == "GK" else 0.12 if role == "DF" else 0.22 if role == "MF" else 0.28
    team_compaction = min(0.0, ball_x - 52.5) * role_pull if attacking else max(0.0, ball_x - 52.5) * 0.08
    x = base_x + team_compaction - (wave * 0.08) - (drift * 0.04)
    z = 34.0 + (base_z - 34.0) * (0.88 if attacking else 0.96)
    speed_ratio = 0.0
    animation_state = "idle"
    state = "holding"
    if role == "GK":
        x = _clamp_pitch_x(99.2 - max(0.0, 87.0 - ball_x) * 0.028)
        z = _clamp_pitch_z(34.0 + (ball_z - 34.0) * 0.18)
        lateral_delta = abs(ball_z - z)
        speed_ratio = 0.22 if lateral_delta > 4.5 else 0.14 if lateral_delta > 2.0 else 0.04
        animation_state = "jog" if speed_ratio > 0.01 else "idle"
        state = "set-position"
    elif has_possession:
        x = ball_x + 0.08
        z = ball_z
        speed_ratio = 0.88 if ball_x <= 31.0 else 0.74
        animation_state = "sprint" if ball_x <= 31.0 else "run"
        state = "carrying"
    elif is_receiver:
        x = ball_x - (3.0 if role == "FW" else 2.35 if role == "MF" else 1.65)
        z = _clamp_pitch_z(ball_z + lane_sign * (2.1 if role == "FW" else 1.45 if role == "MF" else 0.95))
        speed_ratio = 0.72 if role != "DF" else 0.5
        animation_state = "run"
        state = "receiving"
    elif box_marker:
        x = min(base_x, ball_x + 6.2)
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.82)
        speed_ratio = 0.34
        animation_state = "mark"
        state = "marking"
    elif box_cover:
        x = base_x + (ball_x - base_x) * 0.42
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.58)
        speed_ratio = 0.22
        animation_state = "jog"
        state = "covering"
    elif box_runner:
        x = base_x + (ball_x - base_x) * 0.9
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.76 - 0.6)
        speed_ratio = 0.52
        animation_state = "run"
        state = "support"
    elif box_width:
        x = base_x + (ball_x - base_x) * 0.78
        z = _clamp_pitch_z(base_z + lane_sign * 2.3)
        speed_ratio = 0.32
        animation_state = "jog"
        state = "width"
    elif box_cutback:
        x = base_x + (ball_x - base_x) * 0.62
        z = _clamp_pitch_z(base_z + lane_sign * 1.15)
        speed_ratio = 0.24
        animation_state = "jog"
        state = "supporting"
    elif primary_support:
        x = base_x + (ball_x - base_x) * (0.82 if role == "FW" else 0.74 if role == "MF" else 0.58)
        z = _clamp_pitch_z(
            base_z + (ball_z - base_z) * 0.76 + lane_sign * (2.2 if role == "FW" else 1.7 if role == "MF" else 1.1)
        )
        speed_ratio = 0.46 if role == "FW" else 0.34 if role == "MF" else 0.22
        animation_state = "run"
        state = "support"
    elif secondary_support:
        x = base_x + (ball_x - base_x) * (0.56 if role == "FW" else 0.44 if role == "MF" else 0.28)
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.5 + lane_sign * (1.5 if role != "DF" else 0.9))
        speed_ratio = 0.16 if role != "DF" else 0.08
        animation_state = "jog"
        state = "supporting"
    elif primary_press:
        x = base_x + (ball_x - base_x) * (0.74 if role == "MF" else 0.66)
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.68 - lane_sign * 0.9)
        speed_ratio = 0.4 if role == "MF" else 0.28
        animation_state = "press"
        state = "pressing"
    elif secondary_press:
        x = base_x + (ball_x - base_x) * 0.36
        z = _clamp_pitch_z(base_z + (ball_z - base_z) * 0.34 - lane_sign * 0.55)
        speed_ratio = 0.1
        animation_state = "jog"
        state = "covering"
    else:
        speed_ratio = 0.0
        animation_state = "idle"
        state = "shape"

    if minute >= FULLTIME_MINUTE:
        speed_ratio = 0.0
        animation_state = "idle"
        state = "finished"

    x = _clamp_pitch_x(x)
    z = _clamp_pitch_z(z)
    velocity_x = 0.0
    velocity_z = 0.0
    if minute < FULLTIME_MINUTE and speed_ratio > 0.001:
        if role == "GK":
            velocity_x = -0.08
            velocity_z = round((ball_z - z) * 0.025, 3)
        elif has_possession:
            velocity_x = -1.45 if ball_x <= 31.0 else -1.05
            velocity_z = round((ball_z - z) * 0.05, 3)
        elif is_receiver:
            velocity_x = -1.2 if role == "FW" else -0.96
            velocity_z = round((ball_z - z) * 0.08, 3)
        elif primary_support:
            velocity_x = -0.78 if role == "FW" else -0.58 if role == "MF" else -0.32
            velocity_z = round((ball_z - z) * 0.09, 3)
        elif secondary_support:
            velocity_x = -0.38 if role != "DF" else -0.2
            velocity_z = round((ball_z - z) * 0.06, 3)
        elif primary_press:
            velocity_x = -0.14
            velocity_z = round((ball_z - z) * 0.11, 3)
        elif secondary_press:
            velocity_x = -0.08
            velocity_z = round((ball_z - z) * 0.05, 3)
    facing_x, facing_z = _resolve_facing(velocity_x, velocity_z, -1.0)
    return {
        "entityId": f"away-{index}",
        "playerId": f"away-{index}",
        "teamId": "away-team",
        "teamSide": "away",
        "label": str(index),
        "role": role,
        "line": line,
        "shirtNumber": index,
        "active": True,
        "highlighted": has_possession or is_receiver or primary_support,
        "hasPossession": has_possession,
        "animationState": animation_state,
        "speedRatio": speed_ratio,
        "state": state,
        "x": round(x, 3),
        "y": 0.0,
        "z": round(z, 3),
        "velocityX": 0.0 if minute >= FULLTIME_MINUTE else round(velocity_x, 3),
        "velocityY": 0.0,
        "velocityZ": 0.0 if minute >= FULLTIME_MINUTE else round(velocity_z, 3),
        "facingX": facing_x,
        "facingZ": facing_z,
    }


def _events_for_minute(
    seq: int, minute: float, holder_id: str, home_score: int, away_score: int
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [
        {
            "id": "full-session-kickoff",
            "type": "kickoff",
            "sequence": 10,
            "minute": 0,
            "clockLabel": "0'",
            "timeSeconds": 0.0,
            "homeScore": 0,
            "awayScore": 0,
            "bannerText": "Kickoff",
            "commentary": "Full-session validation kickoff.",
        }
    ]

    if minute >= 28.0:
        events.append(
            {
                "id": "full-session-home-goal",
                "type": "goal",
                "sequence": 30,
                "minute": 28,
                "clockLabel": "28'",
                "timeSeconds": 1680.0,
                "teamId": "home-team",
                "teamName": "Full Session Home",
                "primaryPlayerId": "home-10",
                "homeScore": 1,
                "awayScore": 0,
                "bannerText": "Home breakthrough",
                "commentary": "The home side scores first.",
            }
        )

    if minute >= 45.0 and minute < 46.0:
        events.append(
            {
                "id": "full-session-halftime",
                "type": "halftime",
                "sequence": 50,
                "minute": 45,
                "clockLabel": "45'",
                "timeSeconds": 2700.0,
                "homeScore": 1,
                "awayScore": 0,
                "bannerText": "Half time",
                "commentary": "Players head into the break.",
            }
        )

    if minute >= 63.0:
        events.append(
            {
                "id": "full-session-away-goal",
                "type": "goal",
                "sequence": 70,
                "minute": 63,
                "clockLabel": "63'",
                "timeSeconds": 3780.0,
                "teamId": "away-team",
                "teamName": "Full Session Away",
                "primaryPlayerId": "away-9",
                "homeScore": 1,
                "awayScore": 1,
                "bannerText": "Away equalizer",
                "commentary": "The away side levels the match.",
            }
        )

    if minute >= 84.0:
        events.append(
            {
                "id": "full-session-home-winner",
                "type": "goal",
                "sequence": 90,
                "minute": 84,
                "clockLabel": "84'",
                "timeSeconds": 5040.0,
                "teamId": "home-team",
                "teamName": "Full Session Home",
                "primaryPlayerId": "home-11",
                "homeScore": 2,
                "awayScore": 1,
                "bannerText": "Late winner",
                "commentary": "A late finish restores the lead.",
            }
        )

    if minute >= FULLTIME_MINUTE:
        events.append(
            {
                "id": "full-session-fulltime",
                "type": "fulltime",
                "sequence": 150,
                "minute": 90,
                "clockLabel": "90'",
                "timeSeconds": 5400.0,
                "homeScore": home_score,
                "awayScore": away_score,
                "bannerText": "Full time",
                "commentary": "Full-session validation reached full time.",
            }
        )
    else:
        events.append(_live_play_event_for_sequence(seq, minute, holder_id, home_score, away_score))

    return events


def build_payload() -> dict[str, Any]:
    seq = STATE.next_sequence
    minute = _minute_for_sequence(seq)
    phase = _phase_for_sequence(seq)
    home_score, away_score = _score_for_minute(minute)
    holder_id = "" if minute >= FULLTIME_MINUTE else _holder_for_minute(minute)
    ball_x, ball_z, attacking_home = _ball_state_for_minute(minute, holder_id)
    camera_preset = _camera_preset_for_state(minute, ball_x)
    players = [
        *[
            _home_player(
                index, minute=minute, holder_id=holder_id, ball_x=ball_x, ball_z=ball_z, attacking_home=attacking_home
            )
            for index in range(1, 12)
        ],
        *[
            _away_player(
                index, minute=minute, holder_id=holder_id, ball_x=ball_x, ball_z=ball_z, attacking_home=attacking_home
            )
            for index in range(1, 12)
        ],
    ]
    ball_owner_id = holder_id

    events = _events_for_minute(seq, minute, holder_id, home_score, away_score)
    active_event_id = events[-1]["id"] if events else ""

    payload = {
        "matchId": MATCH_ID,
        "source": "full-session-mock",
        "status": "completed" if minute >= FULLTIME_MINUTE else "live",
        "isLive": minute < FULLTIME_MINUTE,
        "frameId": f"full-session-frame-{seq}",
        "clockMinute": minute,
        "phase": phase,
        "homeScore": home_score,
        "awayScore": away_score,
        "possessionSide": "home" if attacking_home else "away",
        "activeEventId": active_event_id,
        "cameraPreset": camera_preset,
        "pitchLengthMeters": 105.0,
        "pitchWidthMeters": 68.0,
        "players": players,
        "ballPosition": {
            "entityId": "ball",
            "playerId": ball_owner_id,
            "label": "Ball",
            "hasPossession": bool(ball_owner_id),
            "state": "settled" if minute >= FULLTIME_MINUTE else ("controlled" if ball_owner_id else "traveling"),
            "x": round(max(4.0, min(101.0, ball_x)), 3),
            "y": 0.0 if minute >= FULLTIME_MINUTE else (0.18 if ball_owner_id else 0.72),
            "z": round(max(4.0, min(64.0, ball_z)), 3),
            "velocityX": 0.0 if minute >= FULLTIME_MINUTE else (1.35 if attacking_home else -1.35),
            "velocityY": 0.0 if minute >= FULLTIME_MINUTE else (0.1 if not ball_owner_id else 0.0),
            "velocityZ": (
                0.0
                if minute >= FULLTIME_MINUTE
                else round(math.sin(_holder_window_progress(minute) * math.pi) * 0.42, 3)
            ),
            "isBall": True,
        },
        "events": events,
    }
    STATE.record_payload(payload)
    return payload


def _require_authorization(header: str | None) -> None:
    if header != f"Bearer {ACCESS_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


@app.post("/admin/reset")
async def reset_session() -> JSONResponse:
    STATE.reset()
    LOGGER.info("full-session scenario reset")
    return JSONResponse(
        {
            "match_id": MATCH_ID,
            "access_token": ACCESS_TOKEN,
            "refresh_token": REFRESH_TOKEN,
        }
    )


@app.get("/admin/session-summary")
async def get_session_summary() -> JSONResponse:
    return JSONResponse(STATE.build_summary())


async def safe_send(websocket: WebSocket, payload: dict[str, Any]) -> bool:
    if websocket.client_state != WebSocketState.CONNECTED or websocket.application_state != WebSocketState.CONNECTED:
        return False

    try:
        await asyncio.wait_for(
            websocket.send_json(payload),
            timeout=SEND_TIMEOUT_SECONDS,
        )
        return True
    except Exception as exc:  # pragma: no cover - harness only
        LOGGER.warning("[GTEX mock server] send failed, continuing simulation: %s", exc)
        return False


@app.get("/match/{match_id}/live")
async def get_live_match(match_id: str, authorization: str | None = Header(default=None)) -> JSONResponse:
    if match_id != MATCH_ID:
        raise HTTPException(status_code=404, detail="not_found")
    _require_authorization(authorization)
    STATE.http_requests += 1
    payload = build_payload()
    LOGGER.info(
        "http live request match=%s frame=%s minute=%.2f score=%s-%s",
        match_id,
        payload["frameId"],
        payload["clockMinute"],
        payload["homeScore"],
        payload["awayScore"],
    )
    return JSONResponse(payload)


@app.post("/match/{match_id}/unity-access/refresh")
async def refresh_live_access(match_id: str) -> JSONResponse:
    if match_id != MATCH_ID:
        raise HTTPException(status_code=404, detail="not_found")
    LOGGER.info("full-session refresh request match=%s", match_id)
    return JSONResponse(
        {
            "match_id": MATCH_ID,
            "access_token": ACCESS_TOKEN,
            "refresh_token": REFRESH_TOKEN,
            "spectator_session_id": "full-session-validation",
            "token_type": "bearer",
            "expires_in": 300,
            "refresh_expires_in": 3600,
            "live_path": f"/match/{match_id}/live",
            "websocket_path": f"/api/v1/ws/match/{match_id}?format=unity",
            "refresh_path": f"/match/{match_id}/unity-access/refresh",
        }
    )


@app.websocket("/api/v1/ws/match/{match_id}")
async def websocket_match_stream(websocket: WebSocket, match_id: str) -> None:
    if match_id != MATCH_ID:
        await websocket.close(code=4404, reason="not_found")
        return

    if websocket.headers.get("authorization") != f"Bearer {ACCESS_TOKEN}":
        await websocket.close(code=4401, reason="unauthorized")
        return

    STATE.websocket_connections += 1
    await websocket.accept()
    LOGGER.info(
        "full-session websocket connect #%s match=%s format=%s",
        STATE.websocket_connections,
        match_id,
        websocket.query_params.get("format"),
    )

    try:
        last_send_ok_at = asyncio.get_running_loop().time()
        last_payload: dict[str, Any] | None = None
        while True:
            payload = build_payload()
            last_payload = payload
            send_ok = await safe_send(websocket, payload)
            if send_ok:
                last_send_ok_at = asyncio.get_running_loop().time()
            else:
                if (
                    websocket.client_state != WebSocketState.CONNECTED
                    or websocket.application_state != WebSocketState.CONNECTED
                ):
                    LOGGER.info(
                        "[GTEX mock server] websocket disconnected; ending simulation stream match=%s",
                        match_id,
                    )
                    break

                idle_for = asyncio.get_running_loop().time() - last_send_ok_at
                if idle_for > CLIENT_IDLE_GRACE_SECONDS:
                    LOGGER.warning(
                        "[GTEX mock server] client idle too long; ending socket but preserving match state match=%s",
                        match_id,
                    )
                    break

            if payload["phase"] == "fulltime":
                LOGGER.info(
                    "full-session websocket final frame match=%s minute=%.2f score=%s-%s",
                    match_id,
                    payload["clockMinute"],
                    payload["homeScore"],
                    payload["awayScore"],
                )
                await asyncio.sleep(WEBSOCKET_FRAME_INTERVAL_SECONDS)
                await websocket.close(code=1000, reason="fulltime")
                return

            await asyncio.sleep(WEBSOCKET_FRAME_INTERVAL_SECONDS)
        if last_payload is not None and last_payload.get("phase") != "fulltime":
            await safe_send(
                websocket,
                {
                    **last_payload,
                    "phase": "fulltime",
                    "clockMinute": FULLTIME_MINUTE,
                },
            )
    except Exception as exc:  # pragma: no cover - harness only
        LOGGER.info("full-session websocket closed match=%s reason=%s", match_id, exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
        ws_ping_interval=None,
        ws_ping_timeout=None,
    )


if __name__ == "__main__":
    main()
