"""Normalize the Phase A economic-policy baseline and collapse duplicate active rows.

Revision ID: 20260827_0114_economic_policy_authority
Revises: 20260827_0113_economic_policy_consistency
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260827_0114_economic_policy_authority"
down_revision = "20260827_0113_economic_policy_consistency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE admin_reward_rules
            SET competition_platform_fee_bps = 3000
            WHERE rule_key = 'platform-economy-defaults'
              AND competition_platform_fee_bps IN (1000, 2000)
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE admin_reward_rules
            SET active = FALSE
            WHERE active
              AND id <> (
                SELECT id
                FROM admin_reward_rules
                WHERE active
                ORDER BY updated_at DESC, id ASC
                LIMIT 1
              )
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE competition_templates
            SET platform_fee_bps = 3000
            WHERE platform_fee_bps IN (1000, 2000)
            """
        )
    )


def downgrade() -> None:
    pass
