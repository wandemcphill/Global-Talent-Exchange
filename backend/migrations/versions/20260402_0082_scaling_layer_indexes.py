"""Verify scaling-layer indexes for player markets and wallet queries.

Revision ID: 20260402_0082_scaling_layer_indexes
Revises: 20260401_0081_wallet_profiles
Create Date: 2026-04-02 11:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260402_0082_scaling_layer_indexes"
down_revision = "20260401_0081_wallet_profiles"
branch_labels = None
depends_on = None


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _indexed_column_sets(bind, table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(index.get("column_names") or ())
        for index in sa.inspect(bind).get_indexes(table_name)
    }


def _unique_column_sets(bind, table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.get("column_names") or ())
        for constraint in sa.inspect(bind).get_unique_constraints(table_name)
    }


def _primary_key_columns(bind, table_name: str) -> tuple[str, ...]:
    return tuple(sa.inspect(bind).get_pk_constraint(table_name).get("constrained_columns") or ())


def _create_index_if_missing(
    bind,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    column_tuple = tuple(columns)
    if index_name in _index_names(bind, table_name):
        return
    if column_tuple in _indexed_column_sets(bind, table_name):
        return
    if column_tuple in _unique_column_sets(bind, table_name):
        return
    if unique and column_tuple == _primary_key_columns(bind, table_name):
        return
    op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_present(bind, *, table_name: str, index_name: str) -> None:
    if index_name in _index_names(bind, table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("players") and _primary_key_columns(bind, "players") != ("id",):
        _create_index_if_missing(
            bind,
            table_name="players",
            index_name="ix_players_id",
            columns=["id"],
            unique=True,
        )

    if inspector.has_table("player_share_markets"):
        _create_index_if_missing(
            bind,
            table_name="player_share_markets",
            index_name="ix_player_share_markets_player_id",
            columns=["player_id"],
        )

    if inspector.has_table("player_share_holdings"):
        _create_index_if_missing(
            bind,
            table_name="player_share_holdings",
            index_name="ix_player_share_holdings_user_id_player_id",
            columns=["user_id", "player_id"],
        )

    if inspector.has_table("wallet_transactions"):
        _create_index_if_missing(
            bind,
            table_name="wallet_transactions",
            index_name="ix_wallet_transactions_user_id",
            columns=["user_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    _drop_index_if_present(
        bind,
        table_name="wallet_transactions",
        index_name="ix_wallet_transactions_user_id",
    )
    _drop_index_if_present(
        bind,
        table_name="player_share_holdings",
        index_name="ix_player_share_holdings_user_id_player_id",
    )
    _drop_index_if_present(
        bind,
        table_name="player_share_markets",
        index_name="ix_player_share_markets_player_id",
    )
    _drop_index_if_present(
        bind,
        table_name="players",
        index_name="ix_players_id",
    )
