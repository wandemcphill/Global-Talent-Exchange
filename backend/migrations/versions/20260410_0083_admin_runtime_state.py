"""Create admin runtime state table for DB-backed admin controls.

Revision ID: 20260410_0083_admin_runtime_state
Revises: 20260402_0082_scaling_layer_indexes
Create Date: 2026-04-10 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260410_0083_admin_runtime_state"
down_revision = "20260402_0082_scaling_layer_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("admin_runtime_states"):
        return

    op.create_table(
        "admin_runtime_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state_key", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_runtime_states")),
        sa.UniqueConstraint("state_key", name=op.f("uq_admin_runtime_states_state_key")),
    )
    op.create_index(
        op.f("ix_admin_runtime_states_state_key"),
        "admin_runtime_states",
        ["state_key"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("admin_runtime_states"):
        return

    op.drop_index(op.f("ix_admin_runtime_states_state_key"), table_name="admin_runtime_states")
    op.drop_table("admin_runtime_states")
