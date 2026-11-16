"""Set the default first-club campaign grant to 2,500 GTX.

Revision ID: 20261116_0260_first_500_club_grant_amount
Revises: 20261116_0259_coin_trader_adverts
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0260_first_500_club_grant_amount"
down_revision = "20261116_0259_coin_trader_adverts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing entitlement amounts are intentionally preserved. Only the
    # server default for newly-created entitlement rows changes.
    with op.batch_alter_table("first_club_entitlements") as batch_op:
        batch_op.alter_column(
            "gtex_grant_amount",
            existing_type=sa.Numeric(18, 4),
            existing_nullable=False,
            server_default="2500.0000",
        )


def downgrade() -> None:
    with op.batch_alter_table("first_club_entitlements") as batch_op:
        batch_op.alter_column(
            "gtex_grant_amount",
            existing_type=sa.Numeric(18, 4),
            existing_nullable=False,
            server_default="100000.0000",
        )
