"""Extend the economy governor for Thread C auto-balancing controls.

Revision ID: 20260328_0053_thread_c_ai_economy_governor
Revises: 20260328_0053_thread_de_risk_social_core
Create Date: 2026-03-28 05:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0053_thread_c_ai_economy_governor"
down_revision = "20260328_0053_thread_de_risk_social_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "economy_governor_policies",
        sa.Column("free_prize_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
    )
    op.add_column(
        "economy_governor_policies",
        sa.Column("agent_activity_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
    )
    op.add_column(
        "economy_governor_policies",
        sa.Column("price_change_limit", sa.Numeric(12, 4), nullable=False, server_default="0.2500"),
    )


def downgrade() -> None:
    op.drop_column("economy_governor_policies", "price_change_limit")
    op.drop_column("economy_governor_policies", "agent_activity_multiplier")
    op.drop_column("economy_governor_policies", "free_prize_multiplier")
