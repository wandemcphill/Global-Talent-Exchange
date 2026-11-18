"""Correct Kennet Eichhorn and attach his portrait.

The existing Leverkusen card had the wrong date of birth, a generic
midfield role, and a placeholder photo. Governed GSI 78 and potential 92
stay as they are. He is a right-footed defensive midfielder, born
27 July 2009, 186 cm.

Revision ID: 20261118_0265_update_kennet_eichhorn
Revises: 20261118_0264_create_sega_fall_mbodji
Create Date: 2026-11-18 00:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261118_0265_update_kennet_eichhorn"
down_revision = "20261118_0264_create_sega_fall_mbodji"
branch_labels = None
depends_on = None

PLAYER_ID = "e2aa7bf2-2ee4-4ca8-bf5f-ad7362751c7c"
PORTRAIT = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1794957882/players/portraits/p_cb55f99a_kennet_eichhorn.webp"
)
TRANSFERMARKT_URL = "https://www.transfermarkt.com/kennet-eichhorn/profil/spieler/1214123"
CLUB = "Bayer 04 Leverkusen"
LEAGUE = "Bundesliga"
DOB = "2009-07-27"
PLAYSTYLE = "Composed deep-lying playmaker who protects the ball, switches play, " "and carries it through pressure"
TRAITS = [
    "Dictates Tempo",
    "First Touch",
    "Long Ball Pass",
    "Press Proven",
    "Intercept",
    "Technical Dribbler",
]
SECONDARY_POSITIONS = ["CM"]
ALL_POSITIONS = ["DM", "CM"]
ATTRIBUTES = {
    "pace": 72,
    "acceleration": 73,
    "sprint_speed": 71,
    "agility": 76,
    "balance": 79,
    "dribbling": 77,
    "ball_control": 80,
    "first_touch": 82,
    "flair": 70,
    "technique": 79,
    "skill_moves": 3,
    "weak_foot": 3,
    "shooting": 68,
    "finishing": 64,
    "shot_power": 72,
    "long_shots": 72,
    "positioning": 76,
    "composure": 81,
    "passing": 80,
    "vision": 81,
    "crossing": 68,
    "short_passing": 82,
    "long_passing": 80,
    "decisions": 80,
    "defending": 76,
    "tackling": 75,
    "interceptions": 78,
    "heading": 70,
    "jumping": 74,
    "strength": 74,
    "stamina": 79,
    "aggression": 72,
    "physical": 75,
    "reactions": 78,
}


def apply_kennet_eichhorn(conn: sa.Connection) -> None:
    if getattr(getattr(conn, "dialect", None), "name", "") != "postgresql":
        return

    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    if "ingestion_players" not in tables:
        return

    exists = conn.execute(
        sa.text("SELECT 1 FROM ingestion_players WHERE id = :pid"),
        {"pid": PLAYER_ID},
    ).scalar()
    if exists is None:
        return

    dna_patch = {
        "age": 17,
        "date_of_birth": DOB,
        "birth_year": 2009,
        "birthplace": "Bernau bei Berlin",
        "position": "DM",
        "normalized_position": "DM",
        "secondary_positions": SECONDARY_POSITIONS,
        "positions": ALL_POSITIONS,
        "position_display": "DM/CM",
        "height_cm": 186,
        "weight_kg": 79,
        "preferred_foot": "Right",
        "weak_foot": 3,
        "skill_moves": 3,
        "shirt_number": 18,
        "nationality": "Germany",
        "nationality_code": "DE",
        "country_name": "Germany",
        "club_country": "Germany",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "youth_national_team": "Germany U17",
        "youth_clubs": ["Hertha BSC"],
        "transfermarkt_id": "1214123",
        "transfermarkt_url": TRANSFERMARKT_URL,
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "real_player_tier": "wonderkid",
        "portraitUrl": PORTRAIT,
        "image_url": PORTRAIT,
        "portraitStatus": "ready",
        "portraitSourceProvider": "cloudinary",
        "attributes": ATTRIBUTES,
        "pace": 72,
        "shooting": 68,
        "passing": 80,
        "dribbling": 77,
        "defending": 76,
        "physical": 75,
    }
    summary_patch = {
        "age": 17,
        "date_of_birth": DOB,
        "position": "DM",
        "normalized_position": "DM",
        "secondary_positions": SECONDARY_POSITIONS,
        "positions": ALL_POSITIONS,
        "position_display": "DM/CM",
        "height_cm": 186,
        "weight_kg": 79,
        "preferred_foot": "Right",
        "shirt_number": 18,
        "nationality": "Germany",
        "country_name": "Germany",
        "nationality_code": "DE",
        "real_world_club_name": CLUB,
        "real_world_league_name": LEAGUE,
        "club_country": "Germany",
        "youth_national_team": "Germany U17",
        "real_player_tier": "wonderkid",
        "is_real_player": True,
        "is_tradable": True,
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "skills": TRAITS,
        "image_url": PORTRAIT,
        "portrait_url": PORTRAIT,
        "portrait_status": "ready",
        "transfermarkt_id": "1214123",
        "transfermarkt_url": TRANSFERMARKT_URL,
        "attributes": ATTRIBUTES,
    }
    market_patch = {
        "position": "DM",
        "position_display": "DM/CM",
        "secondary_positions": SECONDARY_POSITIONS,
        "preferred_foot": "Right",
        "playstyle": PLAYSTYLE,
        "traits": TRAITS,
        "height_cm": 186,
        "club": CLUB,
        "league": LEAGUE,
        "country": "Germany",
        "tier": "wonderkid",
    }

    conn.execute(
        sa.text("""
            UPDATE ingestion_players
            SET first_name = 'Kennet',
                last_name = 'Eichhorn',
                short_name = 'K. Eichhorn',
                canonical_display_name = 'Kennet Eichhorn',
                position = 'DM',
                normalized_position = 'DM',
                secondary_positions_json = CAST(:sec AS json),
                preferred_foot = 'Right',
                height_cm = 186,
                weight_kg = 79,
                shirt_number = 18,
                date_of_birth = CAST(:dob AS date),
                factual_date_of_birth = CAST(:dob AS date),
                real_world_club_name = :club,
                real_world_league_name = :league,
                is_tradable = true,
                is_real_player = true,
                real_player_tier = 'wonderkid',
                legendary_profile_id = NULL,
                dna_profile = (
                    COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb))
                    || CAST(:dna AS jsonb)
                )::json,
                updated_at = NOW()
            WHERE id = :pid
            """),
        {
            "pid": PLAYER_ID,
            "sec": json.dumps(SECONDARY_POSITIONS),
            "dob": DOB,
            "club": CLUB,
            "league": LEAGUE,
            "dna": json.dumps(dna_patch),
        },
    )

    if "player_summary_read_models" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET current_club_name = :club,
                    summary_json = (
                        COALESCE(CAST(summary_json AS jsonb), CAST('{}' AS jsonb))
                        || CAST(:sum AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": PLAYER_ID, "club": CLUB, "sum": json.dumps(summary_patch)},
        )

    if "player_share_markets" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET status = 'active',
                    metadata_json = (
                        COALESCE(CAST(metadata_json AS jsonb), CAST('{}' AS jsonb))
                        || CAST(:mkt AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": PLAYER_ID, "mkt": json.dumps(market_patch)},
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
                    gen_random_uuid()::varchar, :pid, 'cloudinary', :ext, 'portrait', :url,
                    'approved', true, true, NOW(), NOW()
                )
                """),
            {"pid": PLAYER_ID, "ext": f"{PLAYER_ID}-portrait", "url": PORTRAIT},
        )


def upgrade() -> None:
    apply_kennet_eichhorn(op.get_bind())


def downgrade() -> None:
    pass
