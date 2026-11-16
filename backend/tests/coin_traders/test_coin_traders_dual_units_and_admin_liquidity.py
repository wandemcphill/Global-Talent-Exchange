from __future__ import annotations

from decimal import Decimal


def _apply_and_approve_dual_desk(client, *, trader_headers: dict[str, str], admin_headers: dict[str, str]) -> str:
    applied = client.post(
        "/api/coin-traders/apply",
        headers=trader_headers,
        json={
            "display_name": "Dual Unit Liquidity Desk",
            "country_code": "NG",
            "terms": {"same_name_account_only": True, "payment_proof_required": True},
            "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
            "bank_accounts": [{"bank": "GTBank", "account_number": "0123456789", "account_name": "Dual Desk"}],
            "metadata_json": {},
        },
    )
    assert applied.status_code == 201, applied.text
    profile_id = applied.json()["id"]

    approved = client.post(
        f"/api/admin/coin-traders/{profile_id}/approve",
        headers=admin_headers,
        json={"tier": "gold", "note": "dual-unit verification"},
    )
    assert approved.status_code == 200, approved.text

    coin_rate = client.put(
        "/api/coin-traders/me/rates",
        headers=trader_headers,
        json={
            "coin_unit": "coin",
            "fiat_currency": "NGN",
            "buy_rate_fiat": "860",
            "sell_rate_fiat": "920",
            "min_coin_amount": "1",
            "max_coin_amount": "50000",
            "available_liquidity": "2000",
            "is_active": True,
        },
    )
    assert coin_rate.status_code == 200, coin_rate.text

    credit_rate = client.put(
        "/api/coin-traders/me/rates",
        headers=trader_headers,
        json={
            "coin_unit": "credit",
            "fiat_currency": "NGN",
            "buy_rate_fiat": "860",
            "sell_rate_fiat": "920",
            "min_coin_amount": "1",
            "max_coin_amount": "50000",
            "available_liquidity": "2000",
            "is_active": True,
        },
    )
    assert credit_rate.status_code == 200, credit_rate.text
    return profile_id


def test_dual_unit_ngn_buyer_minimums_and_separate_balances(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
) -> None:
    trader = auth_user_factory(
        suffix="dual-desk-trader",
        funded_coin="5000",
        funded_credit="5000",
        account_type="coin_trader",
    )
    buyer = auth_user_factory(suffix="dual-desk-buyer")
    buyer_coin_before = Decimal(
        str(client.get("/api/wallets/summary?currency=coin", headers=buyer["headers"]).json()["available_balance"])
    )
    buyer_credit_before = Decimal(
        str(client.get("/api/wallets/summary?currency=credit", headers=buyer["headers"]).json()["available_balance"])
    )
    profile_id = _apply_and_approve_dual_desk(
        client,
        trader_headers=trader["headers"],
        admin_headers=bootstrap_admin_headers,
    )

    # GTEX Coin (coin): rate=920 NGN/GTC, NGN minimum is 200,000 => 100 GTC (92,000 NGN) fails, 250 GTC (230,000 NGN) succeeds
    too_small_coin = client.post(
        "/api/coin-traders/orders",
        headers=buyer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "100",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "dual-coin-too-small-001",
        },
    )
    assert too_small_coin.status_code == 400, too_small_coin.text
    assert "₦200,000" in too_small_coin.text

    valid_coin = client.post(
        "/api/coin-traders/orders",
        headers=buyer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "250",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "dual-coin-valid-001",
        },
    )
    assert valid_coin.status_code == 201, valid_coin.text
    coin_order_id = valid_coin.json()["id"]
    assert valid_coin.json()["coin_unit"] == "coin"

    # Fan Coin (credit): rate=920 NGN/FNC, NGN minimum is 50,000 => 40 FNC (36,800 NGN) fails, 60 FNC (55,200 NGN) succeeds
    too_small_credit = client.post(
        "/api/coin-traders/orders",
        headers=buyer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "credit",
            "coin_amount": "40",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "dual-credit-too-small-001",
        },
    )
    assert too_small_credit.status_code == 400, too_small_credit.text
    assert "₦50,000" in too_small_credit.text

    valid_credit = client.post(
        "/api/coin-traders/orders",
        headers=buyer["headers"],
        json={
            "trader_profile_id": profile_id,
            "direction": "user_buys",
            "coin_unit": "credit",
            "coin_amount": "60",
            "fiat_currency": "NGN",
            "payment_method": "bank_transfer",
            "idempotency_key": "dual-credit-valid-001",
        },
    )
    assert valid_credit.status_code == 201, valid_credit.text
    credit_order_id = valid_credit.json()["id"]
    assert valid_credit.json()["coin_unit"] == "credit"

    for oid in (coin_order_id, credit_order_id):
        assert client.post(f"/api/coin-traders/orders/{oid}/accept", headers=trader["headers"]).status_code == 200
        assert (
            client.post(
                f"/api/coin-traders/orders/{oid}/proof",
                headers=buyer["headers"],
                json={"proof_reference": f"proof-{oid}", "note": "paid"},
            ).status_code
            == 200
        )
        released = client.post(f"/api/coin-traders/orders/{oid}/confirm", headers=trader["headers"])
        assert released.status_code == 200, released.text

    coin_wallet = client.get("/api/wallets/summary?currency=coin", headers=buyer["headers"])
    credit_wallet = client.get("/api/wallets/summary?currency=credit", headers=buyer["headers"])
    assert coin_wallet.status_code == 200, coin_wallet.text
    assert credit_wallet.status_code == 200, credit_wallet.text
    assert Decimal(str(coin_wallet.json()["available_balance"])) > buyer_coin_before + Decimal("200")
    assert Decimal(str(credit_wallet.json()["available_balance"])) > buyer_credit_before + Decimal("50")


def test_admin_liquidity_issue_and_redeem_for_both_units_and_idempotency(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
    competition_admin_headers,
    app_session_factory,
) -> None:
    from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
    from app.wallets.service import LedgerPosting, WalletService

    trader = auth_user_factory(
        suffix="admin-liq-trader",
        funded_coin="100",
        funded_credit="100",
        account_type="coin_trader",
    )
    normal_user = auth_user_factory(suffix="admin-liq-nonadmin")
    trader_coin_before = Decimal(
        str(client.get("/api/wallets/summary?currency=coin", headers=trader["headers"]).json()["available_balance"])
    )
    trader_credit_before = Decimal(
        str(client.get("/api/wallets/summary?currency=credit", headers=trader["headers"]).json()["available_balance"])
    )
    profile_id = _apply_and_approve_dual_desk(
        client,
        trader_headers=trader["headers"],
        admin_headers=bootstrap_admin_headers,
    )

    # Non-admin & scoped admin without manage_liquidity_desk must fail closed with 403
    for forbidden_headers in (normal_user["headers"], competition_admin_headers):
        res = client.post(
            f"/api/admin/coin-traders/{profile_id}/liquidity/issue",
            headers=forbidden_headers,
            json={"coin_unit": "coin", "amount": "50", "idempotency_key": "forbid-liq-001", "note": "blocked"},
        )
        assert res.status_code == 403, res.text

    # Unfunded platform liquidity pool must fail closed cleanly with HTTP 400 (not unhandled 500)
    unfunded = client.post(
        f"/api/admin/coin-traders/{profile_id}/liquidity/issue",
        headers=bootstrap_admin_headers,
        json={"coin_unit": "coin", "amount": "500", "idempotency_key": "unfunded-coin-001", "note": "unfunded check"},
    )
    assert unfunded.status_code == 400, unfunded.text
    assert "Liquidity pool balance is lower" in unfunded.text

    # Fund non-negative platform liquidity pools for both COIN and CREDIT before issuing
    wallet_service = WalletService()
    with app_session_factory() as session:
        for unit in (LedgerUnit.COIN, LedgerUnit.CREDIT):
            pool = wallet_service.ensure_market_liquidity_account(session, unit)
            funding = wallet_service.ensure_named_system_account(
                session,
                code=f"test:{unit.value}:liquidity_funding_seed",
                label=f"Test {unit.value.upper()} Liquidity Seed",
                unit=unit,
                allow_negative=True,
            )
            wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(account=funding, amount=Decimal("-5000.0000")),
                    LedgerPosting(account=pool, amount=Decimal("5000.0000")),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                reference=f"test-liquidity-pool-seed:{unit.value}",
            )
        session.commit()

    # Issue GTEX Coin (coin) liquidity + idempotent replay
    issue_coin = client.post(
        f"/api/admin/coin-traders/{profile_id}/liquidity/issue",
        headers=bootstrap_admin_headers,
        json={
            "coin_unit": "coin",
            "amount": "500",
            "idempotency_key": "issue-coin-idem-001",
            "note": "Desk GTC restock",
        },
    )
    assert issue_coin.status_code == 200, issue_coin.text
    assert issue_coin.json()["flow"] == "issue"
    assert issue_coin.json()["coin_unit"] == "coin"
    assert Decimal(str(issue_coin.json()["available_balance"])) == trader_coin_before + Decimal("500.0000")

    replay_coin = client.post(
        f"/api/admin/coin-traders/{profile_id}/liquidity/issue",
        headers=bootstrap_admin_headers,
        json={
            "coin_unit": "coin",
            "amount": "500",
            "idempotency_key": "issue-coin-idem-001",
            "note": "Desk GTC restock",
        },
    )
    assert replay_coin.status_code == 200, replay_coin.text
    assert Decimal(str(replay_coin.json()["available_balance"])) == trader_coin_before + Decimal("500.0000")

    # Issue Fan Coin (credit) liquidity + redeem partial
    issue_credit = client.post(
        f"/api/admin/coin-traders/{profile_id}/liquidity/issue",
        headers=bootstrap_admin_headers,
        json={
            "coin_unit": "credit",
            "amount": "300",
            "idempotency_key": "issue-credit-idem-001",
            "note": "Desk FNC restock",
        },
    )
    assert issue_credit.status_code == 200, issue_credit.text
    assert issue_credit.json()["coin_unit"] == "credit"
    assert Decimal(str(issue_credit.json()["available_balance"])) == trader_credit_before + Decimal("300.0000")

    redeem_credit = client.post(
        f"/api/admin/coin-traders/{profile_id}/liquidity/redeem",
        headers=bootstrap_admin_headers,
        json={
            "coin_unit": "credit",
            "amount": "150",
            "idempotency_key": "redeem-credit-idem-001",
            "note": "Desk FNC sweep",
        },
    )
    assert redeem_credit.status_code == 200, redeem_credit.text
    assert redeem_credit.json()["flow"] == "redeem"
    assert redeem_credit.json()["coin_unit"] == "credit"
    assert Decimal(str(redeem_credit.json()["available_balance"])) == trader_credit_before + Decimal("150.0000")
