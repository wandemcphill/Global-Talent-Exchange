"""Add regen ecosystem academy, scouting, events, agents, and voting tables.

Revision ID: 20260327_0037_regen_ecosystem_foundation
Revises: 20260327_0036_live_match_manager_duels
Create Date: 2026-03-27 03:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0037_regen_ecosystem_foundation"
down_revision = "20260327_0036_live_match_manager_duels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "youth_academies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("scouting_regions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default=sa.text("6")),
        sa.Column("upgrade_cost", sa.Integer(), nullable=False, server_default=sa.text("100000")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_user_id", name="uq_youth_academies_club_user_id"),
    )
    op.create_index("ix_youth_academies_club_id", "youth_academies", ["club_id"], unique=False)

    op.create_table(
        "regen_scouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=False),
        sa.Column("skill_rating", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("specialty", sa.String(length=48), nullable=False, server_default=sa.text("'youth'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_scouts_club_user_id", "regen_scouts", ["club_user_id"], unique=False)
    op.create_index("ix_regen_scouts_club_id", "regen_scouts", ["club_id"], unique=False)
    op.create_index("ix_regen_scouts_region", "regen_scouts", ["region"], unique=False)

    op.create_table(
        "regen_attribute_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("visible_stats_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("hidden_stats_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("personality_state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("injury_risk", sa.Float(), nullable=False, server_default=sa.text("20.0")),
        sa.Column("injury_history_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rarity_tier", sa.String(length=24), nullable=False, server_default=sa.text("'common'")),
        sa.Column("uniqueness_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("badge_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("market_value_coin", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_potential_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_regen_attribute_profiles_player_id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_regen_attribute_profiles_regen_profile_id"),
    )
    op.create_index("ix_regen_attribute_profiles_rarity_tier", "regen_attribute_profiles", ["rarity_tier"], unique=False)
    op.create_index("ix_regen_attribute_profiles_market_value_coin", "regen_attribute_profiles", ["market_value_coin"], unique=False)

    op.create_table(
        "regen_bloodline_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("parent_legacy_id", sa.String(length=36), nullable=True),
        sa.Column("lineage_depth", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["parent_legacy_id"], ["regen_legacy_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_regen_bloodline_links_regen_profile_id"),
    )
    op.create_index("ix_regen_bloodline_links_parent_legacy_id", "regen_bloodline_links", ["parent_legacy_id"], unique=False)

    op.create_table(
        "career_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("type", sa.String(length=48), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("impact_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_career_events_player_id", "career_events", ["player_id"], unique=False)
    op.create_index("ix_career_events_regen_profile_id", "career_events", ["regen_profile_id"], unique=False)
    op.create_index("ix_career_events_type", "career_events", ["type"], unique=False)
    op.create_index("ix_career_events_occurred_on", "career_events", ["occurred_on"], unique=False)

    op.create_table(
        "regen_agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("negotiation_skill", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("player_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_agents_name", "regen_agents", ["name"], unique=False)

    op.create_table(
        "regen_award_votes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("award_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("voted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["award_id"], ["regen_universe_awards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["regen_universe_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "player_id", "award_id", "season_id", name="uq_regen_award_votes_scope"),
    )
    op.create_index("ix_regen_award_votes_award_id", "regen_award_votes", ["award_id"], unique=False)
    op.create_index("ix_regen_award_votes_player_id", "regen_award_votes", ["player_id"], unique=False)
    op.create_index("ix_regen_award_votes_season_id", "regen_award_votes", ["season_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regen_award_votes_season_id", table_name="regen_award_votes")
    op.drop_index("ix_regen_award_votes_player_id", table_name="regen_award_votes")
    op.drop_index("ix_regen_award_votes_award_id", table_name="regen_award_votes")
    op.drop_table("regen_award_votes")

    op.drop_index("ix_regen_agents_name", table_name="regen_agents")
    op.drop_table("regen_agents")

    op.drop_index("ix_career_events_occurred_on", table_name="career_events")
    op.drop_index("ix_career_events_type", table_name="career_events")
    op.drop_index("ix_career_events_regen_profile_id", table_name="career_events")
    op.drop_index("ix_career_events_player_id", table_name="career_events")
    op.drop_table("career_events")

    op.drop_index("ix_regen_bloodline_links_parent_legacy_id", table_name="regen_bloodline_links")
    op.drop_table("regen_bloodline_links")

    op.drop_index("ix_regen_attribute_profiles_market_value_coin", table_name="regen_attribute_profiles")
    op.drop_index("ix_regen_attribute_profiles_rarity_tier", table_name="regen_attribute_profiles")
    op.drop_table("regen_attribute_profiles")

    op.drop_index("ix_regen_scouts_region", table_name="regen_scouts")
    op.drop_index("ix_regen_scouts_club_id", table_name="regen_scouts")
    op.drop_index("ix_regen_scouts_club_user_id", table_name="regen_scouts")
    op.drop_table("regen_scouts")

    op.drop_index("ix_youth_academies_club_id", table_name="youth_academies")
    op.drop_table("youth_academies")
