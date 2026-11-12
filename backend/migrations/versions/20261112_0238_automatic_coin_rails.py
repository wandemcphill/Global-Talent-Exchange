"""Turn the default treasury rail to automatic buy and withdrawal.

Revision ID: 20261112_0238_automatic_coin_rails
Revises: 20261112_0237_two_d_launch_and_play_prices

Existing rows that are still on the original manual setting move to automatic.
An admin can set a row back to manual after this runs.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261112_0238_automatic_coin_rails"
down_revision = "20261112_0237_two_d_launch_and_play_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE treasury_settings SET deposit_mode = 'automatic' " "WHERE deposit_mode = 'manual'"))
    op.execute(
        sa.text("UPDATE treasury_settings SET withdrawal_mode = 'automatic' " "WHERE withdrawal_mode = 'manual'")
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE treasury_settings SET deposit_mode = 'manual' " "WHERE deposit_mode = 'automatic'"))
    op.execute(
        sa.text("UPDATE treasury_settings SET withdrawal_mode = 'manual' " "WHERE withdrawal_mode = 'automatic'")
    )
