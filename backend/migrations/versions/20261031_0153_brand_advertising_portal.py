"""Add advertiser portal, moderation, measurement and music promotion fields.

Revision ID: 20261031_0153_brand_advertising_portal
Revises: 20261031_0152_brand_ad_campaigns
Create Date: 2026-10-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261031_0153_brand_advertising_portal"
down_revision = "20261031_0152_brand_ad_campaigns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_brand_ad_campaigns_valid_placement",
        "brand_ad_campaigns",
        type_="check",
    )
    op.create_check_constraint(
        "ck_brand_ad_campaigns_valid_placement",
        "brand_ad_campaigns",
        "placement IN ('homepage_rail', 'homepage_hero', 'partner_showcase', 'auth_canvas', "
        "'music_track', 'music_artist', 'music_playlist')",
    )
    op.add_column("brand_ad_campaigns", sa.Column("campaign_type", sa.String(length=16), server_default="brand", nullable=False))
    op.add_column("brand_ad_campaigns", sa.Column("status", sa.String(length=16), server_default="draft", nullable=False))
    op.add_column("brand_ad_campaigns", sa.Column("budget_amount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("brand_ad_campaigns", sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False))
    op.add_column("brand_ad_campaigns", sa.Column("pricing_model", sa.String(length=8), server_default="CPM", nullable=False))
    op.add_column("brand_ad_campaigns", sa.Column("unit_price", sa.Numeric(18, 4), server_default="0", nullable=False))
    op.add_column("brand_ad_campaigns", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("music_target_type", sa.String(length=16), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("music_target_id", sa.String(length=160), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("music_title", sa.String(length=180), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("music_artist_name", sa.String(length=160), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("music_playlist_name", sa.String(length=160), nullable=True))
    op.add_column("brand_ad_campaigns", sa.Column("music_genre", sa.String(length=80), nullable=True))
    op.create_foreign_key(
        "fk_brand_ad_campaigns_reviewed_by_user_id_users",
        "brand_ad_campaigns",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_brand_ad_campaigns_valid_campaign_type",
        "brand_ad_campaigns",
        "campaign_type IN ('brand', 'music')",
    )
    op.create_check_constraint(
        "ck_brand_ad_campaigns_valid_status",
        "brand_ad_campaigns",
        "status IN ('draft', 'pending', 'approved', 'rejected', 'paused', 'archived')",
    )
    op.create_check_constraint(
        "ck_brand_ad_campaigns_valid_pricing_model",
        "brand_ad_campaigns",
        "pricing_model IN ('CPM', 'CPC')",
    )
    op.execute(
        "UPDATE brand_ad_campaigns SET status = CASE WHEN is_approved = TRUE THEN 'approved' ELSE 'draft' END"
    )
    op.drop_index("ix_brand_ad_campaigns_delivery", table_name="brand_ad_campaigns")
    op.create_index(
        "ix_brand_ad_campaigns_delivery",
        "brand_ad_campaigns",
        ["placement", "campaign_type", "status", "is_approved", "is_active", "start_at", "end_at"],
        unique=False,
    )
    op.create_index("ix_brand_ad_campaigns_advertiser", "brand_ad_campaigns", ["advertiser_id", "status"])

    op.create_table(
        "brand_advertiser_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=False),
        sa.Column("contact_name", sa.String(length=160), nullable=False),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("billing_email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_brand_advertiser_profiles_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_brand_advertiser_profiles"),
        sa.UniqueConstraint("user_id", name="uq_brand_advertiser_profiles_user"),
    )
    op.create_index("ix_brand_advertiser_profiles_user_id", "brand_advertiser_profiles", ["user_id"], unique=False)

    op.create_table(
        "brand_ad_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=96), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_source", sa.String(length=16), server_default="client", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["brand_ad_campaigns.id"], name="fk_brand_ad_events_campaign_id_brand_ad_campaigns", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_brand_ad_events_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_brand_ad_events"),
        sa.UniqueConstraint("idempotency_key", name="uq_brand_ad_events_idempotency_key"),
    )
    op.create_index("ix_brand_ad_events_campaign_type", "brand_ad_events", ["campaign_id", "event_type"], unique=False)
    op.create_index("ix_brand_ad_events_created_at", "brand_ad_events", ["created_at"], unique=False)

    op.create_table(
        "brand_ad_review_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("from_status", sa.String(length=16), nullable=False),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["brand_ad_campaigns.id"], name="fk_brand_ad_review_events_campaign_id_brand_ad_campaigns", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_brand_ad_review_events_actor_user_id_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_brand_ad_review_events"),
    )
    op.create_index("ix_brand_ad_review_events_campaign", "brand_ad_review_events", ["campaign_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_brand_ad_review_events_campaign", table_name="brand_ad_review_events")
    op.drop_table("brand_ad_review_events")
    op.drop_index("ix_brand_ad_events_created_at", table_name="brand_ad_events")
    op.drop_index("ix_brand_ad_events_campaign_type", table_name="brand_ad_events")
    op.drop_table("brand_ad_events")
    op.drop_index("ix_brand_advertiser_profiles_user_id", table_name="brand_advertiser_profiles")
    op.drop_table("brand_advertiser_profiles")
    op.drop_index("ix_brand_ad_campaigns_advertiser", table_name="brand_ad_campaigns")
    op.drop_index("ix_brand_ad_campaigns_delivery", table_name="brand_ad_campaigns")
    op.create_index(
        "ix_brand_ad_campaigns_delivery",
        "brand_ad_campaigns",
        ["placement", "is_approved", "is_active", "start_at", "end_at"],
        unique=False,
    )
    op.drop_constraint("ck_brand_ad_campaigns_valid_pricing_model", "brand_ad_campaigns", type_="check")
    op.drop_constraint("ck_brand_ad_campaigns_valid_status", "brand_ad_campaigns", type_="check")
    op.drop_constraint("ck_brand_ad_campaigns_valid_campaign_type", "brand_ad_campaigns", type_="check")
    op.drop_constraint("fk_brand_ad_campaigns_reviewed_by_user_id_users", "brand_ad_campaigns", type_="foreignkey")
    for column in (
        "music_genre", "music_playlist_name", "music_artist_name", "music_title", "music_target_id",
        "music_target_type", "archived_at", "review_note", "reviewed_by_user_id", "reviewed_at",
        "submitted_at", "unit_price", "pricing_model", "currency", "budget_amount", "status", "campaign_type",
    ):
        op.drop_column("brand_ad_campaigns", column)
    op.drop_constraint("ck_brand_ad_campaigns_valid_placement", "brand_ad_campaigns", type_="check")
    op.create_check_constraint(
        "ck_brand_ad_campaigns_valid_placement",
        "brand_ad_campaigns",
        "placement IN ('homepage_rail', 'homepage_hero', 'partner_showcase', 'auth_canvas')",
    )
