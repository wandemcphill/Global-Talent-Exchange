from __future__ import annotations


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_policy_documents_seeded_on_startup(client) -> None:
    response = client.get("/policies/documents")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["document_key"] == "terms-and-conditions" for item in payload)
    terms = next(item for item in payload if item["document_key"] == "terms-and-conditions")
    assert terms["latest_version"]["version_label"] == "v1.0"


def test_policy_document_detail_returns_seeded_markdown(client) -> None:
    response = client.get("/policies/documents/privacy-policy")
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_key"] == "privacy-policy"
    assert "Privacy Policy" in payload["body_markdown"]


def test_authenticated_user_can_accept_policy_and_list_acceptances(client, demo_seed, demo_user_credentials) -> None:
    headers = _login(client, email=demo_user_credentials["email"], password=demo_user_credentials["password"])
    accept_response = client.post(
        "/policies/acceptances",
        headers=headers,
        json={
            "document_key": "terms-and-conditions",
            "version_label": "v1.0",
            "ip_address": "127.0.0.1",
            "device_id": "test-device-1",
        },
    )
    assert accept_response.status_code == 200, accept_response.text
    acceptance = accept_response.json()
    assert acceptance["document_key"] == "terms-and-conditions"
    assert acceptance["version_label"] == "v1.0"

    list_response = client.get("/policies/me/acceptances", headers=headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["document_key"] == "terms-and-conditions" for item in listed)


def test_admin_can_publish_new_policy_version(client) -> None:
    headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    response = client.post(
        "/admin/policies/documents",
        headers=headers,
        json={
            "document_key": "creator-policy",
            "title": "Creator Policy",
            "version_label": "v1.0",
            "body_markdown": "# Creator Policy\n\nCreators must follow disclosure and brand-safety rules.",
            "changelog": "Initial version.",
            "is_mandatory": False,
            "active": True,
            "is_published": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["document_key"] == "creator-policy"
    assert payload["latest_version"]["version_label"] == "v1.0"

    fetch_response = client.get("/policies/documents/creator-policy")
    assert fetch_response.status_code == 200
    assert "brand-safety" in fetch_response.json()["body_markdown"]


def test_country_policy_falls_back_to_global(client) -> None:
    response = client.get("/policies/country/CA")
    assert response.status_code == 200
    payload = response.json()
    assert payload["country_code"] == "GLOBAL"
    assert payload["market_trading_enabled"] is True



def test_policy_requirements_and_compliance_status(client, demo_seed, demo_user_credentials) -> None:
    headers = _login(client, email=demo_user_credentials["email"], password=demo_user_credentials["password"])
    requirements_response = client.get("/policies/me/requirements", headers=headers)
    assert requirements_response.status_code == 200, requirements_response.text
    requirements = requirements_response.json()
    assert len(requirements) >= 1

    compliance_response = client.get("/policies/me/compliance", headers=headers)
    assert compliance_response.status_code == 200, compliance_response.text
    compliance = compliance_response.json()
    assert compliance["can_deposit"] is False
    assert compliance["required_policy_acceptances_missing"] >= 1


def test_region_profile_exposes_policy_state(client, demo_seed, demo_user_credentials) -> None:
    headers = _login(client, email=demo_user_credentials["email"], password=demo_user_credentials["password"])
    response = client.get("/policies/me/region", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["current_region"] == payload["region_code"]
    assert "next_change_eligible_at" in payload
    assert "permanent_change_used" in payload
    assert "locked" in payload


def test_admin_can_upsert_country_feature_policy(client) -> None:
    headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    response = client.post(
        "/admin/policies/country-policies",
        headers=headers,
        json={
            "country_code": "GH",
            "bucket_type": "default",
            "deposits_enabled": True,
            "market_trading_enabled": True,
            "platform_reward_withdrawals_enabled": False,
            "user_hosted_gift_withdrawals_enabled": False,
            "gtex_competition_gift_withdrawals_enabled": False,
            "national_reward_withdrawals_enabled": False,
            "one_time_region_change_after_days": 365,
            "active": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["country_code"] == "GH"
    assert payload["one_time_region_change_after_days"] == 365

    list_response = client.get("/admin/policies/country-policies", headers=headers)
    assert list_response.status_code == 200, list_response.text
    listed = list_response.json()
    assert any(item["country_code"] == "GH" for item in listed)
