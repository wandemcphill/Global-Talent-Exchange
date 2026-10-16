"""Add persisted user affinity profiles.

Revision ID: 20260328_0057_user_affinity_profiles
Revises: 20260328_0056_clip_variants
Create Date: 2026-03-28 14:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0057_user_affinity_profiles"
down_revision = "20260328_0056_clip_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_affinity_profiles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("favorite_formats_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("favorite_creators_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("affinity_vector_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("avg_watch_time", sa.Float(), nullable=False, server_default="0"),
        sa.Column("skip_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("session_duration", sa.Float(), nullable=False, server_default="0"),
        sa.Column("engagement_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "ix_user_affinity_profiles_updated_at",
        "user_affinity_profiles",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_affinity_profiles_updated_at", table_name="user_affinity_profiles")
    op.drop_table("user_affinity_profiles")
