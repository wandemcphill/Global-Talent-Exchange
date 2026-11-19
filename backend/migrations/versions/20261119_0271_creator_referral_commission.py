"""Add the creator first-deposit referral rate.

Revision ID: 20261119_0271_creator_referral_commission
Revises: 20261118_0270_ai_gateway

Creator accounts earn 25 percent of a referred user's first deposit.
Every other account stays on the existing referrer rate, which is 10 percent.
The person who was referred still receives the user bonus, which is 10 percent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261119_0271_creator_referral_commission"
down_revision = "20261118_0270_ai_gateway"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "referral_programme_settings",
        sa.Column("creator_commission_bps", sa.Integer(), nullable=False, server_default="2500"),
    )


def downgrade() -> None:
    op.drop_column("referral_programme_settings", "creator_commission_bps")
