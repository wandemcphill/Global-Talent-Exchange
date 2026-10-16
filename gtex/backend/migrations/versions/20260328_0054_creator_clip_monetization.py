"""Add creator clip monetization attribution ledger.

Revision ID: 20260328_0054_creator_clip_monetization
Revises: 20260328_0053_thread_c_ai_economy_governor
Create Date: 2026-03-28 08:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0054_creator_clip_monetization"
down_revision = "20260328_0053_thread_c_ai_economy_governor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_clip_revenue_attributions",
        sa.Column("export_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("match_key", sa.String(length=120), nullable=False),
        sa.Column("source_reference", sa.String(length=128), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rpm_per_view", sa.Numeric(18, 4), nullable=False, server_default="0.0020"),
        sa.Column("platform_payout_revenue_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("in_app_ad_revenue_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("sponsored_clip_revenue_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("gross_revenue_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("creator_base_share_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("platform_share_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("growth_pool_share_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("viral_bonus_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("referral_bonus_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("weekly_top_creator_bonus_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("creator_payout_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("growth_pool_retained_credit", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("is_viral", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("wallet_reference", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["export_id"], ["highlight_share_exports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "export_id",
            "source_reference",
            name="uq_creator_clip_revenue_attributions_export_source",
        ),
    )
    op.create_index(
        "ix_creator_clip_revenue_attributions_creator_user_id",
        "creator_clip_revenue_attributions",
        ["creator_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_creator_clip_revenue_attributions_export_id",
        "creator_clip_revenue_attributions",
        ["export_id"],
        unique=False,
    )
    op.create_index(
        "ix_creator_clip_revenue_attributions_match_key",
        "creator_clip_revenue_attributions",
        ["match_key"],
        unique=False,
    )
    op.create_index(
        "ix_creator_clip_revenue_attributions_is_viral",
        "creator_clip_revenue_attributions",
        ["is_viral"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_creator_clip_revenue_attributions_is_viral",
        table_name="creator_clip_revenue_attributions",
    )
    op.drop_index(
        "ix_creator_clip_revenue_attributions_match_key",
        table_name="creator_clip_revenue_attributions",
    )
    op.drop_index(
        "ix_creator_clip_revenue_attributions_export_id",
        table_name="creator_clip_revenue_attributions",
    )
    op.drop_index(
        "ix_creator_clip_revenue_attributions_creator_user_id",
        table_name="creator_clip_revenue_attributions",
    )
    op.drop_table("creator_clip_revenue_attributions")
