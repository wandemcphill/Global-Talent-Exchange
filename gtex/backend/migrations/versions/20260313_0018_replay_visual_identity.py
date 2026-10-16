"""Add visual identity payload to replay archive records."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260313_0018"
down_revision = "20260313_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("replay_archive_records", sa.Column("visual_identity_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("replay_archive_records", "visual_identity_json")
