"""Reprice untraded national-regen share markets with the rating/potential/rarity model.

Only markets with circulating_shares == 0 are touched, so no holder's position is revalued.
Usage: python scripts/reprice_national_regen_markets.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from app.players.regen_share_pricing import PRICING_MODEL, regen_share_price  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None, connect_timeout=60) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """select m.id, m.share_price_coin, m.metadata_json, p.dna_profile from player_share_markets m
                   join ingestion_players p on p.id = m.player_id
                   where p.source_provider = 'gtex_national_seed' and m.circulating_shares = 0"""
            )
            rows = cur.fetchall()
        updates, by_rarity = [], Counter()
        samples: dict[str, list[Decimal]] = {}
        for market_id, old_price, meta, dna in rows:
            dna = dna or {}
            price = regen_share_price(dna.get("current_rating"), dna.get("potential_rating"), dna.get("rarity_tier"))
            meta = dict(meta or {})
            meta.update({"pricing_model": PRICING_MODEL, "initial_share_price_coin": str(price), "previous_share_price_coin": str(old_price)})
            updates.append((price, json.dumps(meta), market_id))
            rarity = str(dna.get("rarity_tier") or "common")
            by_rarity[rarity] += 1
            samples.setdefault(rarity, []).append(price)
        for rarity, prices in samples.items():
            prices.sort()
            print(rarity, by_rarity[rarity], "min", prices[0], "median", prices[len(prices) // 2], "max", prices[-1])
        if args.dry_run:
            return 0
        with conn.cursor() as cur:
            cur.executemany("update player_share_markets set share_price_coin=%s, metadata_json=%s::json, updated_at=now() where id=%s", updates)
        conn.commit()
        print("repriced", len(updates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
