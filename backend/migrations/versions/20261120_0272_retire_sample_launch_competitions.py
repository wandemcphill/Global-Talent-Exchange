"""Retire the three sample launch competitions.

Revision ID: 20261120_0272_retire_sample_launch_competitions
Revises: 20261119_0271_creator_referral_commission

GTEX Lagos Launch Cup, Naija Rising Stars League, and Weekend Knockout Shield
were platform samples. They are not competitions created by a club owner.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261120_0272_retire_sample_launch_competitions"
down_revision = "20261119_0271_creator_referral_commission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE owner_competitions
            SET status = 'cancelled'
            WHERE host_type = 'gtex'
              AND status IN ('open', 'running')
              AND name IN (
                'GTEX Lagos Launch Cup',
                'Naija Rising Stars League',
                'Weekend Knockout Shield'
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE owner_competitions
            SET status = 'open'
            WHERE host_type = 'gtex'
              AND status = 'cancelled'
              AND name IN (
                'GTEX Lagos Launch Cup',
                'Naija Rising Stars League',
                'Weekend Knockout Shield'
              )
            """
        )
    )
