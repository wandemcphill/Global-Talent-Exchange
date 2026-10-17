"""READ-ONLY tests for pre-seeded national regens.

Covers:
- national_regen_seeds table structure/content (11,200 rows, unique names, portraitUrl, country codes)
- Culture naming per country
- Portrait URLs resolve to image/png on Cloudinary
- Tradeable: ingestion_players + player_share_markets exist
- API endpoints: /markets search, /shares/market, /market/players/{id}
- Regression: national-team rental-pool warm call still 200 fast
"""
import os
import re
import time
import random
import pytest
import psycopg
import requests
from dotenv import dotenv_values

ENV = dotenv_values("/app/backend/.env")
DATABASE_URL = ENV["DATABASE_URL"]
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "vidvimedialtd@gmail.com"
ADMIN_PASSWORD = "Desolamcphill89."

NATHAN_ID = "0c2fa2ac-9be8-5657-9205-5c6e0e33e91d"


# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def pg():
    conn = psycopg.connect(DATABASE_URL, prepare_threshold=None, connect_timeout=15)
    conn.read_only = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token") or (data.get("data") or {}).get("access_token")
    assert tok, f"no token in {data}"
    return tok


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- DB structural tests ----------

class TestNationalRegenSeedsTable:

    def test_total_row_count_11200(self, pg):
        with pg.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM national_regen_seeds")
            total = cur.fetchone()[0]
        assert total == 11200, f"expected 11200 seeds, got {total}"

    def test_display_names_all_distinct(self, pg):
        with pg.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT display_name), COUNT(*) FROM national_regen_seeds")
            distinct, total = cur.fetchone()
        assert distinct == total, f"display_name not unique: {distinct} distinct vs {total} rows"

    def test_no_display_name_ends_with_digit(self, pg):
        with pg.cursor() as cur:
            cur.execute("SELECT display_name FROM national_regen_seeds WHERE display_name ~ '[0-9]$' LIMIT 10")
            bad = cur.fetchall()
        assert not bad, f"display_name ending in digit: {bad}"

    def test_naming_country_matches_country_code(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT country_code, metadata_json->>'naming_country_code', display_name
                FROM national_regen_seeds
                WHERE metadata_json->>'naming_country_code' IS DISTINCT FROM country_code
                LIMIT 10
            """)
            mismatches = cur.fetchall()
        assert not mismatches, f"naming_country_code mismatches: {mismatches}"

    def test_all_portrait_urls_cloudinary(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM national_regen_seeds
                WHERE COALESCE(metadata_json->>'portraitUrl','') NOT LIKE 'https://res.cloudinary.com/%'
            """)
            bad = cur.fetchone()[0]
        assert bad == 0, f"{bad} seeds without cloudinary portraitUrl"

    def test_country_codes_look_iso(self, pg):
        with pg.cursor() as cur:
            cur.execute("SELECT DISTINCT country_code FROM national_regen_seeds ORDER BY country_code")
            codes = [r[0] for r in cur.fetchall()]
        assert all(re.fullmatch(r"[A-Z]{2}", c) for c in codes), f"non 2-letter codes: {codes}"
        for special in ("EN", "SC", "NI"):
            assert special in codes, f"missing {special}"

    def test_ie_cz_tr_have_140(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT country_code, COUNT(*)
                FROM national_regen_seeds
                WHERE country_code IN ('IE','CZ','TR')
                GROUP BY country_code
            """)
            counts = dict(cur.fetchall())
        for cc in ("IE", "CZ", "TR"):
            assert counts.get(cc) == 140, f"{cc} count = {counts.get(cc)} (expected 140)"


# ---------- Cultural naming sanity ----------

# Heuristic lists; names expected to CONTAIN at least one of these tokens for each country.
CULTURE_HINTS = {
    "JP": ["Haruto","Yuto","Yuki","Sota","Ren","Riku","Kaito","Takumi","Hiroshi","Sato","Suzuki","Tanaka","Watanabe","Kobayashi","Yamamoto","Ito","Nakamura","Takahashi","Kato","Yoshida","Yamada","Sasaki","Matsumoto"],
    "BR": ["Silva","Santos","Oliveira","Souza","Pereira","Lima","Costa","Gomes","Ribeiro","Carvalho","Almeida","Rodrigues","Ferreira","Barbosa","Araujo","Thiago","Lucas","Gabriel","Rafael","Rodrigo","Felipe","Matheus","Guilherme","Bruno","Rafael","da ","dos ","de "],
    "NG": ["Chukwu","Okafor","Okeke","Eze","Nwosu","Adeyemi","Adewale","Oluwaseun","Chinedu","Emeka","Ifeanyi","Kelechi","Obinna","Olumide","Tunde","Yemi","Oluwa","Chi","Ade","Ola","Babatunde","Oluwatobi","Ndubuisi","Chidi","Uche","Chijioke","Chuks","Ikenna","Obi","Nnamdi","Okon"],
    "IE": ["Murphy","O'","Mc","Kelly","Byrne","Ryan","Sullivan","Walsh","Smith","O’","Conor","Sean","Cian","Oisin","Cillian","Aidan","Niall","Padraig","Fionn","Darragh","Eoin","Ronan","Liam","Molumby","Doherty","Kavanagh","Nolan","McCarthy","McMahon"],
    "SC": ["Mac","Mc","Campbell","Stewart","Robertson","Thomson","Ferguson","Fraser","Angus","Hamish","Rory","Lachlan","Ewan","Finlay","Callum","Dougie","Craig","Gordon","Grant","Murray","Wallace","Ross","Munro","Buchanan"],
    "SA": ["Al-","Al ","Mohammed","Mohamed","Ahmed","Abdul","Abdullah","Hassan","Hussein","Khalid","Faisal","Fahad","Saud","Ali","Omar","Yousef","Nasser","Sultan","Majed","Turki","Bin ","bin "],
    "KR": ["Kim","Lee","Park","Choi","Jung","Jeong","Kang","Cho","Yoon","Jang","Lim","Han","Oh","Shin","Suh","Seo","Hwang","Song","Min-","Jun","Ji-","Hyun","Seung","Woo","Jin","Dong-","Sung","Soo"],
    "DE": ["Müller","Muller","Schmidt","Schneider","Fischer","Weber","Meyer","Wagner","Becker","Schulz","Hoffmann","Schäfer","Schafer","Bauer","Koch","Richter","Klein","Wolf","Neumann","Schwarz","Zimmermann","Lukas","Jonas","Leon","Finn","Maximilian","Felix","Niklas","Tim","Jan","Lars"],
    "MX": ["García","Garcia","Hernández","Hernandez","Martínez","Martinez","López","Lopez","González","Gonzalez","Rodríguez","Rodriguez","Pérez","Perez","Sánchez","Sanchez","Ramírez","Ramirez","Flores","Rivera","Torres","Diego","Santiago","Mateo","Alejandro","Carlos","Luis","Juan","Miguel","José","Jose","Jesús","Jesus"],
}


class TestCulturalNaming:

    @pytest.mark.parametrize("country", list(CULTURE_HINTS.keys()))
    def test_sample_names_fit_culture(self, pg, country):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT display_name FROM national_regen_seeds
                WHERE country_code = %s
                ORDER BY display_name
                LIMIT 50
            """, (country,))
            names = [r[0] for r in cur.fetchall()]
        assert names, f"no seeds for {country}"
        sample = random.sample(names, min(5, len(names)))
        hits = sum(1 for n in sample if any(tok in n for tok in CULTURE_HINTS[country]))
        assert hits >= 2, f"{country} sample {sample} didn't match culture hints"

    def test_no_nigerian_names_outside_ng(self, pg):
        # Pick strong NG surnames extremely unlikely elsewhere
        ng_tokens = ("Chukwu","Okafor","Okeke","Nwosu","Chinedu","Chijioke","Ikenna","Nnamdi","Ndubuisi","Oluwaseun")
        with pg.cursor() as cur:
            like = " OR ".join([f"display_name LIKE '%{t}%'" for t in ng_tokens])
            cur.execute(f"""
                SELECT country_code, display_name FROM national_regen_seeds
                WHERE country_code <> 'NG' AND ({like})
                LIMIT 5
            """)
            leaks = cur.fetchall()
        assert not leaks, f"Nigerian names leaked outside NG: {leaks}"


# ---------- Portrait URL fetching ----------

class TestPortraits:

    def test_random_portraits_load_png(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT metadata_json->>'portraitUrl', country_code,
                       metadata_json->>'portraitEthnicity'
                FROM national_regen_seeds
                ORDER BY random()
                LIMIT 10
            """)
            rows = cur.fetchall()
        assert len(rows) == 10
        failures = []
        for url, cc, eth in rows:
            try:
                r = requests.get(url, timeout=20)
                ok = r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image/")
                if not ok:
                    failures.append((url, r.status_code, r.headers.get("Content-Type")))
            except Exception as e:
                failures.append((url, "exc", str(e)))
        assert not failures, f"portrait fetch failures: {failures}"

    def test_portrait_ethnicity_plausible(self, pg):
        checks = {
            "JP": ("East",),
            "KR": ("East",),
            "IE": ("North", "European"),
            "SC": ("North", "European"),
            "NG": ("African",),
            "DE": ("European",),
            "SA": ("Arab", "Middle"),
            "BR": ("Latin", "South", "American", "European", "African", "Mixed", "Hispanic"),
            "MX": ("Latin", "South", "American", "European", "Mixed", "Hispanic"),
        }
        with pg.cursor() as cur:
            for cc, tokens in checks.items():
                cur.execute("""
                    SELECT metadata_json->>'portraitEthnicity'
                    FROM national_regen_seeds
                    WHERE country_code=%s AND metadata_json->>'portraitEthnicity' IS NOT NULL
                    LIMIT 20
                """, (cc,))
                vals = [r[0] for r in cur.fetchall() if r[0]]
                if not vals:
                    continue  # ethnicity optional
                hits = sum(1 for v in vals if any(t.lower() in v.lower() for t in tokens))
                assert hits >= max(1, len(vals)//2), f"{cc} ethnicities implausible: {vals}"


# ---------- Tradeable: DB joins ----------

class TestTradeability:

    def test_every_seed_has_ingestion_player(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM national_regen_seeds s
                LEFT JOIN ingestion_players ip
                  ON ip.source_provider='gtex_national_seed'
                 AND ip.provider_external_id = s.id::text
                WHERE ip.id IS NULL
            """)
            missing = cur.fetchone()[0]
        assert missing == 0, f"{missing} seeds without ingestion_players row"

    def test_all_ingestion_rows_tradable(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM ingestion_players
                WHERE source_provider='gtex_national_seed' AND is_tradable IS NOT TRUE
            """)
            n = cur.fetchone()[0]
        assert n == 0, f"{n} ingestion rows not tradable"

    def test_every_seed_has_active_market(self, pg):
        with pg.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM national_regen_seeds s
                JOIN ingestion_players ip
                  ON ip.source_provider='gtex_national_seed'
                 AND ip.provider_external_id = s.id::text
                LEFT JOIN player_share_markets m
                  ON m.player_id = ip.id AND m.status='active'
                WHERE m.id IS NULL
            """)
            missing = cur.fetchone()[0]
        assert missing == 0, f"{missing} seeds without active player_share_markets row"


# ---------- API endpoints ----------

class TestMarketAPIs:

    def test_search_nathan_molumby(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/v2/players/markets",
                         params={"search": "Nathan Molumby"},
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        body = r.json()
        items = body.get("data") or body.get("items") or body.get("results") or body
        if isinstance(items, dict):
            items = items.get("items") or items.get("data") or []
        assert items, f"no results for Nathan Molumby: {body}"
        txt = str(items).lower()
        assert "molumby" in txt, f"Molumby not in response: {items}"
        assert "ireland" in txt or "irish" in txt or "ie" in txt, f"Ireland hint not in: {items}"

    def test_nathan_shares_market(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/v2/players/{NATHAN_ID}/shares/market",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"

    def test_nathan_market_profile(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/market/players/{NATHAN_ID}",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        body = r.json()
        payload = body.get("data", body)
        identity = payload.get("identity") or {}
        img = identity.get("image_url") or ""
        assert img.startswith("https://res.cloudinary.com/"), f"image_url not Cloudinary: {img}"
        attrs = payload.get("attributes") or {}
        overall = attrs.get("overall") or payload.get("overall")
        potential = attrs.get("potential") or payload.get("potential")
        assert overall == 72, f"overall expected 72 got {overall}; payload keys={list(payload.keys())}"
        assert potential == 92, f"potential expected 92 got {potential}"


class TestNationalRentalPoolRegression:

    def test_rental_pool_warm_200(self, auth_headers):
        url = (f"{BASE_URL}/api/national-team-engine/competitions/"
               f"8e33f8f7-f18e-48c8-9eed-a678639b56cc/rental-pool"
               f"?limit=12&entry_id=3487e6de-cbe3-4344-abbc-e969026e0e01&country_code=NG")
        # warm
        requests.get(url, headers=auth_headers, timeout=90)
        t0 = time.time()
        r = requests.get(url, headers=auth_headers, timeout=90)
        elapsed = time.time() - t0
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert elapsed < 15, f"warm call slow: {elapsed:.1f}s"
