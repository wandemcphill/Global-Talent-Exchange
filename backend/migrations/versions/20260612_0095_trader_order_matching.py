"""Add trader order matching: fills, partial state, and executed trades."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260612_0095_trader_order_matching"
down_revision = "20260604_0094_club_squad_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trader_orders",
        sa.Column("filled_quantity", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
    )
    op.add_column(
        "trader_orders",
        sa.Column("average_fill_price", sa.Numeric(18, 4), nullable=True),
    )
    op.create_table(
        "trader_trades",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("buy_order_id", sa.String(length=36), nullable=False),
        sa.Column("sell_order_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_user_id", sa.String(length=36), nullable=False),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("notional", sa.Numeric(18, 4), nullable=False),
        sa.Column("fee_amount", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("taker_side", sa.String(length=12), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["trader_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buy_order_id"], ["trader_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sell_order_id"], ["trader_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trader_trades_market_created", "trader_trades", ["market_id", "created_at"], unique=False)
    op.create_index("ix_trader_trades_buy_order", "trader_trades", ["buy_order_id"], unique=False)
    op.create_index("ix_trader_trades_sell_order", "trader_trades", ["sell_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_trader_trades_sell_order", table_name="trader_trades")
    op.drop_index("ix_trader_trades_buy_order", table_name="trader_trades")
    op.drop_index("ix_trader_trades_market_created", table_name="trader_trades")
    op.drop_table("trader_trades")
    op.drop_column("trader_orders", "average_fill_price")
    op.drop_column("trader_orders", "filled_quantity")
