from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.broadcast.broadcast_models import ScoreUpdate, SpectatorEvent, TournamentEvent
from app.broadcast.spectator_gateway import BroadcastRuntime, router


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
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
