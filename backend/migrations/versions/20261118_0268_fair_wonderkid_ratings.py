"""Remove the older Ebenezar Harcourt card and set fair wonderkid ratings.

The 2009 Ebenezer Ifeanyi Harcourt card stays. Ratings the user already
chose are left alone. No female players are inserted.

Revision ID: 20261118_0268_fair_wonderkid_ratings
Revises: 20261118_0267_under18_wonderkids
Create Date: 2026-11-18 02:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261118_0268_fair_wonderkid_ratings"
down_revision = "20261118_0267_under18_wonderkids"
branch_labels = None
depends_on = None

OLD_HARCOURT_ID = "f1ba61fc-265f-46ec-b1c8-705a294381d0"

# Current, potential. Only players the user did not rate.
RATINGS = [
    ("8dacb3d4-7d2c-4fe7-b9a5-94b41d496bf5", 52, 71, 87),  # Filip Pavić
    ("8c776a23-a0ad-4641-b573-6ac9fdb26a7e", 53, 71, 86),  # Erblin Osmani
    ("af3621c6-fd82-438e-9272-86adc3c50a22", 52, 72, 85),  # Louis Lemke
    ("848bbcf0-a932-4d45-8ab0-e6c41fca1868", 55, 70, 84),  # Linus Güther
    ("9712798e-a3c4-42db-89f9-e5d479c64685", 70, 70, 84),  # Ebenezer Ifeanyi Harcourt
    ("3c498782-04ca-4213-8b33-60dec863381e", 70, 70, 83),  # Hamza Kadamani
    ("338b64ce-7de3-4f5a-ac34-d50ba857f386", 70, 70, 83),  # Junai Byfield
    ("82c24f1f-d586-45af-999d-0149c61d2e46", 69, 70, 84),  # Marli Salmon
    ("45e44cc1-e9b0-4621-bdef-7148c03bba33", 68, 71, 85),  # Tian Nai Koren
    ("e2732550-8b15-5deb-993d-fb2e54d35cab", 69, 70, 85),  # Marc Santos
    ("696b5750-9a62-41ea-bdf8-e4e641e91130", 70, 71, 84),  # Ada Yüzgeç
    ("77aff2ea-b2b7-41da-bff0-89cc1dc2ff68", 69, 70, 86),  # Mathew Baker
    ("c0f8ee66-9057-4a43-b61d-18937f394c2e", 71, 73, 90),  # Brian Madjo
    ("95bf8c3e-07c0-4ef8-a587-e12da0d9eb4a", 78, 78, 89),  # Mathis Albert, born 2009
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


def _delete_old_harcourt(conn: sa.Connection, tables: set[str]) -> None:
    if "trade_executions" in tables:
        conn.execute(
            sa.text("DELETE FROM trade_executions WHERE player_id = :pid"),
            {"pid": OLD_HARCOURT_ID},
        )
    if "exchange_orders" in tables:
        conn.execute(
            sa.text("DELETE FROM exchange_orders WHERE player_id = :pid"),
            {"pid": OLD_HARCOURT_ID},
        )
    conn.execute(
        sa.text("""
            DELETE FROM ingestion_players
            WHERE id = :pid
              AND full_name = 'Ebenezar Harcourt'
              AND date_of_birth = DATE '2007-10-15'
            """),
        {"pid": OLD_HARCOURT_ID},
    )


def _apply_rating(
    conn: sa.Connection, tables: set[str], player_id: str, old_gsi: int, gsi: int, potential: int
) -> None:
    price = _calc_price(gsi, potential)
    patch = {
        "gsi": gsi,
        "overall": gsi,
        "current_rating": gsi,
        "sofifa_overall": gsi,
        "global_scouting_index": gsi,
        "potential": potential,
        "potential_gsi": potential,
        "potential_rating": potential,
        "sofifa_potential": potential,
        "governed_gsi": gsi,
        "governed_potential_gsi": potential,
    }
    conn.execute(
        sa.text("""
            UPDATE ingestion_players
            SET governed_gsi = :gsi,
                governed_potential_gsi = :pot,
                potential = :pot,
                gsi_override_reason = :reason,
                dna_profile = (
                    COALESCE(dna_profile::jsonb, CAST('{}' AS jsonb))
                    || CAST(:patch AS jsonb)
                )::json,
                updated_at = NOW()
            WHERE id = :pid
              AND governed_gsi IN (:old_gsi, :gsi)
            """),
        {
            "pid": player_id,
            "old_gsi": old_gsi,
            "gsi": gsi,
            "pot": potential,
            "reason": "Fair wonderkid rating. The user had not set this GSI or potential.",
            "patch": json.dumps(patch),
        },
    )
    if "player_share_markets" in tables:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET share_price_coin = CASE WHEN circulating_shares = 0 THEN :price ELSE share_price_coin END,
                    total_shares = CASE
                        WHEN circulating_shares = 0 AND total_shares = 600 AND :pot >= 72 THEN 400
                        ELSE total_shares
                    END,
                    released_shares = CASE
                        WHEN circulating_shares = 0 AND released_shares = 600 AND :pot >= 72 THEN 400
                        ELSE released_shares
                    END,
                    metadata_json = (
                        COALESCE(metadata_json::jsonb, CAST('{}' AS jsonb))
                        || CAST(:patch AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": player_id, "price": price, "pot": potential, "patch": json.dumps(patch)},
        )
    if "player_summary_read_models" in tables:
        summary_patch = {**patch, "share_price_coin": price}
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET average_rating = :gsi,
                    market_interest_score = :gsi,
                    current_value_credits = CASE
                        WHEN COALESCE((
                            SELECT circulating_shares FROM player_share_markets WHERE player_id = :pid
                        ), 0) = 0 THEN :price
                        ELSE current_value_credits
                    END,
                    summary_json = (
                        COALESCE(summary_json::jsonb, CAST('{}' AS jsonb))
                        || CAST(:patch AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": player_id, "gsi": gsi, "price": price, "patch": json.dumps(summary_patch)},
        )


def apply_fair_ratings(conn: sa.Connection) -> None:
    if getattr(getattr(conn, "dialect", None), "name", "") != "postgresql":
        return
    tables = set(sa.inspect(conn).get_table_names())
    if "ingestion_players" not in tables:
        return
    _delete_old_harcourt(conn, tables)
    for player_id, old_gsi, gsi, potential in RATINGS:
        if gsi < 69 or potential < gsi:
            continue
        _apply_rating(conn, tables, player_id, old_gsi, gsi, potential)


def upgrade() -> None:
    apply_fair_ratings(op.get_bind())


def downgrade() -> None:
    pass
