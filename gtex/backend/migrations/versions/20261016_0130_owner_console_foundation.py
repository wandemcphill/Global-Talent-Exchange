"""Owner Control Center foundation: owner loop state, unified ledger, integrity tables.

Revision ID: 20261016_0130_owner_console_foundation
Revises: 20261013_0129_open_default_launch_flags
"""

from __future__ import annotations

from alembic import op

revision = "20261016_0130_owner_console_foundation"
down_revision = "20261013_0129_open_default_launch_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.owner_console.models import OWNER_CONSOLE_TABLES

    bind = op.get_bind()
    for table in OWNER_CONSOLE_TABLES:
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    from app.owner_console.models import OWNER_CONSOLE_TABLES

    bind = op.get_bind()
    for table in reversed(OWNER_CONSOLE_TABLES):
        table.drop(bind, checkfirst=True)
