"""Align hosted competition template fee defaults with the Admin policy.

Revision ID: 20260822_0111_hosted_competition_template_fee_default
Revises: 20260822_0110_agent_wallet_fail_closed
Create Date: 2026-08-22 14:25:00.000000

Portability only: the 30% template default is unchanged. See revision 0109 for
why the bare alter_column and the integer comparison against the boolean
`active` column both had to go.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0111_hosted_competition_template_fee_default"
down_revision = "20260822_0110_agent_wallet_fail_closed"
branch_labels = None
depends_on = None


def _set_default(value: str) -> None:
    with op.batch_alter_table("competition_templates") as batch_op:
        batch_op.alter_column(
            "platform_fee_bps",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=sa.text(value),
        )


def upgrade() -> None:
    # Template values are display/default metadata only. Actual execution reads
    # the active Admin reward policy, currently intended at 30%.
    _set_default("3000")
    op.execute(sa.text("""
            UPDATE competition_templates
            SET platform_fee_bps = 3000
            WHERE active
              AND platform_fee_bps IN (1000, 2000)
            """))


def downgrade() -> None:
    _set_default("1000")
