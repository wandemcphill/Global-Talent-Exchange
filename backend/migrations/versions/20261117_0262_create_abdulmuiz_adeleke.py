"""Create Abdulmuiz Adeleke as a tradable wonderkid.

Sporting Supreme FC centre-forward, born 12 April 2009. Left-footed
ST/CF/RW/RM/AM who cuts in from the right, shifts the ball onto his left
foot, and dribbles through the centre. GSI 71, potential 84, 184 cm.

Revision ID: 20261117_0262_create_abdulmuiz_adeleke
Revises: 20261117_0261_first_deposit_referral_affiliate
Create Date: 2026-11-17 23:45:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261117_0262_create_abdulmuiz_adeleke"
down_revision = "20261117_0261_first_deposit_referral_affiliate"
branch_labels = None
depends_on = None

PLAYER_ID = "809fd487-eeb1-57e1-b37a-df4119da1af2"
EXTERNAL_ID = "abdulmuiz_adeleke_1625997"
PORTRAIT = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1794955328/players/portraits/p_809fd487_abdulmuiz_adeleke.webp"
)
TRANSFERMARKT_URL = "https://www.transfermarkt.com/abdulmuiz-adeleke/profil/spieler/1625997"
CLUB = "Sporting Supreme FC"
LEAGUE = "N-Youth League (Nigeria)"
DOB = "2009-04-12"
CURRENT_GSI = 71
POTENTIAL_GSI = 84
TOTAL_SHARES = 400
PLAYSTYLE = (
    "Left-footed inside forward who cuts in from the right, "
    "shifts the ball onto his left foot, and dribbles through the centre"
)
TRAITS = [
    "Cuts Inside From Wing",
    "Shifts Onto Left Foot",
    "Dribbles Through The Centre",
    "Technical Dribbler",
    "Flair",
    "First Touch",
]
SECONDARY_POSITIONS = ["CF", "RW", "RM", "AM"]
ALL_POSITIONS = ["ST", "CF", "RW", "RM", "AM"]
ATTRIBUTES = {
    "pace": 77,
    "acceleration": 79,
    "sprint_speed": 76,
    "agility": 82,
    "balance": 76,
    "dribbling": 80,
    "ball_control": 80,
    "first_touch": 78,
    "flair": 81,
    "technique": 79,
    "skill_moves": 4,
    "weak_foot": 2,
    "shooting": 73,
    "finishing": 74,
    "shot_power": 74,
    "long_shots": 68,
    "volleys": 70,
    "positioning": 75,
    "composure": 73,
    "penalties": 70,
    "curve": 76,
    "passing": 69,
    "vision": 70,
    "crossing": 64,
    "short_passing": 70,
    "long_passing": 63,
    "defending": 36,
    "tackling": 32,
    "interceptions": 30,
    "heading": 70,
    "jumping": 73,
    "strength": 76,
    "stamina": 75,
    "aggression": 62,
    "physical": 75,
    "reactions": 73,
    "off_the_ball": 75,
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


def apply_abdulmuiz(conn: sa.Connection) -> None:
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
                WHERE lower(name) = 'nigeria' OR alpha2_code = 'NG'
                ORDER BY CASE WHEN lower(name) = 'nigeria' THEN 0 ELSE 1 END
                LIMIT 1
                """)).scalar()

    dna = {
        "age": 17,
        "overall": CURRENT_GSI,
        "sofifa_overall": CURRENT_GSI,
        "current_rating": CURRENT_GSI,
        "potential": POTENTIAL_GSI,
        "sofifa_potential": POTENTIAL_GSI,
        "potential_rating": POTENTIAL_GSI,
        "position": "ST",
        "normalized_position": "ST",
        "secondary_positions": SECONDARY_POSITIONS,
        "positions": ALL_POSITIONS,
        "position_display": "ST/CF/RW/RM/AM",
        "height_cm": 184,
        "weight_kg": 83,
        "preferred_foot": "Left",
        "weak_foot": 2,
        "skill_moves": 4,
        "date_of_birth": DOB,
        "birth_year": 2009,
        "nationality": "Nigeria",
        "nationality_code": "NG",
        "country_name": "Nigeria",
        "club_country": "Nigeria",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "shirt_number": 33,
        "youth_national_team": "Nigeria U20",
        "youth_national_teams": ["Nigeria U17", "Nigeria U20"],
        "transfermarkt_id": "1625997",
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
        "age": 17,
        "gsi": CURRENT_GSI,
        "overall": CURRENT_GSI,
        "global_scouting_index": CURRENT_GSI,
        "current_rating": CURRENT_GSI,
        "potential": POTENTIAL_GSI,
        "potential_gsi": POTENTIAL_GSI,
        "position": "ST",
        "normalized_position": "ST",
        "secondary_positions": SECONDARY_POSITIONS,
        "positions": ALL_POSITIONS,
        "position_display": "ST/CF/RW/RM/AM",
        "height_cm": 184,
        "weight_kg": 83,
        "preferred_foot": "Left",
        "date_of_birth": DOB,
        "nationality": "Nigeria",
        "country_name": "Nigeria",
        "nationality_code": "NG",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "club_country": "Nigeria",
        "shirt_number": 33,
        "youth_national_team": "Nigeria U20",
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
        "transfermarkt_id": "1625997",
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
        "country": "Nigeria",
        "position": "ST",
        "position_display": "ST/CF/RW/RM/AM",
        "secondary_positions": SECONDARY_POSITIONS,
        "preferred_foot": "Left",
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "height_cm": 184,
        "initial_share_price_coin": price,
        "transfermarkt_id": "1625997",
    }

    conn.execute(
        sa.text("""
            INSERT INTO ingestion_players (
                id, source_provider, provider_external_id, country_id,
                full_name, first_name, last_name, short_name, canonical_display_name,
                position, normalized_position, secondary_positions_json,
                real_world_club_name, real_world_league_name,
                date_of_birth, factual_date_of_birth, height_cm, weight_kg,
                preferred_foot, shirt_number,
                is_tradable, is_real_player, real_player_tier,
                governed_gsi, governed_potential_gsi, potential,
                gsi_methodology_version, gsi_override_reason,
                profile_completeness_score, identity_confidence_score,
                dna_profile, morale, created_at, updated_at, last_synced_at
            ) VALUES (
                :pid, 'curated_roster', :ext_id, :country_id,
                'Abdulmuiz Adeleke', 'Abdulmuiz', 'Adeleke', 'A. Adeleke', 'Abdulmuiz Adeleke',
                'ST', 'ST', CAST(:sec AS json),
                :club, :league,
                CAST(:dob AS date), CAST(:dob AS date), 184, 83,
                'Left', 33,
                true, true, 'wonderkid',
                :gsi, :pot, :pot,
                '2026.roster_governed_calibration',
                'User requested player creation: GSI 71, potential 84, left-footed ST/CF/RW/RM/AM, 184 cm',
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
                weight_kg = EXCLUDED.weight_kg,
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
                    :pid, 'Abdulmuiz Adeleke', :club, :league,
                    NOW(), :price, :price,
                    0.0, :gsi, :gsi, CAST(:sum AS json), NOW(), NOW()
                )
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = 'Abdulmuiz Adeleke',
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
    apply_abdulmuiz(op.get_bind())


def downgrade() -> None:
    pass
