from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService
from app.main import create_app
from app.models.user import UserRole
from backend.tests.match_engine.helpers import build_team


@pytest.fixture()
def app_client(monkeypatch):
    monkeypatch.setenv("GTE_COMPETITIVE_INTEGRITY_WORKER_ENABLED", "0")
    temp_root = Path(__file__).resolve().parents[2] / ".tmp_testdbs"
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = temp_root / f"competitive_integrity_api_{uuid4().hex}.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    try:
        with TestClient(app) as client:
            yield app, client
    finally:
        engine.dispose()
        try:
            database_path.unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            pass


def _create_user(app, email: str, username: str) -> tuple[str, str]:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password=TEST_PASSWORD,
            display_name=username,
        )
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
        return user.id, token


def _create_admin(app, email: str, username: str) -> tuple[str, str]:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password=TEST_PASSWORD,
            display_name=username,
        )
        user.role = UserRole.ADMIN
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
        return user.id, token


def test_competitive_integrity_match_flow_and_notifications(app_client) -> None:
    app, client = app_client
    home_user_id, home_token = _create_user(app, "home@example.com", "home_user")
    away_user_id, _away_token = _create_user(app, "away@example.com", "away_user")
    manager_user_id, _manager_token = _create_user(app, "manager@example.com", "real_manager")

    manager_response = client.post(
        "/api/competitive-integrity/managers",
        headers={"Authorization": f"Bearer {home_token}"},
        json={
            "type": "real_manager",
            "appointed_user_id": manager_user_id,
            "instructions": {
                "formation": "4-3-3",
                "style": "possession",
                "pressing": "high",
                "rules": [
                    {"minute": 60, "condition": "always", "action": "add_striker"},
                ],
            },
            "tactical_profile": {"style": "possession", "pressing": "high"},
        },
    )
    assert manager_response.status_code == 201
    manager_id = manager_response.json()["id"]

    match_response = client.post(
        "/api/competitive-integrity/matches",
        headers={"Authorization": f"Bearer {home_token}"},
        json={
            "competition_type": "casual",
            "home_user_id": home_user_id,
            "away_user_id": away_user_id,
            "home_manager_id": manager_id,
            "is_user_online_home": False,
            "is_user_online_away": True,
            "locked_lineup_home": build_team("home-api", "Home API", 86).model_dump(mode="json"),
            "locked_lineup_away": build_team("away-api", "Away API", 74).model_dump(mode="json"),
        },
    )
    assert match_response.status_code == 201
    match_id = match_response.json()["id"]

    execute_response = client.post(
        f"/api/competitive-integrity/matches/{match_id}/execute",
        headers={"Authorization": f"Bearer {home_token}"},
        json={},
    )
    notifications_response = client.get(
        "/api/notifications",
        headers={"Authorization": f"Bearer {home_token}"},
    )

    assert execute_response.status_code == 200
    body = execute_response.json()
    assert body["controllers"] == {"home": "manager", "away": "user"}
    assert notifications_response.status_code == 200
    assert any(item["type"] == "MATCH_SCHEDULED" for item in notifications_response.json())


def test_gtex_hosted_match_rejects_frozen_control(app_client) -> None:
    app, client = app_client
    home_user_id, home_token = _create_user(app, "frozen-home@example.com", "frozen_home")
    away_user_id, _away_token = _create_user(app, "frozen-away@example.com", "frozen_away")

    match_response = client.post(
        "/api/competitive-integrity/matches",
        headers={"Authorization": f"Bearer {home_token}"},
        json={
            "competition_type": "gtex_hosted",
            "home_user_id": home_user_id,
            "away_user_id": away_user_id,
            "is_user_online_home": False,
            "is_user_online_away": True,
            "locked_lineup_home": build_team("home-hosted", "Home Hosted", 80).model_dump(mode="json"),
            "locked_lineup_away": build_team("away-hosted", "Away Hosted", 80).model_dump(mode="json"),
        },
    )
    assert match_response.status_code == 201
    match_id = match_response.json()["id"]

    execute_response = client.post(
        f"/api/competitive-integrity/matches/{match_id}/execute",
        headers={"Authorization": f"Bearer {home_token}"},
        json={},
    )

    assert execute_response.status_code == 409
    assert "appointed real manager" in execute_response.json()["detail"]


def test_admin_can_fetch_match_validation_summary(app_client) -> None:
    app, client = app_client
    home_user_id, home_token = _create_user(app, "validation-home@example.com", "validation_home")
    away_user_id, _away_token = _create_user(app, "validation-away@example.com", "validation_away")
    _admin_user_id, admin_token = _create_admin(app, "validation-admin@example.com", "validation_admin")

    match_response = client.post(
        "/api/competitive-integrity/matches",
        headers={"Authorization": f"Bearer {home_token}"},
        json={
            "competition_type": "casual",
            "home_user_id": home_user_id,
            "away_user_id": away_user_id,
            "is_user_online_home": False,
            "is_user_online_away": True,
            "locked_lineup_home": build_team("validation-home", "Validation Home", 82).model_dump(mode="json"),
            "locked_lineup_away": build_team("validation-away", "Validation Away", 78).model_dump(mode="json"),
        },
    )
    assert match_response.status_code == 201
    match_id = match_response.json()["id"]

    execute_response = client.post(
        f"/api/competitive-integrity/matches/{match_id}/execute",
        headers={"Authorization": f"Bearer {home_token}"},
        json={},
    )
    assert execute_response.status_code == 200

    validation_response = client.get(
        f"/api/admin/competitive-integrity/matches/{match_id}/validation",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert validation_response.status_code == 200, validation_response.text
    payload = validation_response.json()
    assert payload["match_id"] == match_id
    assert payload["anti_cheat_score"] <= 100
    assert payload["recommended_action"] in {"allow", "manual_review", "freeze_rewards_and_review"}
