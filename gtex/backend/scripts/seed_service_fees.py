"""Seed service-fee pricing rules (fan-coin). 1 fan-coin = ₦1.

Currently sets the fast-match / match-hosting entry fee to 100 fan-coin (= ₦100),
the founder-specified match cost. Idempotent upsert by service_key.

Usage: python scripts/seed_service_fees.py --database-url <url>
"""
from __future__ import annotations

import argparse
import sys

import psycopg

# service_key -> (title, fan-coin price). Fan-coin = ₦1, so price == naira.
FEES: dict[str, tuple[str, int]] = {
    "fast-match-entry": ("Fast Match / match hosting entry", 100),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    args = ap.parse_args()

    sql = """
        insert into service_pricing_rules
            (id, service_key, title, price_coin, price_fancoin_equivalent, active, created_at, updated_at)
        values (gen_random_uuid(), %(key)s, %(title)s, %(price)s, %(price)s, true, now(), now())
        on conflict (service_key) do update
            set title = excluded.title,
                price_coin = excluded.price_coin,
                price_fancoin_equivalent = excluded.price_fancoin_equivalent,
                active = true,
                updated_at = now()
    """
    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            for key, (title, price) in FEES.items():
                cur.execute(sql, {"key": key, "title": title, "price": price})
                print(f"  set {key} = {price} fan-coin (₦{price})")
        conn.commit()
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
