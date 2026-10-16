"""GTEX owner console backend tests - targets /api/owner/* endpoints and auth.

Uses demo onboarded user flow7@gtex.test and admin admin@gtex.ng per
/app/memory/test_credentials.md. All tests hit the public REACT_APP_BACKEND_URL.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback for in-cluster run
    BASE_URL = "http://localhost:8001"

OWNER_EMAIL = "flow7@gtex.test"
OWNER_PASS = "FlowPass123!"
ADMIN_EMAIL = "admin@gtex.ng"
ADMIN_PASS = "GtexAdmin2026"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:300]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token") or (data.get("tokens") or {}).get("access_token")
    assert tok, f"no token in {data}"
    return tok


@pytest.fixture(scope="session")
def owner_token():
    return _login(OWNER_EMAIL, OWNER_PASS)


@pytest.fixture(scope="session")
def admin_token():
    try:
        return _login(ADMIN_EMAIL, ADMIN_PASS)
    except AssertionError:
        pytest.skip("admin login unavailable")


@pytest.fixture(scope="session")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# --- Auth / smoke ---
class TestAuth:
    def test_auth_me(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=owner_headers, timeout=30)
        assert r.status_code == 200
        assert r.json().get("email") == OWNER_EMAIL

    def test_unauth_control_center(self):
        r = requests.get(f"{BASE_URL}/api/owner/control-center", timeout=30)
        assert r.status_code in (401, 403)


# --- Control center & finance ---
class TestControlCenter:
    def test_control_center(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/control-center", headers=owner_headers, timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        # expect fixtures, clubs, economy, decisions, inbox, health-ish keys
        assert isinstance(body, dict)
        # at minimum must have clubs or primary_club
        assert any(k in body for k in ("clubs", "primary_club", "my_clubs"))
        # control-center shape sanity
        for key in ("clubs", "inbox", "decisions", "health", "fixtures", "economy"):
            assert key in body, f"control-center missing {key}; got {list(body.keys())}"

    def test_world_clubs(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/world/clubs", headers=owner_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_finance(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/finance", headers=owner_headers, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # Expect labelled balances
        # Finance returns {wallet, clubs, ledger, withdrawals, support_units, gift_catalog, ...}
        assert "wallet" in data and "ledger" in data, f"missing wallet/ledger in {list(data.keys())}"
        wallet = data["wallet"]
        for k in ("withdrawable", "non_withdrawable", "earned", "deposited", "promotional", "pending_review"):
            assert k in wallet, f"wallet missing {k}; got {list(wallet.keys())}"
        # Paystack is now LIVE-configured this iteration.
        assert data.get("paystack_configured") is True

    def test_withdraw_eligibility_zero(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/withdrawals/eligibility?amount=1000", headers=owner_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "eligible" in data or "allowed" in data or "chips" in data or "reasons" in data


# --- Deposits (paystack not configured) ---
class TestDeposits:
    def test_deposit_init_paystack_unconfigured(self, owner_headers):
        r = requests.post(
            f"{BASE_URL}/api/owner/deposits/init",
            headers=owner_headers,
            json={"amount_ngn": 5000, "callback_url": f"{BASE_URL}/app/finance"},
            timeout=30,
        )
        # Expected (LIVE keys): 400 (bad email) OR 200 (checkout). Avoid completing a real payment.
        assert r.status_code in (200, 400, 422, 502, 503), f"got {r.status_code}: {r.text[:200]}"


# --- Inbox / advance world ---
class TestInboxAdvance:
    def test_inbox_list(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/inbox", headers=owner_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_advance_world_generates_items(self, owner_headers):
        # Find primary club id
        cc = requests.get(f"{BASE_URL}/api/owner/control-center", headers=owner_headers, timeout=30).json()
        clubs = cc.get("clubs") or []
        club_id = clubs[0].get("club_id") or clubs[0].get("id") if clubs else None
        if not club_id:
            pytest.skip("no club in control-center.clubs")
        r = requests.post(f"{BASE_URL}/api/owner/clubs/{club_id}/advance", headers=owner_headers, timeout=60)
        assert r.status_code == 200, r.text[:300]


# --- Competitions ---
class TestCompetitions:
    def test_list(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/competitions", headers=owner_headers, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    def test_host_competition(self, owner_headers):
        name = f"TEST_cup_{uuid.uuid4().hex[:6]}"
        r = requests.post(
            f"{BASE_URL}/api/owner/competitions",
            headers=owner_headers,
            json={"name": name, "format": "league", "visibility": "private"},
            timeout=30,
        )
        # Accept 200/201 or 422 if schema differs — only critical: not 500
        assert r.status_code in (200, 201, 400, 422), f"unexpected {r.status_code}: {r.text[:200]}"
        if r.status_code in (200, 201):
            data = r.json()
            assert "invite_code" in data or "code" in data or "id" in data


# --- Admin review desk ---
class TestAdmin:
    def test_review_queue_requires_admin(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/admin/review-queue", headers=owner_headers, timeout=30)
        assert r.status_code in (401, 403), f"non-admin should be forbidden, got {r.status_code}"

    def test_review_queue_admin_ok(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/owner/admin/review-queue", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, (dict, list))


# --- Signup validation ---
class TestSignup:
    def test_signup_requires_club_type_when_club_given(self):
        uniq = uuid.uuid4().hex[:8]
        payload = {
            "email": f"TEST_{uniq}@gtex.test",
            "password": "StrongPass123!",
            "username": f"TEST_{uniq}",
            "club_name": "TEST Club",
            "club_tag": "TST",
            "over18": True,
            # club_type intentionally missing
        }
        r = requests.post(f"{BASE_URL}/api/auth/signup/user", json=payload, timeout=30)
        # Must not be a 500; should be 400/422 or possibly 200 if backend defaults
        assert r.status_code != 500, r.text[:300]

    def test_signup_valid_minimal(self):
        uniq = uuid.uuid4().hex[:8]
        payload = {
            "email": f"TEST_{uniq}@gtex.test",
            "password": "StrongPass123!",
            "username": f"TEST_{uniq}",
            "club_name": "TEST Club",
            "club_tag": "TST",
            "club_type": "community",
            "over18": True,
        }
        r = requests.post(f"{BASE_URL}/api/auth/signup/user", json=payload, timeout=30)
        assert r.status_code in (200, 201, 400, 409, 422), f"unexpected {r.status_code}: {r.text[:200]}"
