from __future__ import annotations

from datetime import date
from uuid import uuid4

from backend.tests.support.secrets import TEST_PASSWORD
from app.admin_godmode.service import REGEN_OPS_ADMIN_ROLE_NAME


def _create_scoped_admin_headers(
    client,
    bootstrap_admin_headers: dict[str, str],
    *,
    role_name: str,
) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"{role_name}-{suffix}@example.com"
    username = f"{role_name}_{suffix}".replace("-", "_")
    response = client.post(
        "/api/admin/access",
        headers=bootstrap_admin_headers,
        json={
            "email": email,
            "username": username,
            "password": TEST_PASSWORD,
            "display_name": f"Scoped {role_name} {suffix}",
            "role_name": role_name,
            "permissions": [],
        },
    )
    assert response.status_code == 201, response.text

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_inactive_regen_season(client, headers: dict[str, str]) -> str:
    season_number = 100_000 + int(uuid4().hex[:6], 16)
    response = client.post(
        "/admin/regen-universe/seasons",
        headers=headers,
        json={
            "season_number": season_number,
            "start_date": date(2032, 1, 1).isoformat(),
            "end_date": date(2032, 12, 31).isoformat(),
            "is_active": False,
            "source_ingestion_season_ids": [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_super_admin_can_run_regen_admin_routes(client, bootstrap_admin_headers) -> None:
    season_id = _create_inactive_regen_season(client, bootstrap_admin_headers)

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=bootstrap_admin_headers,
        json={
            "country_codes": ["NG"],
            "age_band": "u17",
            "preseed_batch": f"rbac-super-{uuid4().hex[:8]}",
        },
    )
    assert preseed_response.status_code == 201, preseed_response.text
    preseed_payload = preseed_response.json()
    assert preseed_payload["summary"] is not None
    assert preseed_payload["summary"]["created"] + preseed_payload["summary"]["skipped_existing"] >= 1

    story_job_response = client.post(
        "/admin/regen-universe/jobs/story-regeneration",
        headers=bootstrap_admin_headers,
    )
    assert story_job_response.status_code in {200, 202}, story_job_response.text
    assert story_job_response.json()["name"] == "regen_universe.story_regeneration"

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season_id}/close",
        headers=bootstrap_admin_headers,
        json={"start_next_season": False},
    )
    assert close_response.status_code == 200, close_response.text
    assert close_response.json()["season_id"] == season_id


def test_regen_ops_admin_can_preseed_national_regens_and_close_seasons(
    client,
    bootstrap_admin_headers,
) -> None:
    regen_ops_headers = _create_scoped_admin_headers(
        client,
        bootstrap_admin_headers,
        role_name=REGEN_OPS_ADMIN_ROLE_NAME,
    )
    season_id = _create_inactive_regen_season(client, bootstrap_admin_headers)

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=regen_ops_headers,
        json={
            "country_codes": ["GH"],
            "age_band": "u20",
            "preseed_batch": f"rbac-regen-ops-{uuid4().hex[:8]}",
        },
    )
    assert preseed_response.status_code == 201, preseed_response.text

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season_id}/close",
        headers=regen_ops_headers,
        json={"start_next_season": False},
    )
    assert close_response.status_code == 200, close_response.text
    assert close_response.json()["season_id"] == season_id


def test_support_admin_cannot_preseed_or_close_regen_seasons(
    client,
    bootstrap_admin_headers,
) -> None:
    support_headers = _create_scoped_admin_headers(
        client,
        bootstrap_admin_headers,
        role_name="support_admin",
    )
    season_id = _create_inactive_regen_season(client, bootstrap_admin_headers)

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=support_headers,
        json={
            "country_codes": ["SN"],
            "age_band": "senior",
            "preseed_batch": f"rbac-support-{uuid4().hex[:8]}",
        },
    )
    assert preseed_response.status_code == 403
    assert preseed_response.json()["message"] == "Permission manage_national_regens is required for this action."

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season_id}/close",
        headers=support_headers,
        json={"start_next_season": False},
    )
    assert close_response.status_code == 403
    assert close_response.json()["message"] == "Permission manage_regen_universe is required for this action."
