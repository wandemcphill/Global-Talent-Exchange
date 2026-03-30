"""Add competition discovery indexes for GTEX and hosted list routes.

Revision ID: 20260330_0075_competition_discovery_perf_indexes
Revises: 20260330_0074_player_share_market_schema_repair
Create Date: 2026-03-30 09:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260330_0075_competition_discovery_perf_indexes"
down_revision = "20260330_0074_player_share_market_schema_repair"
branch_labels = None
depends_on = None


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _create_index_if_missing(
    bind,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if index_name not in _index_names(bind, table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_present(bind, *, table_name: str, index_name: str) -> None:
    if index_name in _index_names(bind, table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    bind = op.get_bind()
    _create_index_if_missing(
        bind,
        table_name="user_competitions",
        index_name="ix_user_competitions_visibility_created_at",
        columns=["visibility", "created_at"],
    )
    _create_index_if_missing(
        bind,
        table_name="user_competitions",
        index_name="ix_user_competitions_format_visibility_created_at",
        columns=["format", "visibility", "created_at"],
    )
    _create_index_if_missing(
        bind,
        table_name="user_competitions",
        index_name="ix_user_competitions_host_user_id_created_at",
        columns=["host_user_id", "created_at"],
    )
    _create_index_if_missing(
        bind,
        table_name="user_hosted_competitions",
        index_name="ix_user_hosted_competitions_visibility_created_at",
        columns=["visibility", "created_at"],
    )
    _create_index_if_missing(
        bind,
        table_name="user_hosted_competitions",
        index_name="ix_user_hosted_competitions_host_user_id_created_at",
        columns=["host_user_id", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    _drop_index_if_present(
        bind,
        table_name="user_hosted_competitions",
        index_name="ix_user_hosted_competitions_host_user_id_created_at",
    )
    _drop_index_if_present(
        bind,
        table_name="user_hosted_competitions",
        index_name="ix_user_hosted_competitions_visibility_created_at",
    )
    _drop_index_if_present(
        bind,
        table_name="user_competitions",
        index_name="ix_user_competitions_host_user_id_created_at",
    )
    _drop_index_if_present(
        bind,
        table_name="user_competitions",
        index_name="ix_user_competitions_format_visibility_created_at",
    )
    _drop_index_if_present(
        bind,
        table_name="user_competitions",
        index_name="ix_user_competitions_visibility_created_at",
    )
