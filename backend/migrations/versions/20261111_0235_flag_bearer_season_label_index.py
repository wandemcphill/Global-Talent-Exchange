"""Add the missing season_label index on national team flag bearers.

Revision ID: 20261111_0235_flag_bearer_season_label_index
Revises: 20261110_0234_champions_league_played_matches
Create Date: 2026-11-11 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0235_flag_bearer_season_label_index"
down_revision = "20261110_0234_champions_league_played_matches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "national_team_flag_bearers" not in set(inspector.get_table_names()):
        return
    indexes = {index["name"] for index in inspector.get_indexes("national_team_flag_bearers")}
    if "ix_national_team_flag_bearers_season_label" in indexes:
        return
    op.create_index(
        "ix_national_team_flag_bearers_season_label",
        "national_team_flag_bearers",
        ["season_label"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "national_team_flag_bearers" not in set(inspector.get_table_names()):
        return
    indexes = {index["name"] for index in inspector.get_indexes("national_team_flag_bearers")}
    if "ix_national_team_flag_bearers_season_label" in indexes:
        op.drop_index("ix_national_team_flag_bearers_season_label", table_name="national_team_flag_bearers")
