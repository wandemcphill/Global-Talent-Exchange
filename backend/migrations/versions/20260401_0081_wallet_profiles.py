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


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _indexed_column_sets(bind, table_name: str) -> set[tuple[str, ...]]:
    return {tuple(index.get("column_names") or ()) for index in sa.inspect(bind).get_indexes(table_name)}


def _create_index_if_missing(
    bind,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if index_name in _index_names(bind, table_name):
        return
    if tuple(columns) in _indexed_column_sets(bind, table_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_present(bind, *, table_name: str, index_name: str) -> None:
    if index_name in _index_names(bind, table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("user_wallets"):
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

    _create_index_if_missing(
        bind,
        table_name="user_wallets",
        index_name=op.f("ix_user_wallets_user_id"),
        columns=["user_id"],
    )

    if not inspector.has_table("wallet_transactions"):
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

    _create_index_if_missing(
        bind,
        table_name="wallet_transactions",
        index_name=op.f("ix_wallet_transactions_reference"),
        columns=["reference"],
    )
    _create_index_if_missing(
        bind,
        table_name="wallet_transactions",
        index_name=op.f("ix_wallet_transactions_user_id"),
        columns=["user_id"],
    )
    _create_index_if_missing(
        bind,
        table_name="wallet_transactions",
        index_name="ix_wallet_transactions_status",
        columns=["status"],
    )
    _create_index_if_missing(
        bind,
        table_name="wallet_transactions",
        index_name="ix_wallet_transactions_user_created_at",
        columns=["user_id", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("wallet_transactions"):
        _drop_index_if_present(
            bind,
            table_name="wallet_transactions",
            index_name="ix_wallet_transactions_user_created_at",
        )
        _drop_index_if_present(
            bind,
            table_name="wallet_transactions",
            index_name="ix_wallet_transactions_status",
        )
        _drop_index_if_present(
            bind,
            table_name="wallet_transactions",
            index_name=op.f("ix_wallet_transactions_user_id"),
        )
        _drop_index_if_present(
            bind,
            table_name="wallet_transactions",
            index_name=op.f("ix_wallet_transactions_reference"),
        )
        op.drop_table("wallet_transactions")

    if inspector.has_table("user_wallets"):
        _drop_index_if_present(
            bind,
            table_name="user_wallets",
            index_name=op.f("ix_user_wallets_user_id"),
        )
        op.drop_table("user_wallets")
