"""Add documentary mode, rivalries, youth tournaments, and DNA profiles.

Revision ID: 20260327_0037_regen_universe_documentary_and_dna
Revises: 20260327_0036_live_match_manager_duels
Create Date: 2026-03-27 03:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0037_regen_universe_documentary_and_dna"
down_revision = "20260327_0036_live_match_manager_duels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_players",
        sa.Column("dna_profile", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "player_stories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("chapters", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("narrative_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_stories_player_id"),
    )
    op.create_index("ix_player_stories_player_id", "player_stories", ["player_id"], unique=False)

    op.create_table(
        "player_rivalries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_a_id", sa.String(length=36), nullable=False),
        sa.Column("player_b_id", sa.String(length=36), nullable=False),
        sa.Column("intensity_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("history_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["player_a_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_b_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_a_id", "player_b_id", name="uq_player_rivalries_player_pair"),
    )
    op.create_index("ix_player_rivalries_player_a_id", "player_rivalries", ["player_a_id"], unique=False)
    op.create_index("ix_player_rivalries_player_b_id", "player_rivalries", ["player_b_id"], unique=False)
    op.create_index("ix_player_rivalries_intensity_score", "player_rivalries", ["intensity_score"], unique=False)

    op.create_table(
        "youth_tournaments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("age_limit", sa.String(length=12), nullable=False),
        sa.Column("participants_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rewards_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("fixtures_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("standings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("top_players_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_youth_tournaments_name", "youth_tournaments", ["name"], unique=False)
    op.create_index("ix_youth_tournaments_age_limit", "youth_tournaments", ["age_limit"], unique=False)
    op.create_index("ix_youth_tournaments_start_date", "youth_tournaments", ["start_date"], unique=False)
    op.create_index("ix_youth_tournaments_end_date", "youth_tournaments", ["end_date"], unique=False)
    op.create_index("ix_youth_tournaments_status", "youth_tournaments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_youth_tournaments_status", table_name="youth_tournaments")
    op.drop_index("ix_youth_tournaments_end_date", table_name="youth_tournaments")
    op.drop_index("ix_youth_tournaments_start_date", table_name="youth_tournaments")
    op.drop_index("ix_youth_tournaments_age_limit", table_name="youth_tournaments")
    op.drop_index("ix_youth_tournaments_name", table_name="youth_tournaments")
    op.drop_table("youth_tournaments")

    op.drop_index("ix_player_rivalries_intensity_score", table_name="player_rivalries")
    op.drop_index("ix_player_rivalries_player_b_id", table_name="player_rivalries")
    op.drop_index("ix_player_rivalries_player_a_id", table_name="player_rivalries")
    op.drop_table("player_rivalries")

    op.drop_index("ix_player_stories_player_id", table_name="player_stories")
    op.drop_table("player_stories")

    op.drop_column("ingestion_players", "dna_profile")
