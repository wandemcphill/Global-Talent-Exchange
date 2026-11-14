"""Calibrate Younes Ebnoutalib, Said El Mala, Wael Mohya and create Sadiq Saleh.

1. Younes Ebnoutalib (Eintracht Frankfurt): GSI 82, Potential 89, Height 190 cm,
   authentic portrait attached.
2. Said El Mala (1. FC Köln): GSI 84, Potential 90, Position LW/LM/AM/ST,
   Height 187 cm.
3. Sadiq Saleh (FK Metta, Latvia): Created 20yo right-footed ST/SS/LW/LM,
   GSI 73, Potential 79, Height 180 cm, authentic portrait attached.
4. Wael Mohya (Borussia M'gladbach): GSI 78, Potential 86, Position AM/LM/LW/ST,
   Right-footed, very skillful dribbler/playmaker profile.

Revision ID: 20261114_0244_ebnoutalib_el_mala_saleh_mohya_calibration
Revises: 20261113_0243_community_and_owner_comms_overhaul
Create Date: 2026-11-14 12:30:00.000000
"""

from __future__ import annotations

import json
import sqlalchemy as sa
from alembic import op

revision = "20261114_0244_ebnoutalib_el_mala_saleh_mohya_calibration"
down_revision = "20261113_0243_community_and_owner_comms_overhaul"
branch_labels = None
depends_on = None

YOUNES_ID = "a79209be-5230-4283-8dbf-5f8f96e024f6"
YOUNES_PORTRAIT = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1794655684/players/portraits/p_a79209be_younes_ebnoutalib.jpg"
)

SAID_ID = "5a18d2ff-9158-4c71-b3f5-b36707e30bd7"
SAID_PORTRAIT = "https://cdn.sportmonks.com/images/soccer/players/31/37709599.png"

SADIQ_ID = "2ea36f39-0acd-59eb-905c-f5febcd52f0e"
SADIQ_PORTRAIT = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1794655687/players/portraits/p_2ea36f39_sadiq_saleh.png"
)
NIGERIA_COUNTRY_ID = "bd9930c3-0906-4977-8875-2da47926c833"

WAEL_ID = "158e322b-2580-43fd-b87a-feb8dc52c61a"
WAEL_DUP_ID = "a288a6dc-7963-41bf-b397-0b58fc7b2f0d"
WAEL_PORTRAIT = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657842/players/wonderkids/wk_158e322b_wael_mohya.jpg"
)


def _calc_price(cur: int, pot: int) -> float:
    eval_gsi = 0.40 * cur + 0.60 * pot
    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        t = (eval_gsi - 70.0) / 5.0
        base_price *= 0.40 + 0.60 * t
    return round(base_price, 2)


def _upsert_portrait_metadata(conn, player_id: str, provider: str, url: str) -> None:
    conn.execute(
        sa.text("DELETE FROM ingestion_player_image_metadata WHERE player_id = :pid AND image_role = 'portrait'"),
        {"pid": player_id},
    )
    conn.execute(
        sa.text("""
            INSERT INTO ingestion_player_image_metadata (
                id, player_id, source_provider, provider_external_id, image_role, source_url,
                moderation_status, rights_cleared, is_primary, created_at, updated_at
            ) VALUES (
                gen_random_uuid()::varchar, :pid, :provider, :pid, 'portrait', :url,
                'approved', true, true, NOW(), NOW()
            )
            """),
        {"pid": player_id, "provider": provider, "url": url},
    )


def _update_younes(conn, tables: set[str]) -> None:
    price = _calc_price(82, 89)
    attrs = {
        "pace": 83,
        "shooting": 84,
        "passing": 73,
        "dribbling": 80,
        "defending": 45,
        "physical": 85,
    }
    dna_patch = {
        "overall": 82,
        "sofifa_overall": 82,
        "current_rating": 82,
        "potential": 89,
        "sofifa_potential": 89,
        "potential_rating": 89,
        "height_cm": 190,
        "position": "ST",
        "secondary_positions": ["CF", "FW"],
        "portraitUrl": YOUNES_PORTRAIT,
        "image_url": YOUNES_PORTRAIT,
        "portraitStatus": "ready",
        "portraitSourceProvider": "cloudinary",
        "attributes": attrs,
        **attrs,
    }
    summary_patch = {
        "gsi": 82,
        "overall": 82,
        "global_scouting_index": 82,
        "current_rating": 82,
        "potential": 89,
        "potential_gsi": 89,
        "height_cm": 190,
        "position": "ST",
        "normalized_position": "ST",
        "secondary_positions": ["CF", "FW"],
        "real_player_tier": "established",
        "share_price_coin": price,
        "image_url": YOUNES_PORTRAIT,
        "portrait_url": YOUNES_PORTRAIT,
        "portrait_status": "ready",
        "attributes": attrs,
    }
    market_patch = {
        "tier": "core",
        "current_gsi": 82,
        "potential_gsi": 89,
        "governed_gsi": 82,
        "governed_potential_gsi": 89,
    }

    if "ingestion_players" in tables:
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET governed_gsi = 82,
                    governed_potential_gsi = 89,
                    potential = 89,
                    height_cm = 190,
                    position = 'ST',
                    normalized_position = 'ST',
                    secondary_positions_json = CAST(:sec AS json),
                    real_player_tier = 'established',
                    is_tradable = true,
                    gsi_methodology_version = '2026.roster_governed_calibration',
                    gsi_override_reason = 'User requested upgrade to 82/89 and 190 cm height',
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb)) || CAST(:dna AS jsonb))::json,
                    updated_at = NOW()
                WHERE id = :pid
                """),
            {
                "pid": YOUNES_ID,
                "sec": json.dumps(["CF", "FW"]),
                "dna": json.dumps(dna_patch),
            },
        )

    if "player_summary_read_models" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET current_value_credits = :price,
                    previous_value_credits = :price,
                    market_interest_score = 82,
                    summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:sum AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": YOUNES_ID, "price": price, "sum": json.dumps(summary_patch)},
        )

    if "player_share_markets" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET share_price_coin = :price,
                    status = 'active',
                    metadata_json = (COALESCE(CAST(metadata_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:mkt AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": YOUNES_ID, "price": price, "mkt": json.dumps(market_patch)},
        )

    if "real_player_profiles" in tables:
        conn.execute(
            sa.text("""
                UPDATE real_player_profiles
                SET height_cm = 190,
                    primary_position = 'ST',
                    metadata_json = jsonb_set(
                        jsonb_set(
                            COALESCE(CAST(metadata_json AS jsonb), CAST('{}' AS jsonb)),
                            '{photo_url}',
                            to_jsonb(CAST(:url AS text))
                        ),
                        '{image,source_url}',
                        to_jsonb(CAST(:url AS text))
                    )::json,
                    updated_at = NOW()
                WHERE gtex_player_id = :pid
                """),
            {"pid": YOUNES_ID, "url": YOUNES_PORTRAIT},
        )

    if "ingestion_player_image_metadata" in tables:
        _upsert_portrait_metadata(conn, YOUNES_ID, "cloudinary", YOUNES_PORTRAIT)


def _update_said_el_mala(conn, tables: set[str]) -> None:
    price = _calc_price(84, 90)
    sec_pos = ["LM", "AM", "ST"]
    attrs = {
        "pace": 87,
        "dribbling": 86,
        "shooting": 82,
        "passing": 80,
        "physical": 79,
        "defending": 45,
    }
    dna_patch = {
        "overall": 84,
        "sofifa_overall": 84,
        "current_rating": 84,
        "potential": 90,
        "sofifa_potential": 90,
        "potential_rating": 90,
        "height_cm": 187,
        "position": "LW",
        "secondary_positions": sec_pos,
        "positions": ["LW", "LM", "AM", "ST"],
        "position_display": "LW/LM/AM/ST",
        "portraitUrl": SAID_PORTRAIT,
        "image_url": SAID_PORTRAIT,
        "portraitStatus": "ready",
        "attributes": attrs,
        **attrs,
    }
    summary_patch = {
        "gsi": 84,
        "overall": 84,
        "global_scouting_index": 84,
        "current_rating": 84,
        "potential": 90,
        "potential_gsi": 90,
        "height_cm": 187,
        "position": "LW",
        "normalized_position": "LW",
        "secondary_positions": sec_pos,
        "positions": ["LW", "LM", "AM", "ST"],
        "position_display": "LW/LM/AM/ST",
        "real_player_tier": "wonderkid",
        "share_price_coin": price,
        "image_url": SAID_PORTRAIT,
        "portrait_url": SAID_PORTRAIT,
        "portrait_status": "ready",
        "attributes": attrs,
    }
    market_patch = {
        "tier": "wonderkid",
        "current_gsi": 84,
        "potential_gsi": 90,
        "governed_gsi": 84,
        "governed_potential_gsi": 90,
    }

    if "ingestion_players" in tables:
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET governed_gsi = 84,
                    governed_potential_gsi = 90,
                    potential = 90,
                    height_cm = 187,
                    position = 'LW',
                    normalized_position = 'LW',
                    secondary_positions_json = CAST(:sec AS json),
                    real_player_tier = 'wonderkid',
                    is_tradable = true,
                    gsi_methodology_version = '2026.roster_governed_calibration',
                    gsi_override_reason = 'User requested upgrade to 84/90, LW/LM/AM/ST, 187 cm',
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb)) || CAST(:dna AS jsonb))::json,
                    updated_at = NOW()
                WHERE id = :pid
                """),
            {
                "pid": SAID_ID,
                "sec": json.dumps(sec_pos),
                "dna": json.dumps(dna_patch),
            },
        )

    if "player_summary_read_models" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET current_value_credits = :price,
                    previous_value_credits = :price,
                    market_interest_score = 84,
                    summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:sum AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": SAID_ID, "price": price, "sum": json.dumps(summary_patch)},
        )

    if "player_share_markets" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET share_price_coin = :price,
                    status = 'active',
                    metadata_json = (COALESCE(CAST(metadata_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:mkt AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": SAID_ID, "price": price, "mkt": json.dumps(market_patch)},
        )

    if "real_player_profiles" in tables:
        conn.execute(
            sa.text("""
                UPDATE real_player_profiles
                SET height_cm = 187,
                    primary_position = 'LW',
                    secondary_positions_json = CAST(:sec AS json),
                    updated_at = NOW()
                WHERE gtex_player_id = :pid
                """),
            {"pid": SAID_ID, "sec": json.dumps(sec_pos)},
        )


def _create_sadiq_saleh(conn, tables: set[str]) -> None:
    price = _calc_price(73, 79)
    sec_pos = ["SS", "LW", "LM"]
    attrs = {
        "pace": 80,
        "shooting": 75,
        "passing": 66,
        "dribbling": 75,
        "defending": 38,
        "physical": 74,
    }
    dna = {
        "age": 20,
        "overall": 73,
        "sofifa_overall": 73,
        "current_rating": 73,
        "potential": 79,
        "sofifa_potential": 79,
        "potential_rating": 79,
        "position": "ST",
        "secondary_positions": sec_pos,
        "positions": ["ST", "SS", "LW", "LM"],
        "position_display": "ST/SS/LW/LM",
        "height_cm": 180,
        "preferred_foot": "Right",
        "date_of_birth": "2006-05-18",
        "nationality": "Nigeria",
        "nationality_code": "NG",
        "club_country": "Latvia",
        "portraitUrl": SADIQ_PORTRAIT,
        "image_url": SADIQ_PORTRAIT,
        "portraitStatus": "ready",
        "portraitSourceProvider": "cloudinary",
        "attributes": attrs,
        **attrs,
    }
    summary = {
        "age": 20,
        "gsi": 73,
        "overall": 73,
        "global_scouting_index": 73,
        "current_rating": 73,
        "potential": 79,
        "potential_gsi": 79,
        "position": "ST",
        "normalized_position": "ST",
        "secondary_positions": sec_pos,
        "positions": ["ST", "SS", "LW", "LM"],
        "position_display": "ST/SS/LW/LM",
        "height_cm": 180,
        "preferred_foot": "Right",
        "date_of_birth": "2006-05-18",
        "nationality": "Nigeria",
        "country_name": "Nigeria",
        "nationality_code": "NG",
        "real_world_club_name": "FK Metta",
        "real_world_league_name": "Virslīga (Latvia)",
        "club_country": "Latvia",
        "is_legend": False,
        "is_real_player": True,
        "is_tradable": True,
        "real_player_tier": "wonderkid",
        "total_shares": 400,
        "released_shares": 400,
        "available_shares": 400,
        "circulating_shares": 0,
        "share_price_coin": price,
        "market_visibility": {"status": "visible", "eligible": True},
        "image_url": SADIQ_PORTRAIT,
        "portrait_url": SADIQ_PORTRAIT,
        "portrait_status": "ready",
        "attributes": attrs,
    }
    market_meta = {
        "asset_type": "real_player_fractional_share",
        "tier": "wonderkid",
        "current_gsi": 73,
        "potential_gsi": 79,
        "governed_gsi": 73,
        "governed_potential_gsi": 79,
        "club": "FK Metta",
        "country": "Latvia",
        "position": "ST",
        "secondary_positions": sec_pos,
    }

    if "ingestion_players" in tables:
        conn.execute(
            sa.text("""
                INSERT INTO ingestion_players (
                    id, source_provider, provider_external_id, country_id,
                    full_name, first_name, last_name, short_name, canonical_display_name,
                    position, normalized_position, secondary_positions_json,
                    real_world_club_name, real_world_league_name,
                    date_of_birth, height_cm, preferred_foot,
                    is_tradable, is_real_player, real_player_tier,
                    governed_gsi, governed_potential_gsi, potential,
                    gsi_methodology_version, gsi_override_reason,
                    dna_profile, morale, created_at, updated_at, last_synced_at
                ) VALUES (
                    :pid, 'curated_roster', 'sadiq_saleh_2ea36f39', :country_id,
                    'Sadiq Saleh', 'Sadiq', 'Saleh', 'S. Saleh', 'Sadiq Saleh',
                    'ST', 'ST', CAST(:sec AS json),
                    'FK Metta', 'Virslīga (Latvia)',
                    CAST('2006-05-18' AS date), 180, 'Right',
                    true, true, 'wonderkid',
                    73, 79, 79,
                    '2026.roster_governed_calibration', 'User requested player creation and calibration',
                    CAST(:dna AS json), 75.0, NOW(), NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    canonical_display_name = EXCLUDED.canonical_display_name,
                    country_id = EXCLUDED.country_id,
                    position = EXCLUDED.position,
                    normalized_position = EXCLUDED.normalized_position,
                    secondary_positions_json = EXCLUDED.secondary_positions_json,
                    real_world_club_name = EXCLUDED.real_world_club_name,
                    real_world_league_name = EXCLUDED.real_world_league_name,
                    date_of_birth = EXCLUDED.date_of_birth,
                    height_cm = EXCLUDED.height_cm,
                    preferred_foot = EXCLUDED.preferred_foot,
                    is_tradable = true,
                    is_real_player = true,
                    real_player_tier = 'wonderkid',
                    governed_gsi = 73,
                    governed_potential_gsi = 79,
                    potential = 79,
                    dna_profile = (COALESCE(CAST(ingestion_players.dna_profile AS jsonb), CAST('{}' AS jsonb)) || CAST(:dna AS jsonb))::json,
                    updated_at = NOW()
                """),
            {
                "pid": SADIQ_ID,
                "country_id": NIGERIA_COUNTRY_ID,
                "sec": json.dumps(sec_pos),
                "dna": json.dumps(dna),
            },
        )

    if "player_share_markets" in tables:
        conn.execute(
            sa.text("""
                INSERT INTO player_share_markets (
                    id, player_id, total_shares, released_shares, circulating_shares,
                    share_price_coin, status, revenue_distributed_coin,
                    metadata_json, created_at, updated_at
                ) VALUES (
                    gen_random_uuid()::varchar, :pid, 400, 400, 0,
                    :price, 'active', 0.0,
                    CAST(:mkt AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    total_shares = 400,
                    released_shares = 400,
                    share_price_coin = :price,
                    status = 'active',
                    metadata_json = (COALESCE(CAST(player_share_markets.metadata_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:mkt AS jsonb))::json,
                    updated_at = NOW()
                """),
            {"pid": SADIQ_ID, "price": price, "mkt": json.dumps(market_meta)},
        )

    if "player_summary_read_models" in tables:
        conn.execute(
            sa.text("""
                INSERT INTO player_summary_read_models (
                    player_id, player_name, current_club_name, current_competition_name,
                    last_snapshot_at, current_value_credits, previous_value_credits,
                    movement_pct, market_interest_score, summary_json, created_at, updated_at
                ) VALUES (
                    :pid, 'Sadiq Saleh', 'FK Metta', 'Virslīga (Latvia)',
                    NOW(), :price, :price,
                    0.0, 73, CAST(:sum AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = 'Sadiq Saleh',
                    current_club_name = 'FK Metta',
                    current_competition_name = 'Virslīga (Latvia)',
                    current_value_credits = :price,
                    previous_value_credits = :price,
                    market_interest_score = 73,
                    summary_json = (COALESCE(CAST(player_summary_read_models.summary_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:sum AS jsonb))::json,
                    updated_at = NOW()
                """),
            {"pid": SADIQ_ID, "price": price, "sum": json.dumps(summary)},
        )

    if "ingestion_player_image_metadata" in tables:
        _upsert_portrait_metadata(conn, SADIQ_ID, "cloudinary", SADIQ_PORTRAIT)


def _update_wael_mohya(conn, tables: set[str]) -> None:
    price = _calc_price(78, 86)
    sec_pos = ["LM", "LW", "ST"]
    playstyle = "Technical Playmaker & Skillful Dribbler (Flair & Close Control)"
    skills = ["Flair", "Dribbling", "Technical", "Agility", "Ball Control", "Vision"]
    attrs = {
        "pace": 82,
        "dribbling": 86,
        "passing": 80,
        "shooting": 76,
        "physical": 68,
        "defending": 45,
        "flair": 90,
        "technique": 87,
        "agility": 88,
        "ball_control": 86,
        "first_touch": 86,
        "vision": 82,
        "acceleration": 84,
        "skill_moves": 5,
    }
    dna_patch = {
        "overall": 78,
        "sofifa_overall": 78,
        "current_rating": 78,
        "potential": 86,
        "sofifa_potential": 86,
        "potential_rating": 86,
        "position": "AM",
        "secondary_positions": sec_pos,
        "positions": ["AM", "LM", "LW", "ST"],
        "position_display": "AM/LM/LW/ST",
        "preferred_foot": "Right",
        "height_cm": 179,
        "playstyle": playstyle,
        "skills": skills,
        "skill_moves": 5,
        "portraitUrl": WAEL_PORTRAIT,
        "image_url": WAEL_PORTRAIT,
        "portraitStatus": "ready",
        "portraitSourceProvider": "cloudinary",
        "attributes": attrs,
        "pace": 82,
        "dribbling": 86,
        "passing": 80,
        "shooting": 76,
        "physical": 68,
        "defending": 45,
    }
    summary_patch = {
        "gsi": 78,
        "overall": 78,
        "global_scouting_index": 78,
        "current_rating": 78,
        "potential": 86,
        "potential_gsi": 86,
        "position": "AM",
        "normalized_position": "AM",
        "secondary_positions": sec_pos,
        "positions": ["AM", "LM", "LW", "ST"],
        "position_display": "AM/LM/LW/ST",
        "preferred_foot": "Right",
        "height_cm": 179,
        "playstyle": playstyle,
        "skills": skills,
        "skill_moves": 5,
        "real_player_tier": "wonderkid",
        "share_price_coin": price,
        "image_url": WAEL_PORTRAIT,
        "portrait_url": WAEL_PORTRAIT,
        "portrait_status": "ready",
        "attributes": attrs,
    }
    market_patch = {
        "tier": "wonderkid",
        "current_gsi": 78,
        "potential_gsi": 86,
        "governed_gsi": 78,
        "governed_potential_gsi": 86,
    }

    if "ingestion_players" in tables:
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET governed_gsi = 78,
                    governed_potential_gsi = 86,
                    potential = 86,
                    position = 'AM',
                    normalized_position = 'AM',
                    secondary_positions_json = CAST(:sec AS json),
                    preferred_foot = 'Right',
                    height_cm = COALESCE(height_cm, 179),
                    real_player_tier = 'wonderkid',
                    is_tradable = true,
                    gsi_methodology_version = '2026.roster_governed_calibration',
                    gsi_override_reason = 'User requested upgrade to 78/86, AM/LM/LW/ST, right footed, very skillful',
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb)) || CAST(:dna AS jsonb))::json,
                    updated_at = NOW()
                WHERE id = :pid
                """),
            {
                "pid": WAEL_ID,
                "sec": json.dumps(sec_pos),
                "dna": json.dumps(dna_patch),
            },
        )
        # Keep duplicate card retired but aligned on core ratings
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET governed_gsi = 78,
                    governed_potential_gsi = 86,
                    potential = 86,
                    position = 'AM',
                    normalized_position = 'AM',
                    secondary_positions_json = CAST(:sec AS json),
                    preferred_foot = 'Right',
                    is_tradable = false,
                    real_player_tier = 'archived_duplicate',
                    updated_at = NOW()
                WHERE id = :dup_id
                """),
            {"dup_id": WAEL_DUP_ID, "sec": json.dumps(sec_pos)},
        )

    if "player_summary_read_models" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET current_value_credits = :price,
                    previous_value_credits = :price,
                    market_interest_score = 78,
                    summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:sum AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": WAEL_ID, "price": price, "sum": json.dumps(summary_patch)},
        )

    if "player_share_markets" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET share_price_coin = :price,
                    status = 'active',
                    metadata_json = (COALESCE(CAST(metadata_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:mkt AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": WAEL_ID, "price": price, "mkt": json.dumps(market_patch)},
        )


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    _update_younes(conn, tables)
    _update_said_el_mala(conn, tables)
    _create_sadiq_saleh(conn, tables)
    _update_wael_mohya(conn, tables)


def downgrade() -> None:
    pass
