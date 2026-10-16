"""Create an approved demo coin trader (Naira desk) for local/preview testing."""
import os
import sys

import requests

B = os.environ.get("GTEX_API", "http://localhost:8001/api")
ADMIN = (os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"], os.environ["GTE_BOOTSTRAP_ADMIN_PASSWORD"])
EMAIL, PW = "demo.trader@gtex.ng", "DemoTrader2026!"


def login(email, pw):
    r = requests.post(f"{B}/auth/login", json={"email": email, "password": pw})
    return r.json().get("access_token") if r.ok else None


tok = login(EMAIL, PW)
if not tok:
    r = requests.post(f"{B}/auth/signup/user", json={"full_name": "Demo Naira Desk", "username": "demonairadesk", "email": EMAIL, "password": PW, "country": "Nigeria", "is_over_18": True})
    print("signup", r.status_code, r.text[:200])
    tok = login(EMAIL, PW)
H = {"Authorization": f"Bearer {tok}"}
me = requests.get(f"{B}/coin-traders/me", headers=H)
if me.status_code != 200:
    me = requests.post(f"{B}/coin-traders/apply", headers=H, json={"display_name": "Demo Naira Desk", "country_code": "NG", "terms": {"payment_instructions": "Demo only: Moniepoint 0000000000 Demo Naira Desk"}, "bank_accounts": [{"bank_name": "Moniepoint (demo)", "account_number": "0000000000", "account_name": "Demo Naira Desk"}]})
profile = me.json()
print("profile", profile.get("id"), profile.get("status"))
if profile.get("status") != "approved":
    at = login(*ADMIN)
    r = requests.post(f"{B}/admin/coin-traders/{profile['id']}/approve", headers={"Authorization": f"Bearer {at}"}, json={"tier": "silver", "note": "Demo trader for preview testing"})
    print("approve", r.status_code, r.text[:200])
r = requests.put(f"{B}/coin-traders/me/rates", headers=H, json={"coin_unit": "coin", "fiat_currency": "NGN", "buy_rate_fiat": 870, "sell_rate_fiat": 920, "min_coin_amount": 1, "max_coin_amount": 5000, "available_liquidity": 5000})
print("rates", r.status_code, r.text[:200])
sys.exit(0)
