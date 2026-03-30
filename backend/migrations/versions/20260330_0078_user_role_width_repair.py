"""Repair users.role width for modern admin role values.

Revision ID: 20260330_0078_user_role_width_repair
Revises: 20260330_0077_merge_runtime_schema_heads
Create Date: 2026-03-30 11:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260330_0078_user_role_width_repair"
down_revision = "20260330_0077_merge_runtime_schema_heads"
branch_labels = None
depends_on = None

TARGET_ROLE_LENGTH = 32


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    columns = {column["name"]: column for column in inspector.get_columns("users")}
    role_column = columns.get("role")
    if role_column is None:
        return

    existing_type = role_column.get("type")
    existing_length = getattr(existing_type, "length", None)
    if existing_length is not None and existing_length >= TARGET_ROLE_LENGTH:
        return

    with op.batch_alter_table("users", recreate="auto") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=existing_type or sa.String(length=existing_length or 5),
            type_=sa.String(length=TARGET_ROLE_LENGTH),
            existing_nullable=role_column.get("nullable", False),
        )


def downgrade() -> None:
    return None
