"""Align the seeded competition fee policy with the current 30% product default.

Revision ID: 20260822_0109_competition_fee_policy_default
Revises: 20260821_0108_gift_currency_semantics
Create Date: 2026-08-22 02:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0109_competition_fee_policy_default"
down_revision = "20260821_0108_gift_currency_semantics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The product's current intended competition cut is 30%.
    # Admin remains free to change the active rule after migration.
    op.alter_column(
        "admin_reward_rules",
        "competition_platform_fee_bps",
        server_default=sa.text("3000"),
    )
    op.execute(
        sa.text(
            """
            UPDATE admin_reward_rules
            SET competition_platform_fee_bps = 3000
            WHERE active = 1
              AND competition_platform_fee_bps = 1000
            """
        )
    )


def downgrade() -> None:
    op.alter_column(
        "admin_reward_rules",
        "competition_platform_fee_bps",
        server_default=sa.text("1000"),
    )
    op.execute(
        sa.text(
            """
            UPDATE admin_reward_rules
            SET competition_platform_fee_bps = 1000
            WHERE active = 1
              AND competition_platform_fee_bps = 3000
            """
        )
    )
