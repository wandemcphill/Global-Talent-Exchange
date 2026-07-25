"""Appreciation scheduler: recompute every player's frozen price from its
potential-driven effective GSI as it ages. Feed-free — the only moving input is
the passage of time (age advances from stored DOB).

For each real player and regen:
  effective GSI grows from its ingest `overall` toward `potential` by peak age,
  then declines; the banded price (GSI + age + team) is recomputed and written to
  player_summary_read_models.current_value_credits (what the app displays/trades).

Run on a schedule (e.g. weekly) via Render. Idempotent — re-running on the same
day yields the same prices.

Usage:
    python scripts/reprice_appreciation.py --database-url <url> [--as-of YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path
import sys

import psycopg

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from scripts.sofifa_pricing import SOFIFA_SNAPSHOT_DATE, projected_price_credits
from app.value_engine.banded_pricing import share_price_coin_from_credits


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_inputs(source_provider: str, dna) -> tuple[int | None, int | None, int | None]:
    """(overall, potential, club_rating) from dna_profile, handling both key styles."""
    dna = dna if isinstance(dna, dict) else {}
    overall = _int(dna.get("sofifa_overall")) or _int(dna.get("overall"))
    potential = _int(dna.get("sofifa_potential")) or _int(dna.get("potential"))
    club_rating = _int(dna.get("sofifa_club_rating"))  # regens are free agents -> None
    return overall, potential, club_rating


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--as-of", default=None, help="Valuation date YYYY-MM-DD (default: today UTC).")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch-size", type=int, default=1000)
    args = ap.parse_args()

    as_of = (
        datetime.strptime(args.as_of, "%Y-%m-%d").date()
        if args.as_of
        else datetime.now(timezone.utc).date()
    )
    print(f"repricing as-of {as_of}")

    read_sql = """
        select p.id, p.source_provider, p.date_of_birth, p.created_at, p.dna_profile,
               s.current_value_credits
        from ingestion_players p
        join player_summary_read_models s on s.player_id = p.id
        where p.is_real_player = true or p.source_provider = 'gtex_regen'
    """
    update_sql = """
        update player_summary_read_models
        set previous_value_credits = current_value_credits,
            current_value_credits = %(new)s,
            movement_pct = %(mv)s,
            updated_at = now()
        where player_id = %(id)s
    """

    updates: list[dict] = []
    seen = priced = skipped = 0
    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(read_sql)
            for pid, source_provider, dob, created_at, dna, cur_val in cur:
                seen += 1
                overall, potential, club_rating = _extract_inputs(source_provider, dna)
                if overall is None:
                    skipped += 1
                    continue
                anchor = (
                    SOFIFA_SNAPSHOT_DATE
                    if source_provider != "gtex_regen"
                    else (created_at.date() if created_at else as_of)
                )
                new_price, _tier, _ = projected_price_credits(
                    overall=overall,
                    potential=potential,
                    club_rating=club_rating,
                    dob=dob,
                    ingest_date=anchor,
                    as_of=as_of,
                )
                old = float(cur_val or 0.0)
                mv = round((new_price - old) / old * 100.0, 4) if old > 0 else 0.0
                updates.append({"id": pid, "new": round(new_price, 4), "mv": mv})
                priced += 1

        print(f"seen={seen} priced={priced} skipped_no_overall={skipped}")
        if args.dry_run:
            print("DRY RUN — no writes. Sample:")
            for u in updates[:8]:
                print("  ", u)
            return 0

        with conn.cursor() as cur:
            for i in range(0, len(updates), args.batch_size):
                cur.executemany(update_sql, updates[i : i + args.batch_size])
                conn.commit()
                print(f"  committed {min(i + args.batch_size, len(updates))}/{len(updates)}")

        # Re-anchor UNTRADED share markets to the banded fair value so appreciation
        # moves the tradeable price. Traded markets (circulating_shares > 0) are left
        # to their bonding-curve/governor price so we never wipe discovered prices.
        price_by_pid = {u["id"]: u["new"] for u in updates}
        market_updates = []
        with conn.cursor() as cur:
            cur.execute(
                "select player_id, total_shares from player_share_markets where coalesce(circulating_shares,0) = 0"
            )
            for pid, total_shares in cur.fetchall():
                credits = price_by_pid.get(pid)
                if credits is None:
                    continue
                coin = share_price_coin_from_credits(float(credits), int(total_shares or 1000))
                market_updates.append({"pid": pid, "coin": coin})
        if market_updates:
            with conn.cursor() as cur:
                msql = "update player_share_markets set share_price_coin = %(coin)s, updated_at = now() where player_id = %(pid)s"
                for i in range(0, len(market_updates), args.batch_size):
                    cur.executemany(msql, market_updates[i : i + args.batch_size])
                    conn.commit()
            print(f"  re-anchored {len(market_updates)} untraded share markets to fair value")
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
