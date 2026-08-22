"""Make persisted creator-agent wallet defaults fail closed.

Revision ID: 20260822_0110_agent_wallet_fail_closed
Revises: 20260822_0109_competition_fee_policy_default
Create Date: 2026-08-22 14:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0110_agent_wallet_fail_closed"
down_revision = "20260822_0109_competition_fee_policy_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New compatibility-projection rows must not invent monetary value or payout authority.
    op.alter_column(
        "agent_wallets",
        "balance",
        server_default=sa.text("0"),
    )
    op.alter_column(
        "agent_wallets",
        "payout_eligible",
        server_default=sa.text("false"),
    )
    op.alter_column(
        "agent_performance_logs",
        "payout_eligible",
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.alter_column(
        "agent_wallets",
        "balance",
        server_default=sa.text("12"),
    )
    op.alter_column(
        "agent_wallets",
        "payout_eligible",
        server_default=sa.text("true"),
    )
    op.alter_column(
        "agent_performance_logs",
        "payout_eligible",
        server_default=sa.text("true"),
    )
