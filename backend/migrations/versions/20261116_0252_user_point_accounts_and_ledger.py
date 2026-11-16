"""Add personal user_point_accounts and user_point_ledger_entries tables.

Revision ID: 20261116_0252_user_point_accounts_and_ledger
Revises: 20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration
Create Date: 2026-11-16 00:58:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0252_user_point_accounts_and_ledger"
down_revision = "20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_point_accounts",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("balance", sa.Numeric(precision=20, scale=4), server_default="0.0000", nullable=False),
        sa.Column("lifetime_earned", sa.Numeric(precision=20, scale=4), server_default="0.0000", nullable=False),
        sa.Column("lifetime_spent", sa.Numeric(precision=20, scale=4), server_default="0.0000", nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_point_accounts_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_point_accounts"),
        sa.UniqueConstraint("user_id", name="uq_user_point_accounts_user_id"),
    )
    op.create_index("ix_user_point_accounts_user_id", "user_point_accounts", ["user_id"], unique=True)

    op.create_table(
        "user_point_ledger_entries",
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("granted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("delta", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("balance_before", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("reference", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("source_scope", sa.String(length=64), server_default="admin_grant", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["user_point_accounts.id"],
            name="fk_user_point_ledger_entries_account_id_user_point_accounts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_point_ledger_entries_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            name="fk_user_point_ledger_entries_granted_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_point_ledger_entries"),
        sa.UniqueConstraint("idempotency_key", name="uq_user_point_ledger_entries_idempotency_key"),
    )
    op.create_index(
        "ix_user_point_ledger_entries_account_id", "user_point_ledger_entries", ["account_id"], unique=False
    )
    op.create_index("ix_user_point_ledger_entries_user_id", "user_point_ledger_entries", ["user_id"], unique=False)
    op.create_index(
        "ix_user_point_ledger_entries_granted_by_user_id",
        "user_point_ledger_entries",
        ["granted_by_user_id"],
        unique=False,
    )
    op.create_index("ix_user_point_ledger_entries_reference", "user_point_ledger_entries", ["reference"], unique=False)
    op.create_index(
        "ix_user_point_ledger_entries_idempotency_key",
        "user_point_ledger_entries",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_point_ledger_entries_idempotency_key", table_name="user_point_ledger_entries")
    op.drop_index("ix_user_point_ledger_entries_reference", table_name="user_point_ledger_entries")
    op.drop_index("ix_user_point_ledger_entries_granted_by_user_id", table_name="user_point_ledger_entries")
    op.drop_index("ix_user_point_ledger_entries_user_id", table_name="user_point_ledger_entries")
    op.drop_index("ix_user_point_ledger_entries_account_id", table_name="user_point_ledger_entries")
    op.drop_table("user_point_ledger_entries")
    op.drop_index("ix_user_point_accounts_user_id", table_name="user_point_accounts")
    op.drop_table("user_point_accounts")
