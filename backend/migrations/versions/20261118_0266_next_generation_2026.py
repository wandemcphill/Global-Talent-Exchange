"""Add the Guardian Next Generation 2026 players who are not already in GTEX.

Thirty-four of the 60 were already on the books. This adds the other 26,
each with a portrait, traits, position and height where a measured height
exists. Current GSI is at least 69.

Revision ID: 20261118_0266_next_generation_2026
Revises: 20261118_0265_update_kennet_eichhorn
Create Date: 2026-11-18 01:10:00.000000
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "20261118_0266_next_generation_2026"
down_revision = "20261118_0265_update_kennet_eichhorn"
branch_labels = None
depends_on = None

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "next_generation_2026.json"
TOTAL_SHARES = 400


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


def _ensure_tajikistan(conn: sa.Connection) -> None:
    if "ingestion_countries" not in set(sa.inspect(conn).get_table_names()):
        return
    existing = _country_id(conn, ["Tajikistan", "Tadjikistan"])
    if existing:
        return
    conn.execute(
        sa.text("""
            INSERT INTO ingestion_countries (
                id, source_provider, provider_external_id, name,
                alpha2_code, alpha3_code, fifa_code, confederation_code,
                is_enabled_for_universe, created_at, updated_at, last_synced_at
            ) VALUES (
                :id, 'gtex_native', 'tajikistan', 'Tajikistan',
                'TJ', 'TJK', 'TJK', 'AFC',
                true, NOW(), NOW(), NOW()
            )
            ON CONFLICT (source_provider, provider_external_id) DO NOTHING
            """),
        {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "gtex-country:tajikistan"))},
    )


def _already_present(conn: sa.Connection, player: dict) -> bool:
    row = conn.execute(
        sa.text("""
            SELECT id
            FROM ingestion_players
            WHERE id = :pid
               OR (
                    lower(full_name) = lower(:name)
                    AND date_of_birth = CAST(:dob AS date)
               )
            LIMIT 1
            """),
        {"pid": player["id"], "name": player["name"], "dob": player["dob"]},
    ).scalar()
    return row is not None and row != player["id"]


def apply_next_generation(conn: sa.Connection) -> None:
    if getattr(getattr(conn, "dialect", None), "name", "") != "postgresql":
        return
    if not CATALOG_PATH.is_file():
        return

    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    if "ingestion_players" not in tables:
        return

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    _ensure_tajikistan(conn)
    for player in catalog:
        gsi = int(player["gsi"])
        potential = int(player["potential"])
        if gsi < 69:
            continue
        if _already_present(conn, player):
            continue

        price = _calc_price(gsi, potential)
        country_id = None
        if "ingestion_countries" in tables:
            country_id = _country_id(conn, list(player.get("country_names") or []))
        positions = list(player["positions"])
        secondary = list(player["secondary"])
        attrs = dict(player["attributes"])
        portrait = player.get("portrait")
        dna = {
            "age": player["age"],
            "overall": gsi,
            "sofifa_overall": gsi,
            "current_rating": gsi,
            "potential": potential,
            "sofifa_potential": potential,
            "potential_rating": potential,
            "position": player["position"],
            "normalized_position": player["position"],
            "secondary_positions": secondary,
            "positions": positions,
            "position_display": player["position_display"],
            "date_of_birth": player["dob"],
            "birth_year": 2009,
            "nationality": player["country"],
            "country_name": player["country"],
            "real_world_club_name": player["club"],
            "real_world_league_name": player["league"],
            "playstyle": player["playstyle"],
            "traits": player["traits"],
            "skills": player["traits"],
            "aliases": player.get("aliases") or [],
            "attributes": attrs,
            "skill_moves": player["skill_moves"],
            "weak_foot": player["weak_foot"],
            "source": "guardian_next_generation_2026",
            **{key: attrs[key] for key in ("pace", "shooting", "passing", "dribbling", "defending", "physical") if key in attrs},
        }
        if player.get("height") is not None:
            dna["height_cm"] = player["height"]
        if player.get("foot"):
            dna["preferred_foot"] = player["foot"]
        if player.get("notes"):
            dna["notes"] = player["notes"]
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
            "global_scouting_index": gsi,
            "current_rating": gsi,
            "potential": potential,
            "potential_gsi": potential,
            "position": player["position"],
            "normalized_position": player["position"],
            "secondary_positions": secondary,
            "positions": positions,
            "position_display": player["position_display"],
            "date_of_birth": player["dob"],
            "nationality": player["country"],
            "country_name": player["country"],
            "real_world_club_name": player["club"],
            "real_world_league_name": player["league"],
            "is_legend": False,
            "is_real_player": True,
            "is_tradable": True,
            "real_player_tier": "wonderkid",
            "playstyle": player["playstyle"],
            "traits": player["traits"],
            "skills": player["traits"],
            "total_shares": TOTAL_SHARES,
            "released_shares": TOTAL_SHARES,
            "available_shares": TOTAL_SHARES,
            "circulating_shares": 0,
            "share_price_coin": price,
            "market_visibility": {"status": "visible", "eligible": True},
            "attributes": attrs,
        }
        if player.get("height") is not None:
            summary["height_cm"] = player["height"]
        if player.get("foot"):
            summary["preferred_foot"] = player["foot"]
        if portrait:
            summary.update({"image_url": portrait, "portrait_url": portrait, "portrait_status": "ready"})

        market = {
            "asset_type": "real_player_fractional_share",
            "tier": "wonderkid",
            "supply_band": "core",
            "current_gsi": gsi,
            "potential_gsi": potential,
            "governed_gsi": gsi,
            "governed_potential_gsi": potential,
            "club": player["club"],
            "league": player["league"],
            "country": player["country"],
            "position": player["position"],
            "position_display": player["position_display"],
            "secondary_positions": secondary,
            "playstyle": player["playstyle"],
            "traits": player["traits"],
            "initial_share_price_coin": price,
            "source": "guardian_next_generation_2026",
        }
        if player.get("height") is not None:
            market["height_cm"] = player["height"]
        if player.get("foot"):
            market["preferred_foot"] = player["foot"]

        conn.execute(
            sa.text("""
                INSERT INTO ingestion_players (
                    id, source_provider, provider_external_id, country_id,
                    full_name, first_name, last_name, short_name, canonical_display_name,
                    position, normalized_position, secondary_positions_json,
                    real_world_club_name, real_world_league_name,
                    date_of_birth, factual_date_of_birth, height_cm, preferred_foot,
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
                    CAST(:dob AS date), CAST(:dob AS date), :height, :foot,
                    true, true, 'wonderkid',
                    :gsi, :pot, :pot,
                    '2026.roster_governed_calibration',
                    'Guardian Next Generation 2026. Created only because this player was not already in GTEX. GSI floor 69.',
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
                {
                    "pid": player["id"],
                    "shares": TOTAL_SHARES,
                    "price": price,
                    "mkt": json.dumps(market),
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


def upgrade() -> None:
    apply_next_generation(op.get_bind())


def downgrade() -> None:
    pass
