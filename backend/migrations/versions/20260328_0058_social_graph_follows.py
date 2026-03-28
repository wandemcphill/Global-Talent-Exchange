"""Add persisted social graph follows.

Revision ID: 20260328_0058_social_graph_follows
Revises: 20260328_0057_user_affinity_profiles
Create Date: 2026-03-28 17:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0058_social_graph_follows"
down_revision = "20260328_0057_user_affinity_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "follows",
        sa.Column("follower_id", sa.String(length=36), nullable=False),
        sa.Column("following_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["following_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("follower_id", "following_id"),
    )
    op.create_index(
        "ix_follows_follower_id_created_at",
        "follows",
        ["follower_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_follows_following_id_created_at",
        "follows",
        ["following_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_follows_following_id_created_at", table_name="follows")
    op.drop_index("ix_follows_follower_id_created_at", table_name="follows")
    op.drop_table("follows")
