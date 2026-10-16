"""Align wallet ledger tables with PostgreSQL transaction integrity.

Revision ID: 20260327_0049_wallet_transactions_postgres
Revises: 20260327_0048_wallet_ledger_hardening
Create Date: 2026-03-27 16:25:00.000000
"""

from __future__ import annotations

from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision = "20260327_0049_wallet_transactions_postgres"
down_revision = "20260327_0048_wallet_ledger_hardening"
branch_labels = None
depends_on = None

SQL_ROOT = Path(__file__).resolve().parents[1] / "sql"
POSTGRES_UP_SQL = SQL_ROOT / "20260327_0049_wallet_transactions_postgres_up.sql"
POSTGRES_DOWN_SQL = SQL_ROOT / "20260327_0049_wallet_transactions_postgres_down.sql"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("ledger_accounts") and not inspector.has_table("wallets"):
        op.rename_table("ledger_accounts", "wallets")
    if inspector.has_table("ledger_transactions") and not inspector.has_table("transactions"):
        op.rename_table("ledger_transactions", "transactions")

    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_ledger_entries_transaction_id_transactions",
            "transactions",
            ["transaction_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint("ck_ledger_entries_amount_non_zero", "amount <> 0")

    with op.batch_alter_table("ledger_balance_projections", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_ledger_balance_projections_last_transaction_id_transactions",
            "transactions",
            ["last_transaction_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("payment_events", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_payment_events_ledger_transaction_id_transactions",
            "transactions",
            ["ledger_transaction_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("payout_requests", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_payout_requests_hold_transaction_id_transactions",
            "transactions",
            ["hold_transaction_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_payout_requests_settlement_transaction_id_transactions",
            "transactions",
            ["settlement_transaction_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if bind.dialect.name == "postgresql":
        op.execute(POSTGRES_UP_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        op.execute(POSTGRES_DOWN_SQL.read_text(encoding="utf-8"))

    with op.batch_alter_table("payout_requests", schema=None) as batch_op:
        batch_op.drop_constraint("fk_payout_requests_settlement_transaction_id_transactions", type_="foreignkey")
        batch_op.drop_constraint("fk_payout_requests_hold_transaction_id_transactions", type_="foreignkey")

    with op.batch_alter_table("payment_events", schema=None) as batch_op:
        batch_op.drop_constraint("fk_payment_events_ledger_transaction_id_transactions", type_="foreignkey")

    with op.batch_alter_table("ledger_balance_projections", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_ledger_balance_projections_last_transaction_id_transactions",
            type_="foreignkey",
        )

    with op.batch_alter_table("ledger_entries", schema=None) as batch_op:
        batch_op.drop_constraint("ck_ledger_entries_amount_non_zero", type_="check")
        batch_op.drop_constraint("fk_ledger_entries_transaction_id_transactions", type_="foreignkey")

    if inspector.has_table("transactions") and not inspector.has_table("ledger_transactions"):
        op.rename_table("transactions", "ledger_transactions")
    if inspector.has_table("wallets") and not inspector.has_table("ledger_accounts"):
        op.rename_table("wallets", "ledger_accounts")
