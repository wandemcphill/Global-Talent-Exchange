from __future__ import annotations


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_public_catalog_and_pricing_are_seeded(client) -> None:
    gift_response = client.get("/economy/gift-catalog")
    assert gift_response.status_code == 200, gift_response.text
    gifts = gift_response.json()
    assert any(item["key"] == "cheer-burst" for item in gifts)

    pricing_response = client.get("/economy/service-pricing")
    assert pricing_response.status_code == 200, pricing_response.text
    rules = pricing_response.json()
    assert any(item["service_key"] == "premium-video-view" for item in rules)


def test_admin_can_upsert_catalog_and_pricing(client) -> None:
    headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")

    gift_response = client.post(
        "/admin/economy/gift-catalog",
        headers=headers,
        json={
            "key": "goal-thunder",
            "display_name": "Goal Thunder",
            "tier": "epic",
            "fancoin_price": "275.0000",
            "animation_key": "goal_thunder",
            "sound_key": "stadium_thunder",
            "description": "Epic gift for late winners and knockout drama.",
            "active": True,
        },
    )
    assert gift_response.status_code == 200, gift_response.text
    assert gift_response.json()["tier"] == "epic"

    pricing_response = client.post(
        "/admin/economy/service-pricing",
        headers=headers,
        json={
            "service_key": "creator-campaign-slot",
            "title": "Creator Campaign Slot",
            "description": "Boost creator-hosted competition discoverability.",
            "price_coin": "7.5000",
            "price_fancoin_equivalent": "750.0000",
            "active": True,
        },
    )
    assert pricing_response.status_code == 200, pricing_response.text
    assert pricing_response.json()["service_key"] == "creator-campaign-slot"
