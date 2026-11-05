from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from app.auth.dependencies import get_current_user
from app.broadcast.broadcast_models import ScoreUpdate, SpectatorEvent, TournamentEvent
from app.broadcast.spectator_gateway import BroadcastRuntime, router


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="viewer-test",
        username="VerifiedSupporter",
        display_name="VerifiedSupporter",
        is_admin=False,
        is_super_admin=False,
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

    with client.websocket_connect("/ws/spectate/match-sec-1?display_name=Club%20Owner") as guest_ws:
        snap = _receive_until_type(guest_ws, "snapshot")
        assert snap["display_name"] == "Spectator", "Impersonating guest display_name must be neutralized"
        assert snap["user_id"] is None
        _receive_until_type(guest_ws, "viewer_count")

        with client.websocket_connect("/ws/spectate/match-sec-1?display_name=FanTwo") as peer_ws:
            _receive_until_type(peer_ws, "snapshot")
            _receive_until_type(peer_ws, "viewer_count")
            _receive_until_type(guest_ws, "viewer_count")

            # 1. Public WebSocket payload redaction
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
            guest_ws.send_json({"type": "reaction", "reaction": "🔥"})
            rx_ev = _receive_until_type(peer_ws, "reaction")
            _receive_until_type(guest_ws, "reaction")
            assert rx_ev["reaction"] == "🔥"

            # 4. Fourth message within the window triggers rate_limit protection
            guest_ws.send_json({"type": "reaction", "reaction": "👏"})
            rate_ev = _receive_until_type(guest_ws, "rate_limit")
            assert rate_ev["payload"]["code"] == "rate_limit_exceeded"


def test_public_spectator_events_never_expose_account_ids_or_connection_ids() -> None:
    """
    Regression Test (Vulnerabilities 1 & 5):
    Verifies that:
    - _snapshot_from_presence() and all public spectator snapshots redact active_user_ids ([]).
    - Neither authenticated nor unauthenticated spectator events expose account IDs (user_id,
      account_id, owner_user_id) or internal connection IDs (connection_id, client_id, socket_id).
    - Authoritative internal backend presence still tracks authenticated user_id internally.
    """
    app = _build_app()
    client = TestClient(app)

    ticket_resp = client.post("/matches/match-privacy-1/spectate-ticket")
    assert ticket_resp.status_code == 200
    ticket = ticket_resp.json()["ticket"]

    with client.websocket_connect(f"/ws/spectate/match-privacy-1?ticket={ticket}") as auth_ws:
        auth_snap = _receive_until_type(auth_ws, "snapshot")
        auth_vc = _receive_until_type(auth_ws, "viewer_count")

        assert auth_snap["user_id"] is None
        assert auth_snap["payload"]["authenticated"] is True
        assert "connection_id" not in auth_snap["payload"]
        assert auth_snap["snapshot"]["active_user_ids"] == []
        assert auth_vc["snapshot"]["active_user_ids"] == []

        # Confirm internal presence service still preserves authoritative user_id for backend processing
        internal_presence = asyncio.run(
            app.state.broadcast_runtime.presence_service.get_match_presence("match-privacy-1")
        )
        assert internal_presence.active_user_ids == ["viewer-test"]

        # Public REST spectator presence endpoint also redacts active_user_ids for non-admin callers
        rest_presence = client.get("/matches/match-privacy-1/spectators")
        assert rest_presence.status_code == 200
        assert rest_presence.json()["active_user_ids"] == []

        with client.websocket_connect("/ws/spectate/match-privacy-1?display_name=AnonFan") as anon_ws:
            anon_snap = _receive_until_type(anon_ws, "snapshot")
            anon_vc = _receive_until_type(anon_ws, "viewer_count")
            auth_vc_2 = _receive_until_type(auth_ws, "viewer_count")

            assert anon_snap["user_id"] is None
            assert anon_snap["snapshot"]["active_user_ids"] == []
            assert anon_vc["snapshot"]["active_user_ids"] == []
            assert auth_vc_2["snapshot"]["active_user_ids"] == []

            # Authenticated user sends reaction and chat; verify zero account IDs or connection IDs leak
            auth_ws.send_json({"type": "reaction", "reaction": "⚽"})
            rx_on_anon = _receive_until_type(anon_ws, "reaction")
            rx_on_auth = _receive_until_type(auth_ws, "reaction")
            for rx in (rx_on_anon, rx_on_auth):
                assert rx["user_id"] is None
                assert rx["display_name"] == "VerifiedSupporter"
                assert rx["payload"]["authenticated"] is True
                assert "connection_id" not in rx["payload"]
                assert "account_id" not in rx["payload"]

            auth_ws.send_json({"type": "chat_message", "message": "Great buildup play!"})
            chat_on_anon = _receive_until_type(anon_ws, "chat_message")
            chat_on_auth = _receive_until_type(auth_ws, "chat_message")
            for ch in (chat_on_anon, chat_on_auth):
                assert ch["user_id"] is None
                assert ch["display_name"] == "VerifiedSupporter"
                assert ch["payload"]["authenticated"] is True
                assert "connection_id" not in ch["payload"]

            # Publish a server event embedded with sensitive account/connection identifiers; verify sanitization
            asyncio.run(
                app.state.broadcast_runtime.match_room_manager.publish(
                    "match-privacy-1",
                    SpectatorEvent(
                        type="frame",
                        match_id="match-privacy-1",
                        user_id="leaked-user-99",
                        payload={
                            "frame": {"frame_id": "f-200", "time_seconds": 44.0},
                            "user_id": "nested-user-99",
                            "account_id": "acc-99",
                            "owner_user_id": "owner-99",
                            "connection_id": "conn-secret-123",
                            "client_id": "client-secret-456",
                            "socket_id": "sock-secret-789",
                            "active_user_ids": ["viewer-test", "owner-99"],
                        },
                    ),
                    delay_seconds=0,
                )
            )
            sanitized_frame = _receive_until_type(anon_ws, "frame")
            assert sanitized_frame["user_id"] is None
            for forbidden_key in (
                "user_id",
                "account_id",
                "owner_user_id",
                "connection_id",
                "client_id",
                "socket_id",
            ):
                assert forbidden_key not in sanitized_frame["payload"]
            assert sanitized_frame["payload"]["active_user_ids"] == []


def test_match_and_tournament_heartbeats_are_connection_specific_and_rate_limited() -> None:
    """
    Regression Test (Vulnerabilities 2 & 3):
    Verifies that:
    - Match and tournament heartbeats respond ONLY to the sender connection (never broadcast to the room).
    - A second spectator in the same match or tournament room never receives another spectator's heartbeat.
    - Heartbeat messages are subject to per-connection rate limiting and contain no connection_id.
    """
    app = _build_app()
    app.state.broadcast_runtime.rate_limit_max_messages = 2
    app.state.broadcast_runtime.rate_limit_window_seconds = 10.0
    client = TestClient(app)

    # 1. Match room heartbeat isolation & rate limiting
    with client.websocket_connect("/ws/spectate/match-hb-isolation?display_name=SpecOne") as ws_one:
        _receive_until_type(ws_one, "snapshot")
        _receive_until_type(ws_one, "viewer_count")

        with client.websocket_connect("/ws/spectate/match-hb-isolation?display_name=SpecTwo") as ws_two:
            _receive_until_type(ws_two, "snapshot")
            _receive_until_type(ws_two, "viewer_count")
            _receive_until_type(ws_one, "viewer_count")

            # SpecOne sends ping #1 -> only SpecOne receives heartbeat
            ws_one.send_json({"type": "ping"})
            hb_one = _receive_until_type(ws_one, "heartbeat")
            assert hb_one["match_id"] == "match-hb-isolation"
            assert hb_one["user_id"] is None
            assert hb_one["payload"] == {"status": "ok"}
            assert "connection_id" not in hb_one["payload"]

            # SpecOne sends ping #2 -> allowed (2/2 in window)
            ws_one.send_json({"type": "ping"})
            hb_two = _receive_until_type(ws_one, "heartbeat")
            assert hb_two["payload"] == {"status": "ok"}

            # SpecOne sends ping #3 -> rate limited!
            ws_one.send_json({"type": "ping"})
            rl_event = _receive_until_type(ws_one, "rate_limit")
            assert rl_event["payload"]["code"] == "rate_limit_exceeded"
            assert "connection_id" not in rl_event["payload"]

            # Prove SpecTwo received NONE of SpecOne's heartbeats or rate_limit events:
            # Publish a score_update and verify the very next message on ws_two is score_update
            asyncio.run(
                app.state.broadcast_runtime.match_room_manager.publish(
                    "match-hb-isolation",
                    SpectatorEvent(
                        type="score_update",
                        match_id="match-hb-isolation",
                        score_update=ScoreUpdate(match_id="match-hb-isolation", score="1-0", home_score=1, away_score=0),
                    ),
                    delay_seconds=0,
                )
            )
            next_on_two = ws_two.receive_json()
            assert next_on_two["type"] == "score_update", (
                f"Expected score_update as next message on second spectator, got {next_on_two['type']!r}"
            )

    # 2. Tournament room heartbeat isolation & rate limiting
    with client.websocket_connect("/ws/tournament/tourney-hb-isolation?display_name=TourneyOne") as t_one:
        _receive_until_type(t_one, "tournament_snapshot")

        with client.websocket_connect("/ws/tournament/tourney-hb-isolation?display_name=TourneyTwo") as t_two:
            _receive_until_type(t_two, "tournament_snapshot")

            t_one.send_json({"type": "ping"})
            t_hb_1 = _receive_until_type(t_one, "heartbeat")
            assert t_hb_1["tournament_id"] == "tourney-hb-isolation"
            assert t_hb_1["payload"] == {"status": "ok"}
            assert "connection_id" not in t_hb_1["payload"]

            t_one.send_json({"type": "ping"})
            t_hb_2 = _receive_until_type(t_one, "heartbeat")
            assert t_hb_2["payload"] == {"status": "ok"}

            # 3rd tournament ping exceeds rate limit
            t_one.send_json({"type": "ping"})
            t_rl = _receive_until_type(t_one, "rate_limit")
            assert t_rl["payload"]["code"] == "rate_limit_exceeded"
            assert "connection_id" not in t_rl["payload"]

            # Prove TourneyTwo never received TourneyOne's heartbeats
            asyncio.run(
                app.state.broadcast_runtime.tournament_hub.publish(
                    "tourney-hb-isolation",
                    TournamentEvent(
                        type="score_update",
                        tournament_id="tourney-hb-isolation",
                        match_id="m-77",
                        featured_match_id="m-77",
                    ),
                    delay_seconds=0,
                )
            )
            next_on_t_two = t_two.receive_json()
            assert next_on_t_two["type"] == "score_update", (
                f"Expected score_update as next message on second tournament spectator, got {next_on_t_two['type']!r}"
            )


def test_websocket_rejects_url_bearer_tokens_and_enforces_ticket_scope_expiry_and_replay() -> None:
    """
    Regression Test (Vulnerability 4):
    Verifies that:
    - Bearer tokens in WebSocket URL query parameters (?token=...) are rejected with code 4401.
    - Short-lived, single-use, match-scoped tickets enforce:
      1. Scope validation (wrong match_id or tournament scope rejected).
      2. Single-use replay protection (reusing a redeemed ticket rejected).
      3. Expiry validation (expired ticket rejected).
    """
    app = _build_app()
    client = TestClient(app)

    # 1. Raw bearer token in WebSocket URL is strictly rejected
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/spectate/match-auth-99?token=eyJhbGciOiJIUzI1NiJ9.secret"):
            pass
    assert exc_info.value.code == 4401

    with pytest.raises(WebSocketDisconnect) as exc_info_t:
        with client.websocket_connect("/ws/tournament/tourney-auth-99?token=eyJhbGciOiJIUzI1NiJ9.secret"):
            pass
    assert exc_info_t.value.code == 4401

    # 2. Issue a valid match-scoped ticket for match-auth-99
    resp = client.post("/matches/match-auth-99/spectate-ticket")
    assert resp.status_code == 200
    ticket_data = resp.json()
    ticket = ticket_data["ticket"]
    assert ticket_data["match_id"] == "match-auth-99"
    assert ticket_data["scope_type"] == "match"

    # 3. Scope validation: using a ticket scoped to match-auth-99 on match-other-100 is rejected
    with pytest.raises(WebSocketDisconnect) as wrong_match_exc:
        with client.websocket_connect(f"/ws/spectate/match-other-100?ticket={ticket}"):
            pass
    assert wrong_match_exc.value.code == 4401

    # Scope validation: using a match ticket on a tournament WebSocket is rejected
    with pytest.raises(WebSocketDisconnect) as wrong_type_exc:
        with client.websocket_connect(f"/ws/tournament/match-auth-99?ticket={ticket}"):
            pass
    assert wrong_type_exc.value.code == 4401

    # 4. Valid first-time redemption on the scoped match succeeds
    with client.websocket_connect(f"/ws/spectate/match-auth-99?ticket={ticket}") as valid_ws:
        snap = _receive_until_type(valid_ws, "snapshot")
        assert snap["payload"]["authenticated"] is True
        assert snap["display_name"] == "VerifiedSupporter"
        assert snap["user_id"] is None

    # 5. Replay protection: reusing the same ticket a second time is rejected
    with pytest.raises(WebSocketDisconnect) as replay_exc:
        with client.websocket_connect(f"/ws/spectate/match-auth-99?ticket={ticket}"):
            pass
    assert replay_exc.value.code == 4401

    # 6. Expiry enforcement: issue a ticket with a 10ms TTL, wait 30ms, and confirm rejection
    expired_issue = app.state.broadcast_runtime.issue_spectator_ticket(
        user_id="viewer-test",
        display_name="VerifiedSupporter",
        scope_type="match",
        scope_id="match-auth-99",
        ttl_seconds=0.01,
    )
    time.sleep(0.03)
    with pytest.raises(WebSocketDisconnect) as expired_exc:
        with client.websocket_connect(f"/ws/spectate/match-auth-99?ticket={expired_issue['ticket']}"):
            pass
    assert expired_exc.value.code == 4401
