"""Add coin trader pricing governance fields.

Revision ID: 20260515_0094_coin_trader_pricing_governance
Revises: 20260511_0093_governance_viral_collectibles
Create Date: 2026-05-15 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260515_0094_coin_trader_pricing_governance"
down_revision = "20260511_0093_governance_viral_collectibles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("treasury_settings") as batch_op:
        batch_op.add_column(
            sa.Column("min_trader_buy_rate_fiat", sa.Numeric(20, 6), nullable=False, server_default="820.0000")
        )
        batch_op.add_column(
            sa.Column("max_trader_buy_rate_fiat", sa.Numeric(20, 6), nullable=False, server_default="890.0000")
        )
        batch_op.add_column(
            sa.Column("min_trader_sell_rate_fiat", sa.Numeric(20, 6), nullable=False, server_default="900.0000")
        )
        batch_op.add_column(
            sa.Column("max_trader_sell_rate_fiat", sa.Numeric(20, 6), nullable=False, server_default="980.0000")
        )
        batch_op.add_column(
            sa.Column("max_trader_spread_fiat", sa.Numeric(20, 6), nullable=False, server_default="120.0000")
        )
        batch_op.add_column(
            sa.Column("max_buy_above_withdrawal_fiat", sa.Numeric(20, 6), nullable=False, server_default="10.0000")
        )
        batch_op.add_column(
            sa.Column("max_sell_below_deposit_fiat", sa.Numeric(20, 6), nullable=False, server_default="0.0000")
        )

    with op.batch_alter_table("coin_trader_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("verification_level", sa.String(length=32), nullable=False, server_default="standard")
        )
        batch_op.add_column(sa.Column("completed_volume_fiat", sa.Numeric(20, 4), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("dispute_score", sa.Float(), nullable=False, server_default="0"))

    op.create_index("ix_coin_trader_profiles_verification_level", "coin_trader_profiles", ["verification_level"])


def downgrade() -> None:
    op.drop_index("ix_coin_trader_profiles_verification_level", table_name="coin_trader_profiles")

    with op.batch_alter_table("coin_trader_profiles") as batch_op:
        batch_op.drop_column("dispute_score")
        batch_op.drop_column("completed_volume_fiat")
        batch_op.drop_column("verification_level")

    with op.batch_alter_table("treasury_settings") as batch_op:
        batch_op.drop_column("max_sell_below_deposit_fiat")
        batch_op.drop_column("max_buy_above_withdrawal_fiat")
        batch_op.drop_column("max_trader_spread_fiat")
        batch_op.drop_column("max_trader_sell_rate_fiat")
        batch_op.drop_column("min_trader_sell_rate_fiat")
        batch_op.drop_column("max_trader_buy_rate_fiat")
        batch_op.drop_column("min_trader_buy_rate_fiat")
