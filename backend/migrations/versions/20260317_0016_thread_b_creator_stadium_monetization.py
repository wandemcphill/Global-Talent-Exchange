"""Add creator stadium monetization tables and settlement breakdown columns."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0016_creator_stadium"
down_revision = "20260317_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_stadium_controls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("control_key", sa.String(length=32), server_default=sa.text("'default'"), nullable=False),
        sa.Column("max_matchday_ticket_price_coin", sa.Numeric(18, 4), server_default=sa.text("25.0000"), nullable=False),
        sa.Column("max_season_pass_price_coin", sa.Numeric(18, 4), server_default=sa.text("120.0000"), nullable=False),
        sa.Column("max_vip_ticket_price_coin", sa.Numeric(18, 4), server_default=sa.text("60.0000"), nullable=False),
        sa.Column("max_stadium_level", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("vip_seat_ratio_bps", sa.Integer(), server_default=sa.text("500"), nullable=False),
        sa.Column("max_in_stadium_ad_slots", sa.Integer(), server_default=sa.text("6"), nullable=False),
        sa.Column("max_sponsor_banner_slots", sa.Integer(), server_default=sa.text("4"), nullable=False),
        sa.Column("ad_placement_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_creator_stadium_controls"),
        sa.UniqueConstraint("control_key", name="uq_creator_stadium_controls_control_key"),
    )

    op.create_table(
        "creator_stadium_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_stadium_id", sa.String(length=36), nullable=True),
        sa.Column("level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("capacity", sa.Integer(), server_default=sa.text("5000"), nullable=False),
        sa.Column("premium_seat_capacity", sa.Integer(), server_default=sa.text("250"), nullable=False),
        sa.Column("visual_upgrade_level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("custom_chant_text", sa.String(length=255), nullable=True),
        sa.Column("custom_visuals_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_stadium_id"], ["club_stadiums.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_stadium_profiles"),
        sa.UniqueConstraint("club_id", name="uq_creator_stadium_profiles_club_id"),
    )
    op.create_index("ix_creator_stadium_profiles_club_id", "creator_stadium_profiles", ["club_id"], unique=False)
    op.create_index("ix_creator_stadium_profiles_creator_user_id", "creator_stadium_profiles", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_stadium_profiles_club_stadium_id", "creator_stadium_profiles", ["club_stadium_id"], unique=False)

    op.create_table(
        "creator_stadium_pricing",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("matchday_ticket_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("season_pass_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("vip_ticket_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("live_video_access_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("stadium_visual_upgrades_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("custom_chants_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("custom_visuals_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_stadium_pricing"),
        sa.UniqueConstraint("season_id", "club_id", name="uq_creator_stadium_pricing_season_club"),
    )
    op.create_index("ix_creator_stadium_pricing_season_id", "creator_stadium_pricing", ["season_id"], unique=False)
    op.create_index("ix_creator_stadium_pricing_club_id", "creator_stadium_pricing", ["club_id"], unique=False)
    op.create_index("ix_creator_stadium_pricing_creator_user_id", "creator_stadium_pricing", ["creator_user_id"], unique=False)

    op.create_table(
        "creator_stadium_ticket_purchases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_type", sa.String(length=24), nullable=False),
        sa.Column("seat_tier", sa.String(length=24), server_default=sa.text("'general'"), nullable=False),
        sa.Column("price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("creator_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("includes_live_video_access", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("includes_premium_seating", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("includes_stadium_visual_upgrades", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("includes_custom_chants", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("includes_custom_visuals", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_stadium_ticket_purchases"),
        sa.UniqueConstraint("user_id", "match_id", name="uq_creator_stadium_ticket_purchases_user_match"),
    )
    op.create_index("ix_creator_stadium_ticket_purchases_user_id", "creator_stadium_ticket_purchases", ["user_id"], unique=False)
    op.create_index("ix_creator_stadium_ticket_purchases_creator_user_id", "creator_stadium_ticket_purchases", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_stadium_ticket_purchases_season_id", "creator_stadium_ticket_purchases", ["season_id"], unique=False)
    op.create_index("ix_creator_stadium_ticket_purchases_competition_id", "creator_stadium_ticket_purchases", ["competition_id"], unique=False)
    op.create_index("ix_creator_stadium_ticket_purchases_match_id", "creator_stadium_ticket_purchases", ["match_id"], unique=False)
    op.create_index("ix_creator_stadium_ticket_purchases_club_id", "creator_stadium_ticket_purchases", ["club_id"], unique=False)

    op.create_table(
        "creator_stadium_placements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("approved_by_admin_user_id", sa.String(length=36), nullable=True),
        sa.Column("placement_type", sa.String(length=24), nullable=False),
        sa.Column("slot_key", sa.String(length=64), nullable=False),
        sa.Column("sponsor_name", sa.String(length=120), nullable=False),
        sa.Column("creative_asset_url", sa.String(length=255), nullable=True),
        sa.Column("copy_text", sa.String(length=255), nullable=True),
        sa.Column("price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("creator_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column("audit_note", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by_admin_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_stadium_placements"),
        sa.UniqueConstraint("match_id", "placement_type", "slot_key", name="uq_creator_stadium_placements_match_slot"),
    )
    op.create_index("ix_creator_stadium_placements_season_id", "creator_stadium_placements", ["season_id"], unique=False)
    op.create_index("ix_creator_stadium_placements_competition_id", "creator_stadium_placements", ["competition_id"], unique=False)
    op.create_index("ix_creator_stadium_placements_match_id", "creator_stadium_placements", ["match_id"], unique=False)
    op.create_index("ix_creator_stadium_placements_club_id", "creator_stadium_placements", ["club_id"], unique=False)
    op.create_index("ix_creator_stadium_placements_creator_user_id", "creator_stadium_placements", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_stadium_placements_approved_by_admin_user_id", "creator_stadium_placements", ["approved_by_admin_user_id"], unique=False)

    with op.batch_alter_table("creator_revenue_settlements") as batch_op:
        batch_op.add_column(sa.Column("stadium_matchday_revenue_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("stadium_matchday_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("stadium_matchday_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("premium_seating_revenue_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("premium_seating_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("premium_seating_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("in_stadium_ads_revenue_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("in_stadium_ads_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("in_stadium_ads_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("sponsor_banner_revenue_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("sponsor_banner_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("sponsor_banner_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("creator_revenue_settlements") as batch_op:
        batch_op.drop_column("sponsor_banner_platform_share_coin")
        batch_op.drop_column("sponsor_banner_creator_share_coin")
        batch_op.drop_column("sponsor_banner_revenue_coin")
        batch_op.drop_column("in_stadium_ads_platform_share_coin")
        batch_op.drop_column("in_stadium_ads_creator_share_coin")
        batch_op.drop_column("in_stadium_ads_revenue_coin")
        batch_op.drop_column("premium_seating_platform_share_coin")
        batch_op.drop_column("premium_seating_creator_share_coin")
        batch_op.drop_column("premium_seating_revenue_coin")
        batch_op.drop_column("stadium_matchday_platform_share_coin")
        batch_op.drop_column("stadium_matchday_creator_share_coin")
        batch_op.drop_column("stadium_matchday_revenue_coin")

    op.drop_index("ix_creator_stadium_placements_approved_by_admin_user_id", table_name="creator_stadium_placements")
    op.drop_index("ix_creator_stadium_placements_creator_user_id", table_name="creator_stadium_placements")
    op.drop_index("ix_creator_stadium_placements_club_id", table_name="creator_stadium_placements")
    op.drop_index("ix_creator_stadium_placements_match_id", table_name="creator_stadium_placements")
    op.drop_index("ix_creator_stadium_placements_competition_id", table_name="creator_stadium_placements")
    op.drop_index("ix_creator_stadium_placements_season_id", table_name="creator_stadium_placements")
    op.drop_table("creator_stadium_placements")

    op.drop_index("ix_creator_stadium_ticket_purchases_club_id", table_name="creator_stadium_ticket_purchases")
    op.drop_index("ix_creator_stadium_ticket_purchases_match_id", table_name="creator_stadium_ticket_purchases")
    op.drop_index("ix_creator_stadium_ticket_purchases_competition_id", table_name="creator_stadium_ticket_purchases")
    op.drop_index("ix_creator_stadium_ticket_purchases_season_id", table_name="creator_stadium_ticket_purchases")
    op.drop_index("ix_creator_stadium_ticket_purchases_creator_user_id", table_name="creator_stadium_ticket_purchases")
    op.drop_index("ix_creator_stadium_ticket_purchases_user_id", table_name="creator_stadium_ticket_purchases")
    op.drop_table("creator_stadium_ticket_purchases")

    op.drop_index("ix_creator_stadium_pricing_creator_user_id", table_name="creator_stadium_pricing")
    op.drop_index("ix_creator_stadium_pricing_club_id", table_name="creator_stadium_pricing")
    op.drop_index("ix_creator_stadium_pricing_season_id", table_name="creator_stadium_pricing")
    op.drop_table("creator_stadium_pricing")

    op.drop_index("ix_creator_stadium_profiles_club_stadium_id", table_name="creator_stadium_profiles")
    op.drop_index("ix_creator_stadium_profiles_creator_user_id", table_name="creator_stadium_profiles")
    op.drop_index("ix_creator_stadium_profiles_club_id", table_name="creator_stadium_profiles")
    op.drop_table("creator_stadium_profiles")

    op.drop_table("creator_stadium_controls")
