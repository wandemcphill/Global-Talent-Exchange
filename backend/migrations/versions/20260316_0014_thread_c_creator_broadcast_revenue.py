"""Add creator broadcast, season pass, settlement, and analytics tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260316_0014"
down_revision = "20260316_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_broadcast_mode_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("mode_key", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("min_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("max_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("min_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("max_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_creator_broadcast_mode_configs"),
        sa.UniqueConstraint("mode_key", name="uq_creator_broadcast_mode_configs_mode_key"),
    )
    op.create_index(
        "ix_creator_broadcast_mode_configs_mode_key",
        "creator_broadcast_mode_configs",
        ["mode_key"],
        unique=False,
    )

    op.create_table(
        "creator_broadcast_purchases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("mode_key", sa.String(length=32), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("home_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("away_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_broadcast_purchases"),
        sa.UniqueConstraint("user_id", "match_id", name="uq_creator_broadcast_purchases_user_match"),
    )
    op.create_index("ix_creator_broadcast_purchases_user_id", "creator_broadcast_purchases", ["user_id"], unique=False)
    op.create_index("ix_creator_broadcast_purchases_season_id", "creator_broadcast_purchases", ["season_id"], unique=False)
    op.create_index("ix_creator_broadcast_purchases_competition_id", "creator_broadcast_purchases", ["competition_id"], unique=False)
    op.create_index("ix_creator_broadcast_purchases_match_id", "creator_broadcast_purchases", ["match_id"], unique=False)

    op.create_table(
        "creator_season_passes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("access_scope", sa.String(length=48), server_default=sa.text("'creator_league_only'"), nullable=False),
        sa.Column("price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("creator_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("includes_full_season", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("includes_home_away", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("includes_live_highlights", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_season_passes"),
        sa.UniqueConstraint("user_id", "season_id", "club_id", name="uq_creator_season_passes_user_season_club"),
    )
    op.create_index("ix_creator_season_passes_user_id", "creator_season_passes", ["user_id"], unique=False)
    op.create_index("ix_creator_season_passes_creator_user_id", "creator_season_passes", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_season_passes_season_id", "creator_season_passes", ["season_id"], unique=False)
    op.create_index("ix_creator_season_passes_club_id", "creator_season_passes", ["club_id"], unique=False)

    op.create_table(
        "creator_match_gift_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("gift_label", sa.String(length=80), nullable=False),
        sa.Column("gross_amount_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("creator_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_share_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_match_gift_events"),
    )
    op.create_index("ix_creator_match_gift_events_season_id", "creator_match_gift_events", ["season_id"], unique=False)
    op.create_index("ix_creator_match_gift_events_competition_id", "creator_match_gift_events", ["competition_id"], unique=False)
    op.create_index("ix_creator_match_gift_events_match_id", "creator_match_gift_events", ["match_id"], unique=False)
    op.create_index("ix_creator_match_gift_events_sender_user_id", "creator_match_gift_events", ["sender_user_id"], unique=False)
    op.create_index("ix_creator_match_gift_events_recipient_creator_user_id", "creator_match_gift_events", ["recipient_creator_user_id"], unique=False)
    op.create_index("ix_creator_match_gift_events_club_id", "creator_match_gift_events", ["club_id"], unique=False)

    op.create_table(
        "creator_revenue_settlements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("home_club_id", sa.String(length=36), nullable=False),
        sa.Column("away_club_id", sa.String(length=36), nullable=False),
        sa.Column("ticket_sales_gross_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("ticket_sales_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("ticket_sales_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("video_viewer_revenue_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("video_viewer_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("video_viewer_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("gift_revenue_gross_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("gift_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("gift_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("total_revenue_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("total_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("total_platform_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("home_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("away_creator_share_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["away_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_revenue_settlements"),
        sa.UniqueConstraint("match_id", name="uq_creator_revenue_settlements_match_id"),
    )
    op.create_index("ix_creator_revenue_settlements_season_id", "creator_revenue_settlements", ["season_id"], unique=False)
    op.create_index("ix_creator_revenue_settlements_competition_id", "creator_revenue_settlements", ["competition_id"], unique=False)
    op.create_index("ix_creator_revenue_settlements_match_id", "creator_revenue_settlements", ["match_id"], unique=False)
    op.create_index("ix_creator_revenue_settlements_home_club_id", "creator_revenue_settlements", ["home_club_id"], unique=False)
    op.create_index("ix_creator_revenue_settlements_away_club_id", "creator_revenue_settlements", ["away_club_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_creator_revenue_settlements_away_club_id", table_name="creator_revenue_settlements")
    op.drop_index("ix_creator_revenue_settlements_home_club_id", table_name="creator_revenue_settlements")
    op.drop_index("ix_creator_revenue_settlements_match_id", table_name="creator_revenue_settlements")
    op.drop_index("ix_creator_revenue_settlements_competition_id", table_name="creator_revenue_settlements")
    op.drop_index("ix_creator_revenue_settlements_season_id", table_name="creator_revenue_settlements")
    op.drop_table("creator_revenue_settlements")

    op.drop_index("ix_creator_match_gift_events_club_id", table_name="creator_match_gift_events")
    op.drop_index("ix_creator_match_gift_events_recipient_creator_user_id", table_name="creator_match_gift_events")
    op.drop_index("ix_creator_match_gift_events_sender_user_id", table_name="creator_match_gift_events")
    op.drop_index("ix_creator_match_gift_events_match_id", table_name="creator_match_gift_events")
    op.drop_index("ix_creator_match_gift_events_competition_id", table_name="creator_match_gift_events")
    op.drop_index("ix_creator_match_gift_events_season_id", table_name="creator_match_gift_events")
    op.drop_table("creator_match_gift_events")

    op.drop_index("ix_creator_season_passes_club_id", table_name="creator_season_passes")
    op.drop_index("ix_creator_season_passes_season_id", table_name="creator_season_passes")
    op.drop_index("ix_creator_season_passes_creator_user_id", table_name="creator_season_passes")
    op.drop_index("ix_creator_season_passes_user_id", table_name="creator_season_passes")
    op.drop_table("creator_season_passes")

    op.drop_index("ix_creator_broadcast_purchases_match_id", table_name="creator_broadcast_purchases")
    op.drop_index("ix_creator_broadcast_purchases_competition_id", table_name="creator_broadcast_purchases")
    op.drop_index("ix_creator_broadcast_purchases_season_id", table_name="creator_broadcast_purchases")
    op.drop_index("ix_creator_broadcast_purchases_user_id", table_name="creator_broadcast_purchases")
    op.drop_table("creator_broadcast_purchases")

    op.drop_index("ix_creator_broadcast_mode_configs_mode_key", table_name="creator_broadcast_mode_configs")
    op.drop_table("creator_broadcast_mode_configs")
