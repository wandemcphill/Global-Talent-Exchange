"""Add exchange order records and append-only ledger event records."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260311_0006"
down_revision = "20260311_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchange_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("side", sa.Enum("buy", name="order_side", native_enum=False), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("max_price", sa.Numeric(20, 4), nullable=True),
        sa.Column("currency", sa.Enum("coin", "credit", name="ledger_unit", native_enum=False), nullable=False),
        sa.Column("reserved_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.Enum("accepted", "cancelled", "filled", name="order_status", native_enum=False), nullable=False),
        sa.Column("hold_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_exchange_orders_player_id_ingestion_players", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_exchange_orders_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_exchange_orders"),
    )
    op.create_index("ix_exchange_orders_user_id", "exchange_orders", ["user_id"], unique=False)
    op.create_index("ix_exchange_orders_player_id", "exchange_orders", ["player_id"], unique=False)
    op.create_index("ix_exchange_orders_hold_transaction_id", "exchange_orders", ["hold_transaction_id"], unique=False)

    op.create_table(
        "ledger_event_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "order.accepted",
                "order.funds_reserved",
                "order.executed",
                "order.cancelled",
                "order.released",
                name="ledger_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_ledger_event_records_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_event_records"),
    )
    op.create_index("ix_ledger_event_records_aggregate_id", "ledger_event_records", ["aggregate_id"], unique=False)
    op.create_index("ix_ledger_event_records_user_id", "ledger_event_records", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ledger_event_records_user_id", table_name="ledger_event_records")
    op.drop_index("ix_ledger_event_records_aggregate_id", table_name="ledger_event_records")
    op.drop_table("ledger_event_records")

    op.drop_index("ix_exchange_orders_hold_transaction_id", table_name="exchange_orders")
    op.drop_index("ix_exchange_orders_player_id", table_name="exchange_orders")
    op.drop_index("ix_exchange_orders_user_id", table_name="exchange_orders")
    op.drop_table("exchange_orders")
