from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, WebSocket
from fastapi.responses import JSONResponse

ACCESS_TOKEN = "live-full-session-access-token"  # pragma: allowlist secret
REFRESH_TOKEN = "live-full-session-refresh-token"  # pragma: allowlist secret
MATCH_ID = "live-full-session-test"
LOGGER = logging.getLogger("gtex_live_full_session_mock_server")

FIRST_HALF_MINUTE_LIMIT = 45.0
SECOND_HALF_START_MINUTE = 46.0
FULLTIME_MINUTE = 90.0
FRAME_MINUTES = (0.0, 12.0, 24.0, 36.0, 45.0, 48.0, 60.0, 72.0, 84.0, 90.0)
FULLTIME_SEQUENCE = len(FRAME_MINUTES) - 1


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
    return FRAME_MINUTES[normalized]


def _phase_for_sequence(seq: int) -> str:
    minute = _minute_for_sequence(seq)
    if minute >= FULLTIME_MINUTE:
        return "fulltime"
    if minute >= SECOND_HALF_START_MINUTE:
        return "second_half"
    if minute >= FIRST_HALF_MINUTE_LIMIT:
        return "halftime"
    return "first_half"


def _camera_preset_for_minute(minute: float) -> str:
    if minute >= FULLTIME_MINUTE:
        return "broadcast"
    if minute >= 84.0:
        return "box_zoom"
    if minute >= 63.0:
        return "broadcast"
    if minute >= 28.0:
        return "attack_push"
    return "broadcast"


def _holder_for_sequence(seq: int) -> str:
    cycle = (
        "home-8",
        "home-10",
        "home-9",
        "away-6",
        "away-8",
        "home-7",
        "home-11",
        "away-4",
    )
    return cycle[seq % len(cycle)]


def _home_player(index: int, *, minute: float, holder_id: str) -> dict[str, Any]:
    drift = minute / FULLTIME_MINUTE
    wave = ((int(minute) + index) % 5) - 2
    base_x = [8.0, 22.0, 24.0, 24.0, 22.0, 44.0, 48.0, 46.0, 67.0, 77.0, 85.0][index - 1]
    base_z = [34.0, 10.0, 24.0, 44.0, 58.0, 14.0, 34.0, 54.0, 16.0, 34.0, 52.0][index - 1]
    role = "GK" if index == 1 else "DF" if index <= 5 else "MF" if index <= 8 else "FW"
    line = "goalkeeper" if index == 1 else "defense" if index <= 5 else "midfield" if index <= 8 else "attack"
    attacking = minute < 45.0 or minute >= 75.0
    has_possession = holder_id == f"home-{index}"
    speed_ratio = (
        0.0 if minute >= FULLTIME_MINUTE else (0.82 if index in {9, 10, 11} else 0.57 if index in {6, 7, 8} else 0.36)
    )
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
        "highlighted": has_possession or index in {9, 10},
        "hasPossession": has_possession,
        "animationState": (
            "idle"
            if minute >= FULLTIME_MINUTE
            else ("sprint" if index in {9, 10, 11} and attacking else "run" if index in {6, 7, 8} else "jog")
        ),
        "speedRatio": speed_ratio,
        "state": (
            "finished"
            if minute >= FULLTIME_MINUTE
            else ("attacking" if attacking and index in {8, 9, 10, 11} else "moving")
        ),
        "x": round(base_x + (drift * 11.0) + (wave * 0.45), 3),
        "y": 0.0,
        "z": round(base_z + (wave * 0.8), 3),
        "velocityX": 0.0 if minute >= FULLTIME_MINUTE else round(0.8 + (0.06 * index), 3),
        "velocityY": 0.0,
        "velocityZ": 0.0 if minute >= FULLTIME_MINUTE else round(0.05 * wave, 3),
        "facingX": 1.0,
        "facingZ": 0.14 if index % 2 == 0 else -0.14,
    }


def _away_player(index: int, *, minute: float, holder_id: str) -> dict[str, Any]:
    drift = minute / FULLTIME_MINUTE
    wave = (((int(minute) * 2) + index) % 5) - 2
    base_x = [97.0, 83.0, 81.0, 81.0, 83.0, 60.0, 56.0, 58.0, 39.0, 28.0, 20.0][index - 1]
    base_z = [34.0, 10.0, 24.0, 44.0, 58.0, 14.0, 34.0, 54.0, 16.0, 34.0, 52.0][index - 1]
    role = "GK" if index == 1 else "DF" if index <= 5 else "MF" if index <= 8 else "FW"
    line = "goalkeeper" if index == 1 else "defense" if index <= 5 else "midfield" if index <= 8 else "attack"
    pressing = 45.0 <= minute < 84.0
    has_possession = holder_id == f"away-{index}"
    speed_ratio = 0.0 if minute >= FULLTIME_MINUTE else (0.63 if index in {6, 7, 8, 9} else 0.34)
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
        "highlighted": has_possession or index in {8, 9},
        "hasPossession": has_possession,
        "animationState": (
            "idle" if minute >= FULLTIME_MINUTE else ("press" if pressing and index in {6, 7, 8, 9} else "jog")
        ),
        "speedRatio": speed_ratio,
        "state": (
            "finished"
            if minute >= FULLTIME_MINUTE
            else ("pressing" if pressing and index in {6, 7, 8, 9} else "defending")
        ),
        "x": round(base_x - (drift * 11.0) - (wave * 0.35), 3),
        "y": 0.0,
        "z": round(base_z + (wave * 0.7), 3),
        "velocityX": 0.0 if minute >= FULLTIME_MINUTE else round(-0.78 - (0.05 * index), 3),
        "velocityY": 0.0,
        "velocityZ": 0.0 if minute >= FULLTIME_MINUTE else round(0.05 * wave, 3),
        "facingX": -1.0,
        "facingZ": -0.12 if index % 2 == 0 else 0.12,
    }


def _events_for_minute(minute: float, holder_id: str, home_score: int, away_score: int) -> list[dict[str, Any]]:
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
        events.append(
            {
                "id": "full-session-live-play",
                "type": "attack",
                "sequence": 20 + int(minute),
                "minute": int(minute),
                "clockLabel": f"{int(minute)}'",
                "timeSeconds": round(minute * 60.0, 2),
                "teamId": "home-team" if holder_id.startswith("home") else "away-team",
                "teamName": "Full Session Home" if holder_id.startswith("home") else "Full Session Away",
                "primaryPlayerId": holder_id,
                "homeScore": home_score,
                "awayScore": away_score,
                "bannerText": "Live passage",
                "commentary": "Controlled live playback is driving motion, score, and camera changes.",
            }
        )

    return events


def build_payload() -> dict[str, Any]:
    seq = STATE.next_sequence
    minute = _minute_for_sequence(seq)
    phase = _phase_for_sequence(seq)
    home_score, away_score = _score_for_minute(minute)
    holder_id = "" if minute >= FULLTIME_MINUTE else _holder_for_sequence(seq)
    camera_preset = _camera_preset_for_minute(minute)
    players = [
        *[_home_player(index, minute=minute, holder_id=holder_id) for index in range(1, 12)],
        *[_away_player(index, minute=minute, holder_id=holder_id) for index in range(1, 12)],
    ]
    attacking_home = holder_id.startswith("home")
    ball_x = (
        52.5
        if minute >= FULLTIME_MINUTE
        else 50.0 + ((minute / 90.0) * 18.0 if attacking_home else -(minute / 90.0) * 14.0)
    )
    ball_z = 34.0 if minute >= FULLTIME_MINUTE else 34.0 + ((((seq % 5) - 2) * 2.2))
    ball_owner_id = holder_id

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
        "activeEventId": "full-session-fulltime" if minute >= FULLTIME_MINUTE else "full-session-live-play",
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
            "velocityX": 0.0 if minute >= FULLTIME_MINUTE else (2.2 if attacking_home else -1.95),
            "velocityY": 0.0 if minute >= FULLTIME_MINUTE else (0.1 if not ball_owner_id else 0.0),
            "velocityZ": 0.0 if minute >= FULLTIME_MINUTE else (0.3 if seq % 2 == 0 else -0.24),
            "isBall": True,
        },
        "events": _events_for_minute(minute, holder_id, home_score, away_score),
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
        while True:
            payload = build_payload()
            await websocket.send_json(payload)

            if payload["phase"] == "fulltime":
                LOGGER.info(
                    "full-session websocket final frame match=%s minute=%.2f score=%s-%s",
                    match_id,
                    payload["clockMinute"],
                    payload["homeScore"],
                    payload["awayScore"],
                )
                await asyncio.sleep(1.0)
                await websocket.close(code=1000, reason="fulltime")
                return

            await asyncio.sleep(1.0)
    except Exception as exc:  # pragma: no cover - harness only
        LOGGER.info("full-session websocket closed match=%s reason=%s", match_id, exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
