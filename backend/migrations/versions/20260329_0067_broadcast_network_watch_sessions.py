"""Add broadcast watch session ledger.

Revision ID: 20260329_0067_broadcast_network_watch_sessions
Revises: 20260329_0067_merge_global_consistency_heads
Create Date: 2026-03-29 20:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0067_broadcast_network_watch_sessions"
down_revision = "20260329_0067_merge_global_consistency_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broadcast_watch_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=48), nullable=False),
        sa.Column("current_match_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("watched_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("switch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rewarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_broadcast_watch_sessions"),
    )
    op.create_index("ix_broadcast_watch_sessions_user_id", "broadcast_watch_sessions", ["user_id"], unique=False)
    op.create_index("ix_broadcast_watch_sessions_channel_id", "broadcast_watch_sessions", ["channel_id"], unique=False)
    op.create_index("ix_broadcast_watch_sessions_current_match_id", "broadcast_watch_sessions", ["current_match_id"], unique=False)
    op.create_index("ix_broadcast_watch_sessions_status", "broadcast_watch_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_broadcast_watch_sessions_status", table_name="broadcast_watch_sessions")
    op.drop_index("ix_broadcast_watch_sessions_current_match_id", table_name="broadcast_watch_sessions")
    op.drop_index("ix_broadcast_watch_sessions_channel_id", table_name="broadcast_watch_sessions")
    op.drop_index("ix_broadcast_watch_sessions_user_id", table_name="broadcast_watch_sessions")
    op.drop_table("broadcast_watch_sessions")
