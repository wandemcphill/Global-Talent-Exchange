import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import normalize_database_url
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gtex_reprice_dedup")


def calculate_gsi_player_price(current_gsi: int, potential_gsi: int, is_real: bool, is_legend: bool) -> float:
    """Calculates clean player acquisition / share price with potential weighting and low-tier discount.

    - Potential is weighted at 60% and Current Ability at 40% for active players & regens.
    - Low GSI Discount: Players from 70 GSI downwards receive a 60% reduction (multiplier 0.40).
    - Anchor at 90 GSI:
      * Real Player: 250 GTEX Coins (₦25,000)
      * Regen (1-of-1): 500 GTEX Coins (₦50,000)
      * Legend (1-of-1): 900 GTEX Coins (₦90,000)
    """
    cur = max(40, min(99, current_gsi))
    pot = max(cur, min(99, potential_gsi))

    if is_legend:
        eval_gsi = float(pot)
    else:
        eval_gsi = 0.40 * cur + 0.60 * pot

    # Base pricing curve anchored at 90 GSI -> 250 Coins
    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)

    # User rule: Reduce cost of players from 70 GSI downwards by 60% (multiplier 0.40)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        t = (eval_gsi - 70.0) / 5.0
        base_price *= 0.40 + 0.60 * t

    if is_legend:
        return round(base_price * 3.6, 2)
    elif not is_real:
        return round(base_price * 2.0, 2)
    else:
        return round(base_price, 2)


def get_shares_for_gsi(eval_gsi: float) -> tuple[str, int]:
    if eval_gsi >= 97.0:
        return "icon", 100
    elif eval_gsi >= 90.0:
        return "elite", 200
    elif eval_gsi >= 72.0:
        return "core", 400
    elif eval_gsi >= 50.0:
        return "prospect", 600
    else:
        return "discovery", 900


def run_migration():
    logger.info("=== STARTING GTEX UNIVERSE DEDUPLICATION AND REPRICING MIGRATION ===")
    env = dotenv_values(BACKEND_ROOT / ".env")
    db_url = env.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("No DATABASE_URL found!")
        return

    engine = create_engine(normalize_database_url(db_url), connect_args={"prepare_threshold": None})
    SessionLocal = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        # =========================================================================
        # STEP 1: DEDUPLICATION (CANONICAL MERGE)
        # =========================================================================
        logger.info("--- Step 1: Identifying and merging duplicates across providers ---")

        # 1a. Exact (Name + Date of Birth) matches between FM23 and Sportmonks
        dup_rows = session.execute(text("""
            SELECT sm.id as sm_id, fm.id as fm_id, fm.full_name
            FROM ingestion_players fm
            JOIN ingestion_players sm ON LOWER(TRIM(fm.full_name)) = LOWER(TRIM(sm.full_name))
                                     AND fm.date_of_birth = sm.date_of_birth
            WHERE fm.source_provider = 'fm23_genie_scout'
              AND sm.source_provider = 'sportmonks'
              AND fm.is_real_player = true
        """)).fetchall()

        # 1b. Known special cases (e.g. Victor James Osimhen vs Victor Osimhen)
        special_dups = session.execute(text("""
            SELECT sm.id as sm_id, fm.id as fm_id, fm.full_name
            FROM ingestion_players fm
            CROSS JOIN ingestion_players sm
            WHERE fm.source_provider = 'fm23_genie_scout'
              AND sm.source_provider = 'sportmonks'
              AND LOWER(TRIM(fm.full_name)) = 'victor osimhen'
              AND LOWER(TRIM(sm.full_name)) = 'victor james osimhen'
        """)).fetchall()

        # 1c. Sofifa FC25 duplicates matching FM23
        sofifa_dups = session.execute(text("""
            SELECT fc.id as sm_id, fm.id as fm_id, fm.full_name
            FROM ingestion_players fm
            JOIN ingestion_players fc ON LOWER(TRIM(fm.full_name)) = LOWER(TRIM(fc.full_name))
            WHERE fm.source_provider = 'fm23_genie_scout'
              AND fc.source_provider = 'sofifa_fc25'
        """)).fetchall()

        all_duplicates = list(dup_rows) + list(special_dups) + list(sofifa_dups)
        # Unique by duplicate ID (sm_id)
        dedup_map: dict[str, tuple[str, str]] = {}
        for sm_id, fm_id, name in all_duplicates:
            dedup_map[sm_id] = (fm_id, name)

        logger.info("Identified %d duplicate records to retire/link to canonical FM23 assets.", len(dedup_map))

        # Apply deduplication in batches
        dup_ids = list(dedup_map.keys())
        batch_size = 500
        for i in range(0, len(dup_ids), batch_size):
            chunk = dup_ids[i : i + batch_size]
            session.execute(
                text("""
                UPDATE ingestion_players
                SET is_tradable = false,
                    updated_at = :now
                WHERE id = ANY(:ids)
            """),
                {"ids": chunk, "now": now},
            )

            session.execute(
                text("""
                UPDATE player_share_markets
                SET status = 'retired',
                    circulating_shares = 0,
                    updated_at = :now
                WHERE player_id = ANY(:ids)
            """),
                {"ids": chunk, "now": now},
            )
            session.commit()

        logger.info("Successfully retired %d duplicate share markets and marked them non-tradable.", len(dedup_map))

        # =========================================================================
        # STEP 2: REPRICE GTEX_REGEN (12,000 Players - 1-of-1 Indivisible Regens)
        # =========================================================================
        logger.info("--- Step 2: Repricing gtex_regen universe (12,000 players) ---")
        regens = session.execute(text("""
            SELECT id, dna_profile
            FROM ingestion_players
            WHERE source_provider = 'gtex_regen'
        """)).fetchall()

        regen_updates = []
        for p_id, dna_raw in regens:
            dna = dna_raw if isinstance(dna_raw, dict) else {}
            if isinstance(dna_raw, str):
                try:
                    dna = json.loads(dna_raw)
                except Exception:
                    dna = {}
            cur = int(dna.get("overall") or 65)
            pot = int(dna.get("potential") or max(cur, 75))
            price = calculate_gsi_player_price(cur, pot, is_real=False, is_legend=False)
            meta = {
                "asset_type": "regen_single_share",
                "ownership": "100_percent_indivisible",
                "total_shares": 1,
                "current_gsi": cur,
                "potential_gsi": pot,
                "pricing_tier": "gsi_regen",
                "updated_by": "gtex_reprice_dedup_migration",
            }
            regen_updates.append(
                {"pid": p_id, "price": price, "total_shares": 1, "circulating": 1, "meta": json.dumps(meta), "now": now}
            )

        for i in range(0, len(regen_updates), batch_size):
            chunk = regen_updates[i : i + batch_size]
            session.execute(
                text(
                    """
                INSERT INTO player_share_markets (
                    id, player_id, total_shares, circulating_shares, share_price_coin,
                    status, revenue_distributed_coin, metadata_json, created_at, updated_at
                )
                SELECT 
                    p.id, p.id, 1, 1, v.price, 'active', 0.0, v.meta::json, v.now, v.now
                FROM (VALUES """
                    + ", ".join(
                        f"('{r['pid']}', {r['price']}, '{r['meta']}', '{r['now'].isoformat()}'::timestamptz)"
                        for r in chunk
                    )
                    + """) 
                    AS v(pid, price, meta, now)
                JOIN ingestion_players p ON p.id = v.pid
                ON CONFLICT (player_id) DO UPDATE SET
                    share_price_coin = EXCLUDED.share_price_coin,
                    total_shares = 1,
                    circulating_shares = 1,
                    status = 'active',
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at
            """
                )
            )
            session.commit()
            if (i + batch_size) % 3000 == 0 or (i + len(chunk)) == len(regen_updates):
                logger.info(
                    "  Processed %d / %d gtex_regens", min(i + batch_size, len(regen_updates)), len(regen_updates)
                )

        # =========================================================================
        # STEP 3: REPRICE GTEX_NATIONAL_SEED (11,200 Players - 1-of-1 National Regens)
        # =========================================================================
        logger.info("--- Step 3: Repricing gtex_national_seed universe (11,200 players) ---")
        seeds = session.execute(text("""
            SELECT id, dna_profile
            FROM ingestion_players
            WHERE source_provider = 'gtex_national_seed'
        """)).fetchall()

        seed_updates = []
        for p_id, dna_raw in seeds:
            dna = dna_raw if isinstance(dna_raw, dict) else {}
            if isinstance(dna_raw, str):
                try:
                    dna = json.loads(dna_raw)
                except Exception:
                    dna = {}
            cur = int(dna.get("current_rating") or 70)
            pot = int(dna.get("potential_rating") or max(cur, 80))
            price = calculate_gsi_player_price(cur, pot, is_real=False, is_legend=False)
            meta = {
                "asset_type": "national_seed_single_share",
                "ownership": "100_percent_indivisible",
                "total_shares": 1,
                "current_gsi": cur,
                "potential_gsi": pot,
                "pricing_tier": "gsi_national_seed",
                "updated_by": "gtex_reprice_dedup_migration",
            }
            seed_updates.append(
                {"pid": p_id, "price": price, "total_shares": 1, "circulating": 1, "meta": json.dumps(meta), "now": now}
            )

        for i in range(0, len(seed_updates), batch_size):
            chunk = seed_updates[i : i + batch_size]
            session.execute(
                text(
                    """
                INSERT INTO player_share_markets (
                    id, player_id, total_shares, circulating_shares, share_price_coin,
                    status, revenue_distributed_coin, metadata_json, created_at, updated_at
                )
                SELECT 
                    p.id, p.id, 1, 1, v.price, 'active', 0.0, v.meta::json, v.now, v.now
                FROM (VALUES """
                    + ", ".join(
                        f"('{r['pid']}', {r['price']}, '{r['meta']}', '{r['now'].isoformat()}'::timestamptz)"
                        for r in chunk
                    )
                    + """) 
                    AS v(pid, price, meta, now)
                JOIN ingestion_players p ON p.id = v.pid
                ON CONFLICT (player_id) DO UPDATE SET
                    share_price_coin = EXCLUDED.share_price_coin,
                    total_shares = 1,
                    circulating_shares = 1,
                    status = 'active',
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at
            """
                )
            )
            session.commit()
            if (i + batch_size) % 3000 == 0 or (i + len(chunk)) == len(seed_updates):
                logger.info(
                    "  Processed %d / %d gtex_national_seeds", min(i + batch_size, len(seed_updates)), len(seed_updates)
                )

        # =========================================================================
        # STEP 4: REPRICE SPORTMONKS (Active Real Players - Non-Duplicates)
        # =========================================================================
        logger.info("--- Step 4: Repricing sportmonks universe (excluding retired duplicates) ---")
        sm_players = session.execute(text("""
            SELECT id, dna_profile, market_value_eur
            FROM ingestion_players
            WHERE source_provider = 'sportmonks'
              AND is_tradable = true
        """)).fetchall()

        sm_updates = []
        for p_id, dna_raw, mkt_val in sm_players:
            dna = dna_raw if isinstance(dna_raw, dict) else {}
            if isinstance(dna_raw, str):
                try:
                    dna = json.loads(dna_raw)
                except Exception:
                    dna = {}

            # Determine cur and pot
            cur = int(dna.get("overall") or dna.get("sofifa_overall") or 0)
            pot = int(dna.get("potential") or dna.get("sofifa_potential") or 0)

            # Fallback if DNA is empty: infer from market_value_eur
            if cur == 0:
                val = float(mkt_val or 0)
                if val >= 50_000_000:
                    cur, pot = 82, 86
                elif val >= 20_000_000:
                    cur, pot = 77, 81
                elif val >= 5_000_000:
                    cur, pot = 72, 76
                elif val >= 1_000_000:
                    cur, pot = 66, 70
                else:
                    cur, pot = 60, 65
            if pot < cur:
                pot = cur

            eval_gsi = 0.40 * cur + 0.60 * pot
            tier_code, total_shares = get_shares_for_gsi(eval_gsi)
            price = calculate_gsi_player_price(cur, pot, is_real=True, is_legend=False)

            meta = {
                "asset_type": "real_player_fractional",
                "tier_code": tier_code,
                "total_shares": total_shares,
                "current_gsi": cur,
                "potential_gsi": pot,
                "pricing_tier": "gsi_sportmonks",
                "updated_by": "gtex_reprice_dedup_migration",
            }
            sm_updates.append(
                {
                    "pid": p_id,
                    "price": price,
                    "total_shares": total_shares,
                    "circulating": total_shares,
                    "meta": json.dumps(meta),
                    "now": now,
                }
            )

        logger.info("Found %d active non-duplicate Sportmonks players to synchronize.", len(sm_updates))
        for i in range(0, len(sm_updates), batch_size):
            chunk = sm_updates[i : i + batch_size]
            session.execute(
                text(
                    """
                INSERT INTO player_share_markets (
                    id, player_id, total_shares, circulating_shares, share_price_coin,
                    status, revenue_distributed_coin, metadata_json, created_at, updated_at
                )
                SELECT 
                    p.id, p.id, v.shares, v.circ, v.price, 'active', 0.0, v.meta::json, v.now, v.now
                FROM (VALUES """
                    + ", ".join(
                        f"('{r['pid']}', {r['price']}, {r['total_shares']}, {r['circulating']}, '{r['meta']}', '{r['now'].isoformat()}'::timestamptz)"
                        for r in chunk
                    )
                    + """) 
                    AS v(pid, price, shares, circ, meta, now)
                JOIN ingestion_players p ON p.id = v.pid
                ON CONFLICT (player_id) DO UPDATE SET
                    share_price_coin = EXCLUDED.share_price_coin,
                    total_shares = EXCLUDED.total_shares,
                    circulating_shares = EXCLUDED.circulating_shares,
                    status = 'active',
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at
            """
                )
            )
            session.commit()
            if (i + batch_size) % 5000 == 0 or (i + len(chunk)) == len(sm_updates):
                logger.info(
                    "  Processed %d / %d sportmonks players", min(i + batch_size, len(sm_updates)), len(sm_updates)
                )

        # =========================================================================
        # STEP 5: REPRICE SOFIFA_FC25 (Active Real Players - Non-Duplicates)
        # =========================================================================
        logger.info("--- Step 5: Repricing sofifa_fc25 universe (non-duplicates) ---")
        fc_players = session.execute(text("""
            SELECT id, dna_profile
            FROM ingestion_players
            WHERE source_provider = 'sofifa_fc25'
              AND is_tradable = true
        """)).fetchall()

        fc_updates = []
        for p_id, dna_raw in fc_players:
            dna = dna_raw if isinstance(dna_raw, dict) else {}
            if isinstance(dna_raw, str):
                try:
                    dna = json.loads(dna_raw)
                except Exception:
                    dna = {}
            cur = int(dna.get("sofifa_overall") or 65)
            pot = int(dna.get("sofifa_potential") or max(cur, 70))
            eval_gsi = 0.40 * cur + 0.60 * pot
            tier_code, total_shares = get_shares_for_gsi(eval_gsi)
            price = calculate_gsi_player_price(cur, pot, is_real=True, is_legend=False)
            meta = {
                "asset_type": "real_player_fractional",
                "tier_code": tier_code,
                "total_shares": total_shares,
                "current_gsi": cur,
                "potential_gsi": pot,
                "pricing_tier": "gsi_sofifa_fc25",
                "updated_by": "gtex_reprice_dedup_migration",
            }
            fc_updates.append(
                {
                    "pid": p_id,
                    "price": price,
                    "total_shares": total_shares,
                    "circulating": total_shares,
                    "meta": json.dumps(meta),
                    "now": now,
                }
            )

        if fc_updates:
            session.execute(
                text(
                    """
                INSERT INTO player_share_markets (
                    id, player_id, total_shares, circulating_shares, share_price_coin,
                    status, revenue_distributed_coin, metadata_json, created_at, updated_at
                )
                SELECT 
                    p.id, p.id, v.shares, v.circ, v.price, 'active', 0.0, v.meta::json, v.now, v.now
                FROM (VALUES """
                    + ", ".join(
                        f"('{r['pid']}', {r['price']}, {r['total_shares']}, {r['circulating']}, '{r['meta']}', '{r['now'].isoformat()}'::timestamptz)"
                        for r in fc_updates
                    )
                    + """) 
                    AS v(pid, price, shares, circ, meta, now)
                JOIN ingestion_players p ON p.id = v.pid
                ON CONFLICT (player_id) DO UPDATE SET
                    share_price_coin = EXCLUDED.share_price_coin,
                    total_shares = EXCLUDED.total_shares,
                    circulating_shares = EXCLUDED.circulating_shares,
                    status = 'active',
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at
            """
                )
            )
            session.commit()
            logger.info("  Processed %d sofifa_fc25 players", len(fc_updates))

        logger.info("=== GTEX UNIVERSE MIGRATION COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    t0 = time.time()
    run_migration()
    print(f"Total time elapsed: {time.time() - t0:.2f} seconds")
