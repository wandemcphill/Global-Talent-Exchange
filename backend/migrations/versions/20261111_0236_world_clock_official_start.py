"""Record that the game clock has an official start.

Revision ID: 20261111_0236_world_clock_official_start
Revises: 20261111_0235_paystack_deposit_reference_lock
Create Date: 2026-11-11 13:40:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0236_world_clock_official_start"
down_revision = "20261111_0235_paystack_deposit_reference_lock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "world_clock_state" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("world_clock_state")}
    if "officially_started" in columns:
        return
    op.add_column(
        "world_clock_state",
        sa.Column("officially_started", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "world_clock_state" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("world_clock_state")}
    if "officially_started" not in columns:
        return
    op.drop_column("world_clock_state", "officially_started")
