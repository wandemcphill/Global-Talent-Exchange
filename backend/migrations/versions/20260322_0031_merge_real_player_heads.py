"""Merge real-player import, mapping, provider, and value-lineage heads.

Revision ID: 20260322_0031_merge_real_player_heads
Revises: 20260322_0030_real_player_import_ops, 20260322_0030_real_player_provider_import_scaffold, 20260322_0030_real_player_reference_mappings, 20260322_0030_real_player_value_bridge_lineage
Create Date: 2026-03-22 20:50:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260322_0031_merge_real_player_heads"
down_revision = (
    "20260322_0030_real_player_import_ops",
    "20260322_0030_real_player_provider_import_scaffold",
    "20260322_0030_real_player_reference_mappings",
    "20260322_0030_real_player_value_bridge_lineage",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("real_player_profiles") as batch_op:
        batch_op.create_index("ix_real_player_profiles_batch_id", ["ingestion_batch_id"], unique=False)
        batch_op.create_index("ix_real_player_profiles_pricing_snapshot_id", ["pricing_snapshot_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("real_player_profiles") as batch_op:
        batch_op.drop_index("ix_real_player_profiles_pricing_snapshot_id")
        batch_op.drop_index("ix_real_player_profiles_batch_id")
