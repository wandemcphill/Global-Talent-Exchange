"""Add potential rating to ingestion_players (for youth development + appreciation).

Captures SoFIFA/EA FC `potential` so young high-ceiling players can drive
deterministic value appreciation (potential-gap curve) without a live data feed,
and so U17/U20/U21 development has a growth target.

Revision ID: 20260724_0106_player_potential
Revises: 20260628_0105_club_match_plans
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260724_0106_player_potential"
down_revision = "20260628_0105_club_match_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_players",
        sa.Column("potential", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ingestion_players", "potential")
