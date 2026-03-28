"""Add creator marketplace campaigns, offers, participation, and reputation.

Revision ID: 20260328_0058_creator_marketplace
Revises: 20260328_0058_social_graph_follows, 20260328_0058_sponsored_clips
Create Date: 2026-03-28 16:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0058_creator_marketplace"
down_revision = ("20260328_0058_social_graph_follows", "20260328_0058_sponsored_clips")
branch_labels = None
depends_on = None


campaign_payout_type = sa.Enum(
    "fixed",
    "performance",
    name="creator_marketplace_campaign_payout_type",
    native_enum=False,
)
campaign_payout_basis = sa.Enum(
    "views",
    "engagement",
    "conversions",
    name="creator_marketplace_campaign_payout_basis",
    native_enum=False,
)
campaign_status = sa.Enum(
    "draft",
    "open",
    "active",
    "completed",
    "cancelled",
    name="creator_marketplace_campaign_status",
    native_enum=False,
)
offer_status = sa.Enum(
    "pending",
    "accepted",
    "rejected",
    "withdrawn",
    name="creator_marketplace_offer_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    campaign_payout_type.create(bind, checkfirst=True)
    campaign_payout_basis.create(bind, checkfirst=True)
    campaign_status.create(bind, checkfirst=True)
    offer_status.create(bind, checkfirst=True)

    op.create_table(
        "creator_marketplace_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("brand_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("budget", sa.Numeric(20, 4), nullable=False),
        sa.Column("target_formats", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_audience", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("payout_type", campaign_payout_type, nullable=False, server_default="fixed"),
        sa.Column("payout_basis", campaign_payout_basis, nullable=False, server_default="views"),
        sa.Column("payout_rate", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("platform_fee_bps", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("status", campaign_status, nullable=False, server_default="open"),
        sa.ForeignKeyConstraint(["brand_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creator_marketplace_campaigns_brand_id", "creator_marketplace_campaigns", ["brand_id"], unique=False)
    op.create_index("ix_creator_marketplace_campaigns_status", "creator_marketplace_campaigns", ["status"], unique=False)
    op.create_index("ix_creator_marketplace_campaigns_title", "creator_marketplace_campaigns", ["title"], unique=False)

    op.create_table(
        "creator_marketplace_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("proposed_price", sa.Numeric(20, 4), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", offer_status, nullable=False, server_default="pending"),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("match_factors", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["campaign_id"], ["creator_marketplace_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("creator_id", "campaign_id", name="uq_creator_marketplace_offers_creator_campaign"),
    )
    op.create_index("ix_creator_marketplace_offers_campaign_id", "creator_marketplace_offers", ["campaign_id"], unique=False)
    op.create_index("ix_creator_marketplace_offers_creator_id", "creator_marketplace_offers", ["creator_id"], unique=False)
    op.create_index("ix_creator_marketplace_offers_status", "creator_marketplace_offers", ["status"], unique=False)

    op.create_table(
        "creator_marketplace_participations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=True),
        sa.Column("clips_submitted", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("performance_metrics", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("gross_payout", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("payout_earned", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("platform_fee_amount", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("wallet_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("brand_feedback_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("reputation_score_snapshot", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["creator_marketplace_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["creator_marketplace_offers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wallet_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "creator_id",
            "campaign_id",
            name="uq_creator_marketplace_participations_creator_campaign",
        ),
    )
    op.create_index(
        "ix_creator_marketplace_participations_campaign_id",
        "creator_marketplace_participations",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_creator_marketplace_participations_creator_id",
        "creator_marketplace_participations",
        ["creator_id"],
        unique=False,
    )
    op.create_index(
        "ix_creator_marketplace_participations_wallet_transaction_id",
        "creator_marketplace_participations",
        ["wallet_transaction_id"],
        unique=False,
    )

    op.create_table(
        "creator_marketplace_reputation_scores",
        sa.Column("creator_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivery_success_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("campaign_performance_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("brand_feedback_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("completed_campaigns", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["creator_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("creator_id"),
    )
    op.create_index(
        "ix_creator_marketplace_reputation_scores_reputation_score",
        "creator_marketplace_reputation_scores",
        ["reputation_score"],
        unique=False,
    )
    op.create_index(
        "ix_creator_marketplace_reputation_scores_updated_at",
        "creator_marketplace_reputation_scores",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_creator_marketplace_reputation_scores_updated_at",
        table_name="creator_marketplace_reputation_scores",
    )
    op.drop_index(
        "ix_creator_marketplace_reputation_scores_reputation_score",
        table_name="creator_marketplace_reputation_scores",
    )
    op.drop_table("creator_marketplace_reputation_scores")

    op.drop_index(
        "ix_creator_marketplace_participations_wallet_transaction_id",
        table_name="creator_marketplace_participations",
    )
    op.drop_index(
        "ix_creator_marketplace_participations_creator_id",
        table_name="creator_marketplace_participations",
    )
    op.drop_index(
        "ix_creator_marketplace_participations_campaign_id",
        table_name="creator_marketplace_participations",
    )
    op.drop_table("creator_marketplace_participations")

    op.drop_index("ix_creator_marketplace_offers_status", table_name="creator_marketplace_offers")
    op.drop_index("ix_creator_marketplace_offers_creator_id", table_name="creator_marketplace_offers")
    op.drop_index("ix_creator_marketplace_offers_campaign_id", table_name="creator_marketplace_offers")
    op.drop_table("creator_marketplace_offers")

    op.drop_index("ix_creator_marketplace_campaigns_title", table_name="creator_marketplace_campaigns")
    op.drop_index("ix_creator_marketplace_campaigns_status", table_name="creator_marketplace_campaigns")
    op.drop_index("ix_creator_marketplace_campaigns_brand_id", table_name="creator_marketplace_campaigns")
    op.drop_table("creator_marketplace_campaigns")

    bind = op.get_bind()
    offer_status.drop(bind, checkfirst=True)
    campaign_status.drop(bind, checkfirst=True)
    campaign_payout_basis.drop(bind, checkfirst=True)
    campaign_payout_type.drop(bind, checkfirst=True)
