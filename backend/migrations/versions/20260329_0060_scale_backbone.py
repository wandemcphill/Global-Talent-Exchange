"""Add durable scale backbone projections and caches.

Revision ID: 20260329_0060_scale_backbone
Revises: 20260328_0059_agent_state_persistence
Create Date: 2026-03-29 08:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0060_scale_backbone"
down_revision = "20260328_0059_agent_state_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orchestrator_clip_states",
        sa.Column("clip_id", sa.String(length=255), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False, server_default="test"),
        sa.Column("allocated_impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("velocity_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_ad", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_moment", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("bid_weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("age_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("base_clip_id", sa.String(length=255), nullable=True),
        sa.Column("winner_variant_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("clip_id"),
    )
    op.create_index(
        "ix_orchestrator_clip_states_stage_updated_at",
        "orchestrator_clip_states",
        ["stage", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_orchestrator_clip_states_base_clip_id",
        "orchestrator_clip_states",
        ["base_clip_id"],
        unique=False,
    )

    op.create_table(
        "orchestrator_configs",
        sa.Column("config_key", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("config_key"),
    )

    op.create_table(
        "viral_leaderboard_entries",
        sa.Column("clip_id", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("clip_id"),
    )
    op.create_index(
        "ix_viral_leaderboard_entries_score_clip_id",
        "viral_leaderboard_entries",
        ["score", "clip_id"],
        unique=False,
    )

    op.create_table(
        "personalized_feed_cache_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("clip_id", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_key", "clip_id", name="uq_personalized_feed_cache_entries_subject_clip"),
    )
    op.create_index(
        "ix_personalized_feed_cache_entries_subject_position",
        "personalized_feed_cache_entries",
        ["subject_key", "position"],
        unique=False,
    )
    op.create_index(
        "ix_personalized_feed_cache_entries_subject_score",
        "personalized_feed_cache_entries",
        ["subject_key", "score"],
        unique=False,
    )

    op.create_table(
        "personalized_feed_history_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_key", sa.String(length=128), nullable=False),
        sa.Column("clip_id", sa.String(length=255), nullable=False),
        sa.Column("creator_key", sa.String(length=255), nullable=True),
        sa.Column("format_key", sa.String(length=255), nullable=True),
        sa.Column("similarity_key", sa.String(length=255), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_personalized_feed_history_entries_subject_served_at",
        "personalized_feed_history_entries",
        ["subject_key", "served_at"],
        unique=False,
    )

    op.create_table(
        "personalized_feed_seen_clips",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("clip_id", sa.String(length=255), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "clip_id"),
    )
    op.create_index(
        "ix_personalized_feed_seen_clips_user_seen_at",
        "personalized_feed_seen_clips",
        ["user_id", "seen_at"],
        unique=False,
    )

    op.create_table(
        "viral_dispatch_pool_entries",
        sa.Column("clip_id", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("clip_id"),
    )
    op.create_index(
        "ix_viral_dispatch_pool_entries_score_created_at",
        "viral_dispatch_pool_entries",
        ["score", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_viral_dispatch_pool_entries_expires_at",
        "viral_dispatch_pool_entries",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "creator_clip_earnings_projections",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("generated_clip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monetized_clip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_gross_revenue_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_creator_payout_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_platform_share_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_growth_pool_retained_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_viral_bonus_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_referral_bonus_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total_weekly_top_creator_bonus_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("viral_clip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wallet_balance_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("wallet_available_credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("wallet_currency", sa.String(length=16), nullable=False, server_default="CREDIT"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("creator_clip_earnings_projections")

    op.drop_index("ix_viral_dispatch_pool_entries_expires_at", table_name="viral_dispatch_pool_entries")
    op.drop_index("ix_viral_dispatch_pool_entries_score_created_at", table_name="viral_dispatch_pool_entries")
    op.drop_table("viral_dispatch_pool_entries")

    op.drop_index("ix_personalized_feed_seen_clips_user_seen_at", table_name="personalized_feed_seen_clips")
    op.drop_table("personalized_feed_seen_clips")

    op.drop_index("ix_personalized_feed_history_entries_subject_served_at", table_name="personalized_feed_history_entries")
    op.drop_table("personalized_feed_history_entries")

    op.drop_index("ix_personalized_feed_cache_entries_subject_score", table_name="personalized_feed_cache_entries")
    op.drop_index("ix_personalized_feed_cache_entries_subject_position", table_name="personalized_feed_cache_entries")
    op.drop_table("personalized_feed_cache_entries")

    op.drop_index("ix_viral_leaderboard_entries_score_clip_id", table_name="viral_leaderboard_entries")
    op.drop_table("viral_leaderboard_entries")

    op.drop_table("orchestrator_configs")

    op.drop_index("ix_orchestrator_clip_states_base_clip_id", table_name="orchestrator_clip_states")
    op.drop_index("ix_orchestrator_clip_states_stage_updated_at", table_name="orchestrator_clip_states")
    op.drop_table("orchestrator_clip_states")
