"""Add secondary_positions_json to ingestion_players (real-player multi-position).

Revision ID: 20260628_0103_player_secondary_positions
Revises: 20260523_0102_world_super_cup_persistence
Create Date: 2026-06-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260628_0103_player_secondary_positions"
down_revision = "20260523_0102_world_super_cup_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_players",
        sa.Column(
            "secondary_positions_json",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("ingestion_players", "secondary_positions_json")
