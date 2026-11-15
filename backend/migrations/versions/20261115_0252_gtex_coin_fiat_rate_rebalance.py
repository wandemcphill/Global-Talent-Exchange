"""Rebalance GTEX and Fan Coin retail, trader and withdrawal pricing.

Revision ID: 20261115_0252_gtex_coin_fiat_rate_rebalance
Revises: 20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0252_gtex_coin_fiat_rate_rebalance"
down_revision = "20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "treasury_settings",
        sa.Column("fan_coin_deposit_rate_value", sa.Numeric(20, 6), nullable=False, server_default="4.0000"),
    )
    op.add_column(
        "treasury_settings",
        sa.Column("trader_coin_purchase_rate_value", sa.Numeric(20, 6), nullable=False, server_default="50.0000"),
    )
    op.add_column(
        "treasury_settings",
        sa.Column("trader_fan_coin_purchase_rate_value", sa.Numeric(20, 6), nullable=False, server_default="2.5000"),
    )
    op.add_column(
        "treasury_settings",
        sa.Column("trader_withdrawal_rate_value", sa.Numeric(20, 6), nullable=False, server_default="50.0000"),
    )

    # Update the existing live NGN settings row, not only future defaults.
    op.execute(
        sa.text(
            """
            UPDATE treasury_settings
            SET deposit_rate_value = 60.000000,
                deposit_rate_direction = 'fiat_per_coin',
                withdrawal_rate_value = 48.000000,
                withdrawal_rate_direction = 'fiat_per_coin',
                fan_coin_deposit_rate_value = 4.000000,
                trader_coin_purchase_rate_value = 50.000000,
                trader_fan_coin_purchase_rate_value = 2.500000,
                trader_withdrawal_rate_value = 50.000000,
                min_trader_buy_rate_fiat = 48.000000,
                max_trader_buy_rate_fiat = 50.000000,
                min_trader_sell_rate_fiat = 53.000000,
                max_trader_sell_rate_fiat = 59.000000,
                max_trader_spread_fiat = 10.000000,
                max_buy_above_withdrawal_fiat = 2.000000,
                max_sell_below_deposit_fiat = 7.000000
            WHERE currency_code = 'NGN'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE treasury_settings
            SET deposit_rate_value = 900.000000,
                withdrawal_rate_value = 880.000000,
                min_trader_buy_rate_fiat = 820.000000,
                max_trader_buy_rate_fiat = 890.000000,
                min_trader_sell_rate_fiat = 900.000000,
                max_trader_sell_rate_fiat = 980.000000,
                max_trader_spread_fiat = 120.000000,
                max_buy_above_withdrawal_fiat = 10.000000,
                max_sell_below_deposit_fiat = 0.000000
            WHERE currency_code = 'NGN'
            """
        )
    )
    op.drop_column("treasury_settings", "trader_withdrawal_rate_value")
    op.drop_column("treasury_settings", "trader_fan_coin_purchase_rate_value")
    op.drop_column("treasury_settings", "trader_coin_purchase_rate_value")
    op.drop_column("treasury_settings", "fan_coin_deposit_rate_value")
