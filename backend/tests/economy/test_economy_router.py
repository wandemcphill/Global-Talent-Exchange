from __future__ import annotations

from decimal import Decimal

from app.auth.service import AuthService
from app.economy.service import EconomyConfigService
from app.main import (
    INITIAL_ADMIN_DISPLAY_NAME,
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_PASSWORD,
)


def _prepare_economy_defaults(client) -> None:
    startup_thread = getattr(client.app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    with client.app.state.session_factory() as session:
        AuthService().ensure_admin_user(
            session,
            email=INITIAL_ADMIN_EMAIL,
            password=INITIAL_ADMIN_PASSWORD,
            username="economy-test-admin",
            display_name=INITIAL_ADMIN_DISPLAY_NAME,
        )
        EconomyConfigService(session).seed_defaults()
        session.commit()


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_public_catalog_and_pricing_are_seeded(client) -> None:
    _prepare_economy_defaults(client)

    gift_response = client.get("/economy/gift-catalog")
    assert gift_response.status_code == 200, gift_response.text
    gifts = gift_response.json()
    assert any(item["key"] == "fire" for item in gifts)
    assert any(item["key"] == "applause" for item in gifts)
    assert any(item["key"] == "crown" for item in gifts)

    pricing_response = client.get("/economy/service-pricing")
    assert pricing_response.status_code == 200, pricing_response.text
    rules = pricing_response.json()
    assert any(item["service_key"] == "premium-video-view" for item in rules)
    assert any(item["service_key"] == "competitive-match-entry" for item in rules)


def test_admin_revenue_rules_include_match_view_defaults(client) -> None:
    _prepare_economy_defaults(client)
    headers = _login(client, email=INITIAL_ADMIN_EMAIL, password=INITIAL_ADMIN_PASSWORD)

    response = client.get("/admin/economy/revenue-share-rules", headers=headers)
    assert response.status_code == 200, response.text
    rules = response.json()

    match_view_rule = next(item for item in rules if item["rule_key"] == "match-view-default")
    assert match_view_rule["platform_share_bps"] == 5000
    assert match_view_rule["creator_share_bps"] == 3000
    assert match_view_rule["recipient_share_bps"] == 2000


def test_admin_can_upsert_catalog_and_pricing(client) -> None:
    _prepare_economy_defaults(client)
    headers = _login(client, email=INITIAL_ADMIN_EMAIL, password=INITIAL_ADMIN_PASSWORD)

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


def test_admin_governor_and_fx_controls_are_available(client) -> None:
    _prepare_economy_defaults(client)
    headers = _login(client, email=INITIAL_ADMIN_EMAIL, password=INITIAL_ADMIN_PASSWORD)

    governor_response = client.post(
        "/admin/economy/governor/policy",
        headers=headers,
        json={
            "mode": "manual",
            "tournament_entry_multiplier": "1.0000",
            "match_view_cost_multiplier": "1.0000",
            "reward_payout_multiplier": "1.0000",
            "conversion_bonus_bps": 0,
            "burn_bonus_bps": 0,
        },
    )
    assert governor_response.status_code == 200, governor_response.text
    assert governor_response.json()["mode"] == "manual"

    apply_response = client.post(
        "/admin/economy/governor/apply",
        headers=headers,
        json={
            "metrics": {
                "gtex_supply": "180000.0000",
                "fan_supply": "200000.0000",
                "daily_burn": "5000.0000",
                "daily_mint": "12000.0000",
                "avg_user_spend": "35.0000",
                "inflation_rate": "0.1800",
            },
            "allow_manual_override": True,
        },
    )
    assert apply_response.status_code == 200, apply_response.text
    apply_payload = apply_response.json()
    assert Decimal(apply_payload["tournament_entry_multiplier"]) > Decimal("1.0000")
    assert int(apply_payload["burn_bonus_bps"]) >= 500

    fx_update = client.post(
        "/admin/economy/fx-rates",
        headers=headers,
        json={"currency": "GBP", "rate_to_naira": "1500.000000"},
    )
    assert fx_update.status_code == 200, fx_update.text
    assert fx_update.json()["currency"] == "GBP"

    quote_response = client.get("/economy/fx/quote", params={"gtex_amount": "1.0000", "currency": "GBP", "region_code": "EUROPE"})
    assert quote_response.status_code == 200, quote_response.text
    quote_payload = quote_response.json()
    assert Decimal(quote_payload["final_quote"]) > Decimal(quote_payload["base_quote"])
    assert quote_payload["region_code"] == "EUROPE"
