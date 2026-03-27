"""Add live spectating, highlights, and manager duel persistence.

Revision ID: 20260327_0036_live_match_manager_duels
Revises: 20260326_0035_merge_parallel_feature_heads
Create Date: 2026-03-27 02:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0036_live_match_manager_duels"
down_revision = "20260326_0035_merge_parallel_feature_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spectator_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "user_id", name="uq_spectator_sessions_match_user"),
    )
    op.create_index("ix_spectator_sessions_match_id", "spectator_sessions", ["match_id"], unique=False)
    op.create_index("ix_spectator_sessions_user_id", "spectator_sessions", ["user_id"], unique=False)

    op.create_table(
        "highlight_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_highlight_events_match_id", "highlight_events", ["match_id"], unique=False)
    op.create_index("ix_highlight_events_minute", "highlight_events", ["minute"], unique=False)
    op.create_index("ix_highlight_events_type", "highlight_events", ["type"], unique=False)

    op.create_table(
        "manager_duels",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("competition_type", sa.String(length=32), nullable=False, server_default=sa.text("'manager_duel'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("home_user_id", sa.String(length=36), nullable=False),
        sa.Column("away_user_id", sa.String(length=36), nullable=False),
        sa.Column("home_manager_id", sa.String(length=120), nullable=False),
        sa.Column("away_manager_id", sa.String(length=120), nullable=False),
        sa.Column("home_manager_name", sa.String(length=160), nullable=False),
        sa.Column("away_manager_name", sa.String(length=160), nullable=False),
        sa.Column("home_manager_source", sa.String(length=24), nullable=False, server_default=sa.text("'hired'")),
        sa.Column("away_manager_source", sa.String(length=24), nullable=False, server_default=sa.text("'hired'")),
        sa.Column("home_manager_asset_id", sa.String(length=36), nullable=True),
        sa.Column("away_manager_asset_id", sa.String(length=36), nullable=True),
        sa.Column("controller_home", sa.String(length=24), nullable=False, server_default=sa.text("'manager'")),
        sa.Column("controller_away", sa.String(length=24), nullable=False, server_default=sa.text("'manager'")),
        sa.Column("user_control_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("away_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winner_manager_id", sa.String(length=120), nullable=True),
        sa.Column("winner_user_id", sa.String(length=36), nullable=True),
        sa.Column("reputation_delta_home", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("reputation_delta_away", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["away_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manager_duels_competition_type", "manager_duels", ["competition_type"], unique=False)
    op.create_index("ix_manager_duels_status", "manager_duels", ["status"], unique=False)
    op.create_index("ix_manager_duels_home_user_id", "manager_duels", ["home_user_id"], unique=False)
    op.create_index("ix_manager_duels_away_user_id", "manager_duels", ["away_user_id"], unique=False)
    op.create_index("ix_manager_duels_home_manager_id", "manager_duels", ["home_manager_id"], unique=False)
    op.create_index("ix_manager_duels_away_manager_id", "manager_duels", ["away_manager_id"], unique=False)
    op.create_index("ix_manager_duels_home_manager_asset_id", "manager_duels", ["home_manager_asset_id"], unique=False)
    op.create_index("ix_manager_duels_away_manager_asset_id", "manager_duels", ["away_manager_asset_id"], unique=False)
    op.create_index("ix_manager_duels_winner_manager_id", "manager_duels", ["winner_manager_id"], unique=False)
    op.create_index("ix_manager_duels_winner_user_id", "manager_duels", ["winner_user_id"], unique=False)

    op.create_table(
        "manager_duel_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("manager_key", sa.String(length=160), nullable=False),
        sa.Column("manager_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default=sa.text("100")),
        sa.Column("duel_wins", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duel_draws", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duel_losses", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_duel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manager_key"),
    )
    op.create_index("ix_manager_duel_profiles_manager_key", "manager_duel_profiles", ["manager_key"], unique=True)
    op.create_index("ix_manager_duel_profiles_manager_id", "manager_duel_profiles", ["manager_id"], unique=False)
    op.create_index("ix_manager_duel_profiles_owner_user_id", "manager_duel_profiles", ["owner_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_manager_duel_profiles_owner_user_id", table_name="manager_duel_profiles")
    op.drop_index("ix_manager_duel_profiles_manager_id", table_name="manager_duel_profiles")
    op.drop_index("ix_manager_duel_profiles_manager_key", table_name="manager_duel_profiles")
    op.drop_table("manager_duel_profiles")

    op.drop_index("ix_manager_duels_winner_user_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_winner_manager_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_away_manager_asset_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_home_manager_asset_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_away_manager_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_home_manager_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_away_user_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_home_user_id", table_name="manager_duels")
    op.drop_index("ix_manager_duels_status", table_name="manager_duels")
    op.drop_index("ix_manager_duels_competition_type", table_name="manager_duels")
    op.drop_table("manager_duels")

    op.drop_index("ix_highlight_events_type", table_name="highlight_events")
    op.drop_index("ix_highlight_events_minute", table_name="highlight_events")
    op.drop_index("ix_highlight_events_match_id", table_name="highlight_events")
    op.drop_table("highlight_events")

    op.drop_index("ix_spectator_sessions_user_id", table_name="spectator_sessions")
    op.drop_index("ix_spectator_sessions_match_id", table_name="spectator_sessions")
    op.drop_table("spectator_sessions")
