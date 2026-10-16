"""Add projection worker read models.

Revision ID: 20260327_0047_projection_workers
Revises: 20260327_0046_event_backbone
Create Date: 2026-03-27 11:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0047_projection_workers"
down_revision = "20260327_0046_event_backbone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projection_event_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("projection_name", sa.String(length=96), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("projection_name", "event_id", name="uq_projection_event_receipts_projection_event"),
    )
    op.create_index("ix_projection_event_receipts_projection_name", "projection_event_receipts", ["projection_name"], unique=False)
    op.create_index("ix_projection_event_receipts_event_id", "projection_event_receipts", ["event_id"], unique=False)
    op.create_index("ix_projection_event_receipts_event_type", "projection_event_receipts", ["event_type"], unique=False)
    op.create_index("ix_projection_event_receipts_aggregate_id", "projection_event_receipts", ["aggregate_id"], unique=False)

    op.create_table(
        "competition_standing_projections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("competition_id", sa.String(length=64), nullable=False),
        sa.Column("season_id", sa.String(length=64), nullable=True),
        sa.Column("competition_type", sa.String(length=32), nullable=True),
        sa.Column("club_id", sa.String(length=64), nullable=False),
        sa.Column("club_name", sa.String(length=160), nullable=False),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goal_difference", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_fixture_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "competition_id",
            "club_id",
            name="uq_competition_standing_projections_competition_club",
        ),
    )
    op.create_index("ix_competition_standing_projections_competition_id", "competition_standing_projections", ["competition_id"], unique=False)
    op.create_index("ix_competition_standing_projections_season_id", "competition_standing_projections", ["season_id"], unique=False)
    op.create_index("ix_competition_standing_projections_competition_type", "competition_standing_projections", ["competition_type"], unique=False)
    op.create_index("ix_competition_standing_projections_club_id", "competition_standing_projections", ["club_id"], unique=False)
    op.create_index("ix_competition_standing_projections_last_fixture_id", "competition_standing_projections", ["last_fixture_id"], unique=False)

    op.create_table(
        "player_stats_projections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("competition_id", sa.String(length=64), nullable=False),
        sa.Column("season_id", sa.String(length=64), nullable=True),
        sa.Column("competition_type", sa.String(length=32), nullable=True),
        sa.Column("player_id", sa.String(length=64), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("team_name", sa.String(length=160), nullable=False),
        sa.Column("appearances", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutes_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("yellow_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("red_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cumulative_xg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rating_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_fixture_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "competition_id",
            "player_id",
            name="uq_player_stats_projections_competition_player",
        ),
    )
    op.create_index("ix_player_stats_projections_competition_id", "player_stats_projections", ["competition_id"], unique=False)
    op.create_index("ix_player_stats_projections_season_id", "player_stats_projections", ["season_id"], unique=False)
    op.create_index("ix_player_stats_projections_competition_type", "player_stats_projections", ["competition_type"], unique=False)
    op.create_index("ix_player_stats_projections_player_id", "player_stats_projections", ["player_id"], unique=False)
    op.create_index("ix_player_stats_projections_team_id", "player_stats_projections", ["team_id"], unique=False)
    op.create_index("ix_player_stats_projections_last_fixture_id", "player_stats_projections", ["last_fixture_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_stats_projections_last_fixture_id", table_name="player_stats_projections")
    op.drop_index("ix_player_stats_projections_team_id", table_name="player_stats_projections")
    op.drop_index("ix_player_stats_projections_player_id", table_name="player_stats_projections")
    op.drop_index("ix_player_stats_projections_competition_type", table_name="player_stats_projections")
    op.drop_index("ix_player_stats_projections_season_id", table_name="player_stats_projections")
    op.drop_index("ix_player_stats_projections_competition_id", table_name="player_stats_projections")
    op.drop_table("player_stats_projections")

    op.drop_index("ix_competition_standing_projections_last_fixture_id", table_name="competition_standing_projections")
    op.drop_index("ix_competition_standing_projections_club_id", table_name="competition_standing_projections")
    op.drop_index("ix_competition_standing_projections_competition_type", table_name="competition_standing_projections")
    op.drop_index("ix_competition_standing_projections_season_id", table_name="competition_standing_projections")
    op.drop_index("ix_competition_standing_projections_competition_id", table_name="competition_standing_projections")
    op.drop_table("competition_standing_projections")

    op.drop_index("ix_projection_event_receipts_aggregate_id", table_name="projection_event_receipts")
    op.drop_index("ix_projection_event_receipts_event_type", table_name="projection_event_receipts")
    op.drop_index("ix_projection_event_receipts_event_id", table_name="projection_event_receipts")
    op.drop_index("ix_projection_event_receipts_projection_name", table_name="projection_event_receipts")
    op.drop_table("projection_event_receipts")
