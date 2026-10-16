"""Make persisted creator-agent wallet defaults fail closed.

Revision ID: 20260822_0110_agent_wallet_fail_closed
Revises: 20260822_0109_competition_fee_policy_default
Create Date: 2026-08-22 14:20:00.000000

Portability only: the fail-closed defaults are unchanged. The original revision
used bare op.alter_column calls, which SQLite rejects outright.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0110_agent_wallet_fail_closed"
down_revision = "20260822_0109_competition_fee_policy_default"
branch_labels = None
depends_on = None


def _apply(*, balance_default: str, payout_default: str) -> None:
    with op.batch_alter_table("agent_wallets") as batch_op:
        batch_op.alter_column(
            "balance",
            existing_type=sa.Float(),
            existing_nullable=False,
            server_default=sa.text(balance_default),
        )
        batch_op.alter_column(
            "payout_eligible",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.text(payout_default),
        )
    with op.batch_alter_table("agent_performance_logs") as batch_op:
        batch_op.alter_column(
            "payout_eligible",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.text(payout_default),
        )


def upgrade() -> None:
    # New compatibility-projection rows must not invent monetary value or payout authority.
    _apply(balance_default="0", payout_default="false")


def downgrade() -> None:
    _apply(balance_default="12", payout_default="true")
