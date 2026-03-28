"""Add clip variants for viral format competition.

Revision ID: 20260328_0056_clip_variants
Revises: 20260328_0055_leaderboards_seasons
Create Date: 2026-03-28 11:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0056_clip_variants"
down_revision = "20260328_0055_leaderboards_seasons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clip_variants",
        sa.Column("variant_id", sa.String(length=160), nullable=False),
        sa.Column("base_clip_id", sa.String(length=160), nullable=False),
        sa.Column("format_type", sa.String(length=32), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watch_time", sa.Float(), nullable=False, server_default="0"),
        sa.Column("loop_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("drop_off_point_seconds", sa.Float(), nullable=True),
        sa.Column("share_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("comment_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("viral_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("distribution_weight", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("promotion_status", sa.String(length=24), nullable=False, server_default="exploring"),
        sa.Column("promotion_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pushed_to_trending", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("winner_selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("variant_id"),
        sa.UniqueConstraint("base_clip_id", "format_type", name="uq_clip_variants_base_clip_format"),
    )
    op.create_index("ix_clip_variants_base_clip_id", "clip_variants", ["base_clip_id"], unique=False)
    op.create_index(
        "ix_clip_variants_base_clip_created_at",
        "clip_variants",
        ["base_clip_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_clip_variants_base_clip_viral_score",
        "clip_variants",
        ["base_clip_id", "viral_score"],
        unique=False,
    )
    op.create_index(
        "ix_clip_variants_base_clip_winner",
        "clip_variants",
        ["base_clip_id", "is_winner"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_clip_variants_base_clip_winner", table_name="clip_variants")
    op.drop_index("ix_clip_variants_base_clip_viral_score", table_name="clip_variants")
    op.drop_index("ix_clip_variants_base_clip_created_at", table_name="clip_variants")
    op.drop_index("ix_clip_variants_base_clip_id", table_name="clip_variants")
    op.drop_table("clip_variants")
