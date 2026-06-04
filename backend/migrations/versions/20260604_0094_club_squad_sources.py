"""Add club squad source records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260604_0094_club_squad_sources"
down_revision = "20260603_0093_club_formations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_squad_player_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("morale_score", sa.Float(), nullable=True),
        sa.Column("morale_label", sa.String(length=32), nullable=True),
        sa.Column("morale_trend", sa.String(length=32), nullable=True),
        sa.Column("chemistry_overall_score", sa.Float(), nullable=True),
        sa.Column("chemistry_position_fit", sa.Float(), nullable=True),
        sa.Column("chemistry_team_fit", sa.Float(), nullable=True),
        sa.Column("chemistry_warnings_json", sa.JSON(), nullable=False),
        sa.Column("source_ref", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "player_id", name="uq_club_squad_player_sources_club_player"),
    )
    op.create_index("ix_club_squad_player_sources_club_id", "club_squad_player_sources", ["club_id"], unique=False)
    op.create_index("ix_club_squad_player_sources_player_id", "club_squad_player_sources", ["player_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_club_squad_player_sources_player_id", table_name="club_squad_player_sources")
    op.drop_index("ix_club_squad_player_sources_club_id", table_name="club_squad_player_sources")
    op.drop_table("club_squad_player_sources")
