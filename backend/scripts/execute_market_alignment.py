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
logger = logging.getLogger("gtex_market_alignment")

def calculate_gsi_player_price(current_gsi: int, potential_gsi: int, is_real: bool, is_legend: bool) -> float:
    cur = max(40, min(99, current_gsi))
    pot = max(cur, min(99, potential_gsi))

    if is_legend:
        eval_gsi = float(pot)
    else:
        eval_gsi = 0.40 * cur + 0.60 * pot

    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        t = (eval_gsi - 70.0) / 5.0
        base_price *= (0.40 + 0.60 * t)

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


def run_alignment():
    logger.info("=== STARTING GTEX MARKET VALUE & GSI ALIGNMENT ===")
    env = dotenv_values(BACKEND_ROOT / ".env")
    db_url = env.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    engine = create_engine(normalize_database_url(db_url), connect_args={"prepare_threshold": None})
    SessionLocal = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        # =========================================================================
        # 1. CRISTIANO RONALDO UPGRADE (To 98 GSI Prime GOAT Legend)
        # =========================================================================
        logger.info("--- 1. Upgrading Cristiano Ronaldo to 98 GSI Prime Legend ---")
        cr7_id = "6e5ecc38-5ebe-453e-8ebb-9e297b6fbf0b"
        cr7_price = calculate_gsi_player_price(98, 98, is_real=True, is_legend=True) # 1181.93 Coins
        cr7_val = 195_000_000.0

        cr7_dna = {
            "portraitUrl": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/26/Cristiano_Ronaldo_Croatia_v_Portugal_2_July_2026-075_%28cropped%29.jpg/330px-Cristiano_Ronaldo_Croatia_v_Portugal_2_July_2026-075_%28cropped%29.jpg",
            "portraitStatus": "ready",
            "overall": 98,
            "potential": 98,
            "current_rating": 98,
            "potential_rating": 98,
            "attributes": {
                "finishing": 20,
                "heading": 20,
                "jumping": 20,
                "shot_power": 20,
                "penalties": 20,
                "determination": 20,
                "pace": 19,
                "acceleration": 19,
                "off_the_ball": 20,
                "composure": 19,
                "strength": 19,
                "stamina": 19,
                "dribbling": 18,
                "flair": 19,
                "long_shots": 19,
                "free_kicks": 18
            },
            "playstyle": "All-Time Iconic Ultimate Goal Machine & Complete Athletic Apex Forward",
            "traits": [
                "Shoots With Power",
                "Runs With Ball Often",
                "Cuts Inside From Both Wings",
                "Aerial Colossus",
                "Penalty Specialist",
                "Big Match Clutch Performer"
            ],
            "honors": [
                "5x Ballon d'Or Winner",
                "5x UEFA Champions League Winner",
                "UEFA Euro 2016 Champion",
                "All-Time International Top Goalscorer (130+ Goals)",
                "All-Time UEFA Champions League Top Goalscorer (140 Goals)",
                "4x European Golden Shoe"
            ]
        }
        cr7_meta = {
            "asset_type": "legend_single_share",
            "ownership": "100_percent_indivisible",
            "total_shares": 1,
            "current_gsi": 98,
            "potential_gsi": 98,
            "pricing_tier": "gsi_goat_legend",
            "updated_by": "cr7_goat_upgrade"
        }

        session.execute(text("""
            UPDATE ingestion_players SET
                potential = 98,
                market_value_eur = :val,
                current_market_reference_value = :val,
                dna_profile = :dna,
                updated_at = :now
            WHERE id = :id
        """), {"id": cr7_id, "val": cr7_val, "dna": json.dumps(cr7_dna), "now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 1,
                circulating_shares = 1,
                share_price_coin = :price,
                metadata_json = :meta,
                updated_at = :now
            WHERE player_id = :id
        """), {"id": cr7_id, "price": cr7_price, "meta": json.dumps(cr7_meta), "now": now})

        # Retire duplicate Sportmonks CR7
        session.execute(text("UPDATE ingestion_players SET is_tradable = false WHERE id = '070f38a3-87ae-4a1f-8b05-74d8dab4c778'"))
        session.execute(text("UPDATE player_share_markets SET status = 'retired', circulating_shares = 0 WHERE player_id = '070f38a3-87ae-4a1f-8b05-74d8dab4c778'"))
        session.commit()
        logger.info("Cristiano Ronaldo upgraded to 98 GSI (Price: %.2f Coins). Duplicate retired.", cr7_price)

        # =========================================================================
        # 2. THIERRY HENRY DOWNGRADE (To 95 GSI Invincible Legend)
        # =========================================================================
        logger.info("--- 2. Downgrading Thierry Henry from 99 to 95 GSI ---")
        henry_id = "52801d1f-4b08-4af9-acab-cdc090a6edc5"
        henry_price = calculate_gsi_player_price(95, 95, is_real=True, is_legend=True) # 1070.00 Coins
        henry_val = 145_000_000.0

        henry_dna = {
            "portraitUrl": "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b9/Thierry_Henry_%2851649035951%29_%28cropped%29.jpg/330px-Thierry_Henry_%2851649035951%29_%28cropped%29.jpg",
            "portraitStatus": "ready",
            "overall": 95,
            "potential": 95,
            "current_rating": 95,
            "potential_rating": 95,
            "attributes": {
                "pace": 19,
                "acceleration": 19,
                "finishing": 18,
                "dribbling": 18,
                "technique": 18,
                "off_the_ball": 18,
                "passing": 17,
                "agility": 17,
                "composure": 18,
                "flair": 18,
                "vision": 17
            },
            "playstyle": "Premier League Invincible King & Elegance In Motion",
            "traits": [
                "Places Shots",
                "Runs With Ball Down Left",
                "Likes To Try To Beat Offside Trap",
                "Curls Ball"
            ],
            "honors": [
                "FIFA World Cup Champion 1998",
                "UEFA Euro 2000 Champion",
                "UEFA Champions League Winner 2008-09 (Barcelona)",
                "2x Premier League Champion (Arsenal Invincibles)",
                "4x Premier League Golden Boot",
                "Arsenal All-Time Record Goalscorer (228 Goals)"
            ]
        }
        henry_meta = {
            "asset_type": "legend_single_share",
            "ownership": "100_percent_indivisible",
            "total_shares": 1,
            "current_gsi": 95,
            "potential_gsi": 95,
            "pricing_tier": "gsi_legend",
            "updated_by": "henry_calibrated_downgrade"
        }

        session.execute(text("""
            UPDATE ingestion_players SET
                potential = 95,
                market_value_eur = :val,
                current_market_reference_value = :val,
                dna_profile = :dna,
                updated_at = :now
            WHERE id = :id
        """), {"id": henry_id, "val": henry_val, "dna": json.dumps(henry_dna), "now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 1,
                circulating_shares = 1,
                share_price_coin = :price,
                metadata_json = :meta,
                updated_at = :now
            WHERE player_id = :id
        """), {"id": henry_id, "price": henry_price, "meta": json.dumps(henry_meta), "now": now})
        session.commit()
        logger.info("Thierry Henry downgraded to 95 GSI (Price: %.2f Coins).", henry_price)

        # =========================================================================
        # 3. RETIRE INEXACT REMAINING DUPLICATES (Sportmonks vs FM23)
        # =========================================================================
        logger.info("--- 3. Retiring remaining inexact superstar duplicates in Sportmonks ---")
        inexact_duplicate_names = [
            "Lamine Yamal Nasraoui Ebana%",
            "Phil Foden",
            "Harry Kane",
            "Kevin De Bruyne",
            "Erling Haaland",
            "Mohamed Salah Ghaly",
            "Bukayo Saka",
            "Jamal Musiala",
            "Federico Santiago Valverde Dipetta"
        ]
        retired_count = 0
        for pattern in inexact_duplicate_names:
            rows = session.execute(text("""
                SELECT id FROM ingestion_players 
                WHERE source_provider = 'sportmonks' AND full_name ILIKE :p AND is_tradable = true
            """), {"p": pattern}).fetchall()
            for r in rows:
                session.execute(text("UPDATE ingestion_players SET is_tradable = false WHERE id = :id"), {"id": r[0]})
                session.execute(text("UPDATE player_share_markets SET status = 'retired', circulating_shares = 0 WHERE player_id = :id"), {"id": r[0]})
                retired_count += 1
        session.commit()
        logger.info("Retired %d remaining inexact superstar duplicates.", retired_count)

        # =========================================================================
        # 4. UPGRADE KEY WORLD STARS (Mbappé, Vini Jr, Rodri, Van Dijk, etc.)
        # =========================================================================
        logger.info("--- 4. Upgrading key world superstars to elite tier ---")
        
        # 4a. Kylian Mbappé
        mbappe_price = calculate_gsi_player_price(92, 95, is_real=True, is_legend=False) # 283.47 Coins
        session.execute(text("""
            UPDATE ingestion_players SET
                full_name = 'Kylian Mbappé',
                position = 'ST',
                normalized_position = 'ST',
                secondary_positions_json = '["LW", "RW"]',
                real_world_club_name = 'Real Madrid',
                real_world_league_name = 'La Liga',
                potential = 95,
                market_value_eur = 180000000.0,
                current_market_reference_value = 180000000.0,
                real_player_tier = 'marquee',
                supply_tier_id = '00000000-0000-0000-0000-000000001002',
                is_tradable = true,
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{overall}', '92'::jsonb
                ) || '{"potential": 95, "current_rating": 92, "potential_rating": 95}'::jsonb,
                updated_at = :now
            WHERE full_name ILIKE '%Kylian Mbappé%' AND source_provider = 'sportmonks'
        """), {"now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 200,
                circulating_shares = 40,
                share_price_coin = :price,
                status = 'active',
                updated_at = :now
            WHERE player_id IN (SELECT id FROM ingestion_players WHERE full_name ILIKE '%Kylian Mbappé%' AND source_provider = 'sportmonks')
        """), {"price": mbappe_price, "now": now})

        # 4b. Vinicius Junior
        vini_price = calculate_gsi_player_price(91, 94, is_real=True, is_legend=False) # 275.69 Coins
        session.execute(text("""
            UPDATE ingestion_players SET
                full_name = 'Vinicius Junior',
                position = 'LW',
                normalized_position = 'LW',
                secondary_positions_json = '["ST", "RW"]',
                real_world_club_name = 'Real Madrid',
                real_world_league_name = 'La Liga',
                potential = 94,
                market_value_eur = 180000000.0,
                current_market_reference_value = 180000000.0,
                real_player_tier = 'marquee',
                supply_tier_id = '00000000-0000-0000-0000-000000001002',
                is_tradable = true,
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{overall}', '91'::jsonb
                ) || '{"potential": 94, "current_rating": 91, "potential_rating": 94}'::jsonb,
                updated_at = :now
            WHERE full_name ILIKE '%Vinicius José Paixão%' AND source_provider = 'sportmonks'
        """), {"now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 200,
                circulating_shares = 40,
                share_price_coin = :price,
                status = 'active',
                updated_at = :now
            WHERE player_id IN (SELECT id FROM ingestion_players WHERE full_name ILIKE '%Vinicius José Paixão%' AND source_provider = 'sportmonks')
        """), {"price": vini_price, "now": now})

        # 4c. Rodri (Rodrigo Hernández)
        rodri_price = calculate_gsi_player_price(91, 92, is_real=True, is_legend=False) # 264.50 Coins
        session.execute(text("""
            UPDATE ingestion_players SET
                full_name = 'Rodri (Rodrigo Hernández)',
                position = 'DM',
                normalized_position = 'DM',
                secondary_positions_json = '["CM"]',
                real_world_club_name = 'Manchester City',
                real_world_league_name = 'Premier League',
                potential = 92,
                market_value_eur = 130000000.0,
                current_market_reference_value = 130000000.0,
                real_player_tier = 'marquee',
                supply_tier_id = '00000000-0000-0000-0000-000000001002',
                is_tradable = true,
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{overall}', '91'::jsonb
                ) || '{"potential": 92, "current_rating": 91, "potential_rating": 92}'::jsonb,
                updated_at = :now
            WHERE full_name ILIKE '%Rodrigo Hernández Cascante%' AND source_provider = 'sportmonks'
        """), {"now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 200,
                circulating_shares = 40,
                share_price_coin = :price,
                status = 'active',
                updated_at = :now
            WHERE player_id IN (SELECT id FROM ingestion_players WHERE full_name ILIKE '%Rodrigo Hernández Cascante%' AND source_provider = 'sportmonks')
        """), {"price": rodri_price, "now": now})

        # 4d. Virgil van Dijk
        vvd_price = calculate_gsi_player_price(90, 90, is_real=True, is_legend=False) # 250.00 Coins
        session.execute(text("""
            UPDATE ingestion_players SET
                full_name = 'Virgil van Dijk',
                position = 'CB',
                normalized_position = 'CB',
                real_world_club_name = 'Liverpool',
                real_world_league_name = 'Premier League',
                potential = 90,
                market_value_eur = 35000000.0,
                current_market_reference_value = 35000000.0,
                real_player_tier = 'marquee',
                supply_tier_id = '00000000-0000-0000-0000-000000001002',
                is_tradable = true,
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{overall}', '90'::jsonb
                ) || '{"potential": 90, "current_rating": 90, "potential_rating": 90}'::jsonb,
                updated_at = :now
            WHERE full_name ILIKE '%Virgil van Dijk%' AND source_provider = 'sportmonks'
        """), {"now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 200,
                circulating_shares = 40,
                share_price_coin = :price,
                status = 'active',
                updated_at = :now
            WHERE player_id IN (SELECT id FROM ingestion_players WHERE full_name ILIKE '%Virgil van Dijk%' AND source_provider = 'sportmonks')
        """), {"price": vvd_price, "now": now})

        # 4e. Robert Lewandowski
        lewa_price = calculate_gsi_player_price(89, 89, is_real=True, is_legend=False) # 241.22 Coins
        session.execute(text("""
            UPDATE ingestion_players SET
                full_name = 'Robert Lewandowski',
                position = 'ST',
                normalized_position = 'ST',
                real_world_club_name = 'FC Barcelona',
                real_world_league_name = 'La Liga',
                potential = 89,
                market_value_eur = 15000000.0,
                current_market_reference_value = 15000000.0,
                real_player_tier = 'marquee',
                supply_tier_id = '00000000-0000-0000-0000-000000001003',
                is_tradable = true,
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{overall}', '89'::jsonb
                ) || '{"potential": 89, "current_rating": 89, "potential_rating": 89}'::jsonb,
                updated_at = :now
            WHERE full_name ILIKE '%Robert Lewandowski%' AND source_provider = 'sportmonks'
        """), {"now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 400,
                circulating_shares = 80,
                share_price_coin = :price,
                status = 'active',
                updated_at = :now
            WHERE player_id IN (SELECT id FROM ingestion_players WHERE full_name ILIKE '%Robert Lewandowski%' AND source_provider = 'sportmonks')
        """), {"price": lewa_price, "now": now})

        # 4f. Alisson Becker
        alisson_price = calculate_gsi_player_price(89, 89, is_real=True, is_legend=False) # 241.22 Coins
        session.execute(text("""
            UPDATE ingestion_players SET
                full_name = 'Alisson Becker',
                position = 'GK',
                normalized_position = 'GK',
                real_world_club_name = 'Liverpool',
                real_world_league_name = 'Premier League',
                potential = 89,
                market_value_eur = 28000000.0,
                current_market_reference_value = 28000000.0,
                real_player_tier = 'marquee',
                supply_tier_id = '00000000-0000-0000-0000-000000001003',
                is_tradable = true,
                dna_profile = jsonb_set(
                    COALESCE(dna_profile::jsonb, '{}'::jsonb),
                    '{overall}', '89'::jsonb
                ) || '{"potential": 89, "current_rating": 89, "potential_rating": 89}'::jsonb,
                updated_at = :now
            WHERE full_name ILIKE '%Alisson Ramsés Becker%' AND source_provider = 'sportmonks'
        """), {"now": now})

        session.execute(text("""
            UPDATE player_share_markets SET
                total_shares = 400,
                circulating_shares = 80,
                share_price_coin = :price,
                status = 'active',
                updated_at = :now
            WHERE player_id IN (SELECT id FROM ingestion_players WHERE full_name ILIKE '%Alisson Ramsés Becker%' AND source_provider = 'sportmonks')
        """), {"price": alisson_price, "now": now})

        session.commit()
        logger.info("Key superstars upgraded with correct real-world stats and market shares.")

        # =========================================================================
        # 5. CALIBRATE €300M PLACEHOLDER ANOMALIES IN FM23
        # =========================================================================
        logger.info("--- 5. Calibrating €300M placeholder anomalies in FM23 ---")
        session.execute(text("""
            UPDATE ingestion_players SET
                market_value_eur = CASE
                    WHEN potential >= 80 THEN 25000000.0
                    WHEN potential >= 75 THEN 14000000.0
                    WHEN potential >= 70 THEN 7500000.0
                    WHEN potential >= 65 THEN 3500000.0
                    ELSE 1200000.0
                END,
                current_market_reference_value = CASE
                    WHEN potential >= 80 THEN 25000000.0
                    WHEN potential >= 75 THEN 14000000.0
                    WHEN potential >= 70 THEN 7500000.0
                    WHEN potential >= 65 THEN 3500000.0
                    ELSE 1200000.0
                END,
                updated_at = :now
            WHERE source_provider = 'fm23_genie_scout'
              AND market_value_eur = 300000000
              AND potential < 88
        """), {"now": now})
        session.commit()
        logger.info("Calibrated €300M placeholders to realistic GSI valuations.")

        # =========================================================================
        # 6. UNIVERSAL SOFIFA-MAX ALIGNMENT FOR ALL REMAINING ACTIVE SPORTMONKS PLAYERS
        # =========================================================================
        logger.info("--- 6. Universal Sofifa-Max Alignment for remaining active Sportmonks players ---")
        sm_active = session.execute(text("""
            SELECT p.id, p.dna_profile, p.market_value_eur
            FROM ingestion_players p
            JOIN player_share_markets m ON m.player_id = p.id
            WHERE p.source_provider = 'sportmonks'
              AND m.status = 'active'
        """)).fetchall()

        sm_recalibrations = []
        for pid, dna_raw, mkt_val in sm_active:
            dna = dna_raw if isinstance(dna_raw, dict) else {}
            if isinstance(dna_raw, str):
                try:
                    dna = json.loads(dna_raw)
                except Exception:
                    dna = {}

            sofifa_cur = int(dna.get("sofifa_overall") or 0)
            sofifa_pot = int(dna.get("sofifa_potential") or 0)
            syn_cur = int(dna.get("overall") or dna.get("current_rating") or 0)
            syn_pot = int(dna.get("potential") or dna.get("potential_rating") or 0)

            cur = max(sofifa_cur, syn_cur)
            pot = max(sofifa_pot, syn_pot, cur)

            # High-value fallback if missing
            val = float(mkt_val or 0)
            if val >= 80_000_000:
                cur, pot = max(cur, 86), max(pot, 89)
            elif val >= 50_000_000:
                cur, pot = max(cur, 83), max(pot, 86)
            elif val >= 25_000_000:
                cur, pot = max(cur, 80), max(pot, 83)
            elif val >= 10_000_000:
                cur, pot = max(cur, 76), max(pot, 80)
            elif cur == 0:
                cur, pot = 60, 65

            eval_gsi = 0.40 * cur + 0.60 * pot
            tier_code, total_shares = get_shares_for_gsi(eval_gsi)
            new_price = calculate_gsi_player_price(cur, pot, is_real=True, is_legend=False)

            sm_recalibrations.append({
                "pid": pid,
                "price": new_price,
                "shares": total_shares,
                "circ": total_shares,
                "cur": cur,
                "pot": pot
            })

        batch_size = 500
        for i in range(0, len(sm_recalibrations), batch_size):
            chunk = sm_recalibrations[i : i + batch_size]
            session.execute(text("""
                UPDATE player_share_markets AS m
                SET share_price_coin = v.price,
                    total_shares = v.shares,
                    circulating_shares = v.circ,
                    updated_at = :now
                FROM (VALUES """ + ", ".join(f"('{r['pid']}', {r['price']}, {r['shares']}, {r['circ']})" for r in chunk) + """) 
                    AS v(pid, price, shares, circ)
                WHERE m.player_id = v.pid
            """), {"now": now})
            session.commit()

        logger.info("Universal alignment complete across %d Sportmonks active players.", len(sm_recalibrations))
        logger.info("=== MARKET ALIGNMENT SUCCESSFULLY COMPLETED ===")

if __name__ == "__main__":
    t0 = time.time()
    run_alignment()
    print(f"Total alignment time: {time.time() - t0:.2f} seconds")
