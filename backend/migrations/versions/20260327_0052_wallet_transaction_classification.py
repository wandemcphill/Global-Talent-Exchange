"""Add ledger entry transaction classification.

Revision ID: 20260327_0052_wallet_transaction_classification
Revises: 20260327_0051_economy_governor_player_tokens_and_fx
Create Date: 2026-03-27 18:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0052_wallet_transaction_classification"
down_revision = "20260327_0051_economy_governor_player_tokens_and_fx"
branch_labels = None
depends_on = None


ledger_transaction_type = sa.Enum(
    "deposit",
    "withdrawal",
    "match_entry_fee",
    "match_reward",
    "lottery_reward",
    "trade_buy",
    "trade_sell",
    "adjustment",
    "conversion",
    "promo_pool_credit",
    name="ledger_transaction_type",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ledger_transaction_type.create(bind, checkfirst=True)

    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "transaction_type",
                ledger_transaction_type,
                nullable=False,
                server_default="adjustment",
            )
        )
        batch_op.create_index(
            "ix_ledger_entries_transaction_type",
            ["transaction_type"],
            unique=False,
        )

    op.execute(
        """
        UPDATE ledger_entries
        SET transaction_type = CASE
            WHEN reason = 'deposit' THEN 'deposit'
            WHEN reason IN ('withdrawal_hold', 'withdrawal_settlement') THEN 'withdrawal'
            WHEN reason = 'competition_entry' THEN 'match_entry_fee'
            WHEN reason = 'competition_reward' THEN 'match_reward'
            WHEN reason = 'trade_settlement' AND source_tag IN ('player_card_sale', 'club_sale_sale') THEN 'trade_sell'
            WHEN reason = 'trade_settlement' AND source_tag IN ('player_card_purchase', 'player_share_purchase', 'club_sale_purchase', 'trading_fee_burn') THEN 'trade_buy'
            WHEN source_tag = 'promo_pool_credit' THEN 'promo_pool_credit'
            ELSE 'adjustment'
        END
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.drop_index("ix_ledger_entries_transaction_type")
        batch_op.drop_column("transaction_type")

    ledger_transaction_type.drop(op.get_bind(), checkfirst=True)
