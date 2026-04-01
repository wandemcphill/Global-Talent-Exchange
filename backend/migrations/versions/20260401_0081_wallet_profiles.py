"""Add wallet profiles and wallet transaction records.

Revision ID: 20260401_0081_wallet_profiles
Revises: 20260401_0080_auth_session_rebuild
Create Date: 2026-04-01 16:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0081_wallet_profiles"
down_revision = "20260401_0080_auth_session_rebuild"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_wallets",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("balance", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("currency", sa.String(length=16), nullable=False, server_default="credit"),
        sa.Column("compliance_status", sa.String(length=32), nullable=False, server_default="verified"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_wallets_user_id"),
    )
    op.create_index(op.f("ix_user_wallets_user_id"), "user_wallets", ["user_id"], unique=False)

    op.create_table(
        "wallet_transactions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("reference", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_wallet_transactions_reference"),
    )
    op.create_index(op.f("ix_wallet_transactions_reference"), "wallet_transactions", ["reference"], unique=False)
    op.create_index(op.f("ix_wallet_transactions_user_id"), "wallet_transactions", ["user_id"], unique=False)
    op.create_index("ix_wallet_transactions_status", "wallet_transactions", ["status"], unique=False)
    op.create_index(
        "ix_wallet_transactions_user_created_at",
        "wallet_transactions",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wallet_transactions_user_created_at", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_status", table_name="wallet_transactions")
    op.drop_index(op.f("ix_wallet_transactions_user_id"), table_name="wallet_transactions")
    op.drop_index(op.f("ix_wallet_transactions_reference"), table_name="wallet_transactions")
    op.drop_table("wallet_transactions")

    op.drop_index(op.f("ix_user_wallets_user_id"), table_name="user_wallets")
    op.drop_table("user_wallets")
