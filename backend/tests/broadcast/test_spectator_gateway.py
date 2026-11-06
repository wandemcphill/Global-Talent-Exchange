from __future__ import annotations

import asyncio
import json
import os
import redis.asyncio as redis_asyncio
import time
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from redis.exceptions import RedisError
from starlette.websockets import WebSocketDisconnect

from app.auth.dependencies import get_current_user
from app.broadcast.broadcast_models import ScoreUpdate, SpectatorEvent, TournamentEvent
from app.broadcast.match_room_manager import adapt_match_stream_message
from app.broadcast.spectator_gateway import (
    AsyncEvalRedisEmulator,
    BroadcastRuntime,
    MAX_TICKET_TTL_SECONDS,
    SpectatorTicketStoreError,
    redact_ticket_from_log_text,
    router,
    ticket_sha256_digest,
)


def _build_app(
    *,
    shared_redis: object | None = None,
    require_redis_tickets: bool = False,
) -> FastAPI:
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
        require_redis_tickets=require_redis_tickets,
        ticket_redis_client=shared_redis,
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


def test_match_stream_publishers_are_adapted_to_the_spectator_contract() -> None:
    match_event = adapt_match_stream_message(
        "match-stream-1",
        {
            "message_type": "match_event",
            "match_id": "match-stream-1",
            "event_id": "event-9",
            "sequence": 9,
            "event_type": "goal",
            "minute": 63,
            "clock": "63'",
            "home_score": 2,
            "away_score": 1,
            "team": "Home FC",
            "player": "Striker",
            "commentary": "A late goal.",
            "published_at": "2026-11-06T04:00:00+00:00",
            "metadata": {"status": "live", "is_penalty": False, "user_id": "private-user"},
        },
    )
    assert match_event is not None
    assert match_event["type"] == "match_event"
    assert match_event["match_id"] == "match-stream-1"
    assert match_event["score_update"]["home_score"] == 2
    assert match_event["payload"]["event_id"] == "event-9"
    assert match_event["payload"]["event_type"] == "goal"
    assert match_event["payload"]["banner_text"] == "A late goal."
    assert "user_id" not in match_event["payload"]

    ticker_update = adapt_match_stream_message(
        "match-stream-1",
        {
            "type": "live_match_state",
            "match_id": "match-stream-1",
            "minute": 72,
            "phase": "second_half",
            "home_score": 2,
            "away_score": 2,
        },
    )
    assert ticker_update == {
        "type": "score_update",
        "match_id": "match-stream-1",
        "score_update": {
            "home_score": 2,
            "away_score": 2,
            "minute": 72,
            "status": "second_half",
        },
    }
    assert adapt_match_stream_message("another-match", {"message_type": "match_event", "match_id": "match-stream-1"}) is None


@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="requires live Redis")
def test_match_stream_service_raw_redis_event_reaches_spectator_websocket() -> None:
    redis_url = os.environ["REDIS_URL"]
    match_id = f"match-stream-integration-{time.time_ns()}"
    app = _build_app()
    app.state.broadcast_runtime.match_room_manager.redis_url = redis_url
    client = TestClient(app)

    with client.websocket_connect(f"/ws/spectate/{match_id}?display_name=LiveFan") as websocket:
        _receive_until_type(websocket, "snapshot")
        _receive_until_type(websocket, "viewer_count")

        async def publish_raw_match_stream_event() -> None:
            redis = redis_asyncio.Redis.from_url(redis_url, decode_responses=True)
            channel = f"match:{match_id}:events"
            for _ in range(40):
                subscribers = await redis.pubsub_numsub(channel)
                if subscribers and int(subscribers[0][1]) > 0:
                    break
                await asyncio.sleep(0.05)
            await redis.publish(
                channel,
                json.dumps(
                    {
                        "message_type": "match_event",
                        "match_id": match_id,
                        "event_id": "goal-event-1",
                        "sequence": 1,
                        "event_type": "goal",
                        "minute": 19,
                        "clock": "19'",
                        "home_score": 1,
                        "away_score": 0,
                        "commentary": "The home side scores.",
                        "published_at": "2026-11-06T04:00:00+00:00",
                    }
                ),
            )
            await redis.aclose()

        asyncio.run(publish_raw_match_stream_event())
        event = _receive_until_type(websocket, "match_event")
        assert event["payload"]["event_id"] == "goal-event-1"
        assert event["payload"]["event_type"] == "goal"
        assert event["score_update"]["home_score"] == 1


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

            guest_ws.send_json({"type": "reaction", "reaction": "👏"})
            rate_ev = _receive_until_type(guest_ws, "rate_limit")
            assert rate_ev["payload"]["code"] == "rate_limit_exceeded"


def test_public_spectator_events_never_expose_account_ids_or_connection_ids_including_camel_case_aliases() -> None:
    """
    Regression Test:
    Verifies that public spectator events cannot expose account or connection identifiers
    under snake_case, camelCase, PascalCase, or suffix aliases, and that unknown root/snapshot
    fields are rejected by the structural allowlist.
    """
    app = _build_app()
    client = TestClient(app)

    ticket_resp = client.post("/matches/match-privacy-1/spectate-ticket")
    assert ticket_resp.status_code == 200
    assert ticket_resp.headers.get("cache-control") == "no-store"
    ticket = ticket_resp.json()["ticket"]

    with client.websocket_connect(f"/ws/spectate/match-privacy-1?ticket={ticket}") as auth_ws:
        auth_snap = _receive_until_type(auth_ws, "snapshot")
        auth_vc = _receive_until_type(auth_ws, "viewer_count")

        assert auth_snap["user_id"] is None
        assert auth_snap["payload"]["authenticated"] is True
        assert "connection_id" not in auth_snap["payload"]
        assert auth_snap["snapshot"]["active_user_ids"] == []
        assert auth_vc["snapshot"]["active_user_ids"] == []

        internal_presence = asyncio.run(
            app.state.broadcast_runtime.presence_service.get_match_presence("match-privacy-1")
        )
        assert internal_presence.active_user_ids == ["viewer-test"]

        with client.websocket_connect("/ws/spectate/match-privacy-1?display_name=AnonFan") as anon_ws:
            _receive_until_type(anon_ws, "snapshot")
            _receive_until_type(anon_ws, "viewer_count")
            _receive_until_type(auth_ws, "viewer_count")

            asyncio.run(
                app.state.broadcast_runtime.match_room_manager.publish(
                    "match-privacy-1",
                    {
                        "type": "frame",
                        "match_id": "match-privacy-1",
                        "user_id": "leaked-user-99",
                        "unlisted_root_secret": "must-be-dropped-by-root-allowlist",  # pragma: allowlist secret
                        "payload": {
                            "frame": {"frame_id": "f-200", "time_seconds": 44.0},
                            "user_id": "nested-user-99",
                            "userId": "camel-user-99",
                            "accountId": "camel-acc-99",
                            "account_id": "acc-99",
                            "ownerUserId": "camel-owner-99",
                            "owner_user_id": "owner-99",
                            "primary_user_id": "suffix-user-99",
                            "connection_id": "conn-secret-123",
                            "connectionId": "camel-conn-123",
                            "client_id": "client-secret-456",
                            "clientId": "camel-client-456",
                            "socket_id": "sock-secret-789",
                            "socketId": "camel-sock-789",
                            "sessionId": "sess-secret-000",
                            "active_user_ids": ["viewer-test"],
                            "activeUserIds": ["viewer-test"],
                            "coachNotes": ["camel-case secret note"],
                        },
                    },
                    delay_seconds=0,
                )
            )
            sanitized_frame = _receive_until_type(anon_ws, "frame")
            assert sanitized_frame["user_id"] is None
            assert "unlisted_root_secret" not in sanitized_frame
            for forbidden_key in (
                "user_id",
                "userId",
                "account_id",
                "accountId",
                "owner_user_id",
                "ownerUserId",
                "primary_user_id",
                "connection_id",
                "connectionId",
                "client_id",
                "clientId",
                "socket_id",
                "socketId",
                "sessionId",
            ):
                assert forbidden_key not in sanitized_frame["payload"]
            assert sanitized_frame["payload"]["active_user_ids"] == []
            assert sanitized_frame["payload"]["coach_notes"] == []


def test_match_and_tournament_heartbeats_are_connection_specific_and_rate_limited() -> None:
    app = _build_app()
    app.state.broadcast_runtime.rate_limit_max_messages = 2
    app.state.broadcast_runtime.rate_limit_window_seconds = 10.0
    client = TestClient(app)

    with client.websocket_connect("/ws/spectate/match-hb-isolation?display_name=SpecOne") as ws_one:
        _receive_until_type(ws_one, "snapshot")
        _receive_until_type(ws_one, "viewer_count")

        with client.websocket_connect("/ws/spectate/match-hb-isolation?display_name=SpecTwo") as ws_two:
            _receive_until_type(ws_two, "snapshot")
            _receive_until_type(ws_two, "viewer_count")
            _receive_until_type(ws_one, "viewer_count")

            ws_one.send_json({"type": "ping"})
            hb_one = _receive_until_type(ws_one, "heartbeat")
            assert hb_one["match_id"] == "match-hb-isolation"
            assert hb_one["user_id"] is None
            assert hb_one["payload"] == {"status": "ok"}
            assert "connection_id" not in hb_one["payload"]

            ws_one.send_json({"type": "ping"})
            hb_two = _receive_until_type(ws_one, "heartbeat")
            assert hb_two["payload"] == {"status": "ok"}

            ws_one.send_json({"type": "ping"})
            rl_event = _receive_until_type(ws_one, "rate_limit")
            assert rl_event["payload"]["code"] == "rate_limit_exceeded"
            assert "connection_id" not in rl_event["payload"]

            asyncio.run(
                app.state.broadcast_runtime.match_room_manager.publish(
                    "match-hb-isolation",
                    SpectatorEvent(
                        type="score_update",
                        match_id="match-hb-isolation",
                        score_update=ScoreUpdate(
                            match_id="match-hb-isolation", score="1-0", home_score=1, away_score=0
                        ),
                    ),
                    delay_seconds=0,
                )
            )
            next_on_two = ws_two.receive_json()
            assert next_on_two["type"] == "score_update"

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

            t_one.send_json({"type": "ping"})
            t_rl = _receive_until_type(t_one, "rate_limit")
            assert t_rl["payload"]["code"] == "rate_limit_exceeded"

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
            assert next_on_t_two["type"] == "score_update"


def test_distributed_redis_ticket_cross_instance_redemption_and_sha256_storage() -> None:
    """
    Phase B Backend Requirement 1 & 2:
    - Ticket issued by runtime instance A can be redeemed by runtime instance B using shared Redis.
    - Only the SHA-256 digest of the ticket is stored in Redis (never the raw ticket).
    - Maximum 30-second TTL is enforced.
    - Two simultaneous redemption attempts across instances cannot both succeed.
    """
    shared_redis = AsyncEvalRedisEmulator()
    runtime_a = BroadcastRuntime(redis_url=None, ticket_redis_client=shared_redis, require_redis_tickets=True)
    runtime_b = BroadcastRuntime(redis_url=None, ticket_redis_client=shared_redis, require_redis_tickets=True)

    issued = asyncio.run(
        runtime_a.issue_spectator_ticket(
            user_id="user-dist-1",
            display_name="DistributedViewer",
            scope_type="match",
            scope_id="match-dist-500",
            ttl_seconds=120.0,  # Request > 30s to verify hard cap at 30s
        )
    )
    raw_ticket = issued["ticket"]
    expected_digest = ticket_sha256_digest(raw_ticket)
    assert issued["ticket_digest"] == expected_digest
    assert issued["expires_in"] == int(MAX_TICKET_TTL_SECONDS)

    # Verify raw ticket is NOT in Redis keys; only SHA-256 digest key exists
    all_keys = asyncio.run(shared_redis.keys("*"))
    assert all(raw_ticket not in k for k in all_keys)
    expected_redis_key = f"gtex:broadcast:spectator:ticket:{expected_digest}"
    assert expected_redis_key in all_keys

    # Instance B redeems the ticket issued by Instance A
    redeemed_on_b = asyncio.run(
        runtime_b.redeem_spectator_ticket(
            raw_ticket,
            expected_scope_type="match",
            expected_scope_id="match-dist-500",
        )
    )
    assert redeemed_on_b is not None
    assert redeemed_on_b.user_id == "user-dist-1"
    assert redeemed_on_b.display_name == "DistributedViewer"

    # Key is atomically deleted upon redemption
    assert asyncio.run(shared_redis.hgetall(expected_redis_key)) == {}

    # Concurrent redemption test across Instance A and Instance B on a newly issued ticket
    issued_concurrent = asyncio.run(
        runtime_a.issue_spectator_ticket(
            user_id="user-dist-2",
            display_name="ConcurrentViewer",
            scope_type="match",
            scope_id="match-dist-500",
        )
    )
    concurrent_ticket = issued_concurrent["ticket"]

    async def _race_redemptions():
        return await asyncio.gather(
            runtime_a.redeem_spectator_ticket(
                concurrent_ticket,
                expected_scope_type="match",
                expected_scope_id="match-dist-500",
            ),
            runtime_b.redeem_spectator_ticket(
                concurrent_ticket,
                expected_scope_type="match",
                expected_scope_id="match-dist-500",
            ),
        )

    res_a, res_b = asyncio.run(_race_redemptions())
    successes = [r for r in (res_a, res_b) if r is not None]
    assert len(successes) == 1, "Exactly one concurrent redemption attempt may succeed"
    assert successes[0].user_id == "user-dist-2"


def test_websocket_rejects_url_bearer_tokens_and_enforces_ticket_scope_expiry_and_replay() -> None:
    """
    Phase B Backend Requirement 3, 4, 5:
    - Bearer tokens in WebSocket URLs (any case: ?token=, ?TOKEN=, ?Access_Token=) are rejected (4401).
    - Wrong match/tournament scope is rejected AND does not burn the ticket for the valid scope.
    - Expired tickets are rejected.
    - Replayed tickets are rejected.
    """
    shared_redis = AsyncEvalRedisEmulator()
    app = _build_app(shared_redis=shared_redis, require_redis_tickets=True)
    client = TestClient(app)

    for param in ("token", "TOKEN", "Access_Token", "Bearer"):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/spectate/match-auth-99?{param}=eyJhbGciOiJIUzI1NiJ9.secret"):
                pass
        assert exc_info.value.code == 4401

    resp = client.post("/matches/match-auth-99/spectate-ticket")
    assert resp.status_code == 200
    assert resp.headers.get("cache-control") == "no-store"
    ticket = resp.json()["ticket"]

    # Wrong match scope rejected
    with pytest.raises(WebSocketDisconnect) as wrong_match_exc:
        with client.websocket_connect(f"/ws/spectate/match-other-100?ticket={ticket}"):
            pass
    assert wrong_match_exc.value.code == 4401

    # Wrong scope type (tournament vs match) rejected
    with pytest.raises(WebSocketDisconnect) as wrong_type_exc:
        with client.websocket_connect(f"/ws/tournament/match-auth-99?ticket={ticket}"):
            pass
    assert wrong_type_exc.value.code == 4401

    # Valid redemption on the intended match succeeds (wrong-scope probe did not burn ticket)
    with client.websocket_connect(f"/ws/spectate/match-auth-99?ticket={ticket}") as valid_ws:
        snap = _receive_until_type(valid_ws, "snapshot")
        assert snap["payload"]["authenticated"] is True
        assert snap["display_name"] == "VerifiedSupporter"
        assert snap["user_id"] is None

    # Replay attempt with the same ticket is rejected
    with pytest.raises(WebSocketDisconnect) as replay_exc:
        with client.websocket_connect(f"/ws/spectate/match-auth-99?ticket={ticket}"):
            pass
    assert replay_exc.value.code == 4401

    # Expired ticket is rejected
    expired_issue = asyncio.run(
        app.state.broadcast_runtime.issue_spectator_ticket(
            user_id="viewer-test",
            display_name="VerifiedSupporter",
            scope_type="match",
            scope_id="match-auth-99",
            ttl_seconds=0.01,
            enforce_rate_limit=False,
        )
    )
    time.sleep(0.03)
    with pytest.raises(WebSocketDisconnect) as expired_exc:
        with client.websocket_connect(f"/ws/spectate/match-auth-99?ticket={expired_issue['ticket']}"):
            pass
    assert expired_exc.value.code == 4401


def test_redis_failure_fails_closed_in_production_and_enforces_unauth_and_rate_limits() -> None:
    """
    Phase B Backend Requirement 6, 7, 8:
    - Redis failure does not enable unsafe production fallback (fails closed on both issuance and redemption).
    - Unauthenticated users cannot obtain authenticated tickets (401).
    - Ticket issuance rate limits work (429).
    - Ticket values are redacted from log messages.
    """

    class BrokenRedisClient:
        async def eval(self, *args, **kwargs):
            raise RedisError("Simulated production Redis cluster outage")

    # 1. Production runtime with broken Redis fails closed (503 on issuance, 4401 on WS redemption)
    prod_app = _build_app(shared_redis=BrokenRedisClient(), require_redis_tickets=True)
    prod_client = TestClient(prod_app)

    issue_fail_resp = prod_client.post("/matches/match-prod-1/spectate-ticket")
    assert issue_fail_resp.status_code == 503

    with pytest.raises(WebSocketDisconnect) as ws_fail_exc:
        with prod_client.websocket_connect("/ws/spectate/match-prod-1?ticket=any_ticket_value"):
            pass
    assert ws_fail_exc.value.code == 4401

    # Also verify that require_redis_tickets=True with no redis_url and no redis_client fails closed
    no_redis_prod_app = _build_app(shared_redis=None, require_redis_tickets=True)
    no_redis_client = TestClient(no_redis_prod_app)
    assert no_redis_client.post("/matches/match-prod-1/spectate-ticket").status_code == 503

    # 2. Unauthenticated users cannot obtain authenticated tickets
    unauth_app = _build_app()

    def _reject_unauth():
        raise HTTPException(status_code=401, detail="Not authenticated")

    unauth_app.dependency_overrides[get_current_user] = _reject_unauth
    unauth_client = TestClient(unauth_app)
    assert unauth_client.post("/matches/match-auth-only/spectate-ticket").status_code == 401
    assert unauth_client.post("/tournaments/tourney-auth-only/spectate-ticket").status_code == 401

    # 3. Ticket issuance rate limiting (429 Too Many Requests)
    rl_app = _build_app(shared_redis=AsyncEvalRedisEmulator(), require_redis_tickets=True)
    rl_app.state.broadcast_runtime.ticket_rate_limit_max = 2
    rl_app.state.broadcast_runtime.ticket_rate_limit_window_seconds = 60.0
    rl_client = TestClient(rl_app)

    assert rl_client.post("/matches/m-rl/spectate-ticket").status_code == 200
    assert rl_client.post("/matches/m-rl/spectate-ticket").status_code == 200
    third_resp = rl_client.post("/matches/m-rl/spectate-ticket")
    assert third_resp.status_code == 429

    # 4. Log redaction helper strips ticket values from URLs and JSON payloads
    raw_log = 'GET /ws/spectate/m-1?ticket=secret_tok_123 HTTP/1.1 {"ticket": "secret_tok_123"}'
    redacted_log = redact_ticket_from_log_text(raw_log)
    assert "secret_tok_123" not in redacted_log
    assert "ticket=[REDACTED]" in redacted_log
    assert '"ticket": "[REDACTED]"' in redacted_log


def test_real_redis_spectator_ticket_store_lifecycle() -> None:
    """
    Phase 1 Chief Engineer Certification:
    Genuine Redis Integration Test verifying:
    1. Ticket issuance by runtime A.
    2. Redemption by runtime B using the same Redis service.
    3. Atomic concurrent redemption with exactly one successful consumer (out of 20 concurrent tasks).
    4. SHA-256-only ticket-key storage (no raw ticket in Redis keys or data).
    5. Actual Redis TTL enforcement (PEXPIRE <= 30000ms, and eviction).
    6. Correct Lua script execution for storing, redeeming, and sliding-window rate limiting.
    7. Scope validation without burning a ticket on an invalid scope probe.
    8. Sorted set sliding window rate limiter verification.
    9. Redis outage and production fail-closed behaviour.
    """
    redis_url = os.getenv("REDIS_URL") or os.getenv("GTE_REDIS_URL")
    if not redis_url:
        if os.getenv("GTEX_REQUIRE_REAL_REDIS") == "1":
            pytest.fail("GTEX_REQUIRE_REAL_REDIS=1 but REDIS_URL/GTE_REDIS_URL is not configured")
        pytest.skip("Live Redis integration requires REDIS_URL or GTE_REDIS_URL")

    redis_client = redis_asyncio.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=10,
    )

    run_id = str(time.time_ns())
    runtime_a = BroadcastRuntime(
        redis_url=None,
        ticket_redis_client=redis_client,
        require_redis_tickets=True,
    )
    runtime_b = BroadcastRuntime(
        redis_url=None,
        ticket_redis_client=redis_client,
        require_redis_tickets=True,
    )

    async def _run_lifecycle() -> None:
        await redis_client.ping()

        # 1. Ticket issuance by runtime A
        issued = await runtime_a.issue_spectator_ticket(
            user_id=f"user-real-redis-{run_id}",
            display_name="RedisSupporter",
            scope_type="match",
            scope_id=f"match-real-{run_id}",
            ttl_seconds=60.0,  # capped at 30s
        )
        raw_ticket = issued["ticket"]
        digest = issued["ticket_digest"]
        assert digest == ticket_sha256_digest(raw_ticket)
        assert issued["expires_in"] == int(MAX_TICKET_TTL_SECONDS)

        # 4. SHA-256-only ticket-key storage: raw ticket NEVER appears in Redis keys or data
        redis_key = runtime_a.ticket_store.ticket_key_from_digest(digest)
        all_keys = await redis_client.keys("*")
        assert all(raw_ticket not in k for k in all_keys)
        assert redis_key in all_keys

        # 5. Actual Redis TTL enforcement
        pttl = await redis_client.pttl(redis_key)
        assert 0 < pttl <= int(MAX_TICKET_TTL_SECONDS * 1000)

        # Verify Redis itself expires a short-lived ticket without an application read.
        short_lived = await runtime_a.issue_spectator_ticket(
            user_id=f"user-expiry-{run_id}",
            display_name="ExpiryProbe",
            scope_type="match",
            scope_id=f"match-expiry-{run_id}",
            ttl_seconds=0.15,
        )
        short_key = runtime_a.ticket_store.ticket_key_from_digest(short_lived["ticket_digest"])
        assert 0 < await redis_client.pttl(short_key) <= 150
        await asyncio.sleep(0.20)
        assert await redis_client.exists(short_key) == 0

        # 7. Scope validation without burning ticket on invalid scope probe
        wrong_match = await runtime_b.redeem_spectator_ticket(
            raw_ticket,
            expected_scope_type="match",
            expected_scope_id="wrong-match-999",
        )
        assert wrong_match is None
        # Verify ticket key still exists in Redis with positive TTL
        assert await redis_client.exists(redis_key) == 1

        wrong_type = await runtime_b.redeem_spectator_ticket(
            raw_ticket,
            expected_scope_type="tournament",
            expected_scope_id=f"match-real-{run_id}",
        )
        assert wrong_type is None
        assert await redis_client.exists(redis_key) == 1

        # 2. Redemption by runtime B using the same Redis service
        redeemed = await runtime_b.redeem_spectator_ticket(
            raw_ticket,
            expected_scope_type="match",
            expected_scope_id=f"match-real-{run_id}",
        )
        assert redeemed is not None
        assert redeemed.user_id == f"user-real-redis-{run_id}"
        assert redeemed.display_name == "RedisSupporter"

        # Atomically deleted upon redemption
        assert await redis_client.exists(redis_key) == 0

        # Anti-replay: subsequent redemption attempts return None
        replayed = await runtime_a.redeem_spectator_ticket(
            raw_ticket,
            expected_scope_type="match",
            expected_scope_id=f"match-real-{run_id}",
        )
        assert replayed is None

        # 3. Atomic concurrent redemption across 20 simultaneous racers: exactly one winner
        issued_concurrent = await runtime_a.issue_spectator_ticket(
            user_id=f"user-race-{run_id}",
            display_name="ConcurrencyRacer",
            scope_type="match",
            scope_id=f"match-race-{run_id}",
        )
        race_ticket = issued_concurrent["ticket"]

        race_results = await asyncio.gather(
            *(
                runtime_b.redeem_spectator_ticket(
                    race_ticket,
                    expected_scope_type="match",
                    expected_scope_id=f"match-race-{run_id}",
                )
                for _ in range(20)
            )
        )
        winners = [r for r in race_results if r is not None]
        assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}"
        assert winners[0].user_id == f"user-race-{run_id}"
        assert winners[0].display_name == "ConcurrencyRacer"

        # 8. Deterministic sliding-window semantics: expired entries leave the window.
        rl_user = f"user-sliding-window-rl-{run_id}"
        rate_window_ms = 10_000
        rate_t0 = int(time.time() * 1000) + 100_000
        rl_allowed_1 = await runtime_a.ticket_store.check_issuance_rate_limit(
            rl_user, max_tickets=2, window_seconds=10.0, now_ms=rate_t0
        )
        rl_allowed_2 = await runtime_a.ticket_store.check_issuance_rate_limit(
            rl_user, max_tickets=2, window_seconds=10.0, now_ms=rate_t0 + 1_000
        )
        rl_blocked_3 = await runtime_a.ticket_store.check_issuance_rate_limit(
            rl_user, max_tickets=2, window_seconds=10.0, now_ms=rate_t0 + 2_000
        )
        assert rl_allowed_1 is True
        assert rl_allowed_2 is True
        assert rl_blocked_3 is False

        # Advance beyond the first request's expiry but keep the second request in-window.
        rl_allowed_after_expiry = await runtime_a.ticket_store.check_issuance_rate_limit(
            rl_user, max_tickets=2, window_seconds=10.0, now_ms=rate_t0 + rate_window_ms + 1
        )
        assert rl_allowed_after_expiry is True
        rl_key = runtime_a.ticket_store.rate_limit_key(rl_user)
        assert await redis_client.zcard(rl_key) == 2
        assert await redis_client.pttl(rl_key) > 0
        entries = await redis_client.zrange(rl_key, 0, -1, withscores=True)
        retained_scores = {int(score) for _, score in entries}
        assert retained_scores == {rate_t0 + 1_000, rate_t0 + rate_window_ms + 1}

        # 9. Redis outage and fail-closed behaviour
        class OutageRedisClient:
            async def eval(self, *args, **kwargs):
                raise RedisError("Connection refused by Redis cluster")

        outage_runtime = BroadcastRuntime(
            redis_url=None,
            ticket_redis_client=OutageRedisClient(),
            require_redis_tickets=True,
        )
        # Issuance raises SpectatorTicketStoreError (fails closed)
        with pytest.raises(SpectatorTicketStoreError):
            await outage_runtime.issue_spectator_ticket(
                user_id="u-fail",
                display_name="FailUser",
                scope_type="match",
                scope_id="match-fail",
            )
        # Redemption returns None (fails closed)
        fail_closed_redemption = await outage_runtime.redeem_spectator_ticket(
            "dummy_ticket",
            expected_scope_type="match",
            expected_scope_id="match-fail",
        )
        assert fail_closed_redemption is None

        await redis_client.aclose()

    asyncio.run(_run_lifecycle())


def test_fake_redis_spectator_ticket_store_compatibility() -> None:
    """Optional FakeRedis compatibility check; not a substitute for the live Redis gate."""
    fake_redis = pytest.importorskip("fakeredis.aioredis")
    pytest.importorskip("lupa")
    redis_client = fake_redis.FakeRedis(decode_responses=True)
    runtime_a = BroadcastRuntime(
        redis_url=None,
        ticket_redis_client=redis_client,
        require_redis_tickets=True,
    )
    runtime_b = BroadcastRuntime(
        redis_url=None,
        ticket_redis_client=redis_client,
        require_redis_tickets=True,
    )

    async def _run_fake_compatibility() -> None:
        try:
            issued = await runtime_a.issue_spectator_ticket(
                user_id="fake-redis-compat-user",
                display_name="FakeRedisCompatibility",
                scope_type="match",
                scope_id="fake-redis-compat-match",
            )
            redeemed = await runtime_b.redeem_spectator_ticket(
                issued["ticket"],
                expected_scope_type="match",
                expected_scope_id="fake-redis-compat-match",
            )
            assert redeemed is not None
            assert redeemed.user_id == "fake-redis-compat-user"
        finally:
            await redis_client.aclose()

    asyncio.run(_run_fake_compatibility())
