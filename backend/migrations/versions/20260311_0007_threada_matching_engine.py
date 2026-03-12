"""Add matching lifecycle fields and trade execution records."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260311_0007"
down_revision = "20260311_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exchange_orders") as batch_op:
        batch_op.add_column(
            sa.Column("filled_quantity", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0"))
        )
        batch_op.alter_column(
            "side",
            existing_type=sa.String(length=3),
            type_=sa.String(length=8),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=9),
            type_=sa.String(length=32),
            existing_nullable=False,
        )

    op.execute("UPDATE exchange_orders SET status = 'open' WHERE status = 'accepted'")
    op.execute("UPDATE exchange_orders SET filled_quantity = quantity WHERE status = 'filled'")

    with op.batch_alter_table("exchange_orders") as batch_op:
        batch_op.alter_column(
            "filled_quantity",
            existing_type=sa.Numeric(20, 4),
            server_default=None,
            existing_nullable=False,
        )

    op.create_table(
        "trade_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("buy_order_id", sa.String(length=36), nullable=False),
        sa.Column("sell_order_id", sa.String(length=36), nullable=False),
        sa.Column("maker_order_id", sa.String(length=36), nullable=False),
        sa.Column("taker_order_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=False),
        sa.Column("notional", sa.Numeric(20, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_trade_executions_player_id_ingestion_players", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["buy_order_id"], ["exchange_orders.id"], name="fk_trade_executions_buy_order_id_exchange_orders", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sell_order_id"], ["exchange_orders.id"], name="fk_trade_executions_sell_order_id_exchange_orders", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["maker_order_id"], ["exchange_orders.id"], name="fk_trade_executions_maker_order_id_exchange_orders", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["taker_order_id"], ["exchange_orders.id"], name="fk_trade_executions_taker_order_id_exchange_orders", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_trade_executions"),
    )
    op.create_index("ix_trade_executions_player_id", "trade_executions", ["player_id"], unique=False)
    op.create_index("ix_trade_executions_buy_order_id", "trade_executions", ["buy_order_id"], unique=False)
    op.create_index("ix_trade_executions_sell_order_id", "trade_executions", ["sell_order_id"], unique=False)
    op.create_index("ix_trade_executions_maker_order_id", "trade_executions", ["maker_order_id"], unique=False)
    op.create_index("ix_trade_executions_taker_order_id", "trade_executions", ["taker_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_trade_executions_taker_order_id", table_name="trade_executions")
    op.drop_index("ix_trade_executions_maker_order_id", table_name="trade_executions")
    op.drop_index("ix_trade_executions_sell_order_id", table_name="trade_executions")
    op.drop_index("ix_trade_executions_buy_order_id", table_name="trade_executions")
    op.drop_index("ix_trade_executions_player_id", table_name="trade_executions")
    op.drop_table("trade_executions")

    op.execute("UPDATE exchange_orders SET status = 'accepted' WHERE status = 'open'")
    op.execute("UPDATE exchange_orders SET status = 'accepted' WHERE status = 'partially_filled'")
    op.execute("UPDATE exchange_orders SET status = 'cancelled' WHERE status = 'rejected'")

    with op.batch_alter_table("exchange_orders") as batch_op:
        batch_op.drop_column("filled_quantity")
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=32),
            type_=sa.String(length=9),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "side",
            existing_type=sa.String(length=8),
            type_=sa.String(length=3),
            existing_nullable=False,
        )
