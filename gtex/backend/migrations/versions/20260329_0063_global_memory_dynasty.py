"""Add global memory persistence, regen evolution, and dynasty tracking.

Revision ID: 20260329_0063_global_memory_dynasty
Revises: 20260329_0062_national_team_competition_engine_entries
Create Date: 2026-03-29 12:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0063_global_memory_dynasty"
down_revision = "20260329_0062_national_team_competition_engine_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("competition", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_history_player_id", "player_history", ["player_id"], unique=False)

    op.create_table(
        "user_dynasty",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("total_titles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("youth_titles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("senior_titles", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_dynasty_user_id"),
    )
    op.create_index("ix_user_dynasty_user_id", "user_dynasty", ["user_id"], unique=False)

    op.create_table(
        "global_competition_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="entered"),
        sa.Column("performance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("title_awarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "competition_id",
            "player_id",
            name="uq_global_competition_entries_user_competition_player",
        ),
    )
    op.create_index(
        "ix_global_competition_entries_user_id",
        "global_competition_entries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_global_competition_entries_competition_id",
        "global_competition_entries",
        ["competition_id"],
        unique=False,
    )
    op.create_index(
        "ix_global_competition_entries_player_id",
        "global_competition_entries",
        ["player_id"],
        unique=False,
    )

    op.create_table(
        "global_player_rentals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("rental_fee_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("performance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "competition_id",
            "player_id",
            name="uq_global_player_rentals_user_competition_player",
        ),
    )
    op.create_index("ix_global_player_rentals_user_id", "global_player_rentals", ["user_id"], unique=False)
    op.create_index(
        "ix_global_player_rentals_competition_id",
        "global_player_rentals",
        ["competition_id"],
        unique=False,
    )
    op.create_index("ix_global_player_rentals_player_id", "global_player_rentals", ["player_id"], unique=False)

    op.create_table(
        "global_regen_evolution",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("regen_type", sa.String(length=32), nullable=False, server_default="academy"),
        sa.Column("performance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("performance_threshold", sa.Float(), nullable=False, server_default="80.0"),
        sa.Column("title_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_gsi", sa.Integer(), nullable=True),
        sa.Column("is_tradable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_unique", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hall_of_fame", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_evolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_global_regen_evolution_player_id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_global_regen_evolution_regen_profile_id"),
    )
    op.create_index("ix_global_regen_evolution_player_id", "global_regen_evolution", ["player_id"], unique=False)
    op.create_index(
        "ix_global_regen_evolution_regen_profile_id",
        "global_regen_evolution",
        ["regen_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_global_regen_evolution_regen_profile_id", table_name="global_regen_evolution")
    op.drop_index("ix_global_regen_evolution_player_id", table_name="global_regen_evolution")
    op.drop_table("global_regen_evolution")

    op.drop_index("ix_global_player_rentals_player_id", table_name="global_player_rentals")
    op.drop_index("ix_global_player_rentals_competition_id", table_name="global_player_rentals")
    op.drop_index("ix_global_player_rentals_user_id", table_name="global_player_rentals")
    op.drop_table("global_player_rentals")

    op.drop_index("ix_global_competition_entries_player_id", table_name="global_competition_entries")
    op.drop_index("ix_global_competition_entries_competition_id", table_name="global_competition_entries")
    op.drop_index("ix_global_competition_entries_user_id", table_name="global_competition_entries")
    op.drop_table("global_competition_entries")

    op.drop_index("ix_user_dynasty_user_id", table_name="user_dynasty")
    op.drop_table("user_dynasty")

    op.drop_index("ix_player_history_player_id", table_name="player_history")
    op.drop_table("player_history")
