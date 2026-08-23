"""Align the seeded competition fee policy with the current 30% product default.

Revision ID: 20260822_0109_competition_fee_policy_default
Revises: 20260821_0108_gift_currency_semantics
Create Date: 2026-08-22 02:30:00.000000

Portability only: the 30% policy value is unchanged. The original revision used
a bare op.alter_column (rejected by SQLite, which has no ALTER COLUMN) and
compared the boolean `active` column against the integer 1 (rejected by
PostgreSQL: "operator does not exist: boolean = integer"), so it could not be
applied on either backend.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0109_competition_fee_policy_default"
down_revision = "20260821_0108_gift_currency_semantics"
branch_labels = None
depends_on = None


def _set_default(value: str) -> None:
    with op.batch_alter_table("admin_reward_rules") as batch_op:
        batch_op.alter_column(
            "competition_platform_fee_bps",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=sa.text(value),
        )


def upgrade() -> None:
    # The product's current intended competition cut is 30%.
    # Admin remains free to change the active rule after migration.
    _set_default("3000")
    op.execute(
        sa.text(
            """
            UPDATE admin_reward_rules
            SET competition_platform_fee_bps = 3000
            WHERE active
              AND competition_platform_fee_bps = 1000
            """
        )
    )


def downgrade() -> None:
    _set_default("1000")
    op.execute(
        sa.text(
            """
            UPDATE admin_reward_rules
            SET competition_platform_fee_bps = 1000
            WHERE active
              AND competition_platform_fee_bps = 3000
            """
        )
    )
