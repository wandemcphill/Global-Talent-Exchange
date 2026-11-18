"""Add the two missing FM27 under-18 wonderkids and correct bad birth dates.

Luca Scanlon and Marc Santos were not in GTEX. Twenty-three others on the
Wonderkid Finder under-18 list already were. Five of those cards had the
wrong date of birth, position or height. Their governed GSI and potential
are left unchanged. Prospect Signal is not written onto the card.

Revision ID: 20261118_0267_under18_wonderkids
Revises: 20261118_0266_next_generation_2026
Create Date: 2026-11-18 02:20:00.000000
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "20261118_0267_under18_wonderkids"
down_revision = "20261118_0266_next_generation_2026"
branch_labels = None
depends_on = None

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "under18_missing_2026.json"
TOTAL_SHARES = 400

CORRECTIONS = [
    {
        "id": "8dacb3d4-7d2c-4fe7-b9a5-94b41d496bf5",
        "old_dob": "2007-11-19",
        "dob": "2010-01-19",
        "age": 16,
        "height": 193,
        "foot": "Right",
        "position": "CB",
        "secondary": ["RB", "DM"],
        "shirt": 43,
        "playstyle": "Tall right-footed centre-back who also plays right-back and as a number 6.",
        "traits": ["Aerial Fortress", "Intercept", "Press Proven", "Long Ball Pass"],
    },
    {
        "id": "8c776a23-a0ad-4641-b573-6ac9fdb26a7e",
        "old_dob": "2007-11-19",
        "dob": "2009-05-19",
        "age": 17,
        "height": None,
        "foot": "Left",
        "position": "DM",
        "secondary": ["CM"],
        "shirt": None,
        "playstyle": "Left-footed defensive midfielder who also plays in central midfield.",
        "traits": ["Dictates Tempo", "Press Resistant", "Intercept", "Composure"],
    },
    {
        "id": "af3621c6-fd82-438e-9272-86adc3c50a22",
        "old_dob": "2005-05-17",
        "dob": "2009-10-08",
        "age": 17,
        "height": 182,
        "foot": "Left",
        "position": "LB",
        "secondary": ["LM"],
        "shirt": 37,
        "playstyle": "Left-footed left-back who can also play further forward on the left.",
        "traits": ["Overlaps", "Quick Step", "Early Cross", "Stamina"],
    },
    {
        "id": "848bbcf0-a932-4d45-8ab0-e6c41fca1868",
        "old_dob": "2007-12-04",
        "dob": "2010-04-08",
        "age": 16,
        "height": 175,
        "foot": "Right",
        "position": "LW",
        "secondary": ["AM", "RW"],
        "shirt": 49,
        "playstyle": "Right-footed winger who plays both wings and as an attacking midfielder.",
        "traits": ["Technical Dribbler", "Cuts Inside From Wing", "Flair", "First Touch"],
    },
    {
        "id": "77aff2ea-b2b7-41da-bff0-89cc1dc2ff68",
        "old_dob": "2007-09-17",
        "dob": "2009-05-13",
        "age": 17,
        "height": 176,
        "foot": "Left",
        "position": "LB",
        "secondary": ["CB", "DM"],
        "shirt": 36,
        "country": "Indonesia",
        "playstyle": "Left-footed left-back who also plays centre-back and in front of the defence.",
        "traits": ["Overlaps", "Vision", "Takes On Defenders", "Tackler"],
    },
    {
        "id": "fdf23368-5af2-4bf7-9fe1-fe8ce03fc833",
        "old_dob": "2010-10-06",
        "dob": "2010-10-06",
        "age": 16,
        "height": 174,
        "foot": "Right",
        "position": "AM",
        "secondary": ["ST", "LW", "RW"],
        "shirt": 77,
        "playstyle": "Right-footed forward who finishes through the middle and plays off both wings.",
        "traits": ["Clinical Finisher", "Technical Dribbler", "Flair", "Off The Ball"],
    },
]


def _calc_price(cur: int, pot: int) -> float:
    eval_gsi = 0.40 * cur + 0.60 * pot
    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        t = (eval_gsi - 70.0) / 5.0
        base_price *= 0.40 + 0.60 * t
    return round(base_price, 2)


def _fold_country(name: str) -> str:
    folded = name.casefold()
    for mark in ("'", "’", "‘", "`", "´", "ʼ"):
        folded = folded.replace(mark, "")
    return "".join(folded.split())


def _country_id(conn: sa.Connection, names: list[str]) -> str | None:
    wanted = {_fold_country(name) for name in names}
    rows = conn.execute(sa.text("SELECT id, name FROM ingestion_countries")).fetchall()
    for country_id, country_name in rows:
        if country_name and _fold_country(country_name) in wanted:
            return country_id
    return None


def _ensure_gibraltar(conn: sa.Connection) -> None:
    if _country_id(conn, ["Gibraltar"]):
        return
    conn.execute(
        sa.text("""
            INSERT INTO ingestion_countries (
                id, source_provider, provider_external_id, name,
                alpha2_code, alpha3_code, fifa_code, confederation_code,
                is_enabled_for_universe, created_at, updated_at, last_synced_at
            ) VALUES (
                :id, 'gtex_native', 'gibraltar', 'Gibraltar',
                'GI', 'GIB', 'GIB', 'UEFA',
                true, NOW(), NOW(), NOW()
            )
            ON CONFLICT (source_provider, provider_external_id) DO NOTHING
            """),
        {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "gtex-country:gibraltar"))},
    )


def _attributes(player: dict) -> dict:
    gsi = int(player["gsi"])
    if player["position"] == "LB":
        attrs = {
            "pace": gsi + 5,
            "shooting": gsi - 17,
            "passing": gsi - 1,
            "dribbling": gsi + 1,
            "defending": gsi + 1,
            "physical": gsi - 1,
            "tackling": gsi + 1,
        }
    else:
        attrs = {
            "pace": gsi + 5,
            "shooting": gsi - 3,
            "passing": gsi + 3,
            "dribbling": gsi + 7,
            "defending": 40,
            "physical": gsi - 7,
            "vision": gsi + 4,
        }
    attrs["skill_moves"] = player["skill_moves"]
    attrs["weak_foot"] = player["weak_foot"]
    return attrs


def _insert_missing(conn: sa.Connection, tables: set[str]) -> None:
    if not CATALOG_PATH.is_file():
        return
    _ensure_gibraltar(conn)
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for player in catalog:
        gsi = int(player["gsi"])
        potential = int(player["potential"])
        if gsi < 69:
            continue
        existing = conn.execute(
            sa.text("""
                SELECT id FROM ingestion_players
                WHERE id = :pid
                   OR (lower(full_name) = lower(:name) AND date_of_birth = CAST(:dob AS date))
                LIMIT 1
                """),
            {"pid": player["id"], "name": player["name"], "dob": player["dob"]},
        ).scalar()
        if existing is not None and str(existing) != player["id"]:
            continue

        price = _calc_price(gsi, potential)
        country_id = _country_id(conn, list(player.get("country_names") or []))
        secondary = list(player["secondary"])
        attrs = _attributes(player)
        portrait = player.get("portrait")
        dna = {
            "age": player["age"],
            "overall": gsi,
            "current_rating": gsi,
            "potential": potential,
            "potential_rating": potential,
            "position": player["position"],
            "normalized_position": player["position"],
            "secondary_positions": secondary,
            "positions": player["positions"],
            "position_display": player["position_display"],
            "date_of_birth": player["dob"],
            "birth_year": player["birth_year"],
            "nationality": player["country"],
            "country_name": player["country"],
            "real_world_club_name": player["club"],
            "real_world_league_name": player["league"],
            "playstyle": player["playstyle"],
            "traits": player["traits"],
            "skills": player["traits"],
            "aliases": player.get("aliases") or [],
            "legal_name": player.get("legal_name"),
            "attributes": attrs,
            "skill_moves": player["skill_moves"],
            "weak_foot": player["weak_foot"],
            "height_cm": player.get("height"),
            "preferred_foot": player.get("foot"),
            "notes": player.get("notes"),
            "source": "wonderkidfinder_under18_2026",
            "pace": attrs["pace"],
            "shooting": attrs["shooting"],
            "passing": attrs["passing"],
            "dribbling": attrs["dribbling"],
            "defending": attrs["defending"],
            "physical": attrs["physical"],
        }
        if portrait:
            dna.update(
                {
                    "portraitUrl": portrait,
                    "image_url": portrait,
                    "portraitStatus": "ready",
                    "portraitSourceProvider": "cloudinary",
                }
            )
        summary = {
            "age": player["age"],
            "gsi": gsi,
            "overall": gsi,
            "potential": potential,
            "potential_gsi": potential,
            "position": player["position"],
            "secondary_positions": secondary,
            "position_display": player["position_display"],
            "date_of_birth": player["dob"],
            "nationality": player["country"],
            "height_cm": player.get("height"),
            "preferred_foot": player.get("foot"),
            "real_world_club_name": player["club"],
            "real_world_league_name": player["league"],
            "is_tradable": True,
            "real_player_tier": "wonderkid",
            "playstyle": player["playstyle"],
            "traits": player["traits"],
            "total_shares": TOTAL_SHARES,
            "released_shares": TOTAL_SHARES,
            "circulating_shares": 0,
            "share_price_coin": price,
            "attributes": attrs,
        }
        if portrait:
            summary.update({"image_url": portrait, "portrait_url": portrait, "portrait_status": "ready"})
        market = {
            "tier": "wonderkid",
            "current_gsi": gsi,
            "potential_gsi": potential,
            "club": player["club"],
            "league": player["league"],
            "country": player["country"],
            "position": player["position"],
            "position_display": player["position_display"],
            "secondary_positions": secondary,
            "playstyle": player["playstyle"],
            "traits": player["traits"],
            "height_cm": player.get("height"),
            "preferred_foot": player.get("foot"),
            "initial_share_price_coin": price,
            "source": "wonderkidfinder_under18_2026",
        }
        conn.execute(
            sa.text("""
                INSERT INTO ingestion_players (
                    id, source_provider, provider_external_id, country_id,
                    full_name, first_name, last_name, short_name, canonical_display_name,
                    position, normalized_position, secondary_positions_json,
                    real_world_club_name, real_world_league_name,
                    date_of_birth, factual_date_of_birth, height_cm, preferred_foot, shirt_number,
                    is_tradable, is_real_player, real_player_tier,
                    governed_gsi, governed_potential_gsi, potential,
                    gsi_methodology_version, gsi_override_reason,
                    profile_completeness_score, identity_confidence_score,
                    dna_profile, morale, created_at, updated_at, last_synced_at
                ) VALUES (
                    :pid, 'curated_roster', :ext_id, :country_id,
                    :name, :first, :last, :short, :name,
                    :position, :position, CAST(:sec AS json),
                    :club, :league,
                    CAST(:dob AS date), CAST(:dob AS date), :height, :foot, :shirt,
                    true, true, 'wonderkid',
                    :gsi, :pot, :pot,
                    '2026.roster_governed_calibration',
                    'Wonderkid Finder under-18 list. Created because this player was not already in GTEX. GSI floor 69.',
                    0.9, 0.95,
                    CAST(:dna AS json), 75.0, NOW(), NOW(), NOW()
                )
                ON CONFLICT (id) DO NOTHING
                """),
            {
                "pid": player["id"],
                "ext_id": player["external_id"],
                "country_id": country_id,
                "name": player["name"],
                "first": player["first"],
                "last": player["last"],
                "short": player["short"],
                "position": player["position"],
                "sec": json.dumps(secondary),
                "club": player["club"],
                "league": player["league"],
                "dob": player["dob"],
                "height": player.get("height"),
                "foot": player.get("foot"),
                "shirt": player.get("shirt"),
                "gsi": gsi,
                "pot": potential,
                "dna": json.dumps(dna),
            },
        )
        inserted = conn.execute(
            sa.text("SELECT 1 FROM ingestion_players WHERE id = :pid"),
            {"pid": player["id"]},
        ).scalar()
        if inserted is None:
            continue
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
                    ON CONFLICT (player_id) DO NOTHING
                    """),
                {"pid": player["id"], "shares": TOTAL_SHARES, "price": price, "mkt": json.dumps(market)},
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
                        :pid, :name, :club, :league,
                        NOW(), :price, :price,
                        0.0, :gsi, :gsi, CAST(:sum AS json), NOW(), NOW()
                    )
                    ON CONFLICT (player_id) DO NOTHING
                    """),
                {
                    "pid": player["id"],
                    "name": player["name"],
                    "club": player["club"],
                    "league": player["league"],
                    "price": price,
                    "gsi": gsi,
                    "sum": json.dumps(summary),
                },
            )
        if portrait and "ingestion_player_image_metadata" in tables:
            conn.execute(
                sa.text("""
                    INSERT INTO ingestion_player_image_metadata (
                        id, player_id, source_provider, provider_external_id, image_role, source_url,
                        moderation_status, rights_cleared, is_primary, created_at, updated_at
                    )
                    SELECT gen_random_uuid()::varchar, CAST(:pid AS varchar), 'cloudinary',
                           CAST(:ext AS varchar), 'portrait', CAST(:url AS varchar),
                           'approved', true, true, NOW(), NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM ingestion_player_image_metadata
                        WHERE player_id = CAST(:pid AS varchar) AND image_role = 'portrait'
                    )
                    """),
                {"pid": player["id"], "ext": player["id"] + "-portrait", "url": portrait},
            )


def _correct_existing(conn: sa.Connection, tables: set[str]) -> None:
    for fix in CORRECTIONS:
        secondary = list(fix["secondary"])
        display = "/".join([fix["position"], *secondary])
        patch = {
            "age": fix["age"],
            "date_of_birth": fix["dob"],
            "position": fix["position"],
            "normalized_position": fix["position"],
            "secondary_positions": secondary,
            "positions": [fix["position"], *secondary],
            "position_display": display,
            "preferred_foot": fix["foot"],
            "playstyle": fix["playstyle"],
            "traits": fix["traits"],
            "skills": fix["traits"],
        }
        if fix["height"] is not None:
            patch["height_cm"] = fix["height"]
        if fix.get("country"):
            patch["nationality"] = fix["country"]
            patch["country_name"] = fix["country"]
        country_id = _country_id(conn, [fix["country"]]) if fix.get("country") else None
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET date_of_birth = CAST(:dob AS date),
                    factual_date_of_birth = CAST(:dob AS date),
                    height_cm = COALESCE(:height, height_cm),
                    preferred_foot = :foot,
                    position = :position,
                    normalized_position = :position,
                    secondary_positions_json = CAST(:sec AS json),
                    shirt_number = COALESCE(shirt_number, :shirt),
                    country_id = COALESCE(:country_id, country_id),
                    dna_profile = (
                        COALESCE(dna_profile::jsonb, CAST('{}' AS jsonb))
                        || CAST(:patch AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE id = :pid
                  AND date_of_birth IN (CAST(:old_dob AS date), CAST(:dob AS date))
                """),
            {
                "pid": fix["id"],
                "old_dob": fix["old_dob"],
                "dob": fix["dob"],
                "height": fix["height"],
                "foot": fix["foot"],
                "position": fix["position"],
                "sec": json.dumps(secondary),
                "shirt": fix["shirt"],
                "country_id": country_id,
                "patch": json.dumps(patch),
            },
        )
        if "player_summary_read_models" in tables:
            conn.execute(
                sa.text("""
                    UPDATE player_summary_read_models
                    SET summary_json = (
                            COALESCE(summary_json::jsonb, CAST('{}' AS jsonb))
                            || CAST(:patch AS jsonb)
                        )::json,
                        updated_at = NOW()
                    WHERE player_id = :pid
                    """),
                {"pid": fix["id"], "patch": json.dumps(patch)},
            )
        if "player_share_markets" in tables:
            conn.execute(
                sa.text("""
                    UPDATE player_share_markets
                    SET metadata_json = (
                            COALESCE(metadata_json::jsonb, CAST('{}' AS jsonb))
                            || CAST(:patch AS jsonb)
                        )::json,
                        updated_at = NOW()
                    WHERE player_id = :pid
                    """),
                {
                    "pid": fix["id"],
                    "patch": json.dumps(
                        {
                            "position": fix["position"],
                            "position_display": display,
                            "secondary_positions": secondary,
                            "preferred_foot": fix["foot"],
                            "height_cm": fix["height"],
                            "playstyle": fix["playstyle"],
                            "traits": fix["traits"],
                        }
                    ),
                },
            )


def apply_under18(conn: sa.Connection) -> None:
    if getattr(getattr(conn, "dialect", None), "name", "") != "postgresql":
        return
    tables = set(sa.inspect(conn).get_table_names())
    if "ingestion_players" not in tables:
        return
    _insert_missing(conn, tables)
    _correct_existing(conn, tables)


def upgrade() -> None:
    apply_under18(op.get_bind())


def downgrade() -> None:
    pass
