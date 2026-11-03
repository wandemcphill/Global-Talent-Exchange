"""Update and create wonderkids, set governed ratings and upload Cloudinary portraits.

Revision ID: 20261103_0211_update_and_create_wonderkids_and_portraits
Revises: 20261103_0210_r7s_legends_cutout_portrait_assignments
Create Date: 2026-11-03 03:30:00
"""

from __future__ import annotations

import json
from alembic import op
import sqlalchemy as sa

revision = "20261103_0211_update_and_create_wonderkids_and_portraits"
down_revision = "20261103_0210_r7s_legends_cutout_portrait_assignments"
branch_labels = None
depends_on = None

DUPLICATE_IDS = [
    "3f564f54-9842-473d-9225-1918be3e2ec2",  # Akpe Victory (duplicate of Victory Akpe)
    "7f2c0f18-58b6-43fc-a591-47e9913e263c",  # Jeremy Monga untradable duplicate
    "586258a4-1f91-4344-9993-5ceef755f5f9",  # Emmanuel Ayaosi Dakkada duplicate
    "fdc70bf1-d6fd-4d1e-a613-153e75c1facc",  # Gift Orban Verona duplicate
]

NEW_PLAYERS = [
    {
        "id": "88077c5d-3559-4d2a-89b1-5f0962817810",
        "ext_id": "julian_quinones_88077c5d",
        "name": "Julián Quiñones",
        "display_name": "Julián Quiñones",
        "pos": "ST",
        "norm_pos": "ST",
        "sec_pos": ["LW", "RW"],
        "club": "Al-Qadsiah",
        "ovr": 80,
        "pot": 82,
        "dob": "1997-03-24",
        "tier": "established",
        "foot": "Right",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672157/players/portraits/p_88077c5d_julian_quinones.png",
    },
    {
        "id": "47a27eb2-17f1-4db8-b57f-1d89e5a8716b",
        "ext_id": "shedrack_egboh_47a27eb2",
        "name": "Shedrack Egboh",
        "display_name": "Shedrack Egboh",
        "pos": "RW",
        "norm_pos": "RW",
        "sec_pos": ["RM", "AM"],
        "club": "AIK Fotboll",
        "ovr": 70,
        "pot": 81,
        "dob": "2007-04-12",
        "tier": "wonderkid",
        "foot": "Left",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672071/players/portraits/p_47a27eb2_shedrack_egboh.jpg",
    },
    {
        "id": "9f7a3068-154a-43cf-be74-72ffb8bb8061",
        "ext_id": "1448405",
        "name": "Victor Adeoye",
        "display_name": "Victor Adeoye",
        "pos": "DM",
        "norm_pos": "DM",
        "sec_pos": ["CM"],
        "club": "FC Kudrivka",
        "ovr": 69,
        "pot": 78,
        "dob": "2006-05-29",
        "tier": "wonderkid",
        "height": 178,
        "foot": "Right",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672105/players/portraits/p_9f7a3068_victor_adeoye.png",
    },
]

UPDATED_PLAYERS = [
    {
        "id": "ed454740-6cb4-4b50-97d9-7b396b9e8f9b",
        "name": "Victory Akpe",
        "display_name": "Victory Akpe",
        "pos": "CB",
        "norm_pos": "CB",
        "sec_pos": [],
        "club": "FC Basel",
        "ovr": 73,
        "pot": 84,
        "dob": "2006-07-19",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657802/players/wonderkids/wk_ed454740_victory_akpe.png",
    },
    {
        "id": "97bc9cc6-c22d-4470-aec5-91729a57b947",
        "name": "Jeremy Monga",
        "display_name": "Jeremy Monga",
        "pos": "D/WB R",
        "norm_pos": "RB",
        "sec_pos": ["RW"],
        "club": "Leicester City",
        "ovr": 75,
        "pot": 85,
        "dob": "2008-07-10",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658404/players/wonderkids/wk_97bc9cc6_jeremy_monga.jpg",
    },
    {
        "id": "6d135d18-f0e0-49cd-b4d1-665e3c5111ef",
        "name": "Peter Edokpolor",
        "display_name": "Peter Edokpolor",
        "pos": "ST",
        "norm_pos": "ST",
        "sec_pos": [],
        "club": "SL Benfica B",
        "ovr": 72,
        "pot": 81,
        "dob": "2006-12-24",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657772/players/wonderkids/wk_6d135d18_peter_edokpolor.jpg",
    },
    {
        "id": "d7aaf329-52e5-53ae-b5d3-7d1875d6a3e9",
        "name": "Ahmed Abdullahi",
        "display_name": "Ahmed Abdullahi",
        "pos": "ST",
        "norm_pos": "ST",
        "sec_pos": ["FW"],
        "club": "Eyüpspor",
        "ovr": 73,
        "pot": 82,
        "dob": "2004-06-19",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672116/players/portraits/p_d7aaf329_ahmed_abdullahi.png",
    },
    {
        "id": "78929e0a-ba3f-4d48-bc58-e14421a3558c",
        "name": "Gift Orban",
        "display_name": "Gift Orban",
        "pos": "ST",
        "norm_pos": "ST",
        "sec_pos": ["AM", "RW", "LW"],
        "club": "Olympique Lyonnais",
        "ovr": 81,
        "pot": 89,
        "dob": "2002-07-17",
        "tier": "established",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672041/players/portraits/p_78929e0a_gift_orban.png",
    },
    {
        "id": "739e961b-a7bd-43a9-b532-72f6320949b2",
        "name": "Stanley Iheanacho",
        "display_name": "Stanley Iheanacho",
        "pos": "RW",
        "norm_pos": "RW",
        "sec_pos": ["ST", "RM"],
        "club": "FC Midtjylland",
        "ovr": 70,
        "pot": 80,
        "dob": "2005-05-18",
        "tier": "wonderkid",
        "height": 186,
        "foot": "Right",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672048/players/portraits/p_739e961b_stanley_iheanacho.png",
    },
    {
        "id": "66bed7c6-3bb5-478a-97bb-678b8934010e",
        "name": "Victor Orakpo",
        "display_name": "Victor Orakpo",
        "pos": "ST",
        "norm_pos": "ST",
        "sec_pos": ["FW"],
        "club": "OGC Nice",
        "ovr": 71,
        "pot": 81,
        "dob": "2006-01-14",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672055/players/portraits/p_66bed7c6_victor_orakpo.png",
    },
    {
        "id": "d97a6eaa-af0a-4faa-81fd-a0e0fd89110f",
        "name": "Sani Suleiman",
        "display_name": "Sani Suleiman",
        "pos": "LW",
        "norm_pos": "LW",
        "sec_pos": ["FW", "LM", "RW"],
        "club": "AS Trenčín",
        "ovr": 75,
        "pot": 84,
        "dob": "2006-08-31",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672058/players/portraits/p_d97a6eaa_sani_suleiman.png",
    },
    {
        "id": "528b3f8c-4197-4d71-9b77-c1cbb08ec46d",
        "name": "Emmanuel Ayaosi",
        "display_name": "Emmanuel Ayaosi",
        "pos": "LM",
        "norm_pos": "LM",
        "sec_pos": ["LW", "AM", "FW"],
        "club": "SK Slavia Praha",
        "ovr": 73,
        "pot": 80,
        "dob": "2004-10-28",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672163/players/portraits/p_528b3f8c_emmanuel_ayaosi.jpg",
    },
    {
        "id": "87f3264f-d54e-49a5-9d3b-f1c01d950d94",
        "name": "Prosper Obah",
        "display_name": "Prosper Obah",
        "pos": "LM",
        "norm_pos": "LM",
        "sec_pos": ["LW", "RM", "RW", "FW"],
        "club": "Shakhtar Donetsk",
        "ovr": 74,
        "pot": 82,
        "dob": "2003-11-24",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672083/players/portraits/p_87f3264f_prosper_obah.png",
    },
    {
        "id": "d9c483d5-5cbd-4f18-b6f9-7ca2b48cc953",
        "name": "Shola Ogundana",
        "display_name": "Shola Ogundana",
        "pos": "LW",
        "norm_pos": "LW",
        "sec_pos": ["LM", "AM"],
        "club": "Dynamo Kyiv",
        "ovr": 71,
        "pot": 80,
        "dob": "2005-02-21",
        "tier": "wonderkid",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672099/players/portraits/p_d9c483d5_shola_ogundana.png",
    },
    {
        "id": "b61a32d8-b8f0-4eb6-b162-feddfd72cf02",
        "name": "Adam Yakubu",
        "display_name": "Adam Yakubu",
        "pos": "DM",
        "norm_pos": "DM",
        "sec_pos": ["CM"],
        "club": "LNZ Cherkasy",
        "ovr": 75,
        "pot": 84,
        "dob": "2005-02-01",
        "tier": "wonderkid",
        "height": 187,
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793672111/players/portraits/p_b61a32d8_adam_yakubu.png",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if not is_postgres:
        return

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Delete duplicates
    id_list_str = "('" + "', '".join(DUPLICATE_IDS) + "')"
    if "ingestion_player_image_metadata" in tables:
        op.execute(f"DELETE FROM ingestion_player_image_metadata WHERE player_id IN {id_list_str};")
    if "player_share_markets" in tables:
        op.execute(f"DELETE FROM player_share_markets WHERE player_id IN {id_list_str};")
    if "player_summary_read_models" in tables:
        op.execute(f"DELETE FROM player_summary_read_models WHERE player_id IN {id_list_str};")
    if "ingestion_players" in tables:
        op.execute(f"DELETE FROM ingestion_players WHERE id IN {id_list_str};")

    # 2. Insert new players
    for p in NEW_PLAYERS:
        pid = p["id"]
        ext_id = p["ext_id"]
        name = p["name"].replace("'", "''")
        display = p["display_name"].replace("'", "''")
        pos = p["pos"]
        norm_pos = p["norm_pos"]
        club = p["club"].replace("'", "''")
        ovr = p["ovr"]
        pot = p["pot"]
        dob = p["dob"]
        tier = p["tier"]
        portrait = p["portrait"]
        sec_json = json.dumps(p["sec_pos"]).replace("'", "''")

        dna = {
            "current_rating": ovr,
            "overall": ovr,
            "potential_rating": pot,
            "potential": pot,
            "position": pos,
            "secondary_positions": p["sec_pos"],
            "date_of_birth": dob,
            "portraitUrl": portrait,
            "image_url": portrait,
            "portraitStatus": "ready",
            "portraitSourceProvider": "cloudinary",
        }
        if "height" in p:
            dna["height_cm"] = p["height"]
        if "foot" in p:
            dna["preferred_foot"] = p["foot"]
        dna_str = json.dumps(dna).replace("'", "''")

        market = {
            "tier": tier,
            "current_gsi": ovr,
            "potential_gsi": pot,
            "governed_gsi": ovr,
            "governed_potential_gsi": pot,
        }
        market_str = json.dumps(market).replace("'", "''")

        summary = {
            "gsi": ovr,
            "overall": ovr,
            "potential": pot,
            "position": pos,
            "real_player_tier": tier,
            "real_world_club_name": p["club"],
            "total_shares": 200,
            "share_price_coin": 100.0,
            "market_visibility": {"status": "visible", "eligible": True},
            "image_url": portrait,
            "portrait_url": portrait,
            "portrait_status": "ready",
        }
        summary_str = json.dumps(summary).replace("'", "''")

        if "ingestion_players" in tables:
            op.execute(f"""
                INSERT INTO ingestion_players (
                    id, source_provider, provider_external_id, full_name, canonical_display_name,
                    position, normalized_position, real_world_club_name, is_tradable, is_real_player,
                    real_player_tier, governed_gsi, governed_potential_gsi, potential,
                    gsi_methodology_version, gsi_override_reason, date_of_birth, dna_profile,
                    secondary_positions_json, morale, created_at, updated_at, last_synced_at
                )
                VALUES (
                    '{pid}', 'curated_roster', '{ext_id}', '{name}', '{display}',
                    '{pos}', '{norm_pos}', '{club}', true, true,
                    '{tier}', {ovr}, {pot}, {pot},
                    '2026.roster_governed_calibration', 'User requested player creation and calibration',
                    CAST('{dob}' AS DATE), CAST('{dna_str}' AS json), CAST('{sec_json}' AS json), 50.0, NOW(), NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    full_name = '{name}',
                    canonical_display_name = '{display}',
                    position = '{pos}',
                    normalized_position = '{norm_pos}',
                    real_world_club_name = '{club}',
                    is_tradable = true,
                    real_player_tier = '{tier}',
                    governed_gsi = {ovr},
                    governed_potential_gsi = {pot},
                    potential = {pot},
                    date_of_birth = CAST('{dob}' AS DATE),
                    dna_profile = (COALESCE(CAST(ingestion_players.dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{dna_str}' AS jsonb))::json,
                    secondary_positions_json = CAST('{sec_json}' AS json),
                    updated_at = NOW();
            """)

        if "player_share_markets" in tables:
            op.execute(f"""
                INSERT INTO player_share_markets (
                    id, player_id, total_shares, circulating_shares, share_price_coin,
                    status, revenue_distributed_coin, metadata_json, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid()::text, '{pid}', 200, 200, 100.0,
                    'active', 0.0, CAST('{market_str}' AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    metadata_json = (COALESCE(CAST(player_share_markets.metadata_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{market_str}' AS jsonb))::json,
                    updated_at = NOW();
            """)

        if "player_summary_read_models" in tables:
            op.execute(f"""
                INSERT INTO player_summary_read_models (
                    player_id, player_name, current_club_name, last_snapshot_at,
                    current_value_credits, previous_value_credits, movement_pct,
                    market_interest_score, summary_json, created_at, updated_at
                )
                VALUES (
                    '{pid}', '{display}', '{club}', NOW(),
                    100.0, 100.0, 0.0,
                    50, CAST('{summary_str}' AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = '{display}',
                    current_club_name = '{club}',
                    summary_json = (COALESCE(CAST(player_summary_read_models.summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{summary_str}' AS jsonb))::json,
                    updated_at = NOW();
            """)

        if "ingestion_player_image_metadata" in tables:
            op.execute(f"""
                DELETE FROM ingestion_player_image_metadata WHERE player_id = '{pid}' AND image_role = 'portrait';
                INSERT INTO ingestion_player_image_metadata (
                    id, player_id, source_provider, provider_external_id,
                    image_role, source_url, moderation_status, rights_cleared,
                    is_primary, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), '{pid}', 'cloudinary', '{pid}',
                    'portrait', '{portrait}', 'approved', true,
                    true, NOW(), NOW()
                );
            """)

    # 3. Update existing players
    for p in UPDATED_PLAYERS:
        pid = p["id"]
        name = p["name"].replace("'", "''")
        display = p["display_name"].replace("'", "''")
        pos = p["pos"]
        norm_pos = p["norm_pos"]
        club = p["club"].replace("'", "''")
        ovr = p["ovr"]
        pot = p["pot"]
        dob = p["dob"]
        tier = p["tier"]
        portrait = p["portrait"]
        sec_json = json.dumps(p["sec_pos"]).replace("'", "''")

        dna = {
            "current_rating": ovr,
            "overall": ovr,
            "potential_rating": pot,
            "potential": pot,
            "position": pos,
            "secondary_positions": p["sec_pos"],
            "date_of_birth": dob,
            "portraitUrl": portrait,
            "image_url": portrait,
            "portraitStatus": "ready",
            "portraitSourceProvider": "cloudinary",
        }
        if "height" in p:
            dna["height_cm"] = p["height"]
        if "foot" in p:
            dna["preferred_foot"] = p["foot"]
        dna_str = json.dumps(dna).replace("'", "''")

        market = {
            "tier": tier,
            "current_gsi": ovr,
            "potential_gsi": pot,
            "governed_gsi": ovr,
            "governed_potential_gsi": pot,
        }
        market_str = json.dumps(market).replace("'", "''")

        summary = {
            "gsi": ovr,
            "overall": ovr,
            "potential": pot,
            "position": pos,
            "real_player_tier": tier,
            "real_world_club_name": p["club"],
            "image_url": portrait,
            "portrait_url": portrait,
            "portrait_status": "ready",
        }
        summary_str = json.dumps(summary).replace("'", "''")

        if "ingestion_players" in tables:
            op.execute(f"""
                UPDATE ingestion_players
                SET
                    full_name = '{name}',
                    canonical_display_name = '{display}',
                    position = '{pos}',
                    normalized_position = '{norm_pos}',
                    real_world_club_name = '{club}',
                    is_tradable = true,
                    real_player_tier = '{tier}',
                    governed_gsi = {ovr},
                    governed_potential_gsi = {pot},
                    potential = {pot},
                    date_of_birth = CAST('{dob}' AS DATE),
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{dna_str}' AS jsonb))::json,
                    secondary_positions_json = CAST('{sec_json}' AS json),
                    updated_at = NOW()
                WHERE id = '{pid}';
            """)

        if "player_share_markets" in tables:
            op.execute(f"""
                UPDATE player_share_markets
                SET
                    status = 'active',
                    metadata_json = (COALESCE(CAST(metadata_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{market_str}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = '{pid}';
            """)

        if "player_summary_read_models" in tables:
            op.execute(f"""
                UPDATE player_summary_read_models
                SET
                    player_name = '{display}',
                    current_club_name = '{club}',
                    summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{summary_str}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = '{pid}';
            """)

        if "ingestion_player_image_metadata" in tables:
            op.execute(f"""
                DELETE FROM ingestion_player_image_metadata WHERE player_id = '{pid}' AND image_role = 'portrait';
                INSERT INTO ingestion_player_image_metadata (
                    id, player_id, source_provider, provider_external_id,
                    image_role, source_url, moderation_status, rights_cleared,
                    is_primary, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), '{pid}', 'cloudinary', '{pid}',
                    'portrait', '{portrait}', 'approved', true,
                    true, NOW(), NOW()
                );
            """)


def downgrade() -> None:
    pass
