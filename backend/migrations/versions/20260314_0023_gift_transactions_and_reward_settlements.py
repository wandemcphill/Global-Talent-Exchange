"""Add gift transactions and reward settlements."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0023"
down_revision = "20260314_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gift_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=36), nullable=False),
        sa.Column("gift_catalog_item_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False, server_default=sa.text("1.0000")),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_rake_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("recipient_net_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("source_scope", sa.String(length=32), nullable=False, server_default=sa.text("'user_hosted'")),
        sa.Column("ledger_unit", sa.String(length=16), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'settled'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["gift_catalog_item_id"], ["gift_catalog.id"], name="fk_gift_transactions_gift_catalog_item_id_gift_catalog", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], name="fk_gift_transactions_recipient_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], name="fk_gift_transactions_sender_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gift_transactions"),
    )
    op.create_index("ix_gift_transactions_sender_user_id", "gift_transactions", ["sender_user_id"], unique=False)
    op.create_index("ix_gift_transactions_recipient_user_id", "gift_transactions", ["recipient_user_id"], unique=False)
    op.create_index("ix_gift_transactions_gift_catalog_item_id", "gift_transactions", ["gift_catalog_item_id"], unique=False)
    op.create_index("ix_gift_transactions_ledger_transaction_id", "gift_transactions", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "reward_settlements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("competition_key", sa.String(length=64), nullable=False),
        sa.Column("reward_source", sa.String(length=64), nullable=False, server_default=sa.text("'gtex_promotional_pool'")),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_fee_amount", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("net_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("ledger_unit", sa.String(length=16), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'settled'")),
        sa.Column("settled_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["settled_by_user_id"], ["users.id"], name="fk_reward_settlements_settled_by_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_reward_settlements_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_reward_settlements"),
    )
    op.create_index("ix_reward_settlements_user_id", "reward_settlements", ["user_id"], unique=False)
    op.create_index("ix_reward_settlements_competition_key", "reward_settlements", ["competition_key"], unique=False)
    op.create_index("ix_reward_settlements_ledger_transaction_id", "reward_settlements", ["ledger_transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reward_settlements_ledger_transaction_id", table_name="reward_settlements")
    op.drop_index("ix_reward_settlements_competition_key", table_name="reward_settlements")
    op.drop_index("ix_reward_settlements_user_id", table_name="reward_settlements")
    op.drop_table("reward_settlements")

    op.drop_index("ix_gift_transactions_ledger_transaction_id", table_name="gift_transactions")
    op.drop_index("ix_gift_transactions_gift_catalog_item_id", table_name="gift_transactions")
    op.drop_index("ix_gift_transactions_recipient_user_id", table_name="gift_transactions")
    op.drop_index("ix_gift_transactions_sender_user_id", table_name="gift_transactions")
    op.drop_table("gift_transactions")
