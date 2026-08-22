"""Align hosted competition template fee defaults with the Admin policy.

Revision ID: 20260822_0111_hosted_competition_template_fee_default
Revises: 20260822_0110_agent_wallet_fail_closed
Create Date: 2026-08-22 14:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0111_hosted_competition_template_fee_default"
down_revision = "20260822_0110_agent_wallet_fail_closed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Template values are display/default metadata only. Actual execution reads
    # the active Admin reward policy, currently intended at 30%.
    op.alter_column(
        "competition_templates",
        "platform_fee_bps",
        server_default=sa.text("3000"),
    )
    op.execute(sa.text("""
            UPDATE competition_templates
            SET platform_fee_bps = 3000
            WHERE active = 1
              AND platform_fee_bps IN (1000, 2000)
            """))


def downgrade() -> None:
    op.alter_column(
        "competition_templates",
        "platform_fee_bps",
        server_default=sa.text("1000"),
    )
