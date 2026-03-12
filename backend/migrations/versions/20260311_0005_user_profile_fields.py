"""Add optional user profile fields for the auth current-user API."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260311_0005"
down_revision = "20260311_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("avatar_url", sa.String(length=2048), nullable=True))
        batch_op.add_column(sa.Column("favourite_club", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("nationality", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("preferred_position", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("preferred_position")
        batch_op.drop_column("nationality")
        batch_op.drop_column("favourite_club")
        batch_op.drop_column("avatar_url")
