"""Bulk-issue player_share_markets for all gtex_regen players.

Bypasses the ORM's per-player round-trips (which stall the EU pooler at scale)
in favour of 5 bulk SQL statements:

    1. INSERT player_share_markets  (one row per regen)
    2. INSERT wallets               (one liquidity account per regen)
    3. INSERT transactions          (one ledger transaction header per regen)
    4. INSERT ledger_entries        (two entries per regen: +liq, -liq)
    5. INSERT ledger_balance_projections  (one per new wallet)
       + UPDATE clearing account balance

Idempotent: ON CONFLICT DO NOTHING on markets + wallets; entries are only
written when a new wallet row was actually created.

Run with --dry-run to see counts without writing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal

_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace — arbitrary stable seed


def _uuid5(tag: str) -> str:
    return str(uuid.uuid5(_NS, tag))

import psycopg
import psycopg.rows

PLATFORM_CLEARING_WALLET_ID = "891d90db-c71b-44c4-853b-55f67928b69d"
REGEN_PROVIDER = "gtex_regen"


@dataclass
class RegenPlan:
    player_id: str
    player_name: str
    is_real_player: bool
    real_player_tier: str | None
    total_shares: int
    share_price_coin: Decimal
    liquidity_coin: Decimal


def _load_url() -> str | None:
    try:
        for line in open(".env", encoding="utf-8"):
            if line.startswith("GTE_DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        return None
    return None


def compute_plans(conn) -> list[RegenPlan]:
    """Load all regen players not yet having a market; compute their plan."""
    # Import pricing inside the function so sys.path doesn't need patching at module level.
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.players.token_market_defaults import resolve_player_share_market_config
    from app.ingestion.models import Player as _Player  # noqa: F401 — needed for type hints only

    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT p.id, p.canonical_display_name, p.full_name, p.is_real_player,
                   p.real_player_tier, p.market_value_eur, p.current_market_reference_value,
                   p.normalized_position, p.position
            FROM ingestion_players p
            LEFT JOIN player_share_markets psm ON psm.player_id = p.id
            WHERE p.source_provider = %s
              AND p.is_real_player IS FALSE
              AND p.is_tradable IS TRUE
              AND p.country_id IS NOT NULL
              AND (
                    p.current_club_id IS NOT NULL
                    OR p.current_competition_id IS NOT NULL
                    OR p.internal_league_id IS NOT NULL
                    OR NULLIF(BTRIM(p.real_world_club_name), '') IS NOT NULL
                    OR NULLIF(BTRIM(p.real_world_league_name), '') IS NOT NULL
                  )
              AND COALESCE(p.dna_profile ->> 'integrity_hold', 'false') <> 'true'
              AND COALESCE(p.dna_profile ->> 'sanctions', 'false') <> 'true'
              AND COALESCE(p.dna_profile ->> 'manual_block', 'false') <> 'true'
              AND COALESCE(p.dna_profile ->> 'manual_review_required', 'false') <> 'true'
              AND COALESCE(p.dna_profile ->> 'player_share_block', 'false') <> 'true'
              AND COALESCE(p.dna_profile ->> 'share_market_blocked', 'false') <> 'true'
              AND psm.player_id IS NULL
            ORDER BY p.id
            """,
            (REGEN_PROVIDER,),
        )
        rows = cur.fetchall()

    print(f"Regens without a market: {len(rows)}", flush=True)
    if not rows:
        return []

    # Build lightweight player-like objects for the resolver.
    @dataclass
    class _P:
        id: str
        current_market_reference_value: float | None
        market_value_eur: float | None
        normalized_position: str | None
        position: str | None

    plans: list[RegenPlan] = []
    for row in rows:
        p = _P(
            id=row["id"],
            current_market_reference_value=row["current_market_reference_value"],
            market_value_eur=row["market_value_eur"],
            normalized_position=row["normalized_position"],
            position=row["position"],
        )
        cfg = resolve_player_share_market_config(p, total_shares=300, status="active")
        plans.append(
            RegenPlan(
                player_id=row["id"],
                player_name=row["canonical_display_name"] or row["full_name"] or "",
                is_real_player=bool(row["is_real_player"]),
                real_player_tier=row["real_player_tier"],
                total_shares=cfg.total_shares,
                share_price_coin=cfg.share_price_coin,
                liquidity_coin=cfg.liquidity_coin,
            )
        )
    return plans


def liquidity_wallet_code(player_id: str) -> str:
    return f"platform:player_share:{player_id}:liquidity"


def run(plans: list[RegenPlan], conn, *, dry_run: bool) -> dict:
    total_liquidity = sum(p.liquidity_coin for p in plans)

    with conn.cursor() as cur:
        # ── 1. player_share_markets ──────────────────────────────────────────
        market_rows = [
            (
                p.player_id,                   # id (same as player_id for uniqueness)
                p.player_id,                   # player_id
                p.total_shares,
                str(p.share_price_coin),
                "active",
                json.dumps({
                    "player_name": p.player_name,
                    "is_real_player": p.is_real_player,
                    "real_player_tier": p.real_player_tier,
                    "market_issued": True,
                    "auto_initialized": True,
                    "liquidity_coin": str(p.liquidity_coin),
                    "liquidity_account_code": liquidity_wallet_code(p.player_id),
                    "initial_liquidity_coin": str(p.liquidity_coin),
                    "issuance_tier": "discovery",
                    "initial_circulating_cap": 40,
                    "initial_mm_inventory_target": 50,
                    "bulk_issuance_policy": "player_share_issuance_regen.toml",
                }),
            )
            for p in plans
        ]
        cur.executemany(
            """
            INSERT INTO player_share_markets
                (id, player_id, total_shares, share_price_coin, status, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s::json)
            ON CONFLICT (player_id) DO NOTHING
            """,
            market_rows,
        )
        markets_inserted = cur.rowcount if cur.rowcount >= 0 else len(plans)
        print(f"player_share_markets inserted: {markets_inserted}", flush=True)

        # ── 2. wallets (liquidity accounts) ─────────────────────────────────
        wallet_rows = [
            (
                p.player_id,                           # id (reuse player_id for traceability)
                liquidity_wallet_code(p.player_id),    # code
                f"Player share liquidity {p.player_id}",  # label
                "COIN",
                "SYSTEM",
                False,   # allow_negative
                True,    # is_active
            )
            for p in plans
        ]
        cur.executemany(
            """
            INSERT INTO wallets (id, code, label, unit, kind, allow_negative, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            wallet_rows,
        )
        wallets_inserted = cur.rowcount if cur.rowcount >= 0 else len(plans)
        print(f"wallets inserted: {wallets_inserted}", flush=True)

        # ── 3. transactions (one ledger header per regen) ────────────────────
        txn_rows = [
            (
                p.player_id,       # id — reuse player_id for idempotency
                "COMMITTED",
                "ADJUSTMENT",
                "MARKET_TOPUP",
                f"player-share-market-topup:{p.player_id}:bulk",  # reference
                f"Seeded liquidity for player share market {p.player_id}",  # description
                json.dumps({}),
            )
            for p in plans
        ]
        cur.executemany(
            """
            INSERT INTO transactions
                (id, status, reason, source_tag, reference, description, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s::json)
            ON CONFLICT (id) DO NOTHING
            """,
            txn_rows,
        )
        print(f"transactions inserted: {cur.rowcount if cur.rowcount >= 0 else len(plans)}", flush=True)

        # ── 4. ledger_entries (2 per regen) ─────────────────────────────────
        entry_rows = []
        for p in plans:
            # Credit: liquidity wallet gets +liquidity_coin
            entry_rows.append((
                _uuid5(f"{p.player_id}:credit"),
                p.player_id,                  # transaction_id
                p.player_id,                  # account_id = wallet id (same as player_id)
                str(p.liquidity_coin),
                "COIN",
                "ADJUSTMENT",
                f"player-share-market-topup:{p.player_id}:bulk",
                f"Seeded liquidity for player share market {p.player_id}",
                "MARKET_TOPUP",
                "ADJUSTMENT",
            ))
            # Debit: clearing account gets -liquidity_coin
            entry_rows.append((
                _uuid5(f"{p.player_id}:debit"),
                p.player_id,                  # transaction_id
                PLATFORM_CLEARING_WALLET_ID,
                str(-p.liquidity_coin),
                "COIN",
                "ADJUSTMENT",
                f"player-share-market-topup:{p.player_id}:bulk",
                f"Seeded liquidity for player share market {p.player_id}",
                "MARKET_TOPUP",
                "ADJUSTMENT",
            ))
        cur.executemany(
            """
            INSERT INTO ledger_entries
                (id, transaction_id, account_id, amount, unit, reason,
                 reference, description, source_tag, transaction_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            entry_rows,
        )
        print(f"ledger_entries inserted: {cur.rowcount if cur.rowcount >= 0 else len(entry_rows)}", flush=True)

        # ── 5. ledger_balance_projections ────────────────────────────────────
        lbp_rows = [
            (
                p.player_id,   # id
                p.player_id,   # account_id (wallet id)
                "COIN",
                str(p.liquidity_coin),
                p.player_id,   # last_transaction_id
            )
            for p in plans
        ]
        cur.executemany(
            """
            INSERT INTO ledger_balance_projections
                (id, account_id, unit, balance, last_transaction_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (account_id) DO NOTHING
            """,
            lbp_rows,
        )
        print(f"ledger_balance_projections inserted: {cur.rowcount if cur.rowcount >= 0 else len(plans)}", flush=True)

        # Update clearing account balance
        cur.execute(
            """
            UPDATE ledger_balance_projections
            SET balance = balance - %s,
                updated_at = now()
            WHERE account_id = %s
            """,
            (str(total_liquidity), PLATFORM_CLEARING_WALLET_ID),
        )
        print(f"clearing account balance updated (deducted {total_liquidity})", flush=True)

        # ── verification ─────────────────────────────────────────────────────
        cur.execute(
            "select count(*) from player_share_markets m "
            "join ingestion_players p on p.id=m.player_id "
            "where p.source_provider=%s and m.status='active'",
            (REGEN_PROVIDER,),
        )
        regen_markets = cur.fetchone()[0]
        cur.execute("select count(*) from player_share_markets where status='active'")
        total_active = cur.fetchone()[0]
        print(f"regen active markets: {regen_markets}", flush=True)
        print(f"total active markets: {total_active}", flush=True)

        if dry_run:
            conn.rollback()
            print("DRY RUN — rolled back", flush=True)
        else:
            conn.commit()
            print("committed OK", flush=True)

        return {
            "plans": len(plans),
            "total_liquidity_coin": str(total_liquidity),
            "regen_active_markets": regen_markets,
            "total_active_markets": total_active,
            "dry_run": dry_run,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    url = args.database_url or _load_url()
    if not url:
        raise SystemExit("No database URL")

    with psycopg.connect(url, connect_timeout=60) as conn:
        plans = compute_plans(conn)
        if not plans:
            print("Nothing to do — all regens already have markets.")
            return 0
        print(f"Plans computed for {len(plans)} regens", flush=True)
        result = run(plans, conn, dry_run=args.dry_run)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
