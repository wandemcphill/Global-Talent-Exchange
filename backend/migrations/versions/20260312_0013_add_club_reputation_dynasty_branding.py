"""Add club reputation extension, dynasty, branding, jersey, and cosmetic tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0013"
down_revision = "20260312_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_name", sa.String(length=120), nullable=False),
        sa.Column("short_name", sa.String(length=40), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("crest_asset_ref", sa.String(length=255), nullable=True),
        sa.Column("primary_color", sa.String(length=16), nullable=False),
        sa.Column("secondary_color", sa.String(length=16), nullable=False),
        sa.Column("accent_color", sa.String(length=16), nullable=False),
        sa.Column("home_venue_name", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=16), server_default=sa.text("'public'"), nullable=False),
        sa.Column("founded_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_profiles"),
        sa.UniqueConstraint("slug", name="uq_club_profiles_slug"),
    )
    op.create_index("ix_club_profiles_owner_user_id", "club_profiles", ["owner_user_id"], unique=False)
    op.create_index("ix_club_profiles_slug", "club_profiles", ["slug"], unique=False)

    op.create_table(
        "club_trophy_cabinets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("featured_trophy_id", sa.String(length=36), nullable=True),
        sa.Column("display_theme_code", sa.String(length=64), nullable=True),
        sa.Column("showcase_order_json", sa.JSON(), nullable=False),
        sa.Column("total_trophies", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_trophy_cabinets"),
        sa.UniqueConstraint("club_id", name="uq_club_trophy_cabinets_club_id"),
    )
    op.create_index("ix_club_trophy_cabinets_club_id", "club_trophy_cabinets", ["club_id"], unique=False)

    op.create_table(
        "club_trophies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("trophy_type", sa.String(length=48), nullable=False),
        sa.Column("trophy_name", sa.String(length=120), nullable=False),
        sa.Column("competition_source", sa.String(length=120), nullable=False),
        sa.Column("competition_id", sa.String(length=64), nullable=True),
        sa.Column("season_label", sa.String(length=80), nullable=False),
        sa.Column("campaign_label", sa.String(length=80), nullable=True),
        sa.Column("prestige_weight", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_trophies"),
    )
    op.create_index("ix_club_trophies_club_id", "club_trophies", ["club_id"], unique=False)
    op.create_index("ix_club_trophies_trophy_type", "club_trophies", ["trophy_type"], unique=False)
    op.create_index("ix_club_trophies_season_label", "club_trophies", ["season_label"], unique=False)

    op.create_table(
        "club_dynasty_progress",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("dynasty_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("dynasty_level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("dynasty_title", sa.String(length=64), server_default=sa.text("'Foundations'"), nullable=False),
        sa.Column("seasons_completed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("consecutive_top_finishes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("participation_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("trophy_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("community_prestige_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_loyalty_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("creator_legacy_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_season_label", sa.String(length=80), nullable=True),
        sa.Column("showcase_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_dynasty_progress"),
        sa.UniqueConstraint("club_id", name="uq_club_dynasty_progress_club_id"),
    )
    op.create_index("ix_club_dynasty_progress_club_id", "club_dynasty_progress", ["club_id"], unique=False)

    op.create_table(
        "club_dynasty_milestones",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("milestone_type", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("required_value", sa.Integer(), nullable=False),
        sa.Column("progress_value", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("dynasty_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_unlocked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_dynasty_milestones"),
        sa.UniqueConstraint(
            "club_id",
            "milestone_type",
            "required_value",
            name="uq_club_dynasty_milestones_club_type_required",
        ),
    )
    op.create_index("ix_club_dynasty_milestones_club_id", "club_dynasty_milestones", ["club_id"], unique=False)
    op.create_index(
        "ix_club_dynasty_milestones_milestone_type",
        "club_dynasty_milestones",
        ["milestone_type"],
        unique=False,
    )

    op.create_table(
        "club_branding_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=48), nullable=False),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("asset_ref", sa.String(length=255), nullable=True),
        sa.Column("catalog_item_id", sa.String(length=36), nullable=True),
        sa.Column("slot_key", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("moderation_status", sa.String(length=24), server_default=sa.text("'approved'"), nullable=False),
        sa.Column("moderation_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_branding_assets"),
    )
    op.create_index("ix_club_branding_assets_club_id", "club_branding_assets", ["club_id"], unique=False)
    op.create_index("ix_club_branding_assets_asset_type", "club_branding_assets", ["asset_type"], unique=False)
    op.create_index("ix_club_branding_assets_catalog_item_id", "club_branding_assets", ["catalog_item_id"], unique=False)

    op.create_table(
        "club_jersey_designs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slot_type", sa.String(length=16), nullable=False),
        sa.Column("base_template_id", sa.String(length=64), nullable=False),
        sa.Column("primary_color", sa.String(length=16), nullable=False),
        sa.Column("secondary_color", sa.String(length=16), nullable=False),
        sa.Column("trim_color", sa.String(length=16), nullable=False),
        sa.Column("sleeve_style", sa.String(length=32), nullable=True),
        sa.Column("motto_text", sa.String(length=80), nullable=True),
        sa.Column("number_style", sa.String(length=32), nullable=True),
        sa.Column("crest_placement", sa.String(length=32), server_default=sa.text("'left_chest'"), nullable=False),
        sa.Column("preview_asset_ref", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("moderation_status", sa.String(length=24), server_default=sa.text("'approved'"), nullable=False),
        sa.Column("moderation_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_jersey_designs"),
    )
    op.create_index("ix_club_jersey_designs_club_id", "club_jersey_designs", ["club_id"], unique=False)
    op.create_index("ix_club_jersey_designs_slot_type", "club_jersey_designs", ["slot_type"], unique=False)

    op.create_table(
        "club_cosmetic_catalog_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("purchase_type", sa.String(length=48), nullable=False),
        sa.Column("asset_type", sa.String(length=48), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("service_fee_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("moderation_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_club_cosmetic_catalog_items"),
        sa.UniqueConstraint("sku", name="uq_club_cosmetic_catalog_items_sku"),
    )
    op.create_index("ix_club_cosmetic_catalog_items_sku", "club_cosmetic_catalog_items", ["sku"], unique=False)
    op.create_index(
        "ix_club_cosmetic_catalog_items_purchase_type",
        "club_cosmetic_catalog_items",
        ["purchase_type"],
        unique=False,
    )

    op.create_table(
        "club_cosmetic_purchases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("purchase_ref", sa.String(length=72), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_user_id", sa.String(length=36), nullable=False),
        sa.Column("catalog_item_id", sa.String(length=36), nullable=False),
        sa.Column("purchase_type", sa.String(length=48), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'completed'"), nullable=False),
        sa.Column("review_status", sa.String(length=24), server_default=sa.text("'clear'"), nullable=False),
        sa.Column("review_notes", sa.String(length=255), nullable=True),
        sa.Column("payment_reference", sa.String(length=128), nullable=True),
        sa.Column("fraud_flagged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["club_cosmetic_catalog_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_cosmetic_purchases"),
        sa.UniqueConstraint("purchase_ref", name="uq_club_cosmetic_purchases_purchase_ref"),
    )
    op.create_index("ix_club_cosmetic_purchases_purchase_ref", "club_cosmetic_purchases", ["purchase_ref"], unique=False)
    op.create_index("ix_club_cosmetic_purchases_club_id", "club_cosmetic_purchases", ["club_id"], unique=False)
    op.create_index("ix_club_cosmetic_purchases_buyer_user_id", "club_cosmetic_purchases", ["buyer_user_id"], unique=False)
    op.create_index("ix_club_cosmetic_purchases_catalog_item_id", "club_cosmetic_purchases", ["catalog_item_id"], unique=False)

    op.create_table(
        "club_identity_themes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("header_asset_ref", sa.String(length=255), nullable=True),
        sa.Column("backdrop_asset_ref", sa.String(length=255), nullable=True),
        sa.Column("cabinet_theme_code", sa.String(length=64), nullable=True),
        sa.Column("frame_code", sa.String(length=64), nullable=True),
        sa.Column("visibility", sa.String(length=16), server_default=sa.text("'public'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_identity_themes"),
    )
    op.create_index("ix_club_identity_themes_club_id", "club_identity_themes", ["club_id"], unique=False)

    op.create_table(
        "club_showcase_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_key", sa.String(length=80), nullable=False),
        sa.Column("reputation_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("dynasty_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("featured_trophy_id", sa.String(length=36), nullable=True),
        sa.Column("theme_name", sa.String(length=120), nullable=True),
        sa.Column("showcase_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_showcase_snapshots"),
        sa.UniqueConstraint("snapshot_key", name="uq_club_showcase_snapshots_snapshot_key"),
    )
    op.create_index("ix_club_showcase_snapshots_club_id", "club_showcase_snapshots", ["club_id"], unique=False)
    op.create_index("ix_club_showcase_snapshots_snapshot_key", "club_showcase_snapshots", ["snapshot_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_club_showcase_snapshots_snapshot_key", table_name="club_showcase_snapshots")
    op.drop_index("ix_club_showcase_snapshots_club_id", table_name="club_showcase_snapshots")
    op.drop_table("club_showcase_snapshots")

    op.drop_index("ix_club_identity_themes_club_id", table_name="club_identity_themes")
    op.drop_table("club_identity_themes")

    op.drop_index("ix_club_cosmetic_purchases_catalog_item_id", table_name="club_cosmetic_purchases")
    op.drop_index("ix_club_cosmetic_purchases_buyer_user_id", table_name="club_cosmetic_purchases")
    op.drop_index("ix_club_cosmetic_purchases_club_id", table_name="club_cosmetic_purchases")
    op.drop_index("ix_club_cosmetic_purchases_purchase_ref", table_name="club_cosmetic_purchases")
    op.drop_table("club_cosmetic_purchases")

    op.drop_index("ix_club_cosmetic_catalog_items_purchase_type", table_name="club_cosmetic_catalog_items")
    op.drop_index("ix_club_cosmetic_catalog_items_sku", table_name="club_cosmetic_catalog_items")
    op.drop_table("club_cosmetic_catalog_items")

    op.drop_index("ix_club_jersey_designs_slot_type", table_name="club_jersey_designs")
    op.drop_index("ix_club_jersey_designs_club_id", table_name="club_jersey_designs")
    op.drop_table("club_jersey_designs")

    op.drop_index("ix_club_branding_assets_catalog_item_id", table_name="club_branding_assets")
    op.drop_index("ix_club_branding_assets_asset_type", table_name="club_branding_assets")
    op.drop_index("ix_club_branding_assets_club_id", table_name="club_branding_assets")
    op.drop_table("club_branding_assets")

    op.drop_index("ix_club_dynasty_milestones_milestone_type", table_name="club_dynasty_milestones")
    op.drop_index("ix_club_dynasty_milestones_club_id", table_name="club_dynasty_milestones")
    op.drop_table("club_dynasty_milestones")

    op.drop_index("ix_club_dynasty_progress_club_id", table_name="club_dynasty_progress")
    op.drop_table("club_dynasty_progress")

    op.drop_index("ix_club_trophies_season_label", table_name="club_trophies")
    op.drop_index("ix_club_trophies_trophy_type", table_name="club_trophies")
    op.drop_index("ix_club_trophies_club_id", table_name="club_trophies")
    op.drop_table("club_trophies")

    op.drop_index("ix_club_trophy_cabinets_club_id", table_name="club_trophy_cabinets")
    op.drop_table("club_trophy_cabinets")

    op.drop_index("ix_club_profiles_slug", table_name="club_profiles")
    op.drop_index("ix_club_profiles_owner_user_id", table_name="club_profiles")
    op.drop_table("club_profiles")
