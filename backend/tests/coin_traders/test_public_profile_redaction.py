from __future__ import annotations

SECRET_ACCOUNT = "0123456789"
FORBIDDEN_PUBLIC_KEYS = {
    "bank_accounts",
    "verification_reference",
    "verification_provider",
    "metadata_json",
    "liquidity_snapshot",
    "suspended_at",
    "user_id",
}


def _apply_and_approve(client, user, admin_headers) -> str:
    response = client.post(
        "/api/coin-traders/apply",
        headers=user["headers"],
        json={
            "display_name": "Redaction Desk",
            "country_code": "NG",
            "terms": {"note": "public terms"},
            "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
            "bank_accounts": [{"bank": "GTBank", "account_number": SECRET_ACCOUNT, "account_name": "Secret Name"}],
            "metadata_json": {"internal": "do-not-leak"},
        },
    )
    assert response.status_code == 201, response.text
    profile_id = response.json()["id"]
    approval = client.post(
        f"/api/admin/coin-traders/{profile_id}/approve",
        headers=admin_headers,
        json={"tier": "bronze", "note": "internal approval note"},
    )
    assert approval.status_code == 200, approval.text
    return profile_id


def test_public_marketplace_never_exposes_bank_details_or_internal_fields(
    client, auth_user_factory, bootstrap_admin_headers
) -> None:
    user = auth_user_factory(suffix="redaction-desk")
    profile_id = _apply_and_approve(client, user, bootstrap_admin_headers)

    listing = client.get("/api/coin-traders")  # unauthenticated
    assert listing.status_code == 200, listing.text
    detail = client.get(f"/api/coin-traders/{profile_id}")
    assert detail.status_code == 200, detail.text

    for payload in (*listing.json(), detail.json()):
        assert not (FORBIDDEN_PUBLIC_KEYS & set(payload)), set(payload) & FORBIDDEN_PUBLIC_KEYS
    raw = listing.text + detail.text
    assert SECRET_ACCOUNT not in raw
    assert "Secret Name" not in raw
    assert "do-not-leak" not in raw
    assert "internal approval note" not in raw
    assert detail.json()["payment_methods"] == ["Bank transfer"]


def test_owner_still_sees_full_profile_but_applicants_are_not_listed(
    client, auth_user_factory, bootstrap_admin_headers
) -> None:
    user = auth_user_factory(suffix="redaction-owner")
    applied = client.post(
        "/api/coin-traders/apply",
        headers=user["headers"],
        json={
            "display_name": "Pending Desk",
            "country_code": "NG",
            "payment_methods": [],
            "bank_accounts": [{"bank": "GTBank", "account_number": SECRET_ACCOUNT}],
        },
    )
    assert applied.status_code == 201, applied.text
    assert all(p["display_name"] != "Pending Desk" for p in client.get("/api/coin-traders").json())
    mine = client.get("/api/coin-traders/me", headers=user["headers"])
    assert mine.status_code == 200
    assert mine.json()["bank_accounts"][0]["account_number"] == SECRET_ACCOUNT
