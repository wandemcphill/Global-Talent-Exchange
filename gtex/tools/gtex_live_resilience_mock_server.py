from __future__ import annotations

import argparse
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, WebSocket
from fastapi.responses import JSONResponse

INITIAL_ACCESS_TOKEN = "live-resilience-access-token-0"
REFRESHED_ACCESS_TOKEN = "live-resilience-access-token-1"
REFRESH_TOKEN = "live-resilience-refresh-token"
RESILIENCE_MATCH_ID = "live-resilience-test"
TERMINAL_MATCH_ID = "live-terminal-test"
LOGGER = logging.getLogger("gtex_live_resilience_mock_server")


@dataclass
class ScenarioState:
    started_at: float
    refresh_calls: int = 0
    websocket_connections: int = 0

    def reset(self) -> None:
        self.started_at = time.monotonic()
        self.refresh_calls = 0
        self.websocket_connections = 0

    @property
    def current_access_token(self) -> str:
        return REFRESHED_ACCESS_TOKEN if self.refresh_calls > 0 else INITIAL_ACCESS_TOKEN

    @property
    def elapsed_sequence(self) -> int:
        return max(0, int(time.monotonic() - self.started_at))


STATE = ScenarioState(started_at=time.monotonic())
app = FastAPI()


def _home_player(index: int, *, seq: int, holder_id: str) -> dict[str, Any]:
    base_x = [8.0, 22.0, 24.0, 24.0, 22.0, 44.0, 48.0, 46.0, 67.0, 77.0, 85.0][index - 1]
    base_z = [34.0, 10.0, 24.0, 44.0, 58.0, 14.0, 34.0, 54.0, 16.0, 34.0, 52.0][index - 1]
    wave = ((seq + index) % 5) - 2
    role = "GK" if index == 1 else "DF" if index <= 5 else "MF" if index <= 8 else "FW"
    line = "goalkeeper" if index == 1 else "defense" if index <= 5 else "midfield" if index <= 8 else "attack"
    has_possession = holder_id == f"home-{index}"
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
        "animationState": "sprint" if index in {9, 10} else "run" if index in {6, 7, 8} else "jog",
        "speedRatio": 0.82 if index in {9, 10} else 0.58 if index in {6, 7, 8} else 0.34,
        "state": "attacking" if index in {9, 10, 11} else "moving",
        "x": round(base_x + (seq * 1.4) + (wave * 0.45), 3),
        "y": 0.0,
        "z": round(base_z + (wave * 0.85), 3),
        "velocityX": round(1.2 + (0.08 * index), 3),
        "velocityY": 0.0,
        "velocityZ": round(0.06 * wave, 3),
        "facingX": 1.0,
        "facingZ": 0.15 if index % 2 == 0 else -0.15,
    }


def _away_player(index: int, *, seq: int, holder_id: str) -> dict[str, Any]:
    base_x = [97.0, 83.0, 81.0, 81.0, 83.0, 60.0, 56.0, 58.0, 39.0, 28.0, 20.0][index - 1]
    base_z = [34.0, 10.0, 24.0, 44.0, 58.0, 14.0, 34.0, 54.0, 16.0, 34.0, 52.0][index - 1]
    wave = (((seq * 2) + index) % 5) - 2
    role = "GK" if index == 1 else "DF" if index <= 5 else "MF" if index <= 8 else "FW"
    line = "goalkeeper" if index == 1 else "defense" if index <= 5 else "midfield" if index <= 8 else "attack"
    has_possession = holder_id == f"away-{index}"
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
        "animationState": "press" if index in {6, 7, 8, 9} else "jog",
        "speedRatio": 0.61 if index in {6, 7, 8, 9} else 0.33,
        "state": "pressing" if index in {6, 7, 8, 9} else "defending",
        "x": round(base_x - (seq * 1.05) - (wave * 0.35), 3),
        "y": 0.0,
        "z": round(base_z + (wave * 0.7), 3),
        "velocityX": round(-0.92 - (0.05 * index), 3),
        "velocityY": 0.0,
        "velocityZ": round(0.05 * wave, 3),
        "facingX": -1.0,
        "facingZ": -0.12 if index % 2 == 0 else 0.12,
    }


def _require_authorization(header: str | None) -> None:
    expected = f"Bearer {STATE.current_access_token}"
    if header != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def _build_live_payload(match_id: str) -> dict[str, Any]:
    if match_id == TERMINAL_MATCH_ID:
        return {
            "matchId": TERMINAL_MATCH_ID,
            "source": "resilience-mock-terminal",
            "status": "completed",
            "isLive": False,
            "frameId": "terminal-frame-0",
            "clockMinute": 90.0,
            "phase": "fulltime",
            "homeScore": 2,
            "awayScore": 1,
            "possessionSide": "home",
            "activeEventId": "terminal-fulltime",
            "cameraPreset": "broadcast",
            "pitchLengthMeters": 105.0,
            "pitchWidthMeters": 68.0,
            "players": [],
            "ballPosition": {
                "entityId": "ball",
                "playerId": "",
                "label": "Ball",
                "hasPossession": False,
                "state": "settled",
                "x": 52.5,
                "y": 0.0,
                "z": 34.0,
                "velocityX": 0.0,
                "velocityY": 0.0,
                "velocityZ": 0.0,
                "isBall": True,
            },
            "events": [
                {
                    "id": "terminal-fulltime",
                    "type": "fulltime",
                    "sequence": 999,
                    "minute": 90,
                    "clockLabel": "90'",
                    "timeSeconds": 5400.0,
                    "homeScore": 2,
                    "awayScore": 1,
                    "bannerText": "Full time",
                    "commentary": "Terminal match selected for resilience verification.",
                }
            ],
        }

    seq = STATE.elapsed_sequence
    attacking_home = seq % 6 < 4
    holder_id = ["home-8", "home-10", "home-9", "away-6", "away-8", "home-9"][seq % 6]
    players = [
        *[_home_player(index, seq=seq, holder_id=holder_id) for index in range(1, 12)],
        *[_away_player(index, seq=seq, holder_id=holder_id) for index in range(1, 12)],
    ]
    active_event_id = "resilience-save" if not attacking_home and seq % 3 == 0 else "resilience-attack"
    ball_x = 50.0 + (seq * 2.25 if attacking_home else -seq * 1.6)
    ball_z = 34.0 + (((seq % 5) - 2) * 2.1)
    ball_owner_id = holder_id if "save" not in active_event_id else ""
    return {
        "matchId": RESILIENCE_MATCH_ID,
        "source": "resilience-mock",
        "status": "live",
        "isLive": True,
        "frameId": f"resilience-frame-{seq}",
        "clockMinute": round(12.5 + (seq * 0.45), 2),
        "phase": "first_half",
        "homeScore": 2,
        "awayScore": 1,
        "possessionSide": "home" if attacking_home else "away",
        "activeEventId": active_event_id,
        "cameraPreset": "attack_push" if attacking_home and seq % 2 == 0 else "broadcast",
        "pitchLengthMeters": 105.0,
        "pitchWidthMeters": 68.0,
        "players": players,
        "ballPosition": {
            "entityId": "ball",
            "playerId": ball_owner_id,
            "label": "Ball",
            "hasPossession": bool(ball_owner_id),
            "state": "controlled" if ball_owner_id else "traveling",
            "x": round(max(4.0, min(101.0, ball_x)), 3),
            "y": 0.2 if ball_owner_id else 0.8,
            "z": round(max(4.0, min(64.0, ball_z)), 3),
            "velocityX": 2.45 if attacking_home else -2.05,
            "velocityY": 0.12 if not ball_owner_id else 0.0,
            "velocityZ": 0.34 if seq % 2 == 0 else -0.28,
            "isBall": True,
        },
        "events": [
            {
                "id": "resilience-kickoff",
                "type": "kickoff",
                "sequence": 1,
                "minute": 0,
                "clockLabel": "0'",
                "timeSeconds": 0.0,
                "homeScore": 0,
                "awayScore": 0,
                "bannerText": "Kickoff",
                "commentary": "Resilience smoke runtime kickoff.",
            },
            {
                "id": "resilience-attack",
                "type": "attack",
                "sequence": 2 + (seq % 3),
                "minute": 12 + seq,
                "clockLabel": f"{12 + seq}'",
                "timeSeconds": round(seq * 1.0, 2),
                "teamId": "home-team" if attacking_home else "away-team",
                "teamName": "Resilience Home" if attacking_home else "Resilience Away",
                "primaryPlayerId": holder_id,
                "homeScore": 2,
                "awayScore": 1,
                "bannerText": "Pressure building",
                "commentary": "The live resilience server is driving player motion.",
            },
            {
                "id": "resilience-save",
                "type": "save",
                "sequence": 5 + (seq % 3),
                "minute": 13 + seq,
                "clockLabel": f"{13 + seq}'",
                "timeSeconds": round(seq * 1.0 + 0.4, 2),
                "teamId": "away-team",
                "teamName": "Resilience Away",
                "primaryPlayerId": "away-1",
                "secondaryPlayerId": "home-9",
                "homeScore": 2,
                "awayScore": 1,
                "bannerText": "Keeper intervention",
                "commentary": "The keeper gets down to the shot.",
            },
        ],
    }


@app.post("/admin/reset")
async def reset_scenarios() -> JSONResponse:
    STATE.reset()
    LOGGER.info("scenario state reset")
    return JSONResponse(
        {
            "current_access_token": STATE.current_access_token,
            "matches": [RESILIENCE_MATCH_ID, TERMINAL_MATCH_ID],
            "refresh_token": REFRESH_TOKEN,
        }
    )


@app.get("/match/{match_id}/live")
async def get_live_match(match_id: str, authorization: str | None = Header(default=None)) -> JSONResponse:
    if match_id not in {RESILIENCE_MATCH_ID, TERMINAL_MATCH_ID}:
        raise HTTPException(status_code=404, detail="not_found")
    _require_authorization(authorization)
    payload = _build_live_payload(match_id)
    LOGGER.info(
        "http live request match=%s frame=%s token=%s",
        match_id,
        payload["frameId"],
        STATE.current_access_token,
    )
    return JSONResponse(payload)


@app.post("/match/{match_id}/unity-access/refresh")
async def refresh_live_access(match_id: str, authorization: str | None = Header(default=None)) -> JSONResponse:
    if match_id not in {RESILIENCE_MATCH_ID, TERMINAL_MATCH_ID}:
        raise HTTPException(status_code=404, detail="not_found")

    if authorization and authorization != f"Bearer {STATE.current_access_token}":
        raise HTTPException(status_code=401, detail="unauthorized")

    STATE.refresh_calls += 1
    LOGGER.info("refresh request match=%s refresh_calls=%s", match_id, STATE.refresh_calls)
    return JSONResponse(
        {
            "match_id": match_id,
            "access_token": REFRESHED_ACCESS_TOKEN,
            "refresh_token": REFRESH_TOKEN,
            "spectator_session_id": "resilience-session",
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
    if match_id not in {RESILIENCE_MATCH_ID, TERMINAL_MATCH_ID}:
        await websocket.close(code=4404, reason="not_found")
        return

    if websocket.headers.get("authorization") != f"Bearer {STATE.current_access_token}":
        await websocket.close(code=4401, reason="unauthorized")
        return

    await websocket.accept()

    if match_id == TERMINAL_MATCH_ID:
        LOGGER.info("terminal websocket final frame match=%s", match_id)
        await websocket.send_json(_build_live_payload(match_id))
        await websocket.close(code=1000, reason="terminal")
        return

    STATE.websocket_connections += 1
    connection_number = STATE.websocket_connections
    LOGGER.info(
        "resilience websocket connect #%s token=%s format=%s",
        connection_number,
        STATE.current_access_token,
        websocket.query_params.get("format"),
    )

    try:
        if connection_number == 1:
            for _ in range(2):
                await websocket.send_json(_build_live_payload(match_id))
                await asyncio.sleep(1.0)
            LOGGER.info("resilience websocket forcing 4401 close for token refresh")
            await websocket.close(code=4401, reason="unauthorized")
            return

        if connection_number == 2:
            await websocket.send_json(_build_live_payload(match_id))
            LOGGER.info("resilience websocket stalling long enough to trigger stale transport detection")
            await asyncio.sleep(14.5)
            await websocket.send_json(_build_live_payload(match_id))
            return

        LOGGER.info("resilience websocket steady streaming after reconnect")
        while True:
            await websocket.send_json(_build_live_payload(match_id))
            await asyncio.sleep(1.0)
    except Exception as exc:  # pragma: no cover - smoke harness only
        LOGGER.info("websocket closed match=%s reason=%s", match_id, exc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve controlled GTEX live resilience scenarios for the Windows player."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8878)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
