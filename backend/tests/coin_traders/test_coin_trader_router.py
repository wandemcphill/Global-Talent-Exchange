from __future__ import annotations


def test_coin_trader_router_order_lifecycle(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
) -> None:
    trader = auth_user_factory(suffix="coin-trader-router", funded_coin="100000")
    buyer = auth_user_factory(suffix="coin-buyer-router")

    application = client.post(
        "/api/coin-traders/apply",
        headers=trader["headers"],
        json={
            "display_name": "Router OTC Desk",
            "country_code": "NG",
            "terms": {
                "same_name_account_only": True,
                "payment_proof_required": True,
            },
            "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
            "bank_accounts": [{"bank": "GTBank"}],
            "metadata_json": {"test": "router"},
        },
    )
    assert application.status_code == 201, application.text
    profile_id = application.json()["id"]

    approval = client.post(
        f"/api/admin/coin-traders/{profile_id}/approve",
        headers=bootstrap_admin_headers,
        json={"tier": "gold", "note": "router contract test"},
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["status"] == "approved"

    rate = client.put(
        "/api/coin-traders/me/rates",
        headers=trader["headers"],
        json={
            "coin_unit": "coin",
            "fiat_currency": "NGN",
            "buy_rate_fiat": "0.90",
            "sell_rate_fiat": "1.05",
            "min_coin_amount": "100",
            "max_coin_amount": "50000",
            "available_liquidity": "100000",
            "is_active": True,
        },
    )
    assert rate.status_code == 200, rate.text

    marketplace = client.get("/api/coin-traders", params={"coin_unit": "coin"})
    assert marketplace.status_code == 200, marketplace.text
    assert any(item["id"] == profile_id for item in marketplace.json())

    created = client.post(
        "/api/coin-traders/orders",
        headers=buyer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "500",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "router-order-key-001",
        },
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    assert created.json()["terms_snapshot"]["same_name_account_only"] is True

    accepted = client.post(
        f"/api/coin-traders/orders/{order_id}/accept",
        headers=trader["headers"],
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "payment_pending"
    assert accepted.json()["payment_window_expires_at"] is not None

    proof = client.post(
        f"/api/coin-traders/orders/{order_id}/proof",
        headers=buyer["headers"],
        json={"proof_reference": "router-receipt-1", "note": "paid"},
    )
    assert proof.status_code == 200, proof.text
    assert proof.json()["status"] == "proof_submitted"
    assert proof.json()["proof"]["proof_reference"] == "router-receipt-1"

    released = client.post(
        f"/api/coin-traders/orders/{order_id}/confirm",
        headers=trader["headers"],
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"
    assert released.json()["ledger_refs"]["release_entry_ids"]

    orders = client.get("/api/coin-traders/orders", headers=buyer["headers"])
    assert orders.status_code == 200, orders.text
    assert any(item["id"] == order_id and item["status"] == "released" for item in orders.json())


def test_coin_trader_router_enforces_escrow_roles_and_admin_resolution(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
) -> None:
    trader = auth_user_factory(suffix="coin-trader-router-guards", funded_coin="100000")
    customer = auth_user_factory(suffix="coin-customer-router-guards", funded_coin="10000")
    profile_id = _approved_profile_with_rate(
        client,
        trader_headers=trader["headers"],
        admin_headers=bootstrap_admin_headers,
        suffix="guards",
    )

    buy_order = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "500",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "router-guards-buy-001",
        },
    )
    assert buy_order.status_code == 201, buy_order.text
    buy_order_id = buy_order.json()["id"]

    accepted = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/accept",
        headers=trader["headers"],
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "payment_pending"

    premature_release = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/confirm",
        headers=trader["headers"],
    )
    assert premature_release.status_code == 400

    wrong_proof_actor = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/proof",
        headers=trader["headers"],
        json={"proof_reference": "trader-cannot-prove-buyer-payment"},
    )
    assert wrong_proof_actor.status_code == 403

    proof = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/proof",
        headers=customer["headers"],
        json={"proof_reference": "buyer-proof-001", "note": "bank transfer sent"},
    )
    assert proof.status_code == 200, proof.text
    assert proof.json()["status"] == "proof_submitted"

    wrong_receiver = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/confirm",
        headers=customer["headers"],
    )
    assert wrong_receiver.status_code == 403

    disputed = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/dispute",
        headers=customer["headers"],
        json={"reason": "Trader requested manual review", "evidence": {"receipt": "buyer-proof-001"}},
    )
    assert disputed.status_code == 200, disputed.text
    assert disputed.json()["status"] == "disputed"

    normal_release_after_dispute = client.post(
        f"/api/coin-traders/orders/{buy_order_id}/confirm",
        headers=trader["headers"],
    )
    assert normal_release_after_dispute.status_code == 400

    admin_released = client.post(
        f"/api/admin/coin-traders/orders/{buy_order_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"resolution": "release", "note": "Receipt verified by ops."},
    )
    assert admin_released.status_code == 200, admin_released.text
    assert admin_released.json()["status"] == "admin_released"
    assert admin_released.json()["ledger_refs"]["release_entry_ids"]

    cancellable_order = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "600",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "router-guards-cancel-001",
        },
    )
    assert cancellable_order.status_code == 201, cancellable_order.text
    cancellable_order_id = cancellable_order.json()["id"]
    accepted_cancel = client.post(
        f"/api/coin-traders/orders/{cancellable_order_id}/accept",
        headers=trader["headers"],
    )
    assert accepted_cancel.status_code == 200, accepted_cancel.text

    refunded = client.post(
        f"/api/coin-traders/orders/{cancellable_order_id}/cancel",
        headers=customer["headers"],
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["status"] == "refunded"
    assert refunded.json()["ledger_refs"]["refund_entry_ids"]

    sell_order = client.post(
        "/api/coin-traders/orders",
        headers=customer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_sells",
            "coin_unit": "coin",
            "coin_amount": "700",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "router-guards-sell-001",
        },
    )
    assert sell_order.status_code == 201, sell_order.text
    sell_order_id = sell_order.json()["id"]
    accepted_sell = client.post(
        f"/api/coin-traders/orders/{sell_order_id}/accept",
        headers=trader["headers"],
    )
    assert accepted_sell.status_code == 200, accepted_sell.text
    assert accepted_sell.json()["escrow_owner_user_id"] == customer["user_id"]

    wrong_sell_proof_actor = client.post(
        f"/api/coin-traders/orders/{sell_order_id}/proof",
        headers=customer["headers"],
        json={"proof_reference": "seller-cannot-prove-trader-payment"},
    )
    assert wrong_sell_proof_actor.status_code == 403

    trader_proof = client.post(
        f"/api/coin-traders/orders/{sell_order_id}/proof",
        headers=trader["headers"],
        json={"proof_reference": "trader-fiat-proof-001"},
    )
    assert trader_proof.status_code == 200, trader_proof.text
    assert trader_proof.json()["status"] == "proof_submitted"

    wrong_sell_receiver = client.post(
        f"/api/coin-traders/orders/{sell_order_id}/confirm",
        headers=trader["headers"],
    )
    assert wrong_sell_receiver.status_code == 403

    sell_released = client.post(
        f"/api/coin-traders/orders/{sell_order_id}/confirm",
        headers=customer["headers"],
    )
    assert sell_released.status_code == 200, sell_released.text
    assert sell_released.json()["status"] == "released"


def _approved_profile_with_rate(
    client,
    *,
    trader_headers: dict[str, str],
    admin_headers: dict[str, str],
    suffix: str,
) -> str:
    application = client.post(
        "/api/coin-traders/apply",
        headers=trader_headers,
        json={
            "display_name": f"Router {suffix} OTC Desk",
            "country_code": "NG",
            "terms": {
                "same_name_account_only": True,
                "payment_proof_required": True,
            },
            "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
            "bank_accounts": [{"bank": "GTBank"}],
            "metadata_json": {"test": suffix},
        },
    )
    assert application.status_code == 201, application.text
    profile_id = application.json()["id"]

    approval = client.post(
        f"/api/admin/coin-traders/{profile_id}/approve",
        headers=admin_headers,
        json={"tier": "gold", "note": f"{suffix} contract test"},
    )
    assert approval.status_code == 200, approval.text

    rate = client.put(
        "/api/coin-traders/me/rates",
        headers=trader_headers,
        json={
            "coin_unit": "coin",
            "fiat_currency": "NGN",
            "buy_rate_fiat": "0.90",
            "sell_rate_fiat": "1.05",
            "min_coin_amount": "100",
            "max_coin_amount": "50000",
            "available_liquidity": "100000",
            "is_active": True,
        },
    )
    assert rate.status_code == 200, rate.text
    return profile_id
