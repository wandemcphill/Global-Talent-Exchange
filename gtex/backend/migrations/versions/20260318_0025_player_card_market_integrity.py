"""player card marketplace integrity controls

Revision ID: 20260318_0025
Revises: 20260317_0024_gift_economy_stabilizer
Create Date: 2026-03-18 08:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_0025"
down_revision = "20260317_0024_gift_economy_stabilizer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "player_card_listings",
        sa.Column("integrity_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "player_card_sales",
        sa.Column("integrity_flags_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("player_card_sales", "integrity_flags_json")
    op.drop_column("player_card_listings", "integrity_context_json")
