"""Create Sega Fall Mbodji as a tradable wonderkid.

AS Génération Foot winger, born 27 November 2009. Right-footed, skillful
LW/LM/ST/RW/AM. GSI 73, potential 84, 175 cm. Senegal.

Revision ID: 20261118_0264_create_sega_fall_mbodji
Revises: 20261117_0263_create_hector_asumu
Create Date: 2026-11-18 00:10:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261118_0264_create_sega_fall_mbodji"
down_revision = "20261117_0263_create_hector_asumu"
branch_labels = None
depends_on = None

PLAYER_ID = "f5b7ac73-327b-594d-bb90-f5d4cf8b3341"
EXTERNAL_ID = "sega_fall_mbodji_1475230"
PORTRAIT = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1794956979/players/portraits/p_f5b7ac73_sega_fall_mbodji.webp"
)
TRANSFERMARKT_URL = "https://www.transfermarkt.com/sega-mbodji/profil/spieler/1475230"
CLUB = "AS Génération Foot"
LEAGUE = "Ligue 1 (Senegal)"
DOB = "2009-11-27"
CURRENT_GSI = 73
POTENTIAL_GSI = 84
TOTAL_SHARES = 400
PLAYSTYLE = "Skillful right-footed winger who plays both wings and can finish through the middle"
TRAITS = [
    "Technical Dribbler",
    "Flair",
    "Trickster",
    "First Touch",
    "Cuts Inside From Wing",
    "Quick Step",
]
SECONDARY_POSITIONS = ["LM", "ST", "RW", "AM"]
ALL_POSITIONS = ["LW", "LM", "ST", "RW", "AM"]
ATTRIBUTES = {
    "pace": 76,
    "acceleration": 78,
    "sprint_speed": 75,
    "agility": 83,
    "balance": 81,
    "dribbling": 80,
    "ball_control": 79,
    "first_touch": 78,
    "flair": 83,
    "technique": 80,
    "skill_moves": 5,
    "weak_foot": 3,
    "shooting": 70,
    "finishing": 70,
    "shot_power": 72,
    "long_shots": 68,
    "volleys": 66,
    "positioning": 72,
    "composure": 73,
    "penalties": 64,
    "curve": 76,
    "passing": 71,
    "vision": 72,
    "crossing": 74,
    "short_passing": 72,
    "long_passing": 66,
    "defending": 34,
    "tackling": 32,
    "interceptions": 30,
    "heading": 58,
    "jumping": 64,
    "strength": 62,
    "stamina": 75,
    "aggression": 64,
    "physical": 64,
    "reactions": 74,
    "off_the_ball": 74,
}


def _calc_price(cur: int, pot: int) -> float:
    eval_gsi = 0.40 * cur + 0.60 * pot
    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        t = (eval_gsi - 70.0) / 5.0
        base_price *= 0.40 + 0.60 * t
    return round(base_price, 2)


def apply_sega_fall_mbodji(conn: sa.Connection) -> None:
    if getattr(getattr(conn, "dialect", None), "name", "") != "postgresql":
        return

    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    if "ingestion_players" not in tables:
        return

    price = _calc_price(CURRENT_GSI, POTENTIAL_GSI)
    country_id = None
    if "ingestion_countries" in tables:
        country_id = conn.execute(sa.text("""
                SELECT id
                FROM ingestion_countries
                WHERE lower(name) = 'senegal' OR alpha2_code = 'SN'
                ORDER BY CASE WHEN lower(name) = 'senegal' THEN 0 ELSE 1 END
                LIMIT 1
                """)).scalar()

    dna = {
        "age": 16,
        "overall": CURRENT_GSI,
        "sofifa_overall": CURRENT_GSI,
        "current_rating": CURRENT_GSI,
        "potential": POTENTIAL_GSI,
        "sofifa_potential": POTENTIAL_GSI,
        "potential_rating": POTENTIAL_GSI,
        "position": "LW",
        "normalized_position": "LW",
        "secondary_positions": SECONDARY_POSITIONS,
        "positions": ALL_POSITIONS,
        "position_display": "LW/LM/ST/RW/AM",
        "height_cm": 175,
        "preferred_foot": "Right",
        "weak_foot": 3,
        "skill_moves": 5,
        "date_of_birth": DOB,
        "birth_year": 2009,
        "aliases": ["Sega Mbodji", "Séga Fall Mbodji"],
        "nationality": "Senegal",
        "nationality_code": "SN",
        "country_name": "Senegal",
        "club_country": "Senegal",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "shirt_number": 7,
        "youth_national_team": "Senegal U17",
        "honours": ["AFCON U17 2026"],
        "transfermarkt_id": "1475230",
        "transfermarkt_url": TRANSFERMARKT_URL,
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "portraitUrl": PORTRAIT,
        "image_url": PORTRAIT,
        "portraitStatus": "ready",
        "portraitSourceProvider": "cloudinary",
        "attributes": ATTRIBUTES,
        **ATTRIBUTES,
    }
    summary = {
        "age": 16,
        "gsi": CURRENT_GSI,
        "overall": CURRENT_GSI,
        "global_scouting_index": CURRENT_GSI,
        "current_rating": CURRENT_GSI,
        "potential": POTENTIAL_GSI,
        "potential_gsi": POTENTIAL_GSI,
        "position": "LW",
        "normalized_position": "LW",
        "secondary_positions": SECONDARY_POSITIONS,
        "positions": ALL_POSITIONS,
        "position_display": "LW/LM/ST/RW/AM",
        "height_cm": 175,
        "preferred_foot": "Right",
        "date_of_birth": DOB,
        "nationality": "Senegal",
        "country_name": "Senegal",
        "nationality_code": "SN",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "club_country": "Senegal",
        "shirt_number": 7,
        "youth_national_team": "Senegal U17",
        "is_legend": False,
        "is_real_player": True,
        "is_tradable": True,
        "real_player_tier": "wonderkid",
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "total_shares": TOTAL_SHARES,
        "released_shares": TOTAL_SHARES,
        "available_shares": TOTAL_SHARES,
        "circulating_shares": 0,
        "share_price_coin": price,
        "market_visibility": {"status": "visible", "eligible": True},
        "image_url": PORTRAIT,
        "portrait_url": PORTRAIT,
        "portrait_status": "ready",
        "transfermarkt_id": "1475230",
        "transfermarkt_url": TRANSFERMARKT_URL,
        "attributes": ATTRIBUTES,
    }
    market_meta = {
        "asset_type": "real_player_fractional_share",
        "tier": "wonderkid",
        "supply_band": "core",
        "current_gsi": CURRENT_GSI,
        "potential_gsi": POTENTIAL_GSI,
        "governed_gsi": CURRENT_GSI,
        "governed_potential_gsi": POTENTIAL_GSI,
        "club": CLUB,
        "league": LEAGUE,
        "country": "Senegal",
        "position": "LW",
        "position_display": "LW/LM/ST/RW/AM",
        "secondary_positions": SECONDARY_POSITIONS,
        "preferred_foot": "Right",
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "height_cm": 175,
        "initial_share_price_coin": price,
        "transfermarkt_id": "1475230",
    }

    conn.execute(
        sa.text("""
            INSERT INTO ingestion_players (
                id, source_provider, provider_external_id, country_id,
                full_name, first_name, last_name, short_name, canonical_display_name,
                position, normalized_position, secondary_positions_json,
                real_world_club_name, real_world_league_name,
                date_of_birth, factual_date_of_birth, height_cm,
                preferred_foot, shirt_number,
                is_tradable, is_real_player, real_player_tier,
                governed_gsi, governed_potential_gsi, potential,
                gsi_methodology_version, gsi_override_reason,
                profile_completeness_score, identity_confidence_score,
                dna_profile, morale, created_at, updated_at, last_synced_at
            ) VALUES (
                :pid, 'curated_roster', :ext_id, :country_id,
                'Sega Fall Mbodji', 'Sega Fall', 'Mbodji', 'S. Mbodji', 'Sega Fall Mbodji',
                'LW', 'LW', CAST(:sec AS json),
                :club, :league,
                CAST(:dob AS date), CAST(:dob AS date), 175,
                'Right', 7,
                true, true, 'wonderkid',
                :gsi, :pot, :pot,
                '2026.roster_governed_calibration',
                'User requested player creation: GSI 73, potential 84, right-footed skillful LW/LM/ST/RW/AM, 175 cm',
                0.95, 0.98,
                CAST(:dna AS json), 75.0, NOW(), NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                source_provider = 'curated_roster',
                provider_external_id = EXCLUDED.provider_external_id,
                country_id = COALESCE(EXCLUDED.country_id, ingestion_players.country_id),
                full_name = EXCLUDED.full_name,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                short_name = EXCLUDED.short_name,
                canonical_display_name = EXCLUDED.canonical_display_name,
                position = EXCLUDED.position,
                normalized_position = EXCLUDED.normalized_position,
                secondary_positions_json = EXCLUDED.secondary_positions_json,
                real_world_club_name = EXCLUDED.real_world_club_name,
                real_world_league_name = EXCLUDED.real_world_league_name,
                date_of_birth = EXCLUDED.date_of_birth,
                factual_date_of_birth = EXCLUDED.factual_date_of_birth,
                height_cm = EXCLUDED.height_cm,
                preferred_foot = EXCLUDED.preferred_foot,
                shirt_number = EXCLUDED.shirt_number,
                is_tradable = true,
                is_real_player = true,
                real_player_tier = 'wonderkid',
                legendary_profile_id = NULL,
                governed_gsi = EXCLUDED.governed_gsi,
                governed_potential_gsi = EXCLUDED.governed_potential_gsi,
                potential = EXCLUDED.potential,
                gsi_methodology_version = EXCLUDED.gsi_methodology_version,
                gsi_override_reason = EXCLUDED.gsi_override_reason,
                dna_profile = (
                    COALESCE(CAST(ingestion_players.dna_profile AS jsonb), CAST('{}' AS jsonb))
                    || CAST(:dna AS jsonb)
                )::json,
                updated_at = NOW()
            """),
        {
            "pid": PLAYER_ID,
            "ext_id": EXTERNAL_ID,
            "country_id": country_id,
            "sec": json.dumps(SECONDARY_POSITIONS),
            "club": CLUB,
            "league": LEAGUE,
            "dob": DOB,
            "gsi": CURRENT_GSI,
            "pot": POTENTIAL_GSI,
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
                    gen_random_uuid()::varchar, :pid, :shares, :shares, 0,
                    :price, 'active', 0.0,
                    CAST(:mkt AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    total_shares = :shares,
                    released_shares = :shares,
                    status = 'active',
                    share_price_coin = CASE
                        WHEN player_share_markets.circulating_shares = 0 THEN :price
                        ELSE player_share_markets.share_price_coin
                    END,
                    metadata_json = (
                        COALESCE(CAST(player_share_markets.metadata_json AS jsonb), CAST('{}' AS jsonb))
                        || CAST(:mkt AS jsonb)
                    )::json,
                    updated_at = NOW()
                """),
            {
                "pid": PLAYER_ID,
                "shares": TOTAL_SHARES,
                "price": price,
                "mkt": json.dumps(market_meta),
            },
        )

    if "player_summary_read_models" in tables:
        conn.execute(
            sa.text("""
                INSERT INTO player_summary_read_models (
                    player_id, player_name, current_club_name, current_competition_name,
                    last_snapshot_at, current_value_credits, previous_value_credits,
                    movement_pct, average_rating, market_interest_score,
                    summary_json, created_at, updated_at
                ) VALUES (
                    :pid, 'Sega Fall Mbodji', :club, :league,
                    NOW(), :price, :price,
                    0.0, :gsi, :gsi, CAST(:sum AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = 'Sega Fall Mbodji',
                    current_club_name = :club,
                    current_competition_name = :league,
                    current_value_credits = CASE
                        WHEN COALESCE((
                            SELECT circulating_shares FROM player_share_markets WHERE player_id = :pid
                        ), 0) = 0 THEN :price
                        ELSE player_summary_read_models.current_value_credits
                    END,
                    market_interest_score = :gsi,
                    average_rating = :gsi,
                    summary_json = (
                        COALESCE(CAST(player_summary_read_models.summary_json AS jsonb), CAST('{}' AS jsonb))
                        || CAST(:sum AS jsonb)
                    )::json,
                    updated_at = NOW()
                """),
            {
                "pid": PLAYER_ID,
                "club": CLUB,
                "league": LEAGUE,
                "price": price,
                "gsi": CURRENT_GSI,
                "sum": json.dumps(summary),
            },
        )

    if "ingestion_player_image_metadata" in tables:
        conn.execute(
            sa.text("""
                DELETE FROM ingestion_player_image_metadata
                WHERE player_id = :pid AND image_role = 'portrait'
                """),
            {"pid": PLAYER_ID},
        )
        conn.execute(
            sa.text("""
                INSERT INTO ingestion_player_image_metadata (
                    id, player_id, source_provider, provider_external_id, image_role, source_url,
                    moderation_status, rights_cleared, is_primary, created_at, updated_at
                ) VALUES (
                    gen_random_uuid()::varchar, :pid, 'cloudinary', :pid, 'portrait', :url,
                    'approved', true, true, NOW(), NOW()
                )
                """),
            {"pid": PLAYER_ID, "url": PORTRAIT},
        )


def upgrade() -> None:
    apply_sega_fall_mbodji(op.get_bind())


def downgrade() -> None:
    pass
