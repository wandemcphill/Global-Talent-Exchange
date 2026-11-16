"""Rebalance GTEX and Fan Coin retail, trader and withdrawal pricing.

Revision ID: 20261116_0253_gtex_coin_fiat_rate_rebalance
Revises: 20261115_0252_canonical_live_match_execution
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa
from decimal import Decimal, ROUND_UP


revision = "20261116_0253_gtex_coin_fiat_rate_rebalance"
down_revision = "20261115_0252_canonical_live_match_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A 15:1 gift conversion makes outstanding Fan Coin claims larger in GTEX
    # terms than the historical 100:1 backing. Never activate it unless the
    # existing gift bridge can cover every outstanding user Fan Coin balance.
    connection = op.get_bind()
    outstanding_fan_coin = connection.execute(
        sa.text(
            """
            SELECT COALESCE(SUM(balance), 0)
            FROM (
                SELECT w.id, SUM(le.amount) AS balance
                FROM wallets AS w
                JOIN ledger_entries AS le ON le.account_id = w.id
                JOIN transactions AS t ON t.id = le.transaction_id
                WHERE w.owner_user_id IS NOT NULL
                  AND LOWER(w.unit) = 'credit'
                  AND LOWER(w.kind) = 'user'
                  AND LOWER(t.status) = 'committed'
                GROUP BY w.id
                HAVING SUM(le.amount) > 0
            ) AS outstanding_user_fan_coin
            """
        )
    ).scalar_one()
    bridge_coin_balance = connection.execute(
        sa.text(
            """
            SELECT COALESCE(SUM(le.amount), 0)
            FROM wallets AS w
            JOIN ledger_entries AS le ON le.account_id = w.id
            JOIN transactions AS t ON t.id = le.transaction_id
            WHERE w.code = 'platform:coin:gift_conversion_bridge'
              AND LOWER(t.status) = 'committed'
            """
        )
    ).scalar_one()
    required_bridge_coin = (
        Decimal(str(outstanding_fan_coin or 0)) / Decimal("15")
    ).quantize(Decimal("0.0001"), rounding=ROUND_UP)
    available_bridge_coin = Decimal(str(bridge_coin_balance or 0))
    if available_bridge_coin < required_bridge_coin:
        shortfall = required_bridge_coin - available_bridge_coin
        raise RuntimeError(
            "Treasury rebalance blocked: existing user Fan Coin requires "
            f"{required_bridge_coin} GTEX on the gift-conversion bridge, but "
            f"only {available_bridge_coin} is available (shortfall {shortfall}). "
            "Fund and reconcile the bridge before deploying the 15:1 conversion rate. "
            "No user balance or ledger entry was changed."
        )

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
    # Legacy active trader quotes cannot be left visible after the new
    # governance limits take effect. Deactivate only NGN quotes that fail the
    # new limits; traders can republish compliant rates.
    op.execute(
        sa.text(
            """
            UPDATE coin_trader_rates
            SET is_active = FALSE
            WHERE UPPER(fiat_currency) = 'NGN'
              AND is_active = TRUE
              AND (
                (
                  LOWER(coin_unit) = 'coin'
                  AND (
                    buy_rate_fiat < 48.0000 OR buy_rate_fiat > 50.0000
                    OR sell_rate_fiat < 53.0000 OR sell_rate_fiat > 59.0000
                    OR sell_rate_fiat < buy_rate_fiat
                    OR sell_rate_fiat - buy_rate_fiat > 10.0000
                  )
                )
                OR
                (
                  LOWER(coin_unit) = 'credit'
                  AND (
                    buy_rate_fiat <> 2.5000
                    OR sell_rate_fiat < 2.7500 OR sell_rate_fiat > 3.5000
                    OR sell_rate_fiat < buy_rate_fiat
                    OR sell_rate_fiat - buy_rate_fiat > 1.0000
                  )
                )
              )
            """
        )
    )

    op.execute(sa.text("""
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
            """))


def downgrade() -> None:
    op.execute(sa.text("""
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
            """))
    op.drop_column("treasury_settings", "trader_withdrawal_rate_value")
    op.drop_column("treasury_settings", "trader_fan_coin_purchase_rate_value")
    op.drop_column("treasury_settings", "trader_coin_purchase_rate_value")
    op.drop_column("treasury_settings", "fan_coin_deposit_rate_value")
