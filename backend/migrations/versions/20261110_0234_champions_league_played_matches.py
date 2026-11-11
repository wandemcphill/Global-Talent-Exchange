"""Store Champions League results so match coin does not depend on process memory.

Revision ID: 20261110_0234_champions_league_played_matches
Revises: 20261110_0233_division_season_memory
Create Date: 2026-11-10 18:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261110_0234_champions_league_played_matches"
down_revision = "20261110_0233_division_season_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "champions_league_played_matches" in set(inspector.get_table_names()):
        return
    op.create_table(
        "champions_league_played_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=64), nullable=False),
        sa.Column("match_id", sa.String(length=64), nullable=False),
        sa.Column("home_club_id", sa.String(length=64), nullable=False),
        sa.Column("away_club_id", sa.String(length=64), nullable=False),
        sa.Column("home_goals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("away_goals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage_reached", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("club_user_ids", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("fee_status", sa.String(length=16), nullable=False, server_default="owed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "match_id", name="uq_champions_league_played_matches_season_match"),
    )
    op.create_index(
        "ix_champions_league_played_matches_season_id",
        "champions_league_played_matches",
        ["season_id"],
    )
    op.create_index(
        "ix_champions_league_played_matches_match_id",
        "champions_league_played_matches",
        ["match_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "champions_league_played_matches" in set(inspector.get_table_names()):
        op.drop_table("champions_league_played_matches")
