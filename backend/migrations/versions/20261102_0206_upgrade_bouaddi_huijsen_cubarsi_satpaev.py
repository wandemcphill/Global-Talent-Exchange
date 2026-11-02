"""Upgrade Ayyoub Bouaddi, Dean Huijsen, Pau Cubarsi, and Dastan Satpaev ratings and club.

Revision ID: 20261102_0206_upgrade_bouaddi_huijsen_cubarsi_satpaev
Revises: 20261102_0205_wonderkids_rating_position_calibration
Create Date: 2026-11-02 20:38:00
"""

from __future__ import annotations

import json
from alembic import op
import sqlalchemy as sa

revision = "20261102_0206_upgrade_bouaddi_huijsen_cubarsi_satpaev"
down_revision = "20261102_0205_wonderkids_rating_position_calibration"
branch_labels = None
depends_on = None

UPGRADES = [
    {
        "name": "Ayyoub Bouaddi",
        "ovr": 84,
        "pot": 91,
        "club": "Man City",
        "pos": "DM/CM",
        "norm_pos": "DM",
        "tier": "wonderkid",
        "ids": ["7349dee2-5456-4093-95a7-0763fd4623dd", "c607e5e3-640a-4156-8fcc-f6a97a69f5ce"],
    },
    {
        "name": "Dean Huijsen",
        "ovr": 81,
        "pot": 90,
        "club": "AFC Bournemouth",
        "pos": "CB",
        "norm_pos": "CB",
        "tier": "wonderkid",
        "ids": ["2344adb1-c70a-4615-8852-c334e36f2c1c", "940e6105-e9b2-474f-83da-c3e2b4628768"],
    },
    {
        "name": "Pau Cubarsí",
        "ovr": 86,
        "pot": 94,
        "club": "FC Barcelona",
        "pos": "CB",
        "norm_pos": "CB",
        "tier": "wonderkid",
        "ids": ["c0843527-8b8b-40ee-8792-4c7162e58cc7", "323765c4-43db-46ad-b289-3a7704147854"],
    },
    {
        "name": "Dastan Satpaev",
        "ovr": 76,
        "pot": 87,
        "club": "Chelsea",
        "pos": "AM RLC",
        "norm_pos": "AM",
        "tier": "wonderkid",
        "ids": ["7a4588b3-c72a-4e26-a8ae-7f401762b166", "aaf33042-efe1-4071-8605-e3cf1c001888"],
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    is_postgres = bind.dialect.name == "postgresql"

    if not is_postgres:
        return

    for item in UPGRADES:
        ovr = item["ovr"]
        pot = item["pot"]
        club = item["club"]
        pos = item["pos"]
        norm_pos = item["norm_pos"]
        tier = item["tier"]
        pids = tuple(item["ids"])

        id_list_str = "('" + "', '".join(pids) + "')"

        # 1. Update ingestion_players
        if "ingestion_players" in tables:
            dna_patch = json.dumps(
                {
                    "current_rating": ovr,
                    "overall": ovr,
                    "potential_rating": pot,
                    "potential": pot,
                    "position": pos,
                }
            )
            op.execute(f"""
                UPDATE ingestion_players
                SET
                    governed_gsi = {ovr},
                    governed_potential_gsi = {pot},
                    potential = {pot},
                    position = '{pos}',
                    normalized_position = '{norm_pos}',
                    real_world_club_name = '{club}',
                    real_player_tier = '{tier}',
                    gsi_methodology_version = '2026.fc27_wonderkid_calibration',
                    gsi_override_reason = 'Governed upgrade per user request',
                    dna_profile = (
                        COALESCE(dna_profile::jsonb, '{{}}'::jsonb) || '{dna_patch}'::jsonb
                    )::json,
                    updated_at = NOW()
                WHERE id IN {id_list_str};
            """)

        # 2. Update player_share_markets
        if "player_share_markets" in tables:
            market_patch = json.dumps(
                {
                    "current_gsi": ovr,
                    "potential_gsi": pot,
                    "governed_gsi": ovr,
                    "governed_potential_gsi": pot,
                }
            )
            op.execute(f"""
                UPDATE player_share_markets
                SET
                    metadata_json = (
                        COALESCE(metadata_json::jsonb, '{{}}'::jsonb) || '{market_patch}'::jsonb
                    )::json,
                    updated_at = NOW()
                WHERE player_id IN {id_list_str};
            """)

        # 3. Update player_summary_read_models
        if "player_summary_read_models" in tables:
            summary_patch = json.dumps(
                {
                    "gsi": ovr,
                    "overall": ovr,
                    "potential": pot,
                    "position": pos,
                    "real_player_tier": tier,
                    "real_world_club_name": club,
                }
            )
            op.execute(f"""
                UPDATE player_summary_read_models
                SET
                    current_club_name = '{club}',
                    summary_json = (
                        COALESCE(summary_json::jsonb, '{{}}'::jsonb) || '{summary_patch}'::jsonb
                    )::json,
                    updated_at = NOW()
                WHERE player_id IN {id_list_str};
            """)


def downgrade() -> None:
    pass
