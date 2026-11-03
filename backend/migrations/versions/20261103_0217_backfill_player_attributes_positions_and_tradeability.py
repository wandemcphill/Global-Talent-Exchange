"""Backfill player attributes, positions, ratings, nationalities, and ensure universal tradeability.

Revision ID: 20261103_0217_backfill_player_attributes_positions_and_tradeability
Revises: 20261103_0216_marquee_units_and_fc_ratings_calibration
Create Date: 2026-11-03 08:25:00.000000
"""

from alembic import op

revision = "20261103_0217_backfill_player_attributes_positions_and_tradeability"
down_revision = "20261103_0216_marquee_units_and_fc_ratings_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    raw_conn = conn.connection
    with raw_conn.cursor() as cur:
        # 1. Resolve missing country_id using precomputed name and club mappings
        cur.execute("SELECT id FROM ingestion_countries WHERE name = 'England' LIMIT 1;")
        row = cur.fetchone()
        default_country_id = row[0] if row else None

        cur.execute("""
            SELECT id, full_name, real_world_club_name, current_club_id
            FROM ingestion_players
            WHERE country_id IS NULL;
        """)
        missing_country_players = cur.fetchall()

        if missing_country_players:
            cur.execute("""
                SELECT LOWER(TRIM(real_world_club_name)), country_id, COUNT(*)
                FROM ingestion_players
                WHERE country_id IS NOT NULL AND real_world_club_name IS NOT NULL AND TRIM(real_world_club_name) != ''
                GROUP BY LOWER(TRIM(real_world_club_name)), country_id;
            """)
            club_map = {}
            for club, cid, cnt in cur.fetchall():
                if club not in club_map or cnt > club_map[club][1]:
                    club_map[club] = (cid, cnt)
            club_to_country = {k: v[0] for k, v in club_map.items()}

            cur.execute("""
                SELECT LOWER(TRIM(full_name)), country_id, COUNT(*)
                FROM ingestion_players
                WHERE country_id IS NOT NULL
                GROUP BY LOWER(TRIM(full_name)), country_id;
            """)
            name_map = {}
            for name, cid, cnt in cur.fetchall():
                if name not in name_map or cnt > name_map[name][1]:
                    name_map[name] = (cid, cnt)
            name_to_country = {k: v[0] for k, v in name_map.items()}

            cur.execute("SELECT id, country_id FROM ingestion_clubs WHERE country_id IS NOT NULL;")
            club_id_to_country = dict(cur.fetchall())

            cur.execute("SELECT LOWER(TRIM(name)), country_id FROM ingestion_clubs WHERE country_id IS NOT NULL;")
            club_name_to_country = dict(cur.fetchall())

            country_updates = []
            for pid, name, club, club_id in missing_country_players:
                cid = None
                if name and name.lower().strip() in name_to_country:
                    cid = name_to_country[name.lower().strip()]
                elif club_id and club_id in club_id_to_country:
                    cid = club_id_to_country[club_id]
                elif club and club.lower().strip() in club_to_country:
                    cid = club_to_country[club.lower().strip()]
                elif club and club.lower().strip() in club_name_to_country:
                    cid = club_name_to_country[club.lower().strip()]
                if not cid:
                    cid = default_country_id
                if cid:
                    country_updates.append((cid, pid))

            if country_updates:
                cur.executemany(
                    "UPDATE ingestion_players SET country_id = %s, updated_at = NOW() WHERE id = %s;",
                    country_updates,
                )

        # 2. Backfill missing date_of_birth
        cur.execute("""
            UPDATE ingestion_players ip
            SET date_of_birth = make_date(
                CASE 
                    WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                         COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 12 THEN 2007
                    WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                         COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 8 THEN 2005
                    WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                         COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 5 THEN 2003
                    WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                         COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 2 THEN 2000
                    ELSE 1998
                END,
                (abs(hashtext(ip.id)) % 12) + 1,
                (abs(hashtext(ip.id)) % 28) + 1
            ),
            factual_date_of_birth = COALESCE(
                factual_date_of_birth,
                make_date(
                    CASE 
                        WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                             COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 12 THEN 2007
                        WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                             COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 8 THEN 2005
                        WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                             COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 5 THEN 2003
                        WHEN COALESCE((dna_profile->>'potential')::int, (dna_profile->>'potential_rating')::int, 75) - 
                             COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) >= 2 THEN 2000
                        ELSE 1998
                    END,
                    (abs(hashtext(ip.id)) % 12) + 1,
                    (abs(hashtext(ip.id)) % 28) + 1
                )
            ),
            updated_at = NOW()
            WHERE ip.date_of_birth IS NULL;
        """)

        # 3. Calibrate governed_gsi and potential [40, 99], enforce potential >= governed_gsi
        cur.execute("""
            UPDATE ingestion_players ip
            SET governed_gsi = LEAST(99, GREATEST(40, COALESCE(
                    governed_gsi,
                    (dna_profile->>'overall')::int,
                    (dna_profile->>'current_rating')::int,
                    (dna_profile->>'sofifa_overall')::int,
                    70
                ))),
                governed_potential_gsi = LEAST(99, GREATEST(40, COALESCE(
                    governed_potential_gsi,
                    potential,
                    (dna_profile->>'potential')::int,
                    (dna_profile->>'potential_rating')::int,
                    (dna_profile->>'sofifa_potential')::int,
                    COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) + 4,
                    74
                ))),
                potential = LEAST(99, GREATEST(40, COALESCE(
                    potential,
                    governed_potential_gsi,
                    (dna_profile->>'potential')::int,
                    (dna_profile->>'potential_rating')::int,
                    (dna_profile->>'sofifa_potential')::int,
                    COALESCE(governed_gsi, (dna_profile->>'overall')::int, (dna_profile->>'current_rating')::int, 70) + 4,
                    74
                ))),
                updated_at = NOW()
            WHERE governed_gsi IS NULL 
               OR governed_potential_gsi IS NULL 
               OR potential IS NULL
               OR potential < governed_gsi;
        """)

        cur.execute("""
            UPDATE ingestion_players
            SET potential = GREATEST(potential, governed_gsi),
                governed_potential_gsi = GREATEST(governed_potential_gsi, governed_gsi),
                updated_at = NOW()
            WHERE potential < governed_gsi OR governed_potential_gsi < governed_gsi;
        """)

        # 4. Universal tradeability on ingestion_players
        cur.execute("""
            UPDATE ingestion_players
            SET is_tradable = true,
                updated_at = NOW()
            WHERE is_tradable IS NOT TRUE;
        """)

        # 5. Insert missing player_share_markets and activate retired/bad markets
        cur.execute("""
            INSERT INTO player_share_markets (
                id, player_id, total_shares, circulating_shares, share_price_coin,
                status, revenue_distributed_coin, metadata_json, created_at, updated_at
            )
            SELECT 
                gen_random_uuid()::text,
                ip.id,
                400,
                0,
                ROUND((ip.governed_gsi * 2.1 + ip.potential * 0.35)::numeric, 2),
                'active',
                0.0,
                jsonb_build_object('market_state', 'active', 'tier', 'open')::json,
                NOW(),
                NOW()
            FROM ingestion_players ip
            LEFT JOIN player_share_markets psm ON psm.player_id = ip.id
            WHERE psm.id IS NULL;
        """)

        cur.execute("""
            UPDATE player_share_markets psm
            SET status = 'active',
                total_shares = COALESCE(NULLIF(total_shares, 0), 400),
                circulating_shares = COALESCE(circulating_shares, 0),
                share_price_coin = COALESCE(
                    NULLIF(share_price_coin, 0),
                    ROUND((ip.governed_gsi * 2.1 + ip.potential * 0.35)::numeric, 2)
                ),
                updated_at = NOW()
            FROM ingestion_players ip
            WHERE ip.id = psm.player_id
              AND (psm.status != 'active' OR psm.share_price_coin IS NULL OR psm.share_price_coin <= 0 OR psm.total_shares IS NULL OR psm.total_shares <= 0);
        """)

        # 6. Insert missing read models
        cur.execute("""
            INSERT INTO player_summary_read_models (
                player_id, player_name, current_club_id, current_club_name,
                current_competition_id, current_competition_name,
                last_snapshot_at, current_value_credits, previous_value_credits,
                movement_pct, average_rating, market_interest_score,
                summary_json, created_at, updated_at
            )
            SELECT 
                ip.id,
                COALESCE(ip.canonical_display_name, ip.full_name),
                ip.current_club_id,
                ip.real_world_club_name,
                ip.current_competition_id,
                ip.real_world_league_name,
                NOW(),
                COALESCE(psm.share_price_coin::float8, ROUND((ip.governed_gsi * 2.1 + ip.potential * 0.35)::numeric, 2)::float8),
                COALESCE(psm.share_price_coin::float8, ROUND((ip.governed_gsi * 2.1 + ip.potential * 0.35)::numeric, 2)::float8),
                0.0,
                ip.governed_gsi::float8,
                50,
                jsonb_build_object(
                    'gsi', ip.governed_gsi,
                    'overall', ip.governed_gsi,
                    'global_scouting_index', ip.governed_gsi,
                    'potential', ip.potential,
                    'position', ip.position,
                    'normalized_position', ip.normalized_position,
                    'real_world_club_name', ip.real_world_club_name,
                    'country_name', ic.name,
                    'nationality', ic.name,
                    'nationality_code', COALESCE(ic.alpha3_code, ic.alpha2_code),
                    'date_of_birth', ip.date_of_birth,
                    'age', EXTRACT(YEAR FROM age(CURRENT_DATE, ip.date_of_birth))::int,
                    'total_shares', COALESCE(psm.total_shares, 400),
                    'circulating_shares', COALESCE(psm.circulating_shares, 0),
                    'share_price_coin', COALESCE(psm.share_price_coin, ROUND((ip.governed_gsi * 2.1 + ip.potential * 0.35)::numeric, 2)),
                    'is_tradable', true,
                    'market_visibility', jsonb_build_object('status', 'visible', 'eligible', true),
                    'attributes', jsonb_build_object(
                        'pace', CASE 
                            WHEN COALESCE(ip.dna_profile->>'pace', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'pace')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 18))
                            WHEN ip.normalized_position IN ('LB', 'RB', 'LWB', 'RWB') OR ip.position ILIKE '%wing-back%' OR ip.position ILIKE '%full-back%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 5))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'DM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 1))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                        END,
                        'shooting', CASE 
                            WHEN COALESCE(ip.dna_profile->>'shooting', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'shooting')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 35))
                            WHEN ip.normalized_position IN ('LB', 'RB', 'LWB', 'RWB') OR ip.position ILIKE '%wing-back%' OR ip.position ILIKE '%full-back%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 15))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 25))
                            WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi - 12))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 4))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                        END,
                        'passing', CASE 
                            WHEN COALESCE(ip.dna_profile->>'passing', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'passing')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 10))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 8))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi - 2))
                        END,
                        'dribbling', CASE 
                            WHEN COALESCE(ip.dna_profile->>'dribbling', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'dribbling')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 20))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 3))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 12))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                        END,
                        'defending', CASE 
                            WHEN COALESCE(ip.dna_profile->>'defending', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'defending')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 15))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                            WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 8))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi - 28))
                        END,
                        'physical', CASE 
                            WHEN COALESCE(ip.dna_profile->>'physical', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'physical')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 2))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi + 3))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi))
                        END
                    )
                )::json,
                NOW(),
                NOW()
            FROM ingestion_players ip
            LEFT JOIN player_summary_read_models rm ON rm.player_id = ip.id
            LEFT JOIN player_share_markets psm ON psm.player_id = ip.id
            LEFT JOIN ingestion_countries ic ON ic.id = ip.country_id
            WHERE rm.player_id IS NULL;
        """)

        # 7. Update existing read models summary_json to ensure tradeability and attributes
        cur.execute("""
            UPDATE player_summary_read_models rm
            SET summary_json = (
                rm.summary_json::jsonb || jsonb_build_object(
                    'is_tradable', true,
                    'market_visibility', jsonb_build_object('status', 'visible', 'eligible', true),
                    'total_shares', COALESCE((rm.summary_json->>'total_shares')::int, psm.total_shares, 400),
                    'circulating_shares', COALESCE((rm.summary_json->>'circulating_shares')::int, psm.circulating_shares, 0),
                    'share_price_coin', COALESCE(psm.share_price_coin, (rm.summary_json->>'share_price_coin')::numeric, 50.0),
                    'gsi', COALESCE(ip.governed_gsi, (rm.summary_json->>'gsi')::int, 70),
                    'overall', COALESCE(ip.governed_gsi, (rm.summary_json->>'overall')::int, 70),
                    'global_scouting_index', COALESCE(ip.governed_gsi, (rm.summary_json->>'global_scouting_index')::int, 70),
                    'potential', COALESCE(ip.potential, (rm.summary_json->>'potential')::int, ip.governed_gsi, 70),
                    'position', COALESCE(ip.position, rm.summary_json->>'position'),
                    'normalized_position', COALESCE(ip.normalized_position, rm.summary_json->>'normalized_position'),
                    'country_name', COALESCE(ic.name, rm.summary_json->>'country_name'),
                    'nationality', COALESCE(ic.name, rm.summary_json->>'nationality'),
                    'nationality_code', COALESCE(ic.alpha3_code, ic.alpha2_code, rm.summary_json->>'nationality_code'),
                    'date_of_birth', COALESCE(ip.date_of_birth::text, rm.summary_json->>'date_of_birth'),
                    'age', COALESCE(EXTRACT(YEAR FROM age(CURRENT_DATE, ip.date_of_birth))::int, (rm.summary_json->>'age')::int)
                )
            )::json,
            current_value_credits = COALESCE(psm.share_price_coin::float8, rm.current_value_credits),
            updated_at = NOW()
            FROM ingestion_players ip
            LEFT JOIN player_share_markets psm ON psm.player_id = ip.id
            LEFT JOIN ingestion_countries ic ON ic.id = ip.country_id
            WHERE ip.id = rm.player_id
              AND (
                  (rm.summary_json->>'is_tradable') IS NULL 
                  OR rm.summary_json->>'is_tradable' != 'true'
                  OR (rm.summary_json->'market_visibility'->>'eligible') IS NULL
                  OR rm.summary_json->'market_visibility'->>'eligible' != 'true'
                  OR rm.summary_json->>'gsi' IS NULL
                  OR rm.summary_json->>'nationality' IS NULL
                  OR rm.summary_json->>'date_of_birth' IS NULL
              );
        """)

        # 8. Enrich dna_profile for players missing attributes dict
        cur.execute("""
            UPDATE ingestion_players ip
            SET dna_profile = (
                ip.dna_profile::jsonb || jsonb_build_object(
                    'overall', ip.governed_gsi,
                    'potential', ip.potential,
                    'current_rating', ip.governed_gsi,
                    'potential_rating', ip.potential,
                    'date_of_birth', ip.date_of_birth::text,
                    'age', EXTRACT(YEAR FROM age(CURRENT_DATE, ip.date_of_birth))::int,
                    'nationality', ic.name,
                    'nationality_code', COALESCE(ic.alpha3_code, ic.alpha2_code),
                    'pace', CASE 
                        WHEN COALESCE(ip.dna_profile->>'pace', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'pace')::int
                        WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 18))
                        WHEN ip.normalized_position IN ('LB', 'RB', 'LWB', 'RWB') OR ip.position ILIKE '%wing-back%' OR ip.position ILIKE '%full-back%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                        WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 5))
                        WHEN ip.normalized_position IN ('MID', 'CM', 'DM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 1))
                        ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                    END,
                    'shooting', CASE 
                        WHEN COALESCE(ip.dna_profile->>'shooting', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'shooting')::int
                        WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 35))
                        WHEN ip.normalized_position IN ('LB', 'RB', 'LWB', 'RWB') OR ip.position ILIKE '%wing-back%' OR ip.position ILIKE '%full-back%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 15))
                        WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 25))
                        WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi - 12))
                        WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 4))
                        ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                    END,
                    'passing', CASE 
                        WHEN COALESCE(ip.dna_profile->>'passing', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'passing')::int
                        WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 10))
                        WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                        WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 8))
                        ELSE LEAST(99, GREATEST(20, ip.governed_gsi - 2))
                    END,
                    'dribbling', CASE 
                        WHEN COALESCE(ip.dna_profile->>'dribbling', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'dribbling')::int
                        WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 20))
                        WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 3))
                        WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 12))
                        ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                    END,
                    'defending', CASE 
                        WHEN COALESCE(ip.dna_profile->>'defending', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'defending')::int
                        WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 15))
                        WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                        WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                        WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 8))
                        ELSE LEAST(99, GREATEST(20, ip.governed_gsi - 28))
                    END,
                    'physical', CASE 
                        WHEN COALESCE(ip.dna_profile->>'physical', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'physical')::int
                        WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 2))
                        WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                        WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi + 3))
                        ELSE LEAST(99, GREATEST(20, ip.governed_gsi))
                    END,
                    'attributes', jsonb_build_object(
                        'pace', CASE 
                            WHEN COALESCE(ip.dna_profile->>'pace', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'pace')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 18))
                            WHEN ip.normalized_position IN ('LB', 'RB', 'LWB', 'RWB') OR ip.position ILIKE '%wing-back%' OR ip.position ILIKE '%full-back%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 5))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'DM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 1))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                        END,
                        'shooting', CASE 
                            WHEN COALESCE(ip.dna_profile->>'shooting', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'shooting')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 35))
                            WHEN ip.normalized_position IN ('LB', 'RB', 'LWB', 'RWB') OR ip.position ILIKE '%wing-back%' OR ip.position ILIKE '%full-back%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 15))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 25))
                            WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi - 12))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 4))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                        END,
                        'passing', CASE 
                            WHEN COALESCE(ip.dna_profile->>'passing', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'passing')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 10))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 8))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi - 2))
                        END,
                        'dribbling', CASE 
                            WHEN COALESCE(ip.dna_profile->>'dribbling', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'dribbling')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 20))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 3))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 12))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                        END,
                        'defending', CASE 
                            WHEN COALESCE(ip.dna_profile->>'defending', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'defending')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 15))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 5))
                            WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('MID', 'CM', 'CAM', 'AM', 'LM', 'RM', 'MF') OR ip.position ILIKE '%midfield%' THEN LEAST(99, GREATEST(20, ip.governed_gsi - 8))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi - 28))
                        END,
                        'physical', CASE 
                            WHEN COALESCE(ip.dna_profile->>'physical', '') ~ '^[0-9]+$' THEN (ip.dna_profile->>'physical')::int
                            WHEN ip.normalized_position = 'GK' OR ip.position ILIKE '%GK%' OR ip.position ILIKE '%Goalkeeper%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 2))
                            WHEN ip.normalized_position IN ('DEF', 'CB', 'DF') OR ip.position ILIKE '%back%' OR ip.position ILIKE '%defender%' THEN LEAST(99, GREATEST(20, ip.governed_gsi + 4))
                            WHEN ip.normalized_position IN ('DM', 'CDM') THEN LEAST(99, GREATEST(20, ip.governed_gsi + 3))
                            ELSE LEAST(99, GREATEST(20, ip.governed_gsi))
                        END
                    )
                )
            )::json,
            updated_at = NOW()
            FROM ingestion_countries ic
            WHERE ic.id = ip.country_id
              AND (ip.dna_profile::jsonb ? 'attributes') IS NOT TRUE;
        """)

        # 9. Sync attributes to player_summary_read_models for any remaining rows
        cur.execute("""
            UPDATE player_summary_read_models rm
            SET summary_json = (
                rm.summary_json::jsonb || jsonb_build_object('attributes', (ip.dna_profile->'attributes')::jsonb)
            )::json,
            updated_at = NOW()
            FROM ingestion_players ip
            WHERE ip.id = rm.player_id
              AND (rm.summary_json::jsonb ? 'attributes') IS NOT TRUE;
        """)


def downgrade() -> None:
    pass
