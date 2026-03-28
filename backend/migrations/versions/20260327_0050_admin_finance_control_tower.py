"""Add admin finance control-tower daily aggregates.

Revision ID: 20260327_0050_admin_finance_control_tower
Revises: 20260327_0049_wallet_transactions_postgres
Create Date: 2026-03-27 19:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0050_admin_finance_control_tower"
down_revision = "20260327_0049_wallet_transactions_postgres"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economy_daily_stats",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("gtex_minted", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("gtex_burned", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("fan_minted", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("fan_burned", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("revenue_naira", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("marketplace_fee_amount", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("match_spend_amount", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("tournament_pool_amount", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("gtex_supply", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("fan_supply", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("date", name="pk_economy_daily_stats"),
    )


def downgrade() -> None:
    op.drop_table("economy_daily_stats")
