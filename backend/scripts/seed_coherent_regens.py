"""Seed a bounded, coherent FREE-AGENT regen pool into the FastAPI surface.

Targets the tables the GTEX backend actually serves:
  * ingestion_players          -> search / player profile (global_search does select(Player))
  * player_summary_read_models -> market summary / marketplace value

Coherent names come from the country-specific naming pools in app.services.regen_service
(NOT Faker), so nationality/gender are correct. Ratings live in dna_profile JSON, mirroring
the sportmonks rows (e.g. {'overall':57,'potential':73,...}).

Idempotent: all ids are deterministic uuid5(seq), inserted with ON CONFLICT DO NOTHING, so
re-running tops up to --target without duplicating. Regens are unowned free agents
(no club, no holding) since this DB has no clubs/users yet.

Usage:
    PYTHONPATH=. python scripts/seed_coherent_regens.py --database-url <url> --target 12000 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

import psycopg

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.services.regen_service import generate_country_display_name, resolve_country_naming_profile
from scripts.sofifa_pricing import compute_price_credits

SOURCE_PROVIDER = "gtex_regen"
NS = uuid.UUID("5f9b7d2e-0000-4000-8000-000000000001")  # stable namespace for deterministic ids

COUNTRY_WEIGHTS = [
    ("FR", "France", 9), ("BR", "Brazil", 9), ("ES", "Spain", 8), ("DE", "Germany", 7),
    ("IT", "Italy", 7), ("AR", "Argentina", 7), ("EN", "England", 8), ("PT", "Portugal", 6),
    ("NG", "Nigeria", 6), ("GH", "Ghana", 4), ("SN", "Senegal", 4), ("CI", "Ivory Coast", 3),
    ("CM", "Cameroon", 3), ("MA", "Morocco", 4), ("EG", "Egypt", 3), ("ZA", "South Africa", 2),
    ("TR", "Turkey", 5), ("JP", "Japan", 4), ("KR", "South Korea", 3), ("US", "United States", 3),
    ("KE", "Kenya", 2), ("ET", "Ethiopia", 2), ("ML", "Mali", 2), ("CD", "DR Congo", 2),
    ("PL", "Poland", 3), ("RS", "Serbia", 3),
]
# position -> (weight, attribute fracs: pace, shooting, passing, dribbling, defending, physical)
POSITIONS = {
    "GK": (0.12, (0.55, 0.30, 0.70, 0.40, 0.95, 0.85)),
    "DF": (0.33, (0.78, 0.45, 0.72, 0.62, 0.95, 0.92)),
    "MF": (0.30, (0.80, 0.70, 0.95, 0.85, 0.70, 0.78)),
    "FW": (0.25, (0.92, 0.95, 0.72, 0.92, 0.45, 0.80)),
}
NORM_POS = {"GK": "GK", "DF": "defender", "MF": "midfielder", "FW": "forward"}
PERSONALITIES = ("professional", "ambitious", "determined", "leader", "model_citizen", "mercurial")
TRAIT_POOL = ("long_shots", "playmaker", "speedster", "dribbler", "rock", "poacher", "engine", "wall")


def _clamp(v, lo=1, hi=99):
    return max(lo, min(hi, v))


def _pick(rng, items):
    total = sum(w for _k, w in items)
    marker = rng.uniform(0, total)
    run = 0.0
    for k, w in items:
        run += w
        if marker <= run:
            return k
    return items[-1][0]


def build_regens(target: int, seed: int = 20260623):
    rng = random.Random(seed)
    country_items = [((code, name), w) for code, name, w in COUNTRY_WEIGHTS]
    position_items = [(p, m[0]) for p, m in POSITIONS.items()]
    profiles = {c: resolve_country_naming_profile(c, default_country_code="NG") for c, _n, _w in COUNTRY_WEIGHTS}
    used = {c: set() for c, _n, _w in COUNTRY_WEIGHTS}
    now = datetime.now(timezone.utc)
    out = []
    for i in range(target):
        code, nationality = _pick(rng, country_items)
        position = _pick(rng, position_items)
        fr = POSITIONS[position][1]
        _p, name = generate_country_display_name(profiles[code], rng=rng, used_names=used[code])
        age = rng.randint(15, 21)
        overall = _clamp(rng.randint(52, 74) - max(0, 19 - age), 40, 82)
        potential = _clamp(overall + rng.randint(6, 18), overall + 4, 95)
        pace, shooting, passing, dribbling, defending, physical = (_clamp(int(overall * f) + rng.randint(-6, 6)) for f in fr)
        first = name.split(" ", 1)[0]
        last = name.split(" ", 1)[1] if " " in name else None
        ext = f"regen:{i}"
        pid = str(uuid.uuid5(NS, ext))
        dna = {
            "source": "gtex_regen_v2", "overall": overall, "potential": potential,
            "pace": pace, "shooting": shooting, "passing": passing, "dribbling": dribbling,
            "defending": defending, "physical": physical, "nationality": nationality,
            "personality": rng.choice(PERSONALITIES), "traits": rng.sample(TRAIT_POOL, rng.randint(0, 2)),
            "is_regen": True,
        }
        dob = (now - timedelta(days=age * 365)).date()
        mv = float(overall) * 12_000.0
        out.append({
            "id": pid, "ext": ext, "name": name, "first": first, "last": last,
            "position": position, "norm": NORM_POS[position], "dob": dob, "mv": mv,
            "dna": dna, "now": now, "overall": overall, "potential": potential, "nationality": nationality,
            "age": age,
        })
    return out


def insert_players(cur, regens):
    sql = """
    INSERT INTO ingestion_players
      (id, source_provider, provider_external_id, full_name, first_name, last_name, short_name,
       canonical_display_name, position, normalized_position, date_of_birth, preferred_foot,
       last_synced_at, created_at, updated_at, market_value_eur, profile_completeness_score,
       is_tradable, is_real_player, dna_profile, morale)
    VALUES (%(id)s, 'gtex_regen', %(ext)s, %(name)s, %(first)s, %(last)s, %(name)s,
       %(name)s, %(position)s, %(norm)s, %(dob)s, 'right',
       %(now)s, %(now)s, %(now)s, %(mv)s, 0.96,
       true, false, %(dna)s, 50.0)
    ON CONFLICT (source_provider, provider_external_id) DO NOTHING
    """
    rows = [{**r, "dna": json.dumps(r["dna"])} for r in regens]
    cur.executemany(sql, rows)


def insert_summaries(cur, regens):
    sql = """
    INSERT INTO player_summary_read_models
      (player_id, player_name, last_snapshot_at, current_value_credits, previous_value_credits,
       movement_pct, market_interest_score, summary_json, created_at, updated_at)
    VALUES (%(id)s, %(name)s, %(now)s, %(val)s, %(val)s, 0.0, %(interest)s, %(summary)s, %(now)s, %(now)s)
    ON CONFLICT (player_id) DO NOTHING
    """
    rows = []
    for r in regens:
        # Banded pricing, same formula as real players (GSI + age + neutral team,
        # since regens are free agents with no club). Keeps regens coherent with
        # the rest of the market instead of the old overall*25k blow-up.
        val = compute_price_credits(overall=r["overall"], club_rating=None, age=float(r["age"]))[0]
        summary = {"position": r["position"], "nationality": r["nationality"], "overall": r["overall"],
                   "potential": r["potential"], "is_regen": True, "asset_origin": "regen_newgen"}
        rows.append({"id": r["id"], "name": r["name"], "now": r["now"], "val": val,
                     "interest": r["overall"], "summary": json.dumps(summary)})
    cur.executemany(sql, rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--target", type=int, default=12000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    regens = build_regens(args.target)
    print(f"generated {len(regens)} coherent regens (target={args.target})")
    for r in regens[:8]:
        print(f"  {r['name']!r:28} {r['nationality']:14} {r['position']} OVR={r['overall']} POT={r['potential']}")
    if args.dry_run:
        print("DRY RUN — no writes")
        return 0

    with psycopg.connect(args.database_url) as conn:
        cur = conn.cursor()
        cur.execute("select count(*) from ingestion_players where source_provider='gtex_regen'")
        ip_before = cur.fetchone()[0]
        insert_players(cur, regens)
        insert_summaries(cur, regens)
        conn.commit()
        cur.execute("select count(*) from ingestion_players where source_provider='gtex_regen'")
        ip_after = cur.fetchone()[0]
        cur.execute("select count(*) from player_summary_read_models prm join ingestion_players p on p.id=prm.player_id where p.source_provider='gtex_regen'")
        sm = cur.fetchone()[0]
    print(f"ingestion_players regens: before={ip_before} after={ip_after} (+{ip_after - ip_before})")
    print(f"player_summary_read_models for regens: {sm}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
