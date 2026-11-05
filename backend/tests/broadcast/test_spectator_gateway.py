from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.broadcast.broadcast_models import ScoreUpdate, SpectatorEvent, TournamentEvent
from app.broadcast.spectator_gateway import BroadcastRuntime, router


from app.auth.dependencies import get_current_user
from types import SimpleNamespace

def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="viewer-test", is_admin=False, is_super_admin=False
    )
    app.state.broadcast_runtime = BroadcastRuntime(
        redis_url=None,
        delay_seconds=0,
        viewer_ttl_seconds=60,
        heartbeat_interval_seconds=60,
        max_queue_size=32,
    )
    app.state.broadcast = app.state.broadcast_runtime
    return app


def _receive_until_type(websocket, expected_type: str, *, limit: int = 6) -> dict[str, object]:
    for _ in range(limit):
        payload = websocket.receive_json()
        if payload["type"] == expected_type:
            return payload
    raise AssertionError(f"Did not receive event type {expected_type!r} within {limit} messages.")


def test_spectator_gateway_tracks_presence_and_match_events() -> None:
    app = _build_app()
    client = TestClient(app)

    with client.websocket_connect("/ws/spectate/match-1?display_name=Alice") as first:
        first_snapshot = _receive_until_type(first, "snapshot")
        first_viewers = _receive_until_type(first, "viewer_count")
        assert first_snapshot["snapshot"]["viewer_count"] == 1
        assert first_viewers["snapshot"]["viewer_count"] == 1

        with client.websocket_connect("/ws/spectate/match-1?display_name=Bob") as second:
            second_snapshot = _receive_until_type(second, "snapshot")
            second_viewers = _receive_until_type(second, "viewer_count")
            first_updated_viewers = _receive_until_type(first, "viewer_count")

            assert second_snapshot["snapshot"]["viewer_count"] == 2
            assert second_viewers["snapshot"]["viewer_count"] == 2
            assert first_updated_viewers["snapshot"]["viewer_count"] == 2

            presence_response = client.get("/matches/match-1/spectators")
            assert presence_response.status_code == 200
            assert presence_response.json() == {
                "match_id": "match-1",
                "active_viewers": 2,
                "peak_viewers": 2,
                "active_user_ids": [],
            }

            first.send_json({"type": "reaction", "reaction": "🔥"})
            reaction_event = _receive_until_type(second, "reaction")
            assert reaction_event["reaction"] == "🔥"
            assert reaction_event["display_name"] == "Alice"

            asyncio.run(
                app.state.broadcast_runtime.match_room_manager.publish(
                    "match-1",
                    SpectatorEvent(
                        type="score_update",
                        match_id="match-1",
                        score_update=ScoreUpdate(
                            match_id="match-1",
                            score="2-1",
                            home_score=2,
                            away_score=1,
                        ),
                    ),
                    delay_seconds=0,
                )
            )
            score_event = _receive_until_type(first, "score_update")
            assert score_event["score_update"]["score"] == "2-1"

        updated_presence = client.get("/matches/match-1/spectators")
        assert updated_presence.status_code == 200
        assert updated_presence.json() == {
            "match_id": "match-1",
            "active_viewers": 1,
            "peak_viewers": 2,
            "active_user_ids": [],
        }
        remaining_viewers = _receive_until_type(first, "viewer_count")
        assert remaining_viewers["snapshot"]["viewer_count"] == 1


def test_tournament_gateway_streams_featured_match_updates() -> None:
    app = _build_app()
    client = TestClient(app)

    with client.websocket_connect("/ws/tournament/tournament-1?display_name=Desk") as websocket:
        snapshot = _receive_until_type(websocket, "tournament_snapshot")
        assert snapshot["payload"]["viewer_count"] == 1
        assert snapshot["featured_match_id"] is None

        asyncio.run(
            app.state.broadcast_runtime.tournament_hub.publish(
                "tournament-1",
                TournamentEvent(
                    type="score_update",
                    tournament_id="tournament-1",
                    match_id="match-42",
                    featured_match_id="match-42",
                    standings=[{"team_id": "team-a", "points": 9}],
                    payload={"summary": "featured match live"},
                ),
                delay_seconds=0,
            )
        )

        update = _receive_until_type(websocket, "score_update")
        assert update["match_id"] == "match-42"
        assert update["featured_match_id"] == "match-42"
        assert update["standings"] == [{"team_id": "team-a", "points": 9}]


def test_spectator_gateway_redacts_confidential_tactics_and_prevents_spoofing_and_rate_abuse() -> None:
    app = _build_app()
    app.state.broadcast_runtime.rate_limit_max_messages = 3
    app.state.broadcast_runtime.rate_limit_window_seconds = 10.0
    client = TestClient(app)

    # Guest attempting to impersonate 'Club Owner' via display_name query param
    with client.websocket_connect("/ws/spectate/match-sec-1?display_name=Club%20Owner") as guest_ws:
        snap = _receive_until_type(guest_ws, "snapshot")
        assert snap["display_name"] == "Spectator", "Impersonating guest display_name must be neutralized"
        assert snap["user_id"] is None
        _receive_until_type(guest_ws, "viewer_count")

        with client.websocket_connect("/ws/spectate/match-sec-1?display_name=FanTwo") as peer_ws:
            _receive_until_type(peer_ws, "snapshot")
            _receive_until_type(peer_ws, "viewer_count")
            _receive_until_type(guest_ws, "viewer_count")

            # 1. Public WebSocket payload redaction: publish event containing confidential coach_notes & internal_tactics
            asyncio.run(
                app.state.broadcast_runtime.match_room_manager.publish(
                    "match-sec-1",
                    SpectatorEvent(
                        type="frame",
                        match_id="match-sec-1",
                        payload={
                            "frame": {"frame_id": "f-10", "time_seconds": 15.0},
                            "coach_notes": ["Secret press trigger on left wingback"],
                            "internal_tactics": {"exploit_channel": "right"},
                            "deterministic_seed": 99999,
                            "presentation_package": {
                                "match_label": "Apex vs Stars",
                                "coach_notes": ["Hidden note"],
                            },
                        },
                    ),
                    delay_seconds=0,
                )
            )
            frame_ev = _receive_until_type(guest_ws, "frame")
            assert frame_ev["payload"]["coach_notes"] == []
            assert "internal_tactics" not in frame_ev["payload"]
            assert "deterministic_seed" not in frame_ev["payload"]
            assert frame_ev["payload"]["presentation_package"]["coach_notes"] == []

            # 2. Identity spoofing in client payload must be ignored
            guest_ws.send_json(
                {
                    "type": "chat_message",
                    "user_id": "spoofed-owner-id",
                    "display_name": "Admin Override",
                    "message": "Hello match room!",
                }
            )
            chat_ev = _receive_until_type(peer_ws, "chat_message")
            _receive_until_type(guest_ws, "chat_message")
            assert chat_ev["user_id"] is None
            assert chat_ev["display_name"] == "Spectator"
            assert chat_ev["payload"]["authenticated"] is False
            assert chat_ev["message"] == "Hello match room!"

            # 3. Malicious script injection in chat/reaction is dropped
            guest_ws.send_json(
                {
                    "type": "chat_message",
                    "message": "<script>alert('xss')</script>",
                }
            )
            # Send 2 more valid reactions to hit the 3-message rate limit (1 chat + 1 dropped script + 1 reaction = 3)
            guest_ws.send_json({"type": "reaction", "reaction": "🔥"})
            rx_ev = _receive_until_type(peer_ws, "reaction")
            _receive_until_type(guest_ws, "reaction")
            assert rx_ev["reaction"] == "🔥"

            # 4. Fourth message within the window triggers rate_limit protection
            guest_ws.send_json({"type": "reaction", "reaction": "👏"})
            rate_ev = _receive_until_type(guest_ws, "rate_limit")
            assert rate_ev["payload"]["code"] == "rate_limit_exceeded"
