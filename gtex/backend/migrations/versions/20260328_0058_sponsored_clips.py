"""Add sponsored clip campaigns for feed ad injection.

Revision ID: 20260328_0058_sponsored_clips
Revises: 20260328_0057_user_affinity_profiles
Create Date: 2026-03-28 16:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0058_sponsored_clips"
down_revision = "20260328_0057_user_affinity_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sponsored_clips",
        sa.Column("advertiser_id", sa.String(length=36), nullable=False),
        sa.Column("clip_id", sa.String(length=120), nullable=False),
        sa.Column("budget", sa.Numeric(18, 4), nullable=False),
        sa.Column("bid_cpm", sa.Numeric(18, 4), nullable=False),
        sa.Column("target_formats_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_creators_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_regions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("impressions_served", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_watch_time_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("clip_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sponsored_clips_advertiser_id", "sponsored_clips", ["advertiser_id"], unique=False)
    op.create_index("ix_sponsored_clips_clip_id", "sponsored_clips", ["clip_id"], unique=False)
    op.create_index("ix_sponsored_clips_start_time", "sponsored_clips", ["start_time"], unique=False)
    op.create_index("ix_sponsored_clips_end_time", "sponsored_clips", ["end_time"], unique=False)
    op.create_index("ix_sponsored_clips_is_active", "sponsored_clips", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sponsored_clips_is_active", table_name="sponsored_clips")
    op.drop_index("ix_sponsored_clips_end_time", table_name="sponsored_clips")
    op.drop_index("ix_sponsored_clips_start_time", table_name="sponsored_clips")
    op.drop_index("ix_sponsored_clips_clip_id", table_name="sponsored_clips")
    op.drop_index("ix_sponsored_clips_advertiser_id", table_name="sponsored_clips")
    op.drop_table("sponsored_clips")
