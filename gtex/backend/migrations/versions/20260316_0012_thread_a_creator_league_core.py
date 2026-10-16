"""Add Creator League control-plane tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260316_0012"
down_revision = "20260316_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_league_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("league_key", sa.String(length=64), server_default=sa.text("'creator_league'"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("seasons_paused", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("league_format", sa.String(length=64), server_default=sa.text("'double_round_robin'"), nullable=False),
        sa.Column("default_club_count", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("match_frequency_days", sa.Integer(), server_default=sa.text("7"), nullable=False),
        sa.Column("season_duration_days", sa.Integer(), server_default=sa.text("266"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_creator_league_configs"),
        sa.UniqueConstraint("league_key", name="uq_creator_league_configs_league_key"),
    )

    op.create_table(
        "creator_league_tiers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("config_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=96), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("club_count", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("promotion_spots", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("relegation_spots", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["creator_league_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_league_tiers"),
        sa.UniqueConstraint("config_id", "display_order", name="uq_creator_league_tiers_config_order"),
        sa.UniqueConstraint("config_id", "slug", name="uq_creator_league_tiers_config_slug"),
    )
    op.create_index("ix_creator_league_tiers_config_id", "creator_league_tiers", ["config_id"], unique=False)

    op.create_table(
        "creator_league_seasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("config_id", sa.String(length=36), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("match_frequency_days", sa.Integer(), server_default=sa.text("7"), nullable=False),
        sa.Column("season_duration_days", sa.Integer(), server_default=sa.text("266"), nullable=False),
        sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["creator_league_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_league_seasons"),
        sa.UniqueConstraint("config_id", "season_number", name="uq_creator_league_seasons_config_number"),
    )
    op.create_index("ix_creator_league_seasons_config_id", "creator_league_seasons", ["config_id"], unique=False)
    op.create_index("ix_creator_league_seasons_status", "creator_league_seasons", ["status"], unique=False)

    op.create_table(
        "creator_league_season_tiers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("tier_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("competition_name", sa.String(length=160), nullable=False),
        sa.Column("tier_name", sa.String(length=80), nullable=False),
        sa.Column("tier_order", sa.Integer(), nullable=False),
        sa.Column("club_ids_json", sa.JSON(), nullable=False),
        sa.Column("round_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("fixture_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("banner_title", sa.String(length=120), nullable=True),
        sa.Column("banner_subtitle", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_league_season_tiers"),
        sa.UniqueConstraint("season_id", "tier_order", name="uq_creator_league_season_tiers_season_order"),
        sa.UniqueConstraint("competition_id", name="uq_creator_league_season_tiers_competition_id"),
    )
    op.create_index("ix_creator_league_season_tiers_season_id", "creator_league_season_tiers", ["season_id"], unique=False)
    op.create_index("ix_creator_league_season_tiers_tier_id", "creator_league_season_tiers", ["tier_id"], unique=False)
    op.create_index("ix_creator_league_season_tiers_competition_id", "creator_league_season_tiers", ["competition_id"], unique=False)
    op.create_index("ix_creator_league_season_tiers_status", "creator_league_season_tiers", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_creator_league_season_tiers_status", table_name="creator_league_season_tiers")
    op.drop_index("ix_creator_league_season_tiers_competition_id", table_name="creator_league_season_tiers")
    op.drop_index("ix_creator_league_season_tiers_tier_id", table_name="creator_league_season_tiers")
    op.drop_index("ix_creator_league_season_tiers_season_id", table_name="creator_league_season_tiers")
    op.drop_table("creator_league_season_tiers")

    op.drop_index("ix_creator_league_seasons_status", table_name="creator_league_seasons")
    op.drop_index("ix_creator_league_seasons_config_id", table_name="creator_league_seasons")
    op.drop_table("creator_league_seasons")

    op.drop_index("ix_creator_league_tiers_config_id", table_name="creator_league_tiers")
    op.drop_table("creator_league_tiers")

    op.drop_table("creator_league_configs")
