"""Backend tests for Wonderkid sort, Price History, and daily snapshot cron."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gtex-clubhq.preview.emergentagent.com").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_CRON_SECRET", "QG8Ienw6S-h1tmeNXTHdpEj-JKvC8XL7BeDgbSQm6jgWJNaF")

ADMIN_EMAIL = "vidvimedialtd@gmail.com"
ADMIN_PWD = "Desolamcphill89."

REGEN_PLAYER_ID = "f9ff343d-434e-52e0-975f-5ade01a3d680"  # Tunde Olawale, Nigeria


def _envelope(r):
    data = r.json()
    if isinstance(data, dict) and "success" in data and "data" in data:
        return data["data"]
    return data


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/v2/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PWD},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    payload = _envelope(r)
    tok = payload.get("access_token") or payload.get("token") or (payload.get("tokens") or {}).get("access_token")
    assert tok, f"no token in {payload}"
    return tok


# ---- Wonderkid sort ----

class TestWonderkidSort:
    def test_wonderkid_sort_all_regen_u22_with_potential(self):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/markets",
            params={"sort": "wonderkid", "per_page": 50},
            timeout=180,
        )
        assert r.status_code == 200, r.text
        data = _envelope(r)
        items = data["items"]
        assert len(items) > 0
        pots = []
        for it in items:
            assert it["is_regen"] is True, f"non-regen leaked: {it['player_name']}"
            assert it.get("age") is not None and it["age"] <= 21, f"age>{21} for {it['player_name']}"
            assert it.get("potential") is not None
            pots.append(it["potential"])
        # ordering: potential desc
        assert pots == sorted(pots, reverse=True), pots

    def test_wonderkid_nigeria_filter(self):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/markets",
            params={"sort": "wonderkid", "nation": "Nigeria", "per_page": 20},
            timeout=180,
        )
        assert r.status_code == 200
        data = _envelope(r)
        assert data["total"] > 400  # expected around 643
        for it in data["items"]:
            assert it["nationality"] == "Nigeria"
            assert it["is_regen"] is True
            assert it["age"] <= 21

    def test_wonderkid_with_source_real_still_regen(self):
        """Spec: sort=wonderkid together with source=real still returns regens only."""
        r = requests.get(
            f"{BASE_URL}/api/v2/players/markets",
            params={"sort": "wonderkid", "source": "real", "per_page": 10},
            timeout=180,
        )
        assert r.status_code == 200
        data = _envelope(r)
        for it in data["items"]:
            assert it["is_regen"] is True


# ---- Default sort still works and real items have null rating/potential ----

class TestDefaultSort:
    def test_default_name_ordering_includes_rating_potential_fields(self):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/markets",
            params={"per_page": 20, "source": "real"},
            timeout=180,
        )
        assert r.status_code == 200
        data = _envelope(r)
        items = data["items"]
        assert items
        for it in items:
            assert "rating" in it
            assert "potential" in it
            # real players: rating/potential should be null
            assert it["rating"] is None
            assert it["potential"] is None

    def test_regen_default_has_rating_potential(self):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/markets",
            params={"per_page": 20, "source": "regen"},
            timeout=180,
        )
        assert r.status_code == 200
        data = _envelope(r)
        items = data["items"]
        assert items
        for it in items:
            assert it["is_regen"] is True


# ---- Price history ----

class TestPriceHistory:
    @pytest.mark.parametrize("range_key", ["7d", "30d", "all"])
    def test_price_history_valid_ranges(self, range_key):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/{REGEN_PLAYER_ID}/shares/price-history",
            params={"range": range_key},
            timeout=180,
        )
        assert r.status_code == 200, r.text
        data = _envelope(r)
        assert data["range"] == range_key
        assert "points" in data and isinstance(data["points"], list)
        assert len(data["points"]) >= 1
        for p in data["points"]:
            assert "at" in p and "price" in p and "kind" in p
        for key in ("open_price", "current_price", "high_price", "low_price", "change_pct", "trade_count"):
            assert key in data, f"missing {key}"

    def test_price_history_invalid_range_422(self):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/{REGEN_PLAYER_ID}/shares/price-history",
            params={"range": "xx"},
            timeout=120,
        )
        assert r.status_code == 422

    def test_price_history_unknown_player_404(self):
        r = requests.get(
            f"{BASE_URL}/api/v2/players/00000000-0000-0000-0000-000000000000/shares/price-history",
            timeout=120,
        )
        assert r.status_code == 404


# ---- Cron snapshot endpoint ----

class TestSnapshotCron:
    def test_cron_no_auth_401(self):
        r = requests.post(f"{BASE_URL}/api/v2/players/markets/price-snapshots/cron", timeout=30)
        assert r.status_code == 401

    def test_cron_wrong_token_401(self):
        r = requests.post(
            f"{BASE_URL}/api/v2/players/markets/price-snapshots/cron",
            headers={"Authorization": "Bearer wrong"},
            timeout=120,
        )
        assert r.status_code == 401

    def test_cron_valid_token_202_and_idempotent(self):
        headers = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}
        r1 = requests.post(f"{BASE_URL}/api/v2/players/markets/price-snapshots/cron", headers=headers, timeout=30)
        assert r1.status_code == 202, r1.text
        # Second call same day: should still 202 (ON CONFLICT DO NOTHING keeps it idempotent)
        r2 = requests.post(f"{BASE_URL}/api/v2/players/markets/price-snapshots/cron", headers=headers, timeout=30)
        assert r2.status_code == 202
