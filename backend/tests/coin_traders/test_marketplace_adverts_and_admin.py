from __future__ import annotations

from decimal import Decimal


def _fund_user(client, admin_headers, user_id: str, unit: str, amount: str) -> None:
    resp = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=admin_headers,
        json={
            "user_id": user_id,
            "unit": unit,
            "amount": amount,
            "reason": "Test marketplace funding",
            "idempotency_key": f"fund-{user_id}-{unit}-{amount}",
        },
    )
    assert resp.status_code == 201, resp.text


def _setup_approved_trader(client, auth_user_factory, admin_headers, *, suffix: str, display_name: str):
    trader = auth_user_factory(suffix=suffix)
    applied = client.post(
        "/api/coin-traders/apply",
        headers=trader["headers"],
        json={
            "display_name": display_name,
            "country_code": "NG",
            "terms": {"same_name_account_only": True, "kyc_required": False},
            "payment_methods": [{"label": "Bank Transfer", "type": "bank_transfer"}, {"label": "OPay", "type": "opay"}],
            "bank_accounts": [{"bank_name": "GTBank", "account_number": "0123456789", "account_name": display_name}],
            "metadata_json": {},
        },
    )
    assert applied.status_code == 201, applied.text
    profile_id = applied.json()["id"]
    approved = client.post(
        f"/api/admin/coin-traders/{profile_id}/approve",
        headers=admin_headers,
        json={"tier": "gold", "note": "approved for marketplace tests"},
    )
    assert approved.status_code == 200, approved.text
    return trader, profile_id


def test_empty_marketplace_truthful_empty_state(client) -> None:
    resp = client.get("/api/coin-traders/marketplace", params={"coin_unit": "coin", "side": "sell"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["offers"] == []
    assert Decimal(str(data["market_reference"]["min_p2p_buy_fiat"])) == Decimal("0.0000")
    assert Decimal(str(data["market_reference"]["platform_fee_fiat"])) == Decimal("0.0000")

    ref_resp = client.get("/api/coin-traders/market-reference")
    assert ref_resp.status_code == 200
    assert len(ref_resp.json()["assets"]) == 2


def test_advert_lifecycle_four_markets_filters_sorting_quote_and_ratings(
    client, auth_user_factory, bootstrap_admin_headers
) -> None:
    trader1, profile1_id = _setup_approved_trader(
        client, auth_user_factory, bootstrap_admin_headers, suffix="mkt-t1", display_name="Alpha Liquidity"
    )
    trader2, profile2_id = _setup_approved_trader(
        client, auth_user_factory, bootstrap_admin_headers, suffix="mkt-t2", display_name="Beta Exchange"
    )
    customer = auth_user_factory(suffix="mkt-cust")

    # Cannot publish sell advert without inventory
    no_inv = client.put(
        "/api/coin-traders/me/adverts",
        headers=trader1["headers"],
        json={
            "coin_unit": "coin",
            "fiat_currency": "NGN",
            "side": "sell",
            "pricing_mode": "fixed",
            "price_fiat": "55",
            "min_coin_amount": "1000",
            "max_coin_amount": "20000",
            "payment_window_minutes": 15,
            "payment_methods": ["Bank Transfer"],
            "status": "active",
        },
    )
    assert no_inv.status_code == 400
    assert "inventory" in no_inv.text.lower()

    # Fund traders with GTC and FNC
    _fund_user(client, bootstrap_admin_headers, trader1["user_id"], "coin", "20000")
    _fund_user(client, bootstrap_admin_headers, trader2["user_id"], "coin", "20000")
    _fund_user(client, bootstrap_admin_headers, trader1["user_id"], "credit", "50000")
    _fund_user(client, bootstrap_admin_headers, customer["user_id"], "coin", "5000")
    _fund_user(client, bootstrap_admin_headers, customer["user_id"], "credit", "30000")

    # Trader 1 publishes all 4 market adverts (GTC Sell 55, GTC Buy 49, FNC Sell 3.2, FNC Buy 2.5)
    ad_gtc_sell_1 = client.put(
        "/api/coin-traders/me/adverts",
        headers=trader1["headers"],
        json={
            "coin_unit": "coin",
            "fiat_currency": "NGN",
            "side": "sell",
            "pricing_mode": "fixed",
            "price_fiat": "55",
            "min_coin_amount": "4000",
            "max_coin_amount": "15000",
            "daily_limit_coin": "12000",
            "payment_window_minutes": 15,
            "payment_methods": ["Bank Transfer", "OPay"],
            "terms_text": "Receipts required; same-name transfers only.",
            "status": "active",
        },
    )
    assert ad_gtc_sell_1.status_code == 200, ad_gtc_sell_1.text
    ad1_id = ad_gtc_sell_1.json()["id"]

    # Trader 2 uses floating pricing (ref 60 - 4 = 56)
    ad_gtc_sell_2 = client.put(
        "/api/coin-traders/me/adverts",
        headers=trader2["headers"],
        json={
            "coin_unit": "coin",
            "fiat_currency": "NGN",
            "side": "sell",
            "pricing_mode": "floating",
            "price_fiat": "56",
            "spread_fiat": "-4",
            "min_coin_amount": "4000",
            "max_coin_amount": "20000",
            "payment_window_minutes": 20,
            "payment_methods": ["OPay"],
            "status": "active",
        },
    )
    assert ad_gtc_sell_2.status_code == 200, ad_gtc_sell_2.text
    assert Decimal(str(ad_gtc_sell_2.json()["effective_price_fiat"])) == Decimal("56.0000")

    # Customer Buy GTC marketplace sorted lowest price first
    mkt_buy_gtc = client.get(
        "/api/coin-traders/marketplace",
        params={"coin_unit": "coin", "side": "sell", "sort_by": "price_asc"},
    )
    assert mkt_buy_gtc.status_code == 200, mkt_buy_gtc.text
    offers = mkt_buy_gtc.json()["offers"]
    assert len(offers) == 2
    assert offers[0]["trader_profile_id"] == profile1_id  # 55 before 56
    assert offers[0]["is_new_merchant"] is True
    assert offers[0]["verification_badge_label"] == "Approved by GTEX"
    assert "0123456789" not in mkt_buy_gtc.text  # bank details never leak publicly

    # Filter by payment_method=Bank Transfer excludes Trader 2 (OPay only)
    filtered = client.get(
        "/api/coin-traders/marketplace",
        params={"coin_unit": "coin", "side": "sell", "payment_method": "Bank Transfer"},
    )
    assert [o["trader_profile_id"] for o in filtered.json()["offers"]] == [profile1_id]

    # Quote order
    quote_resp = client.post(
        "/api/coin-traders/orders/quote",
        json={"advert_id": ad1_id, "coin_amount": "5000"},
    )
    assert quote_resp.status_code == 200, quote_resp.text
    q = quote_resp.json()
    assert Decimal(str(q["fiat_total"])) == Decimal("275000.00")
    assert Decimal(str(q["fee_fiat"])) == Decimal("0.0000")

    # Stale quote protection rejects mismatched expected_rate_fiat
    stale = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile1_id,
            "advert_id": ad1_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "5000",
            "expected_rate_fiat": "54",
            "payment_method": "Bank Transfer",
            "idempotency_key": "mkt-stale-quote-1",
        },
    )
    assert stale.status_code == 400

    # Place valid order using advert_id -> bank details still hidden while status == created
    order_resp = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile1_id,
            "advert_id": ad1_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "5000",
            "expected_rate_fiat": "55",
            "payment_method": "Bank Transfer",
            "idempotency_key": "mkt-buy-order-1",
        },
    )
    assert order_resp.status_code == 201, order_resp.text
    order = order_resp.json()
    assert order["advert_id"] == ad1_id
    assert order["payment_window_minutes"] == 15
    assert order["counterparty_payment_details"] == []  # hidden until accepted!

    # Daily limit check: remaining is 12000 - 5000 = 7000, so ordering 8000 must fail
    over_daily = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile1_id,
            "advert_id": ad1_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "8000",
            "payment_method": "Bank Transfer",
            "idempotency_key": "mkt-over-daily-1",
        },
    )
    assert over_daily.status_code == 400
    assert "daily" in over_daily.text.lower()

    # Trader accepts -> bank details revealed to participants, 15m window applied
    accepted = client.post(f"/api/coin-traders/orders/{order['id']}/accept", headers=trader1["headers"])
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["counterparty_payment_details"][0]["account_number"] == "0123456789"

    # Chat message persisted in table
    msg_resp = client.post(
        f"/api/coin-traders/orders/{order['id']}/messages",
        headers=customer["headers"],
        json={"message": "Sending Naira now"},
    )
    assert msg_resp.status_code == 201, msg_resp.text

    # Customer submits proof, trader confirms and releases
    proof = client.post(
        f"/api/coin-traders/orders/{order['id']}/proof",
        headers=customer["headers"],
        json={"proof_reference": "NIP-998877"},
    )
    assert proof.status_code == 200, proof.text
    released = client.post(f"/api/coin-traders/orders/{order['id']}/confirm", headers=trader1["headers"])
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"

    # Customer rates completed order; duplicate rating fails
    rating = client.post(
        f"/api/coin-traders/orders/{order['id']}/rating",
        headers=customer["headers"],
        json={"score": 5, "comment": "Very fast release"},
    )
    assert rating.status_code == 201, rating.text
    dup_rating = client.post(
        f"/api/coin-traders/orders/{order['id']}/rating",
        headers=customer["headers"],
        json={"score": 4},
    )
    assert dup_rating.status_code == 400

    # Merchant dashboard shows separated balances and updated metrics
    dash = client.get("/api/coin-traders/me/dashboard", headers=trader1["headers"])
    assert dash.status_code == 200, dash.text
    d = dash.json()
    assert Decimal(str(d["balances"]["coin_available"])) == Decimal("15000.0000")
    assert Decimal(str(d["balances"]["coin_reserved"])) == Decimal("0.0000")
    assert d["order_counts"]["completed"] == 1
    assert d["performance"]["rating"] == 5.0
    assert d["performance"]["rating_count"] == 1

    # Pause advert -> immediately gone from marketplace and rejects new orders
    paused = client.patch(
        f"/api/coin-traders/me/adverts/{ad1_id}/status",
        headers=trader1["headers"],
        json={"status": "paused"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    mkt_after_pause = client.get(
        "/api/coin-traders/marketplace",
        params={"coin_unit": "coin", "side": "sell"},
    )
    assert all(o["advert_id"] != ad1_id for o in mkt_after_pause.json()["offers"])

    # Admin pauses Trader 2's advert, trader cannot resume it themselves
    ad2_id = ad_gtc_sell_2.json()["id"]
    admin_pause = client.post(
        f"/api/admin/coin-traders/adverts/{ad2_id}/pause",
        headers=bootstrap_admin_headers,
        json={"reason": "Suspicious pricing behavior"},
    )
    assert admin_pause.status_code == 200
    assert admin_pause.json()["status"] == "admin_paused"

    trader_resume_blocked = client.patch(
        f"/api/coin-traders/me/adverts/{ad2_id}/status",
        headers=trader2["headers"],
        json={"status": "active"},
    )
    assert trader_resume_blocked.status_code == 400

    # Fan Coin Sell market (customer sells FNC to trader) + customer_payout_details
    ad_fnc_buy = client.put(
        "/api/coin-traders/me/adverts",
        headers=trader1["headers"],
        json={
            "coin_unit": "credit",
            "fiat_currency": "NGN",
            "side": "buy",
            "pricing_mode": "fixed",
            "price_fiat": "2.5",
            "min_coin_amount": "1000",
            "max_coin_amount": "50000",
            "payment_window_minutes": 15,
            "payment_methods": ["Bank Transfer"],
            "status": "active",
        },
    )
    assert ad_fnc_buy.status_code == 200, ad_fnc_buy.text
    sell_order = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile1_id,
            "advert_id": ad_fnc_buy.json()["id"],
            "direction": "user_sells",
            "coin_unit": "credit",
            "coin_amount": "2000",
            "payment_method": "Bank Transfer",
            "customer_payout_details": {"bank_name": "Kuda", "account_number": "2020202020"},
            "idempotency_key": "mkt-sell-fnc-1",
        },
    )
    assert sell_order.status_code == 201, sell_order.text
    assert sell_order.json()["customer_payout_details"]["account_number"] == "2020202020"

    # Admin overview, config, and audit logs
    overview = client.get("/api/admin/coin-traders/overview", headers=bootstrap_admin_headers)
    assert overview.status_code == 200
    assert overview.json()["total_traders"] >= 2

    # Scenario H: Customer opens dispute on accepted sell order -> prevents release -> admin resolves refund
    accepted_sell = client.post(
        f"/api/coin-traders/orders/{sell_order.json()['id']}/accept", headers=trader1["headers"]
    )
    assert accepted_sell.status_code == 200, accepted_sell.text
    disputed = client.post(
        f"/api/coin-traders/orders/{sell_order.json()['id']}/dispute",
        headers=customer["headers"],
        json={"reason": "Naira transfer delayed"},
    )
    assert disputed.status_code == 200
    assert disputed.json()["status"] == "disputed"
    blocked_release = client.post(
        f"/api/coin-traders/orders/{sell_order.json()['id']}/confirm", headers=customer["headers"]
    )
    assert blocked_release.status_code == 400
    resolved = client.post(
        f"/api/admin/coin-traders/orders/{sell_order.json()['id']}/resolve",
        headers=bootstrap_admin_headers,
        json={"resolution": "refund", "note": "No fiat sent"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "admin_refunded"

    # Scenario I: Admin suspends trader 1 -> excluded from marketplace & cannot accept new orders
    suspended = client.post(
        f"/api/admin/coin-traders/{profile1_id}/suspend",
        headers=bootstrap_admin_headers,
        json={"reason": "Compliance review"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    mkt_after_suspend = client.get(
        "/api/coin-traders/marketplace",
        params={"coin_unit": "credit", "side": "buy"},
    )
    assert all(o["trader_profile_id"] != profile1_id for o in mkt_after_suspend.json()["offers"])

    audits = client.get("/api/admin/coin-traders/audit-logs", headers=bootstrap_admin_headers)
    assert audits.status_code == 200
    action_keys = {a["action_key"] for a in audits.json()}
    assert "coin_trader.approve" in action_keys
    assert "coin_trader.advert.admin_pause" in action_keys
    assert "coin_trader.suspend" in action_keys
    assert "coin_trader.order.refund" in action_keys
