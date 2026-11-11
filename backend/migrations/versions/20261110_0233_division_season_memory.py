"""Remember which league season already moved a club's division.

Revision ID: 20261110_0233_division_season_memory
Revises: 20261110_0232_competition_flag_bearers_and_foundation
Create Date: 2026-11-10 15:40:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261110_0233_division_season_memory"
down_revision = "20261110_0232_competition_flag_bearers_and_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_club_states" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("owner_club_states")}
    if "division_season_ids" not in columns:
        op.add_column(
            "owner_club_states",
            sa.Column("division_season_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_club_states" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("owner_club_states")}
    if "division_season_ids" in columns:
        op.drop_column("owner_club_states", "division_season_ids")
