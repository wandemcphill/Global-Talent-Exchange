from __future__ import annotations

import os

from backend.tests.support.secrets import TEST_PASSWORD
from backend.tests.support.signup_payloads import user_signup_payload


def _create_competition(client, *, host: dict[str, str], name: str) -> str:
    response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": name,
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "credit",
            "capacity": 8,
            "creator_id": f"host-{name}",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _error_message(response) -> str:
    payload = response.json()
    return payload.get("message") or payload.get("detail")


def _register_user(client, *, suffix: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email=f"{suffix}@example.com",
            username=suffix.replace("-", "_"),
            password=TEST_PASSWORD,
            full_name=f"User {suffix}",
        ),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return (
        {"Authorization": f"Bearer {payload['access_token']}"},
        payload["user"]["id"],
    )


def _bootstrap_admin_headers(client) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={
            "email": os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"],
            "password": os.environ["GTE_BOOTSTRAP_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_scoped_admin_headers(
    client,
    *,
    suffix: str,
    permissions: list[str],
) -> dict[str, str]:
    password = TEST_PASSWORD
    email = f"{suffix}@example.com"
    username = suffix.replace("-", "_")
    response = client.post(
        "/api/admin/access",
        headers=_bootstrap_admin_headers(client),
        json={
            "email": email,
            "username": username,
            "password": password,
            "display_name": f"Scoped {suffix}",
            "permissions": permissions,
        },
    )
    assert response.status_code == 201, response.text

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_authenticated_join_rejects_payload_user_spoofing(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="join-auth-host")
    entrant = auth_user_factory(suffix="join-auth-user")
    competition_id = _create_competition(client, host=host, name="join-auth-guard")

    response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": "someone-else"},
    )

    assert response.status_code == 403
    assert _error_message(response) == "Authenticated user does not match competition join payload."


def test_anonymous_join_is_rejected(client, competition_admin_headers, auth_user_factory) -> None:
    host = auth_user_factory(suffix="join-anon-host")
    competition_id = _create_competition(client, host=host, name="join-anon-blocked")

    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200, publish.text

    response = client.post(
        f"/api/competitions/{competition_id}/join",
        json={"user_id": "anonymous-user"},
    )

    assert response.status_code == 401
    assert _error_message(response) == "Authentication credentials were not provided."


def test_authenticated_scoped_admin_without_manage_competitions_cannot_publish_or_launch(
    client,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="publish-auth-host")
    competition_id = _create_competition(client, host=host, name="publish-auth-guard")
    headers = _create_scoped_admin_headers(
        client,
        suffix="competition-blocked-admin",
        permissions=[],
    )

    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=headers,
        json={"open_for_join": True},
    )
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=headers,
    )

    assert publish.status_code == 403
    assert _error_message(publish) == "Permission manage_competitions is required for this action."
    assert launch.status_code == 403
    assert _error_message(launch) == "Permission manage_competitions is required for this action."


def test_anonymous_publish_is_rejected(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="publish-anon-host")
    competition_id = _create_competition(client, host=host, name="publish-anon-blocked")

    response = client.post(
        f"/api/competitions/{competition_id}/publish",
        json={"open_for_join": True},
    )

    assert response.status_code == 401
    assert _error_message(response) == "Authentication credentials were not provided."


def test_authenticated_scoped_admin_with_manage_competitions_can_publish(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="publish-live-host")
    competition_id = _create_competition(client, host=host, name="publish-auth-live")
    headers = _create_scoped_admin_headers(
        client,
        suffix="competition-live-admin",
        permissions=["manage_competitions"],
    )

    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=headers,
        json={"open_for_join": True},
    )

    assert publish.status_code == 200, publish.text
    assert publish.json()["status"] == "open"


def test_anonymous_launch_is_rejected(client, competition_admin_headers, auth_user_factory) -> None:
    host = auth_user_factory(suffix="launch-anon-host")
    competition_id = _create_competition(client, host=host, name="launch-anon-blocked")
    entrant_a = auth_user_factory(suffix="launch-anon-a")
    entrant_b = auth_user_factory(suffix="launch-anon-b")

    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200, publish.text

    for entrant in (entrant_a, entrant_b):
        joined = client.post(
            f"/api/competitions/{competition_id}/join",
            headers=entrant["headers"],
            json={"user_id": entrant["user_id"]},
        )
        assert joined.status_code == 200, joined.text

    seed = client.post(
        f"/api/competitions/{competition_id}/seed",
        headers=competition_admin_headers,
        json={"seed_method": "random"},
    )
    assert seed.status_code == 200, seed.text

    response = client.post(f"/api/competitions/{competition_id}/launch")

    assert response.status_code == 401
    assert _error_message(response) == "Authentication credentials were not provided."
