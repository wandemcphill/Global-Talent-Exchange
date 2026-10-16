"""Add persisted auth sessions for refresh-token rotation and logout revocation.

Revision ID: 20260401_0080_auth_session_rebuild
Revises: 20260401_0079_history_engagement_schema_repair
Create Date: 2026-04-01 14:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260401_0080_auth_session_rebuild"
down_revision = "20260401_0079_history_engagement_schema_repair"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


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


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revocation_reason", sa.String(length=120), nullable=True),
            sa.Column("device_id", sa.String(length=120), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing(
        bind,
        table_name="auth_sessions",
        index_name=op.f("ix_auth_sessions_expires_at"),
        columns=["expires_at"],
    )
    _create_index_if_missing(
        bind,
        table_name="auth_sessions",
        index_name=op.f("ix_auth_sessions_revoked_at"),
        columns=["revoked_at"],
    )
    _create_index_if_missing(
        bind,
        table_name="auth_sessions",
        index_name=op.f("ix_auth_sessions_user_id"),
        columns=["user_id"],
    )
    _create_index_if_missing(
        bind,
        table_name="auth_sessions",
        index_name="ix_auth_sessions_user_id_expires_at",
        columns=["user_id", "expires_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "auth_sessions"):
        return

    existing_indexes = _index_names(bind, "auth_sessions")
    for index_name in (
        "ix_auth_sessions_user_id_expires_at",
        op.f("ix_auth_sessions_user_id"),
        op.f("ix_auth_sessions_revoked_at"),
        op.f("ix_auth_sessions_expires_at"),
    ):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="auth_sessions")
    op.drop_table("auth_sessions")
