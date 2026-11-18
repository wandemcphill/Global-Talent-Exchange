"""Create Héctor Asumu as a tradable wonderkid.

FC Barcelona U16 left winger, born 19 February 2011. Left-footed
LW/ST/CF/AM/RW. GSI 68, potential 86, 180 cm.

Revision ID: 20261117_0263_create_hector_asumu
Revises: 20261117_0262_create_abdulmuiz_adeleke
Create Date: 2026-11-17 23:55:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261117_0263_create_hector_asumu"
down_revision = "20261117_0262_create_abdulmuiz_adeleke"
branch_labels = None
depends_on = None

PLAYER_ID = "6220afa4-499c-5693-a1d8-44ad63227d90"
EXTERNAL_ID = "hector_asumu_1447509"
TRANSFERMARKT_URL = "https://www.transfermarkt.com/hector-asumu/profil/spieler/1447509"
CLUB = "FC Barcelona U16"
LEAGUE = "La Masia (Spain)"
DOB = "2011-02-19"
CURRENT_GSI = 68
POTENTIAL_GSI = 86
TOTAL_SHARES = 400
PLAYSTYLE = "Explosive left-footed winger who usually plays on the right " "and can also play left wing or as a striker"
TRAITS = [
    "Speed Dribbler",
    "Rapid",
    "Cuts Inside From Wing",
    "Technical Dribbler",
    "Flair",
    "Quick Step",
]
SECONDARY_POSITIONS = ["ST", "CF", "AM", "RW"]
ALL_POSITIONS = ["LW", "ST", "CF", "AM", "RW"]
ATTRIBUTES = {
    "pace": 76,
    "acceleration": 78,
    "sprint_speed": 77,
    "agility": 77,
    "balance": 73,
    "dribbling": 73,
    "ball_control": 72,
    "first_touch": 71,
    "flair": 74,
    "technique": 73,
    "skill_moves": 4,
    "weak_foot": 2,
    "shooting": 64,
    "finishing": 63,
    "shot_power": 71,
    "long_shots": 60,
    "volleys": 61,
    "positioning": 67,
    "composure": 66,
    "penalties": 58,
    "curve": 69,
    "passing": 67,
    "vision": 68,
    "crossing": 66,
    "short_passing": 68,
    "long_passing": 62,
    "defending": 30,
    "tackling": 28,
    "interceptions": 26,
    "heading": 64,
    "jumping": 72,
    "strength": 73,
    "stamina": 75,
    "aggression": 70,
    "physical": 73,
    "reactions": 69,
    "off_the_ball": 71,
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


def apply_hector_asumu(conn: sa.Connection) -> None:
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
                WHERE lower(name) = 'spain'
                LIMIT 1
                """)).scalar()

    dna = {
        "age": 15,
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
        "position_display": "LW/ST/CF/AM/RW",
        "height_cm": 180,
        "preferred_foot": "Left",
        "weak_foot": 2,
        "skill_moves": 4,
        "date_of_birth": DOB,
        "birth_year": 2011,
        "legal_name": "Héctor Néstor Asumu Oyana",
        "aliases": ["Hector Asumu", "Héctor Néstor Asumu Oyana"],
        "nationality": "Spain",
        "nationality_code": "ES",
        "country_name": "Spain",
        "second_nationality": "Equatorial Guinea",
        "birthplace": "Barcelona",
        "club_country": "Spain",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "youth_national_team": "Spain U16",
        "youth_clubs": ["FE Grama"],
        "transfermarkt_id": "1447509",
        "transfermarkt_url": TRANSFERMARKT_URL,
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "attributes": ATTRIBUTES,
        **ATTRIBUTES,
    }
    summary = {
        "age": 15,
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
        "position_display": "LW/ST/CF/AM/RW",
        "height_cm": 180,
        "preferred_foot": "Left",
        "date_of_birth": DOB,
        "nationality": "Spain",
        "country_name": "Spain",
        "nationality_code": "ES",
        "second_nationality": "Equatorial Guinea",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "club_country": "Spain",
        "youth_national_team": "Spain U16",
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
        "transfermarkt_id": "1447509",
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
        "country": "Spain",
        "position": "LW",
        "position_display": "LW/ST/CF/AM/RW",
        "secondary_positions": SECONDARY_POSITIONS,
        "preferred_foot": "Left",
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "height_cm": 180,
        "initial_share_price_coin": price,
        "transfermarkt_id": "1447509",
    }

    conn.execute(
        sa.text("""
            INSERT INTO ingestion_players (
                id, source_provider, provider_external_id, country_id,
                full_name, first_name, last_name, short_name, canonical_display_name,
                position, normalized_position, secondary_positions_json,
                real_world_club_name, real_world_league_name,
                date_of_birth, factual_date_of_birth, height_cm,
                preferred_foot,
                is_tradable, is_real_player, real_player_tier,
                governed_gsi, governed_potential_gsi, potential,
                gsi_methodology_version, gsi_override_reason,
                profile_completeness_score, identity_confidence_score,
                dna_profile, morale, created_at, updated_at, last_synced_at
            ) VALUES (
                :pid, 'curated_roster', :ext_id, :country_id,
                'Héctor Asumu', 'Héctor', 'Asumu', 'H. Asumu', 'Héctor Asumu',
                'LW', 'LW', CAST(:sec AS json),
                :club, :league,
                CAST(:dob AS date), CAST(:dob AS date), 180,
                'Left',
                true, true, 'wonderkid',
                :gsi, :pot, :pot,
                '2026.roster_governed_calibration',
                'User requested player creation: GSI 68, potential 86, left-footed LW/ST/CF/AM/RW, 180 cm',
                0.9, 0.98,
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
                    :pid, 'Héctor Asumu', :club, :league,
                    NOW(), :price, :price,
                    0.0, :gsi, :gsi, CAST(:sum AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = 'Héctor Asumu',
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


def upgrade() -> None:
    apply_hector_asumu(op.get_bind())


def downgrade() -> None:
    pass
