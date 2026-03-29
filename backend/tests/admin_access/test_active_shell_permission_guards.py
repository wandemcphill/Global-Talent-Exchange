from __future__ import annotations

import os


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
    password = "SuperSecret1"
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


def test_scoped_admin_without_catalog_permission_cannot_open_real_player_import_status(
    client,
) -> None:
    headers = _create_scoped_admin_headers(
        client,
        suffix="catalog-blocked-admin",
        permissions=[],
    )

    response = client.get(
        "/internal/ingestion/real-players/status",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission manage_manager_catalog is required for this action."
    }


def test_scoped_admin_with_catalog_permission_can_open_real_player_import_status(
    client,
) -> None:
    headers = _create_scoped_admin_headers(
        client,
        suffix="catalog-live-admin",
        permissions=["manage_manager_catalog"],
    )

    response = client.get(
        "/internal/ingestion/real-players/status",
        headers=headers,
    )

    assert response.status_code == 200, response.text


def test_scoped_admin_without_supply_permission_cannot_issue_share_market(
    client,
) -> None:
    headers = _create_scoped_admin_headers(
        client,
        suffix="supply-blocked-admin",
        permissions=["manage_manager_catalog"],
    )

    response = client.post(
        "/players/nonexistent-player/shares/issue",
        headers=headers,
        json={
            "total_shares": 1000,
            "share_price_coin": 10,
            "status": "active",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Permission manage_manager_supply is required for this action."
    }


def test_scoped_admin_with_supply_permission_reaches_share_issue_handler(client) -> None:
    headers = _create_scoped_admin_headers(
        client,
        suffix="supply-live-admin",
        permissions=["manage_manager_supply"],
    )

    response = client.post(
        "/players/nonexistent-player/shares/issue",
        headers=headers,
        json={
            "total_shares": 1000,
            "share_price_coin": 10,
            "status": "active",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]
