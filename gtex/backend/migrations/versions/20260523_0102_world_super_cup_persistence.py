"""Persist World Super Cup authority snapshots.

Revision ID: 20260523_0102_world_super_cup_persistence
Revises: 20260519_0101_merge_identity_trader_and_club_ranking_heads
Create Date: 2026-05-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260523_0102_world_super_cup_persistence"
down_revision = "20260519_0101_merge_identity_trader_and_club_ranking_heads"
branch_labels = None
depends_on = None


def _id_column() -> sa.Column:
    return sa.Column("id", sa.String(length=36), nullable=False)


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "world_super_cup_tournaments",
        sa.Column("id", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.Column("competition_id", sa.String(length=64), nullable=True),
        sa.Column("tournament_name", sa.String(length=160), nullable=False),
        sa.Column("season_label", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seasons_considered_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("champion_club_id", sa.String(length=64), nullable=True),
        sa.Column("runner_up_club_id", sa.String(length=64), nullable=True),
        sa.Column("ceremony_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_label", name="uq_world_super_cup_tournaments_season_label"),
    )
    op.create_index(
        "ix_world_super_cup_tournaments_status_starts",
        "world_super_cup_tournaments",
        ["status", "starts_at"],
    )
    op.create_index(
        "ix_world_super_cup_tournaments_competition_id",
        "world_super_cup_tournaments",
        ["competition_id"],
    )

    op.create_table(
        "world_super_cup_countdowns",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("tournament_name", sa.String(length=160), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("minutes_until_start", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pause_policy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", name="uq_world_super_cup_countdowns_tournament"),
    )
    op.create_index("ix_world_super_cup_countdowns_tournament_id", "world_super_cup_countdowns", ["tournament_id"])
    op.create_index("ix_world_super_cup_countdowns_starts_at", "world_super_cup_countdowns", ["starts_at"])

    op.create_table(
        "world_super_cup_coefficients",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("ranking", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.String(length=64), nullable=False),
        sa.Column("club_name", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.Column("recent_season_points", sa.Integer(), nullable=False),
        sa.Column("previous_season_points", sa.Integer(), nullable=False),
        sa.Column("winner_seasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("runner_up_seasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "club_id", name="uq_world_super_cup_coefficients_tournament_club"),
    )
    op.create_index("ix_world_super_cup_coefficients_tournament_id", "world_super_cup_coefficients", ["tournament_id"])
    op.create_index("ix_world_super_cup_coefficients_club_id", "world_super_cup_coefficients", ["club_id"])
    op.create_index(
        "ix_world_super_cup_coefficients_tournament_rank",
        "world_super_cup_coefficients",
        ["tournament_id", "ranking"],
    )

    op.create_table(
        "world_super_cup_qualified_clubs",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("qualification_stage", sa.String(length=32), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.String(length=64), nullable=False),
        sa.Column("club_name", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("qualification_path", sa.String(length=64), nullable=False),
        sa.Column("coefficient_points", sa.Integer(), nullable=False),
        sa.Column("regional_seed", sa.Integer(), nullable=False),
        sa.Column("overall_seed", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tournament_id",
            "qualification_stage",
            "club_id",
            name="uq_world_super_cup_qualified_clubs_stage_club",
        ),
    )
    op.create_index(
        "ix_world_super_cup_qualified_clubs_tournament_id",
        "world_super_cup_qualified_clubs",
        ["tournament_id"],
    )
    op.create_index("ix_world_super_cup_qualified_clubs_club_id", "world_super_cup_qualified_clubs", ["club_id"])
    op.create_index(
        "ix_world_super_cup_qualified_clubs_tournament_stage_order",
        "world_super_cup_qualified_clubs",
        ["tournament_id", "qualification_stage", "display_order"],
    )

    op.create_table(
        "world_super_cup_groups",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("group_name", sa.String(length=12), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("club_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "group_name", name="uq_world_super_cup_groups_tournament_group"),
    )
    op.create_index("ix_world_super_cup_groups_tournament_id", "world_super_cup_groups", ["tournament_id"])
    op.create_index(
        "ix_world_super_cup_groups_tournament_order",
        "world_super_cup_groups",
        ["tournament_id", "display_order"],
    )

    op.create_table(
        "world_super_cup_fixtures",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("fixture_id", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("round_name", sa.String(length=32), nullable=True),
        sa.Column("group_name", sa.String(length=12), nullable=True),
        sa.Column("matchday", sa.Integer(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("home_club_id", sa.String(length=64), nullable=False),
        sa.Column("away_club_id", sa.String(length=64), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("winner_club_id", sa.String(length=64), nullable=True),
        sa.Column("decided_by", sa.String(length=32), nullable=True),
        sa.Column("requires_winner", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "fixture_id", name="uq_world_super_cup_fixtures_tournament_fixture"),
    )
    op.create_index("ix_world_super_cup_fixtures_tournament_id", "world_super_cup_fixtures", ["tournament_id"])
    op.create_index("ix_world_super_cup_fixtures_home_club_id", "world_super_cup_fixtures", ["home_club_id"])
    op.create_index("ix_world_super_cup_fixtures_away_club_id", "world_super_cup_fixtures", ["away_club_id"])
    op.create_index("ix_world_super_cup_fixtures_winner_club_id", "world_super_cup_fixtures", ["winner_club_id"])
    op.create_index(
        "ix_world_super_cup_fixtures_tournament_stage",
        "world_super_cup_fixtures",
        ["tournament_id", "stage", "sequence"],
    )
    op.create_index(
        "ix_world_super_cup_fixtures_status_kickoff",
        "world_super_cup_fixtures",
        ["status", "kickoff_at"],
    )

    op.create_table(
        "world_super_cup_standings",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("group_name", sa.String(length=12), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.String(length=64), nullable=False),
        sa.Column("played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goal_difference", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "group_name", "club_id", name="uq_world_super_cup_standings_group_club"),
    )
    op.create_index("ix_world_super_cup_standings_tournament_id", "world_super_cup_standings", ["tournament_id"])
    op.create_index("ix_world_super_cup_standings_club_id", "world_super_cup_standings", ["club_id"])
    op.create_index(
        "ix_world_super_cup_standings_tournament_group_position",
        "world_super_cup_standings",
        ["tournament_id", "group_name", "position"],
    )

    op.create_table(
        "world_super_cup_settlements",
        _id_column(),
        *_timestamps(),
        sa.Column("tournament_id", sa.String(length=64), nullable=False),
        sa.Column("fixture_id", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("winner_club_id", sa.String(length=64), nullable=True),
        sa.Column("decided_by", sa.String(length=32), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["tournament_id"], ["world_super_cup_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_world_super_cup_settlements_idempotency_key"),
    )
    op.create_index("ix_world_super_cup_settlements_tournament_id", "world_super_cup_settlements", ["tournament_id"])
    op.create_index("ix_world_super_cup_settlements_fixture_id", "world_super_cup_settlements", ["fixture_id"])
    op.create_index(
        "ix_world_super_cup_settlements_tournament_fixture",
        "world_super_cup_settlements",
        ["tournament_id", "fixture_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_world_super_cup_settlements_tournament_fixture", table_name="world_super_cup_settlements")
    op.drop_index("ix_world_super_cup_settlements_fixture_id", table_name="world_super_cup_settlements")
    op.drop_index("ix_world_super_cup_settlements_tournament_id", table_name="world_super_cup_settlements")
    op.drop_table("world_super_cup_settlements")

    op.drop_index("ix_world_super_cup_standings_tournament_group_position", table_name="world_super_cup_standings")
    op.drop_index("ix_world_super_cup_standings_club_id", table_name="world_super_cup_standings")
    op.drop_index("ix_world_super_cup_standings_tournament_id", table_name="world_super_cup_standings")
    op.drop_table("world_super_cup_standings")

    op.drop_index("ix_world_super_cup_fixtures_status_kickoff", table_name="world_super_cup_fixtures")
    op.drop_index("ix_world_super_cup_fixtures_tournament_stage", table_name="world_super_cup_fixtures")
    op.drop_index("ix_world_super_cup_fixtures_winner_club_id", table_name="world_super_cup_fixtures")
    op.drop_index("ix_world_super_cup_fixtures_away_club_id", table_name="world_super_cup_fixtures")
    op.drop_index("ix_world_super_cup_fixtures_home_club_id", table_name="world_super_cup_fixtures")
    op.drop_index("ix_world_super_cup_fixtures_tournament_id", table_name="world_super_cup_fixtures")
    op.drop_table("world_super_cup_fixtures")

    op.drop_index("ix_world_super_cup_groups_tournament_order", table_name="world_super_cup_groups")
    op.drop_index("ix_world_super_cup_groups_tournament_id", table_name="world_super_cup_groups")
    op.drop_table("world_super_cup_groups")

    op.drop_index(
        "ix_world_super_cup_qualified_clubs_tournament_stage_order",
        table_name="world_super_cup_qualified_clubs",
    )
    op.drop_index("ix_world_super_cup_qualified_clubs_club_id", table_name="world_super_cup_qualified_clubs")
    op.drop_index("ix_world_super_cup_qualified_clubs_tournament_id", table_name="world_super_cup_qualified_clubs")
    op.drop_table("world_super_cup_qualified_clubs")

    op.drop_index("ix_world_super_cup_coefficients_tournament_rank", table_name="world_super_cup_coefficients")
    op.drop_index("ix_world_super_cup_coefficients_club_id", table_name="world_super_cup_coefficients")
    op.drop_index("ix_world_super_cup_coefficients_tournament_id", table_name="world_super_cup_coefficients")
    op.drop_table("world_super_cup_coefficients")

    op.drop_index("ix_world_super_cup_countdowns_starts_at", table_name="world_super_cup_countdowns")
    op.drop_index("ix_world_super_cup_countdowns_tournament_id", table_name="world_super_cup_countdowns")
    op.drop_table("world_super_cup_countdowns")

    op.drop_index("ix_world_super_cup_tournaments_competition_id", table_name="world_super_cup_tournaments")
    op.drop_index("ix_world_super_cup_tournaments_status_starts", table_name="world_super_cup_tournaments")
    op.drop_table("world_super_cup_tournaments")
