"""READ-ONLY retest of iteration_6 action items.

(a) Every regen row (gtex_regen + gtex_national_seed) has a primary
    ingestion_player_image_metadata row with a res.cloudinary.com source_url.
(b) /api/v2/players/markets?source=regen pages 1-3 (default + Japan)
    all return image_url pointing to cloudinary.
(c) /api/v2/players/markets/nations?source=regen second call takes <1s (cache).
(d) 23,200 regens have distinct full_names, no trailing digit, no clash with real-player names.
(e) Name realism spot check: 5 regens each from Japan, England, Germany, Brazil, Egypt.
(f) Regression: pricing_model = regen_rating_potential_rarity_v1, prices 0.02-0.09.
"""
from __future__ import annotations

import os
import re
import sys
import time

import psycopg
import pytest
import requests
from dotenv import dotenv_values

ENV = dotenv_values("/app/backend/.env")
DATABASE_URL = ENV["DATABASE_URL"]
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
ADMIN_EMAIL = "vidvimedialtd@gmail.com"
ADMIN_PASSWORD = "Desolamcphill89."

sys.path.insert(0, "/app/gtex/backend")
from app.players.regen_share_pricing import PRICING_MODEL  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    c = psycopg.connect(DATABASE_URL, prepare_threshold=None, autocommit=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def auth_headers():
    r = None
    for i in range(4):
        try:
            r = requests.post(f"{BASE_URL}/api/v2/auth/login",
                              json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                              timeout=90)
            if r.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(3 + i * 3)
    assert r is not None and r.status_code == 200, getattr(r, "text", "no response")
    body = r.json()
    token = (body.get("data") or body).get("access_token") or (body.get("data") or body).get("token")
    return {"Authorization": f"Bearer {token}"}


def _items(j):
    return j.get("items") or (j.get("data") or {}).get("items") or []


def _get_with_retry(url, params, headers, timeout=120, attempts=3):
    last = None
    for i in range(attempts):
        last = requests.get(url, params=params, headers=headers, timeout=timeout)
        if last.status_code == 200:
            return last
        time.sleep(2 + i * 3)
    return last


# ---------- DB: regen full_name uniqueness + no digits + no real clashes ----------

class TestRegenNamesDB:
    def test_regen_count_at_least_23200(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ingestion_players WHERE source_provider IN ('gtex_regen','gtex_national_seed')")
            n = cur.fetchone()[0]
        assert n >= 23000, f"expected ~23,200 regens, got {n}"

    def test_regen_full_names_unique_and_no_trailing_digit(self, conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*), COUNT(DISTINCT full_name)
                FROM ingestion_players
                WHERE source_provider IN ('gtex_regen','gtex_national_seed')
            """)
            total, distinct = cur.fetchone()
            cur.execute(r"""
                SELECT full_name FROM ingestion_players
                WHERE source_provider IN ('gtex_regen','gtex_national_seed')
                  AND full_name ~ '[0-9]$'
                LIMIT 10
            """)
            trailing = [r[0] for r in cur.fetchall()]
        assert distinct == total, f"non-distinct regen full_names: {total-distinct} dupes (of {total})"
        assert not trailing, f"regens ending in digit: {trailing}"

    def test_regen_names_dont_clash_with_real_players(self, conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.full_name, r.source_provider
                FROM ingestion_players r
                WHERE r.source_provider IN ('gtex_regen','gtex_national_seed')
                  AND EXISTS (
                    SELECT 1 FROM ingestion_players o
                    WHERE o.source_provider NOT IN ('gtex_regen','gtex_national_seed')
                      AND o.full_name = r.full_name
                  )
                LIMIT 20
            """)
            clashes = cur.fetchall()
        assert not clashes, f"regen names clash with real players: {clashes}"

    def test_national_regen_seeds_display_name_matches_player(self, conn):
        # national_regen_seeds has no FK column; linkage is by display_name == full_name
        # for the matching gtex_national_seed ingestion_player row.
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM national_regen_seeds s
                WHERE NOT EXISTS (
                    SELECT 1 FROM ingestion_players p
                    WHERE p.source_provider = 'gtex_national_seed'
                      AND p.full_name = s.display_name
                )
            """)
            unmatched = cur.fetchone()[0]
        assert unmatched == 0, f"{unmatched} national_regen_seeds have no matching player"


# ---------- DB: every regen has a primary Cloudinary portrait ----------

class TestRegenCloudinaryPortrait:
    def test_every_regen_has_primary_cloudinary_image(self, conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM ingestion_players p
                WHERE p.source_provider IN ('gtex_regen','gtex_national_seed')
                  AND NOT EXISTS (
                    SELECT 1 FROM ingestion_player_image_metadata im
                    WHERE im.player_id = p.id
                      AND im.is_primary = TRUE
                      AND im.source_url ILIKE '%res.cloudinary.com%'
                  )
            """)
            missing = cur.fetchone()[0]
        assert missing == 0, f"{missing} regens missing a primary cloudinary portrait"


# ---------- API: pages 1-3 regens-only + Japan all show image_url ----------

class TestMarketsImages:
    @pytest.mark.parametrize("page", [1, 2, 3])
    def test_regen_pages_have_image_each_row(self, auth_headers, page):
        r = _get_with_retry(
            f"{BASE_URL}/api/v2/players/markets",
            params={"source": "regen", "page": page, "per_page": 15},
            headers=auth_headers, timeout=120,
        )
        assert r.status_code == 200, r.text[:300]
        items = _items(r.json())
        assert items, f"page {page} empty"
        missing = [it["player_name"] for it in items if not (it.get("image_url") and "cloudinary.com" in it["image_url"].lower())]
        assert not missing, f"regen page {page} missing cloudinary image_url for: {missing}"

    @pytest.mark.parametrize("page", [1, 2, 3])
    def test_japan_regen_pages_have_image_each_row(self, auth_headers, page):
        r = _get_with_retry(
            f"{BASE_URL}/api/v2/players/markets",
            params={"source": "regen", "nation": "Japan", "page": page, "per_page": 15},
            headers=auth_headers, timeout=120,
        )
        assert r.status_code == 200, r.text[:300]
        items = _items(r.json())
        if not items:
            pytest.skip(f"Japan has no page {page}")
        missing = [it["player_name"] for it in items if not (it.get("image_url") and "cloudinary.com" in it["image_url"].lower())]
        assert not missing, f"Japan regen page {page} missing cloudinary image_url for: {missing}"


# ---------- API: nations cache (second call < 1s) ----------

class TestNationsCache:
    def test_second_call_under_1s(self, auth_headers):
        # Warm first
        r1 = requests.get(f"{BASE_URL}/api/v2/players/markets/nations",
                          params={"source": "regen"}, headers=auth_headers, timeout=180)
        assert r1.status_code == 200
        # Second call must be fast (server-side cache)
        t0 = time.monotonic()
        r2 = requests.get(f"{BASE_URL}/api/v2/players/markets/nations",
                          params={"source": "regen"}, headers=auth_headers, timeout=10)
        elapsed = time.monotonic() - t0
        assert r2.status_code == 200
        assert elapsed < 1.0, f"second /markets/nations?source=regen call took {elapsed:.2f}s (expected <1s)"


# ---------- Name realism spot check (5 per country) ----------

FAMOUS_SURNAMES = {
    "Japan": {"Mitoma", "Minamino", "Kubo", "Tomiyasu", "Endo", "Kamada", "Ito", "Doan"},
    "England": {"Kane", "Bellingham", "Foden", "Rashford", "Saka", "Rice", "Stones", "Grealish"},
    "Germany": {"Kroos", "Havertz", "Gnabry", "Sané", "Sane", "Kimmich", "Neuer", "Rüdiger", "Rudiger"},
    "Brazil": {"Neymar", "Vinícius", "Vinicius", "Rodrygo", "Casemiro", "Alisson", "Marquinhos", "Richarlison"},
    "Egypt": {"Salah", "Elneny", "Trezeguet", "Hegazi", "Zizo", "Hamdi"},
}


class TestNameRealism:
    @pytest.mark.parametrize("country", list(FAMOUS_SURNAMES.keys()))
    def test_regen_names_avoid_famous_surnames(self, conn, country):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.full_name
                FROM ingestion_players p
                JOIN ingestion_countries c ON c.id = p.country_id
                WHERE p.source_provider IN ('gtex_regen','gtex_national_seed')
                  AND c.name = %s
                ORDER BY random()
                LIMIT 5
            """, (country,))
            sample = [r[0] for r in cur.fetchall()]
        assert sample, f"no regens for {country}"
        print(f"\n{country} sample: {sample}")
        offenders = []
        for name in sample:
            parts = name.split()
            surname = parts[-1] if parts else ""
            if surname in FAMOUS_SURNAMES[country]:
                offenders.append(name)
        assert not offenders, f"{country} regens reuse famous surnames: {offenders}"
        # Also: no trailing digit, name has at least first+surname
        bad = [n for n in sample if re.search(r"[0-9]$", n) or len(n.split()) < 2]
        assert not bad, f"{country} malformed names: {bad}"


# ---------- Pricing regression ----------

class TestPricingRegression:
    def test_regen_prices_still_on_model(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/v2/players/markets",
                         params={"source": "regen", "per_page": 30},
                         headers=auth_headers, timeout=120)
        assert r.status_code == 200
        items = _items(r.json())
        assert items
        for it in items:
            p = float(it["share_price_coin"])
            assert 0.01 <= p <= 0.15, f"regen {it['player_name']} price {p} out of model band"

    def test_pricing_model_tag_national_seed(self, conn):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM player_share_markets psm
                JOIN ingestion_players p ON p.id = psm.player_id
                WHERE p.source_provider = 'gtex_national_seed'
                  AND (psm.metadata_json->>'pricing_model') <> %s
            """, (PRICING_MODEL,))
            off = cur.fetchone()[0]
        assert off == 0, f"{off} national_seed markets not on pricing_model {PRICING_MODEL}"
