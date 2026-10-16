"""Add generic tournament engine tables.

Revision ID: 20260329_0060_tournament_engine
Revises: 20260328_0059_agent_state_persistence
Create Date: 2026-03-29 08:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0060_tournament_engine"
down_revision = "20260328_0059_agent_state_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tournaments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("game_type", sa.String(length=24), nullable=False),
        sa.Column("entry_fee", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_players", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="registration"),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("current_round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prize_pool", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("round_timeout_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tournaments_status", "tournaments", ["status"], unique=False)
    op.create_index("ix_tournaments_winner_user_id", "tournaments", ["winner_user_id"], unique=False)

    op.create_table(
        "tournament_players",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("bracket_slot", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="registered"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("entry_transaction_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_tournament_players_tournament_user"),
        sa.UniqueConstraint("tournament_id", "bracket_slot", name="uq_tournament_players_tournament_slot"),
    )
    op.create_index("ix_tournament_players_tournament_id", "tournament_players", ["tournament_id"], unique=False)
    op.create_index("ix_tournament_players_user_id", "tournament_players", ["user_id"], unique=False)
    op.create_index("ix_tournament_players_status", "tournament_players", ["status"], unique=False)
    op.create_index("ix_tournament_players_entry_transaction_id", "tournament_players", ["entry_transaction_id"], unique=False)

    op.create_table(
        "tournament_rounds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("timeout_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "round_number", name="uq_tournament_rounds_tournament_round"),
    )
    op.create_index("ix_tournament_rounds_tournament_id", "tournament_rounds", ["tournament_id"], unique=False)
    op.create_index("ix_tournament_rounds_status", "tournament_rounds", ["status"], unique=False)

    op.create_table(
        "tournament_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("round_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("player_one_user_id", sa.String(length=36), nullable=True),
        sa.Column("player_two_user_id", sa.String(length=36), nullable=True),
        sa.Column("winner_user_id", sa.String(length=36), nullable=True),
        sa.Column("player_one_score", sa.Integer(), nullable=True),
        sa.Column("player_two_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("resolution", sa.String(length=24), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["round_id"], ["tournament_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_one_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_two_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "round_number", "slot_index", name="uq_tournament_matches_round_slot"),
    )
    op.create_index("ix_tournament_matches_tournament_id", "tournament_matches", ["tournament_id"], unique=False)
    op.create_index("ix_tournament_matches_round_id", "tournament_matches", ["round_id"], unique=False)
    op.create_index("ix_tournament_matches_round_number", "tournament_matches", ["round_number"], unique=False)
    op.create_index("ix_tournament_matches_player_one_user_id", "tournament_matches", ["player_one_user_id"], unique=False)
    op.create_index("ix_tournament_matches_player_two_user_id", "tournament_matches", ["player_two_user_id"], unique=False)
    op.create_index("ix_tournament_matches_winner_user_id", "tournament_matches", ["winner_user_id"], unique=False)
    op.create_index("ix_tournament_matches_status", "tournament_matches", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tournament_matches_status", table_name="tournament_matches")
    op.drop_index("ix_tournament_matches_winner_user_id", table_name="tournament_matches")
    op.drop_index("ix_tournament_matches_player_two_user_id", table_name="tournament_matches")
    op.drop_index("ix_tournament_matches_player_one_user_id", table_name="tournament_matches")
    op.drop_index("ix_tournament_matches_round_number", table_name="tournament_matches")
    op.drop_index("ix_tournament_matches_round_id", table_name="tournament_matches")
    op.drop_index("ix_tournament_matches_tournament_id", table_name="tournament_matches")
    op.drop_table("tournament_matches")

    op.drop_index("ix_tournament_rounds_status", table_name="tournament_rounds")
    op.drop_index("ix_tournament_rounds_tournament_id", table_name="tournament_rounds")
    op.drop_table("tournament_rounds")

    op.drop_index("ix_tournament_players_entry_transaction_id", table_name="tournament_players")
    op.drop_index("ix_tournament_players_status", table_name="tournament_players")
    op.drop_index("ix_tournament_players_user_id", table_name="tournament_players")
    op.drop_index("ix_tournament_players_tournament_id", table_name="tournament_players")
    op.drop_table("tournament_players")

    op.drop_index("ix_tournaments_winner_user_id", table_name="tournaments")
    op.drop_index("ix_tournaments_status", table_name="tournaments")
    op.drop_table("tournaments")
