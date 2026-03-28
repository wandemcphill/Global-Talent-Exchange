from __future__ import annotations

from datetime import datetime, timezone
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.auth.service import AuthService
from app.live_matches.service import ensure_live_match_hub
from app.main import create_app
from app.models.base import generate_uuid
from app.models.manager_market import ManagerCatalogEntry, ManagerHolding, ManagerTeamAssignment
from app.models.user import User


def _create_authenticated_user(app, *, email: str, username: str, display_name: str) -> tuple[User, dict[str, str]]:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password="SuperSecret1",
            display_name=display_name,
        )
        token, _ = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
        return user, {"Authorization": f"Bearer {token}"}


def _seed_manager(app, *, owner_user_id: str, manager_id: str, display_name: str) -> None:
    with app.state.session_factory() as session:
        session.add(
            ManagerCatalogEntry(
                manager_id=manager_id,
                display_name=display_name,
                rarity="elite",
                mentality="attacking",
                tactics=["high_press_attack", "counter_attack"],
                traits=["tactical_flexibility", "great_motivator"],
                substitution_tendency="balanced_substitution",
                philosophy_summary=f"{display_name} drives human-led tactical execution.",
                club_associations=[],
                supply_total=1,
                supply_available=0,
            )
        )
        asset_id = generate_uuid()
        session.add(
            ManagerHolding(
                asset_id=asset_id,
                manager_id=manager_id,
                owner_user_id=owner_user_id,
                status="owned",
                acquired_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.add(
            ManagerTeamAssignment(
                user_id=owner_user_id,
                main_manager_asset_id=asset_id,
                academy_manager_asset_id=None,
            )
        )
        session.commit()


def _wait_for_completion(client: TestClient, duel_id: str, *, timeout_seconds: float = 5.0) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    payload: dict[str, object] = {}
    while time.time() < deadline:
        response = client.get(f"/api/manager-duels/{duel_id}")
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] == "completed":
            return payload
        time.sleep(0.1)
    return payload


def test_manager_duel_live_spectate_highlights_and_leaderboard(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'manager_duels.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        ensure_live_match_hub(app, step_interval_seconds=0.1)
        home_user, home_headers = _create_authenticated_user(
            app,
            email="home-duel@example.com",
            username="home_duel",
            display_name="Home Duelist",
        )
        away_user, _away_headers = _create_authenticated_user(
            app,
            email="away-duel@example.com",
            username="away_duel",
            display_name="Away Duelist",
        )
        spectator_user, spectator_headers = _create_authenticated_user(
            app,
            email="spectator-duel@example.com",
            username="spectator_duel",
            display_name="Spectator Duelist",
        )
        _seed_manager(app, owner_user_id=home_user.id, manager_id="home-manager", display_name="Home Manager")
        _seed_manager(app, owner_user_id=away_user.id, manager_id="away-manager", display_name="Away Manager")

        duel_response = client.post(
            "/api/manager-duels",
            headers=home_headers,
            json={
                "home_user_id": home_user.id,
                "away_user_id": away_user.id,
                "simulation_seed": 4,
            },
        )
        assert duel_response.status_code == 201, duel_response.text
        duel_payload = duel_response.json()
        duel_id = duel_payload["id"]
        assert duel_payload["competition_type"] == "manager_duel"
        assert duel_payload["controller_home"] == "manager"
        assert duel_payload["controller_away"] == "manager"
        assert duel_payload["user_control_enabled"] is False

        spectate_response = client.post(
            f"/api/matches/{duel_id}/spectate",
            headers=spectator_headers,
        )
        assert spectate_response.status_code == 200, spectate_response.text
        spectate_payload = spectate_response.json()
        assert spectate_payload["user_id"] == spectator_user.id
        assert spectate_payload["read_only"] is True
        assert spectate_payload["channel"] == f"match:{duel_id}"
        assert spectate_payload["sync_strategy"] == "deterministic_playback"
        assert spectate_payload["watch_party_enabled"] is True
        assert spectate_payload["reactions_enabled"] is True
        assert spectate_payload["commentary_websocket_path"].endswith(f"/api/matches/{duel_id}/commentary/stream?session_id={spectate_payload['id']}")
        assert spectate_payload["tts_websocket_path"] == "/tts/live?voice=default"

        websocket_path = spectate_payload["websocket_path"]
        with client.websocket_connect(websocket_path) as websocket:
            first_message = websocket.receive_json()
            assert first_message["channel"] == f"match:{duel_id}"
            assert first_message["kind"] == "snapshot"
            assert {"home", "draw", "away"} <= set(
                first_message["payload"]["win_probability"].keys()
            )
            assert {"home_line", "draw_line", "away_line", "volatility", "tension"} <= set(
                first_message["payload"]["market_pulse"].keys()
            )
            saw_event_batch = False
            for _ in range(20):
                message = websocket.receive_json()
                if message["kind"] == "events":
                    assert isinstance(message["payload"], list)
                    assert message["payload"][0]["experience"]["motion"]["model_key"] == "gtex_motion_blend_v1"
                    assert message["payload"][0]["experience"]["commentary"]["tts_ready"] is True
                    assert message["payload"][0]["experience"]["crowd"]["profile"]
                    assert message["payload"][0]["experience"]["spectator_sync"]["sync_strategy"] == "deterministic_playback"
                    saw_event_batch = True
                    break
            assert saw_event_batch is True

        with client.websocket_connect(spectate_payload["commentary_websocket_path"]) as commentary_socket:
            first_commentary = commentary_socket.receive_json()
            assert first_commentary["kind"] == "commentary_snapshot"
            saw_commentary = False
            for _ in range(20):
                message = commentary_socket.receive_json()
                if message["kind"] == "commentary":
                    assert isinstance(message["payload"], list)
                    assert message["payload"][0]["line"]
                    assert message["payload"][0]["cue"]["tts_ready"] is True
                    saw_commentary = True
                    break
            assert saw_commentary is True

        completed_payload = _wait_for_completion(client, duel_id)
        assert completed_payload["status"] == "completed"
        assert completed_payload["live_state"]["is_live"] is False
        assert completed_payload["live_state"]["crowd_state"]["profile"]
        assert completed_payload["live_state"]["spectator_sync"]["sync_strategy"] == "deterministic_playback"
        assert {"home", "draw", "away"} <= set(
            completed_payload["live_state"]["snapshot"]["win_probability"].keys()
        )
        assert completed_payload["live_state"]["snapshot"]["market_pulse"]["home_line"] > 0

        commentary_response = client.get(
            f"/api/matches/{duel_id}/commentary",
            params={"tone": "hype", "voice_enabled": True},
        )
        assert commentary_response.status_code == 200, commentary_response.text
        commentary_payload = commentary_response.json()
        assert commentary_payload["match_id"] == duel_id
        assert commentary_payload["tone"] == "hype"
        assert commentary_payload["voice_enabled"] is True
        assert commentary_payload["events"]
        assert commentary_payload["events"][0]["voice"]["status"] == "not_configured"

        highlights_response = client.get(f"/api/matches/{duel_id}/highlights")
        assert highlights_response.status_code == 200, highlights_response.text
        highlights_payload = highlights_response.json()
        assert highlights_payload["highlights"]
        assert {"minute", "type", "description"} <= set(highlights_payload["highlights"][0].keys())

        leaderboard_response = client.get("/api/manager-duels/leaderboard")
        assert leaderboard_response.status_code == 200, leaderboard_response.text
        leaderboard_payload = leaderboard_response.json()
        assert {item["manager_id"] for item in leaderboard_payload} & {"home-manager", "away-manager"}
        assert all(item["matches_played"] >= 0 for item in leaderboard_payload)

        notifications_response = client.get("/api/notifications/me", headers=home_headers)
        assert notifications_response.status_code == 200, notifications_response.text
        template_keys = {item["template_key"] for item in notifications_response.json()}
        assert "COMMENTARY_HIGHLIGHT" in template_keys
        assert "LIVE_MATCH_STARTED" in template_keys
        assert "HIGHLIGHTS_READY" in template_keys
    engine.dispose()
