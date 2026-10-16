"""Read-only live backend validation for GTEX review request."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gtex-clubhq.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "vidvimedialtd@gmail.com"
ADMIN_PASS = "Desolamcphill89."
TIMEOUT = 90


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/v2/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                      timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("success") is True
    tok = data["data"].get("access_token") or data["data"].get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _get_with_retry(url, headers=None, retries=3):
    last = None
    for _ in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            last = r
        except Exception as e:
            last = e
    return last


# ---- v2 auth/me ----
def test_auth_me(auth_headers):
    r = requests.get(f"{BASE_URL}/api/v2/auth/me", headers=auth_headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    assert body["data"].get("email", "").lower() == ADMIN_EMAIL


# ---- player markets ----
def test_markets_list():
    r = _get_with_retry(f"{BASE_URL}/api/v2/players/markets?per_page=5")
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("success") is True
    data = body["data"]
    items = data.get("items") or data.get("markets") or data.get("results")
    assert items is not None and len(items) > 0, f"no items: {data}"
    assert len(items) <= 5


def test_markets_search():
    r = _get_with_retry(f"{BASE_URL}/api/v2/players/markets?per_page=5&search=Gomes")
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("success") is True


# ---- players ----
def test_players_list():
    r = requests.get(f"{BASE_URL}/api/v2/players?limit=5", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    data = body["data"]
    assert "players" in data
    assert isinstance(data["players"], list)
    assert len(data["players"]) <= 5
    assert "has_more" in data
    # Capture ids for next test
    pytest.player_ids = [p.get("player_id") or p.get("id") for p in data["players"] if (p.get("player_id") or p.get("id"))]


def test_players_by_position_goalkeeper():
    r = requests.get(f"{BASE_URL}/api/v2/players?limit=5&position=goalkeeper", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    players = body["data"]["players"]
    assert len(players) > 0


# ---- owner quote ----
def test_owner_market_quote_variation(auth_headers):
    ids = getattr(pytest, "player_ids", [])
    if not ids:
        r = requests.get(f"{BASE_URL}/api/v2/players?limit=5", timeout=TIMEOUT)
        ids = [p.get("player_id") or p["id"] for p in r.json()["data"]["players"]]
    assert len(ids) >= 2
    url = f"{BASE_URL}/api/owner/market/quote?player_ids=" + ",".join(ids)
    r = requests.get(url, headers=auth_headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    quotes = body.get("quotes") or body.get("data") or body
    if isinstance(quotes, dict) and "quotes" in quotes:
        quotes = quotes["quotes"]
    # quotes may be a dict keyed by player_id OR a list of quote objects
    if isinstance(quotes, dict):
        quote_list = list(quotes.values())
    else:
        quote_list = list(quotes)
    assert len(quote_list) >= 2, f"body={body}"
    prices = {q.get("price") or q.get("price_coins") or q.get("fair_price") for q in quote_list}
    ratings = {q.get("rating") or q.get("overall") for q in quote_list}
    # Prices or ratings should not be a single flat value (regression check: previously 800/57 for every player)
    assert len(prices) > 1 or len(ratings) > 1, f"flat quotes: {quote_list}"
    # Ensure the fixed flat defaults are gone
    assert prices != {800} and ratings != {57}, f"legacy flat defaults still present: {quote_list}"


# ---- owner control / finance ----
def test_owner_control_center(auth_headers):
    r = requests.get(f"{BASE_URL}/api/owner/control-center", headers=auth_headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text


def test_owner_finance(auth_headers):
    r = requests.get(f"{BASE_URL}/api/owner/finance", headers=auth_headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text


# ---- national team ----
def test_national_competitions(auth_headers):
    r = requests.get(f"{BASE_URL}/api/national-team-engine/competitions",
                     headers=auth_headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text


def test_national_me_history(auth_headers):
    r = requests.get(f"{BASE_URL}/api/national-team-engine/me/history",
                     headers=auth_headers, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
