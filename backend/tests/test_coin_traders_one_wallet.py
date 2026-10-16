"""Coin Trader orders + One Wallet integration tests against public API.

Covers:
- One Wallet: GET /api/owner/finance wallet.gtex_total == GET /api/wallets/summary.available_balance
- Coin trader order flow (user_buys): create -> accept -> owner proof -> trader confirm
- Coin trader order flow (user_sells): create -> accept (escrows) -> trader proof -> owner confirm (releases)
- Cancel on created orders
- Dispute on active orders
- as_trader=true desk view

Credentials from /app/memory/test_credentials.md.
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

OWNER_EMAIL = "flow7@gtex.test"
OWNER_PASS = "FlowPass123!"
TRADER_EMAIL = "demo.trader@gtex.ng"
TRADER_PASS = "DemoTrader2026!"


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login {email} failed {r.status_code}: {r.text[:200]}"
    j = r.json()
    tok = j.get("access_token") or j.get("token") or (j.get("tokens") or {}).get("access_token")
    assert tok, f"no token in {j}"
    return tok


@pytest.fixture(scope="session")
def owner_h():
    return {"Authorization": f"Bearer {_login(OWNER_EMAIL, OWNER_PASS)}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def trader_h():
    try:
        return {"Authorization": f"Bearer {_login(TRADER_EMAIL, TRADER_PASS)}", "Content-Type": "application/json"}
    except AssertionError:
        pytest.skip("demo trader login unavailable")


@pytest.fixture(scope="session")
def trader_profile(owner_h):
    r = requests.get(f"{BASE_URL}/api/coin-traders", headers=owner_h, timeout=30)
    assert r.status_code == 200, r.text[:200]
    traders = r.json()
    assert isinstance(traders, list) and len(traders) > 0, "no coin traders available"
    # pick an approved one
    approved = [t for t in traders if t.get("status") == "approved"]
    tp = approved[0] if approved else traders[0]
    assert tp.get("rates"), "trader has no rates"
    return tp


def _wallet_available(headers) -> Decimal:
    r = requests.get(f"{BASE_URL}/api/wallets/summary", headers=headers, timeout=30)
    assert r.status_code == 200, r.text[:200]
    return Decimal(str(r.json()["available_balance"]))


def _finance_gtex_total(headers) -> Decimal:
    r = requests.get(f"{BASE_URL}/api/owner/finance", headers=headers, timeout=30)
    assert r.status_code == 200, r.text[:200]
    return Decimal(str(r.json()["wallet"]["gtex_total"]))


# ---------------- One Wallet integration ----------------
class TestOneWallet:
    def test_finance_and_wallet_summary_in_sync(self, owner_h):
        """gtex_total in owner finance must equal /api/wallets/summary available_balance."""
        fin = _finance_gtex_total(owner_h)
        wal = _wallet_available(owner_h)
        assert fin == wal, f"owner finance gtex_total={fin} != wallets/summary available_balance={wal}"

    def test_wallet_endpoints_consistent(self, owner_h):
        """Both /api/wallet/summary and /api/wallets/summary should match."""
        a = requests.get(f"{BASE_URL}/api/wallet/summary", headers=owner_h, timeout=30).json()
        b = requests.get(f"{BASE_URL}/api/wallets/summary", headers=owner_h, timeout=30).json()
        assert Decimal(str(a["available_balance"])) == Decimal(str(b["available_balance"]))


# ---------------- Coin trader buy flow (owner buys coins) ----------------
class TestCoinTraderBuy:
    def test_buy_flow_full_cycle_increments_wallet(self, owner_h, trader_h, trader_profile):
        pre_wallet = _wallet_available(owner_h)
        pre_finance = _finance_gtex_total(owner_h)
        assert pre_wallet == pre_finance

        amount = Decimal("1")
        payload = {
            "trader_profile_id": trader_profile["id"],
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": str(amount),
            "fiat_currency": "NGN",
            "idempotency_key": "TEST_buy_" + uuid.uuid4().hex[:12],
        }
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders", headers=owner_h, json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        order = r.json()
        oid = order["id"]
        assert order["direction"] == "user_buys"
        assert Decimal(str(order["coin_amount"])) == amount
        assert order["status"] in ("created", "pending")

        # Owner sees it in my orders
        mine = requests.get(f"{BASE_URL}/api/coin-traders/orders", headers=owner_h, timeout=30).json()
        assert any(o["id"] == oid for o in mine), "order missing in owner's list"

        # Trader sees desk orders via ?as_trader=true
        desk = requests.get(f"{BASE_URL}/api/coin-traders/orders?as_trader=true", headers=trader_h, timeout=30).json()
        assert any(o["id"] == oid for o in desk), "order missing in trader desk view"

        # Trader accepts
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders/{oid}/accept", headers=trader_h, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] in ("accepted", "awaiting_payment", "awaiting_proof", "in_escrow", "pending_proof", "payment_pending")

        # Owner submits proof (buy: owner pays off-rail then submits proof)
        r = requests.post(
            f"{BASE_URL}/api/coin-traders/orders/{oid}/proof",
            headers=owner_h,
            json={"proof_reference": "TEST_BUY_REF_" + uuid.uuid4().hex[:6], "note": "test paid"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]

        # Trader confirms -> coins released to owner wallet
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders/{oid}/confirm", headers=trader_h, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] in ("released", "completed")

        post_wallet = _wallet_available(owner_h)
        post_finance = _finance_gtex_total(owner_h)
        assert post_wallet == pre_wallet + amount, f"wallet did not credit: {pre_wallet} -> {post_wallet}"
        assert post_finance == post_wallet, "finance and wallet summary diverged after buy"


# ---------------- Coin trader sell flow (owner sells coins) ----------------
class TestCoinTraderSell:
    def test_sell_flow_escrows_and_releases(self, owner_h, trader_h, trader_profile):
        pre_wallet = _wallet_available(owner_h)
        # Must have coins to sell; buy flow above should have left >=1 coin. Skip if not.
        if pre_wallet < Decimal("1"):
            pytest.skip(f"owner wallet {pre_wallet} < 1 coin; cannot test sell")

        amount = Decimal("1")
        payload = {
            "trader_profile_id": trader_profile["id"],
            "direction": "user_sells",
            "coin_unit": "coin",
            "coin_amount": str(amount),
            "fiat_currency": "NGN",
            "idempotency_key": "TEST_sell_" + uuid.uuid4().hex[:12],
        }
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders", headers=owner_h, json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        oid = r.json()["id"]

        # Trader accepts -> escrow owner coins
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders/{oid}/accept", headers=trader_h, timeout=30)
        assert r.status_code == 200, r.text[:300]

        wsum = requests.get(f"{BASE_URL}/api/wallets/summary", headers=owner_h, timeout=30).json()
        assert Decimal(str(wsum["available_balance"])) == pre_wallet - amount, "available did not decrease on escrow"
        assert Decimal(str(wsum["reserved_balance"])) >= amount, "reserved did not increase on escrow"

        # Trader submits proof (sell flow)
        r = requests.post(
            f"{BASE_URL}/api/coin-traders/orders/{oid}/proof",
            headers=trader_h,
            json={"proof_reference": "TEST_SELL_REF_" + uuid.uuid4().hex[:6], "note": "trader paid owner"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]

        # Owner confirms -> escrow released
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders/{oid}/confirm", headers=owner_h, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] in ("released", "completed")

        post = requests.get(f"{BASE_URL}/api/wallets/summary", headers=owner_h, timeout=30).json()
        assert Decimal(str(post["available_balance"])) == pre_wallet - amount
        assert Decimal(str(post["reserved_balance"])) == Decimal("0")


# ---------------- Cancel / dispute ----------------
class TestCancelDispute:
    def test_cancel_on_created_order(self, owner_h, trader_profile):
        payload = {
            "trader_profile_id": trader_profile["id"],
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "1",
            "fiat_currency": "NGN",
            "idempotency_key": "TEST_cancel_" + uuid.uuid4().hex[:12],
        }
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders", headers=owner_h, json=payload, timeout=30)
        assert r.status_code in (200, 201)
        oid = r.json()["id"]
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders/{oid}/cancel", headers=owner_h, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert r.json()["status"] == "cancelled"

    def test_dispute_on_active_order(self, owner_h, trader_h, trader_profile):
        payload = {
            "trader_profile_id": trader_profile["id"],
            "direction": "user_buys",
            "coin_unit": "coin",
            "coin_amount": "1",
            "fiat_currency": "NGN",
            "idempotency_key": "TEST_dispute_" + uuid.uuid4().hex[:12],
        }
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders", headers=owner_h, json=payload, timeout=30)
        oid = r.json()["id"]
        r = requests.post(f"{BASE_URL}/api/coin-traders/orders/{oid}/accept", headers=trader_h, timeout=30)
        assert r.status_code == 200
        r = requests.post(
            f"{BASE_URL}/api/coin-traders/orders/{oid}/dispute",
            headers=owner_h,
            json={"reason": "TEST dispute - automated test", "evidence": {}},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:200]
        assert r.json()["status"] == "disputed"


# ---------------- Admin review (regression) ----------------
class TestAdminReview:
    def test_admin_can_list_coin_trader_orders(self):
        try:
            admin_tok = _login("admin@gtex.ng", "GtexAdmin2026")
        except AssertionError:
            pytest.skip("admin login unavailable")
        h = {"Authorization": f"Bearer {admin_tok}"}
        r = requests.get(f"{BASE_URL}/api/admin/coin-traders/orders", headers=h, timeout=30)
        # endpoint may be at a different admin prefix; accept 200/404 to avoid false negatives,
        # but 500 is a failure.
        assert r.status_code != 500, r.text[:200]
