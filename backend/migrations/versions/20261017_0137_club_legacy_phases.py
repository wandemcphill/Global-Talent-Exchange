"""Club Legacy phases 2-9 tables.

Revision ID: 20261017_0137_club_legacy_phases
Revises: 20261017_0136_club_legacy_foundations
"""

from __future__ import annotations

from alembic import op

revision = "20261017_0137_club_legacy_phases"
down_revision = "20261017_0136_club_legacy_foundations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.club_legacy.models import CLUB_LEGACY_PHASE_TABLES

    bind = op.get_bind()
    for table in CLUB_LEGACY_PHASE_TABLES:
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    from app.club_legacy.models import CLUB_LEGACY_PHASE_TABLES

    bind = op.get_bind()
    for table in reversed(CLUB_LEGACY_PHASE_TABLES):
        table.drop(bind, checkfirst=True)
