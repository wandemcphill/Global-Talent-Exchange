"""Add real-player valuation lineage read model.

Revision ID: 20260322_0030_real_player_value_bridge_lineage
Revises: 20260322_0029_regen_universe_layer
Create Date: 2026-03-22 18:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0030_real_player_value_bridge_lineage"
down_revision = "20260322_0029_regen_universe_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_player_value_lineages",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False, server_default="intraday"),
        sa.Column("config_version", sa.String(length=64), nullable=False, server_default="baseline-v1"),
        sa.Column("adapter_code", sa.String(length=64), nullable=False),
        sa.Column("adapter_version", sa.String(length=64), nullable=False),
        sa.Column("source_reference_tier", sa.String(length=32), nullable=True),
        sa.Column("source_reference_origin", sa.String(length=128), nullable=True),
        sa.Column("source_market_value_eur", sa.Float(), nullable=False),
        sa.Column("bridge_market_value_eur", sa.Float(), nullable=False),
        sa.Column("base_value_credits", sa.Float(), nullable=False),
        sa.Column("floor_credits", sa.Float(), nullable=False),
        sa.Column("ceiling_credits", sa.Float(), nullable=False),
        sa.Column("previous_bridge_market_value_eur", sa.Float(), nullable=True),
        sa.Column("smoothing_factor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("inputs_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("components_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("explanation_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["player_value_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", name="uq_real_player_value_lineages_snapshot_id"),
        sa.UniqueConstraint("player_id", "as_of", "snapshot_type", name="uq_real_player_value_lineages_player_as_of_type"),
    )
    op.create_index(
        "ix_real_player_value_lineages_player_id",
        "real_player_value_lineages",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_value_lineages_snapshot_id",
        "real_player_value_lineages",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_value_lineages_as_of",
        "real_player_value_lineages",
        ["as_of"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_value_lineages_snapshot_type",
        "real_player_value_lineages",
        ["snapshot_type"],
        unique=False,
    )
    op.create_index(
        "ix_real_player_value_lineages_adapter_version",
        "real_player_value_lineages",
        ["adapter_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_real_player_value_lineages_adapter_version", table_name="real_player_value_lineages")
    op.drop_index("ix_real_player_value_lineages_snapshot_type", table_name="real_player_value_lineages")
    op.drop_index("ix_real_player_value_lineages_as_of", table_name="real_player_value_lineages")
    op.drop_index("ix_real_player_value_lineages_snapshot_id", table_name="real_player_value_lineages")
    op.drop_index("ix_real_player_value_lineages_player_id", table_name="real_player_value_lineages")
    op.drop_table("real_player_value_lineages")
