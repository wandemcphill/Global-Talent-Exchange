"""Assign every tradable player a supply tier (scarcity) and liquidity band.

Scarcity is the lever that lets specific players appreciate despite thousands of
copies elsewhere: high-GSI players land in low-supply tiers (icon/elite), filler in
high-supply tiers. Uses the already-seeded ingestion_supply_tiers /
ingestion_liquidity_bands. Supply tier is chosen by GSI (score = overall/100, matching
the banded pricing model); liquidity band by the current credit price.

Idempotent. Usage:
    python scripts/assign_supply_scarcity.py --database-url <url> [--dry-run]
"""
from __future__ import annotations

import argparse
import sys

import psycopg


def _overall(dna) -> int | None:
    if not isinstance(dna, dict):
        return None
    for key in ("sofifa_overall", "overall"):
        v = dna.get(key)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
    return None


def _pick(bands, value, lo_key, hi_key):
    for code, lo, hi in bands:
        if value >= lo and (hi is None or value <= hi):
            return code
    return bands[-1][0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch-size", type=int, default=1000)
    args = ap.parse_args()

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("select code, min_score, max_score from ingestion_supply_tiers order by rank")
            supply = [(c, float(lo), float(hi)) for c, lo, hi in cur.fetchall()]
            cur.execute("select code, min_price_credits, max_price_credits from ingestion_liquidity_bands order by rank")
            bands = [(c, float(lo), (float(hi) if hi is not None else None)) for c, lo, hi in cur.fetchall()]
            cur.execute("select id, code from ingestion_supply_tiers")
            tier_id = {c: i for i, c in cur.fetchall()}
            cur.execute("select id, code from ingestion_liquidity_bands")
            band_id = {c: i for i, c in cur.fetchall()}

            cur.execute(
                """
                select p.id, p.is_tradable, p.dna_profile, coalesce(s.current_value_credits, 0)
                from ingestion_players p
                left join player_summary_read_models s on s.player_id = p.id
                where p.is_real_player = true or p.source_provider = 'gtex_regen'
                """
            )
            rows = cur.fetchall()

        updates = []
        dist: dict[str, int] = {}
        for pid, tradable, dna, price in rows:
            if not tradable:
                updates.append({"id": pid, "st": None, "lb": None})
                continue
            ov = _overall(dna)
            score = (ov or 0) / 100.0
            st_code = _pick(supply, score, "min", "max")
            lb_code = _pick(bands, float(price or 0), "min", "max")
            dist[st_code] = dist.get(st_code, 0) + 1
            updates.append({"id": pid, "st": tier_id.get(st_code), "lb": band_id.get(lb_code)})

        print(f"players={len(rows)} supply_tier_distribution={dist}")
        if args.dry_run:
            print("DRY RUN — no writes")
            return 0

        with conn.cursor() as cur:
            sql = "update ingestion_players set supply_tier_id=%(st)s, liquidity_band_id=%(lb)s where id=%(id)s"
            for i in range(0, len(updates), args.batch_size):
                cur.executemany(sql, updates[i : i + args.batch_size])
                conn.commit()
                print(f"  committed {min(i + args.batch_size, len(updates))}/{len(updates)}")
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
