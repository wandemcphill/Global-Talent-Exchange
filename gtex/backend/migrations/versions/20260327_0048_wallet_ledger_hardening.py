"""Add wallet transaction headers and balance projections.

Revision ID: 20260327_0048_wallet_ledger_hardening
Revises: 20260327_0047_projection_workers
Create Date: 2026-03-27 14:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0048_wallet_ledger_hardening"
down_revision = "20260327_0047_projection_workers"
branch_labels = None
depends_on = None


ledger_transaction_status = sa.Enum(
    "pending",
    "committed",
    "failed",
    name="ledger_transaction_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ledger_transaction_status.create(bind, checkfirst=True)

    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", ledger_transaction_status, nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("source_tag", sa.String(length=64), nullable=False, server_default="admin_adjustment"),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_ledger_transactions_idempotency_key"),
    )
    op.create_index("ix_ledger_transactions_status", "ledger_transactions", ["status"], unique=False)
    op.create_index("ix_ledger_transactions_reference", "ledger_transactions", ["reference"], unique=False)
    op.create_index("ix_ledger_transactions_external_reference", "ledger_transactions", ["external_reference"], unique=False)
    op.create_index("ix_ledger_transactions_idempotency_key", "ledger_transactions", ["idempotency_key"], unique=False)
    op.create_index("ix_ledger_transactions_created_by_user_id", "ledger_transactions", ["created_by_user_id"], unique=False)

    op.create_table(
        "ledger_balance_projections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("balance", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("last_transaction_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["ledger_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_ledger_balance_projections_account"),
    )
    op.create_index("ix_ledger_balance_projections_account_id", "ledger_balance_projections", ["account_id"], unique=False)
    op.create_index("ix_ledger_balance_projections_owner_user_id", "ledger_balance_projections", ["owner_user_id"], unique=False)
    op.create_index("ix_ledger_balance_projections_last_transaction_id", "ledger_balance_projections", ["last_transaction_id"], unique=False)

    op.execute(
        """
        INSERT INTO ledger_transactions (
            id,
            status,
            reason,
            source_tag,
            reference,
            external_reference,
            description,
            metadata_json,
            created_by_user_id,
            created_at,
            committed_at
        )
        SELECT
            ledger_entries.transaction_id,
            'committed',
            MIN(ledger_entries.reason),
            MIN(ledger_entries.source_tag),
            MIN(ledger_entries.reference),
            MIN(ledger_entries.external_reference),
            MIN(ledger_entries.description),
            '{}',
            MIN(ledger_entries.created_by_user_id),
            MIN(ledger_entries.created_at),
            MIN(ledger_entries.created_at)
        FROM ledger_entries
        WHERE NOT EXISTS (
            SELECT 1
            FROM ledger_transactions
            WHERE ledger_transactions.id = ledger_entries.transaction_id
        )
        GROUP BY ledger_entries.transaction_id
        """
    )

    op.execute(
        """
        INSERT INTO ledger_balance_projections (
            id,
            account_id,
            owner_user_id,
            unit,
            balance,
            last_transaction_id
        )
        SELECT
            ledger_accounts.id,
            ledger_accounts.id,
            ledger_accounts.owner_user_id,
            ledger_accounts.unit,
            COALESCE(SUM(ledger_entries.amount), 0),
            NULL
        FROM ledger_accounts
        LEFT JOIN ledger_entries ON ledger_entries.account_id = ledger_accounts.id
        GROUP BY ledger_accounts.id, ledger_accounts.owner_user_id, ledger_accounts.unit
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ledger_balance_projections_last_transaction_id", table_name="ledger_balance_projections")
    op.drop_index("ix_ledger_balance_projections_owner_user_id", table_name="ledger_balance_projections")
    op.drop_index("ix_ledger_balance_projections_account_id", table_name="ledger_balance_projections")
    op.drop_table("ledger_balance_projections")

    op.drop_index("ix_ledger_transactions_created_by_user_id", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_idempotency_key", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_external_reference", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_reference", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_status", table_name="ledger_transactions")
    op.drop_table("ledger_transactions")

    ledger_transaction_status.drop(op.get_bind(), checkfirst=True)
