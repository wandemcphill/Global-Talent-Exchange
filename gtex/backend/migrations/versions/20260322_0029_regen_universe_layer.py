"""Add regen universe awards, rankings, seasons, and hall of fame layer.

Revision ID: 20260322_0029_regen_universe_layer
Revises: 20260322_0028_real_player_ingestion_layer
Create Date: 2026-03-22 13:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_0029_regen_universe_layer"
down_revision = "20260322_0028_real_player_ingestion_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regen_universe_seasons",
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_number", name="uq_regen_universe_seasons_season_number"),
    )
    op.create_index("ix_regen_universe_seasons_is_active", "regen_universe_seasons", ["is_active"], unique=False)

    op.create_table(
        "regen_universe_awards",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="seasonal"),
        sa.Column("ranking_category", sa.String(length=32), nullable=True),
        sa.Column("eligibility_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_regen_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_regen_universe_awards_code"),
    )
    op.create_index("ix_regen_universe_awards_sort_order", "regen_universe_awards", ["sort_order"], unique=False)

    op.create_table(
        "regen_universe_performance_records",
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("position_group", sa.String(length=32), nullable=False),
        sa.Column("appearances", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutes_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clean_sheets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("matches_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("competition_importance", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("consistency_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("previous_overall_score", sa.Float(), nullable=True),
        sa.Column("improvement_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("forward_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("midfielder_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("defender_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("goalkeeper_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("playmaker_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scorer_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["regen_universe_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "player_id", name="uq_regen_universe_performance_records_season_player"),
    )
    op.create_index("ix_regen_universe_performance_records_player_id", "regen_universe_performance_records", ["player_id"], unique=False)
    op.create_index("ix_regen_universe_performance_records_position_group", "regen_universe_performance_records", ["position_group"], unique=False)
    op.create_index("ix_regen_universe_performance_records_overall_score", "regen_universe_performance_records", ["overall_score"], unique=False)

    op.create_table(
        "regen_universe_ranking_snapshots",
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["regen_universe_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "category", "player_id", name="uq_regen_universe_ranking_snapshots_category_player"),
    )
    op.create_index(
        "ix_regen_universe_ranking_snapshots_season_category_rank",
        "regen_universe_ranking_snapshots",
        ["season_id", "category", "rank"],
        unique=False,
    )
    op.create_index("ix_regen_universe_ranking_snapshots_player_id", "regen_universe_ranking_snapshots", ["player_id"], unique=False)

    op.create_table(
        "regen_universe_award_winners",
        sa.Column("award_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("ranking_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["award_id"], ["regen_universe_awards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["regen_universe_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("award_id", "season_id", "player_id", name="uq_regen_universe_award_winners_award_season_player"),
    )
    op.create_index("ix_regen_universe_award_winners_season_id", "regen_universe_award_winners", ["season_id"], unique=False)
    op.create_index("ix_regen_universe_award_winners_player_id", "regen_universe_award_winners", ["player_id"], unique=False)

    op.create_table(
        "regen_universe_hall_of_fame",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("total_awards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("peak_rank", sa.Integer(), nullable=True),
        sa.Column("seasons_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("legacy_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_regen_universe_hall_of_fame_player_id"),
    )
    op.create_index("ix_regen_universe_hall_of_fame_legacy_score", "regen_universe_hall_of_fame", ["legacy_score"], unique=False)
    op.create_index("ix_regen_universe_hall_of_fame_peak_rank", "regen_universe_hall_of_fame", ["peak_rank"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regen_universe_hall_of_fame_peak_rank", table_name="regen_universe_hall_of_fame")
    op.drop_index("ix_regen_universe_hall_of_fame_legacy_score", table_name="regen_universe_hall_of_fame")
    op.drop_table("regen_universe_hall_of_fame")

    op.drop_index("ix_regen_universe_award_winners_player_id", table_name="regen_universe_award_winners")
    op.drop_index("ix_regen_universe_award_winners_season_id", table_name="regen_universe_award_winners")
    op.drop_table("regen_universe_award_winners")

    op.drop_index("ix_regen_universe_ranking_snapshots_player_id", table_name="regen_universe_ranking_snapshots")
    op.drop_index("ix_regen_universe_ranking_snapshots_season_category_rank", table_name="regen_universe_ranking_snapshots")
    op.drop_table("regen_universe_ranking_snapshots")

    op.drop_index("ix_regen_universe_performance_records_overall_score", table_name="regen_universe_performance_records")
    op.drop_index("ix_regen_universe_performance_records_position_group", table_name="regen_universe_performance_records")
    op.drop_index("ix_regen_universe_performance_records_player_id", table_name="regen_universe_performance_records")
    op.drop_table("regen_universe_performance_records")

    op.drop_index("ix_regen_universe_awards_sort_order", table_name="regen_universe_awards")
    op.drop_table("regen_universe_awards")

    op.drop_index("ix_regen_universe_seasons_is_active", table_name="regen_universe_seasons")
    op.drop_table("regen_universe_seasons")
