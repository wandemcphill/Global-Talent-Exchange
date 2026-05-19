from __future__ import annotations

from uuid import uuid4

from backend.tests.support.secrets import TEST_PASSWORD
from backend.tests.support.signup_payloads import user_signup_payload
from app.admin_godmode.runtime_paths import admin_godmode_state_path
from app.models.admin_runtime_state import AdminRuntimeState


def _suffix(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _register_user(client, *, prefix: str) -> dict[str, object]:
    email = f"{_suffix(prefix)}@example.com"
    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email=email,
            username=email.split("@", maxsplit=1)[0].replace("-", "_"),
            full_name=f"{prefix.title()} User",
            password=TEST_PASSWORD,
        ),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["headers"] = {"Authorization": f"Bearer {payload['access_token']}"}
    return payload


def test_creator_owned_gtex_hosted_competition_can_publish_without_admin_permission(client) -> None:
    host = _register_user(client, prefix="gtex-hosted-owner")

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Creator Hosted Publish",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user"]["id"],
            "creator_name": "Host Club",
            "source_type": "gtex_hosted",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules": "Owner-hosted publish and launch should not require admin competition permission.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["status"] == "open"


def test_creator_owned_gtex_hosted_launch_is_not_blocked_by_admin_permission_gate(client) -> None:
    host = _register_user(client, prefix="gtex-hosted-launch-owner")

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Creator Hosted Launch Gate",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user"]["id"],
            "creator_name": "Host Club",
            "source_type": "gtex_hosted",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules": "This regression only asserts the launch request is not blocked by the admin permission gate.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    launch_response = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=host["headers"],
    )

    assert launch_response.status_code != 403, launch_response.text


def test_non_owner_still_cannot_publish_someone_elses_gtex_hosted_competition(client) -> None:
    host = _register_user(client, prefix="gtex-hosted-owner-block")
    intruder = _register_user(client, prefix="gtex-hosted-intruder")

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Creator Hosted Publish Guard",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user"]["id"],
            "creator_name": "Host Club",
            "source_type": "gtex_hosted",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules": "Only the owner should bypass admin competition permission here.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=intruder["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 403
    assert publish_response.json()["message"] == "Admin access is required for this action."


def test_bootstrap_super_admin_can_publish_platform_competition_without_runtime_state(
    client,
    app_session_factory,
    bootstrap_admin_headers,
) -> None:
    host = _register_user(client, prefix="platform-competition-host")

    with app_session_factory() as session:
        session.query(AdminRuntimeState).delete()
        session.commit()

    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    if state_path.exists():
        state_path.unlink()

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Platform Competition Root Publish",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user"]["id"],
            "creator_name": "Host Club",
            "source_type": "gtex",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules": "Bootstrap super admin should publish this even when runtime admin state is absent.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=bootstrap_admin_headers,
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["status"] == "open"


def test_competition_ops_admin_created_via_admin_access_can_publish_with_stale_db_runtime_state(
    client,
    app_session_factory,
    bootstrap_admin_headers,
) -> None:
    host = _register_user(client, prefix="scoped-admin-platform-host")

    with app_session_factory() as session:
        session.query(AdminRuntimeState).delete()
        session.add(AdminRuntimeState(state_key="admin_god_mode", payload_json={}))
        session.commit()

    state_path = admin_godmode_state_path(client.app.state.settings.config_root)
    if state_path.exists():
        state_path.unlink()

    create_admin_response = client.post(
        "/api/admin/access",
        headers=bootstrap_admin_headers,
        json={
            "email": "scoped-competition-admin@example.com",
            "username": "scoped_competition_admin",
            "password": TEST_PASSWORD,
            "display_name": "Scoped Competition Admin",
            "role_name": "competition_ops_admin",
            "permissions": [],
        },
    )
    assert create_admin_response.status_code == 201, create_admin_response.text
    create_admin_payload = create_admin_response.json()
    assert create_admin_payload["admin_role_name"] == "competition_ops_admin"
    assert sorted(create_admin_payload["permissions"]) == ["manage_competitions", "view_audit_log"]

    admin_login = client.post(
        "/auth/login",
        json={
            "email": "scoped-competition-admin@example.com",
            "password": TEST_PASSWORD,
        },
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    create_response = client.post(
        "/api/competitions/create",
        headers=host["headers"],
        json={
            "name": "Scoped Admin Platform Publish",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user"]["id"],
            "creator_name": "Host Club",
            "source_type": "gtex",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules": "This captures the remaining stale DB runtime-state blocker for scoped admins.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=admin_headers,
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["status"] == "open"
