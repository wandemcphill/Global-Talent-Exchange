"""Add shared world-date and academy-intake sequence state to owner simulation.

Revision ID: 20261027_0151_owner_world_tick_date
Revises: 20261026_0150_world_clock_and_autonomous_fixtures
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261027_0151_owner_world_tick_date"
down_revision = "20261026_0150_world_clock_and_autonomous_fixtures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "owner_club_states" not in tables:
        return
    columns = {column["name"] for column in inspector.get_columns("owner_club_states")}
    if "last_world_tick_date" not in columns:
        op.add_column(
            "owner_club_states",
            sa.Column("last_world_tick_date", sa.Date(), nullable=True),
        )
    if "academy_intake_sequence" not in columns:
        op.add_column(
            "owner_club_states",
            sa.Column("academy_intake_sequence", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "owner_club_states" not in tables:
        return
    columns = {column["name"] for column in inspector.get_columns("owner_club_states")}
    if "academy_intake_sequence" in columns:
        op.drop_column("owner_club_states", "academy_intake_sequence")
    if "last_world_tick_date" in columns:
        op.drop_column("owner_club_states", "last_world_tick_date")
