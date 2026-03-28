"""Add leaderboard seasons, ratings, snapshots, and rewards.

Revision ID: 20260328_0055_leaderboards_seasons
Revises: 20260328_0054_creator_clip_monetization, 20260328_0053_thread_de_risk_social_core
Create Date: 2026-03-28 09:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0055_leaderboards_seasons"
down_revision = ("20260328_0054_creator_clip_monetization", "20260328_0053_thread_de_risk_social_core")
branch_labels = None
depends_on = None


leaderboard_season_status = sa.Enum(
    "active",
    "ended",
    name="leaderboard_season_status",
    native_enum=False,
)

leaderboard_reset_strategy = sa.Enum(
    "hard",
    "soft",
    name="leaderboard_reset_strategy",
    native_enum=False,
)

leaderboard_reward_delivery_status = sa.Enum(
    "pending",
    "distributed",
    "failed",
    name="leaderboard_reward_delivery_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    leaderboard_season_status.create(bind, checkfirst=True)
    leaderboard_reset_strategy.create(bind, checkfirst=True)
    leaderboard_reward_delivery_status.create(bind, checkfirst=True)

    op.create_table(
        "leaderboard_seasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", leaderboard_season_status, nullable=False, server_default="active"),
        sa.Column("default_rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("k_factor", sa.Integer(), nullable=False, server_default="32"),
        sa.Column("reset_strategy", leaderboard_reset_strategy, nullable=False, server_default="soft"),
        sa.Column("soft_reset_factor", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rewards_distributed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leaderboard_seasons_start_date", "leaderboard_seasons", ["start_date"], unique=False)
    op.create_index("ix_leaderboard_seasons_end_date", "leaderboard_seasons", ["end_date"], unique=False)
    op.create_index(
        "ix_leaderboard_seasons_status_dates",
        "leaderboard_seasons",
        ["status", "start_date", "end_date"],
        unique=False,
    )

    op.create_table(
        "leaderboard_player_ratings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=True),
        sa.Column("division", sa.String(length=32), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("highest_rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("last_rating_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_match_id", sa.String(length=128), nullable=True),
        sa.Column("last_result", sa.Float(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "player_id", name="uq_leaderboard_player_ratings_season_player"),
    )
    op.create_index("ix_leaderboard_player_ratings_season_id", "leaderboard_player_ratings", ["season_id"], unique=False)
    op.create_index("ix_leaderboard_player_ratings_player_id", "leaderboard_player_ratings", ["player_id"], unique=False)
    op.create_index("ix_leaderboard_player_ratings_region", "leaderboard_player_ratings", ["region"], unique=False)
    op.create_index("ix_leaderboard_player_ratings_division", "leaderboard_player_ratings", ["division"], unique=False)
    op.create_index(
        "ix_leaderboard_player_ratings_season_rating",
        "leaderboard_player_ratings",
        ["season_id", "rating"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_player_ratings_season_region",
        "leaderboard_player_ratings",
        ["season_id", "region"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_player_ratings_season_division",
        "leaderboard_player_ratings",
        ["season_id", "division"],
        unique=False,
    )

    op.create_table(
        "leaderboard_match_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=128), nullable=False),
        sa.Column("source_event_id", sa.String(length=64), nullable=True),
        sa.Column("player_a_id", sa.String(length=64), nullable=False),
        sa.Column("player_b_id", sa.String(length=64), nullable=False),
        sa.Column("result", sa.Float(), nullable=False),
        sa.Column("player_a_rating_before", sa.Integer(), nullable=False),
        sa.Column("player_b_rating_before", sa.Integer(), nullable=False),
        sa.Column("player_a_rating_after", sa.Integer(), nullable=False),
        sa.Column("player_b_rating_after", sa.Integer(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "match_id", name="uq_leaderboard_match_results_season_match"),
        sa.UniqueConstraint("source_event_id", name="uq_leaderboard_match_results_source_event"),
    )
    op.create_index("ix_leaderboard_match_results_season_id", "leaderboard_match_results", ["season_id"], unique=False)
    op.create_index("ix_leaderboard_match_results_match_id", "leaderboard_match_results", ["match_id"], unique=False)
    op.create_index(
        "ix_leaderboard_match_results_source_event_id",
        "leaderboard_match_results",
        ["source_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_match_results_processed_at",
        "leaderboard_match_results",
        ["processed_at"],
        unique=False,
    )
    op.create_index("ix_leaderboard_match_results_player_a_id", "leaderboard_match_results", ["player_a_id"], unique=False)
    op.create_index("ix_leaderboard_match_results_player_b_id", "leaderboard_match_results", ["player_b_id"], unique=False)

    op.create_table(
        "leaderboard_season_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("board_key", sa.String(length=96), nullable=False),
        sa.Column("player_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=True),
        sa.Column("division", sa.String(length=32), nullable=True),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "board_key", "player_id", name="uq_leaderboard_season_snapshots_board_player"),
    )
    op.create_index("ix_leaderboard_season_snapshots_season_id", "leaderboard_season_snapshots", ["season_id"], unique=False)
    op.create_index("ix_leaderboard_season_snapshots_board_key", "leaderboard_season_snapshots", ["board_key"], unique=False)
    op.create_index("ix_leaderboard_season_snapshots_player_id", "leaderboard_season_snapshots", ["player_id"], unique=False)
    op.create_index("ix_leaderboard_season_snapshots_region", "leaderboard_season_snapshots", ["region"], unique=False)
    op.create_index("ix_leaderboard_season_snapshots_division", "leaderboard_season_snapshots", ["division"], unique=False)
    op.create_index(
        "ix_leaderboard_season_snapshots_captured_at",
        "leaderboard_season_snapshots",
        ["captured_at"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_season_snapshots_season_board_rank",
        "leaderboard_season_snapshots",
        ["season_id", "board_key", "rank_position"],
        unique=False,
    )

    op.create_table(
        "leaderboard_season_rewards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("board_key", sa.String(length=96), nullable=False, server_default="global"),
        sa.Column("player_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("coins", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("trophies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("badges_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("status", leaderboard_reward_delivery_status, nullable=False, server_default="pending"),
        sa.Column("distributed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["season_id"], ["leaderboard_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "board_key", "player_id", name="uq_leaderboard_season_rewards_board_player"),
    )
    op.create_index("ix_leaderboard_season_rewards_season_id", "leaderboard_season_rewards", ["season_id"], unique=False)
    op.create_index("ix_leaderboard_season_rewards_player_id", "leaderboard_season_rewards", ["player_id"], unique=False)
    op.create_index(
        "ix_leaderboard_season_rewards_ledger_transaction_id",
        "leaderboard_season_rewards",
        ["ledger_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_leaderboard_season_rewards_season_rank",
        "leaderboard_season_rewards",
        ["season_id", "board_key", "rank_position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leaderboard_season_rewards_season_rank", table_name="leaderboard_season_rewards")
    op.drop_index("ix_leaderboard_season_rewards_ledger_transaction_id", table_name="leaderboard_season_rewards")
    op.drop_index("ix_leaderboard_season_rewards_player_id", table_name="leaderboard_season_rewards")
    op.drop_index("ix_leaderboard_season_rewards_season_id", table_name="leaderboard_season_rewards")
    op.drop_table("leaderboard_season_rewards")

    op.drop_index("ix_leaderboard_season_snapshots_season_board_rank", table_name="leaderboard_season_snapshots")
    op.drop_index("ix_leaderboard_season_snapshots_captured_at", table_name="leaderboard_season_snapshots")
    op.drop_index("ix_leaderboard_season_snapshots_division", table_name="leaderboard_season_snapshots")
    op.drop_index("ix_leaderboard_season_snapshots_region", table_name="leaderboard_season_snapshots")
    op.drop_index("ix_leaderboard_season_snapshots_player_id", table_name="leaderboard_season_snapshots")
    op.drop_index("ix_leaderboard_season_snapshots_board_key", table_name="leaderboard_season_snapshots")
    op.drop_index("ix_leaderboard_season_snapshots_season_id", table_name="leaderboard_season_snapshots")
    op.drop_table("leaderboard_season_snapshots")

    op.drop_index("ix_leaderboard_match_results_player_b_id", table_name="leaderboard_match_results")
    op.drop_index("ix_leaderboard_match_results_player_a_id", table_name="leaderboard_match_results")
    op.drop_index("ix_leaderboard_match_results_processed_at", table_name="leaderboard_match_results")
    op.drop_index("ix_leaderboard_match_results_source_event_id", table_name="leaderboard_match_results")
    op.drop_index("ix_leaderboard_match_results_match_id", table_name="leaderboard_match_results")
    op.drop_index("ix_leaderboard_match_results_season_id", table_name="leaderboard_match_results")
    op.drop_table("leaderboard_match_results")

    op.drop_index("ix_leaderboard_player_ratings_season_division", table_name="leaderboard_player_ratings")
    op.drop_index("ix_leaderboard_player_ratings_season_region", table_name="leaderboard_player_ratings")
    op.drop_index("ix_leaderboard_player_ratings_season_rating", table_name="leaderboard_player_ratings")
    op.drop_index("ix_leaderboard_player_ratings_division", table_name="leaderboard_player_ratings")
    op.drop_index("ix_leaderboard_player_ratings_region", table_name="leaderboard_player_ratings")
    op.drop_index("ix_leaderboard_player_ratings_player_id", table_name="leaderboard_player_ratings")
    op.drop_index("ix_leaderboard_player_ratings_season_id", table_name="leaderboard_player_ratings")
    op.drop_table("leaderboard_player_ratings")

    op.drop_index("ix_leaderboard_seasons_status_dates", table_name="leaderboard_seasons")
    op.drop_index("ix_leaderboard_seasons_end_date", table_name="leaderboard_seasons")
    op.drop_index("ix_leaderboard_seasons_start_date", table_name="leaderboard_seasons")
    op.drop_table("leaderboard_seasons")

    bind = op.get_bind()
    leaderboard_reward_delivery_status.drop(bind, checkfirst=True)
    leaderboard_reset_strategy.drop(bind, checkfirst=True)
    leaderboard_season_status.drop(bind, checkfirst=True)
