"""Apply Wonderkids Rating, Position, and Club Calibration across Supabase tables.

Updates ingestion_players, player_share_markets, and player_summary_read_models
with fan-expected benchmarks adhering strictly to the FC 27 ±1 guideline.
"""

import json
import logging
import os
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    try:
        from app.core.config import settings

        DB_URL = str(settings.database_url)
    except Exception:
        DB_URL = ""

SPEC_FILE = r"C:\Users\ayomc\.gemini\antigravity\scratch\final_wonderkids_specs.json"


def apply_calibration():
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        specs = json.load(f)

    logger.info("Loaded %d wonderkid calibration specs.", len(specs))

    conn = psycopg.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    total_ingestion_updated = 0
    total_markets_updated = 0
    total_summaries_updated = 0

    try:
        for spec in specs:
            cname = spec["canonical_name"]
            ovr = spec["ovr"]
            pot = spec["pot"]
            pos = spec["pos"]
            norm_pos = spec["norm_pos"]
            club = spec["club"]
            tier = spec["tier"]
            pids = spec["ids"]

            if not pids:
                continue

            dna_patch = json.dumps(
                {"current_rating": ovr, "overall": ovr, "potential_rating": pot, "potential": pot, "position": pos}
            )

            market_patch = json.dumps(
                {"current_gsi": ovr, "potential_gsi": pot, "governed_gsi": ovr, "governed_potential_gsi": pot}
            )

            summary_patch = json.dumps(
                {
                    "gsi": ovr,
                    "overall": ovr,
                    "potential": pot,
                    "position": pos,
                    "real_player_tier": tier,
                    "real_world_club_name": club,
                }
            )

            # 1. Update ingestion_players
            cur.execute(
                """
                UPDATE ingestion_players
                SET
                    governed_gsi = %s,
                    governed_potential_gsi = %s,
                    potential = %s,
                    position = %s,
                    normalized_position = %s,
                    real_world_club_name = %s,
                    real_player_tier = %s,
                    gsi_methodology_version = '2026.fc27_wonderkid_calibration',
                    gsi_override_reason = 'Governed calibration per FC 27 benchmark',
                    dna_profile = (
                        COALESCE(dna_profile::jsonb, '{}'::jsonb) || (%s)::jsonb
                    )::json,
                    updated_at = NOW()
                WHERE id = ANY(%s);
            """,
                (ovr, pot, pot, pos, norm_pos, club, tier, dna_patch, pids),
            )
            ingestion_count = cur.rowcount
            total_ingestion_updated += ingestion_count

            # 2. Update player_share_markets
            cur.execute(
                """
                UPDATE player_share_markets
                SET
                    metadata_json = (
                        COALESCE(metadata_json::jsonb, '{}'::jsonb) || (%s)::jsonb
                    )::json,
                    updated_at = NOW()
                WHERE player_id = ANY(%s);
            """,
                (market_patch, pids),
            )
            markets_count = cur.rowcount
            total_markets_updated += markets_count

            # 3. Update player_summary_read_models
            cur.execute(
                """
                UPDATE player_summary_read_models
                SET
                    current_club_name = %s,
                    summary_json = (
                        COALESCE(summary_json::jsonb, '{}'::jsonb) || (%s)::jsonb
                    )::json,
                    updated_at = NOW()
                WHERE player_id = ANY(%s);
            """,
                (club, summary_patch, pids),
            )
            summaries_count = cur.rowcount
            total_summaries_updated += summaries_count

            logger.info(
                "Calibrated %s (OVR %d, POT %d, POS %s, CLUB %s): %d ingestion, %d markets, %d summaries",
                cname,
                ovr,
                pot,
                pos,
                club,
                ingestion_count,
                markets_count,
                summaries_count,
            )

        conn.commit()
        logger.info(
            "COMMITTED CALIBRATION SUCCESSFULLY: Total %d ingestion_players, %d player_share_markets, %d player_summary_read_models updated.",
            total_ingestion_updated,
            total_markets_updated,
            total_summaries_updated,
        )
    except Exception as e:
        conn.rollback()
        logger.error("Failed to apply wonderkids calibration: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    apply_calibration()
