"""Club Legacy phase 1: continent, delegation tables, and a disabled feature flag.

Revision ID: 20261017_0136_club_legacy_foundations
Revises: 20261017_0135_owner_console_foundation
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261017_0136_club_legacy_foundations"
down_revision = "20261017_0135_owner_console_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("club_profiles", sa.Column("continent_code", sa.String(length=2), nullable=True))
    from app.club_legacy.models import CLUB_LEGACY_TABLES

    bind = op.get_bind()
    for table in CLUB_LEGACY_TABLES:
        table.create(bind, checkfirst=True)

    from sqlalchemy.orm import Session

    from app.admin_engine.service import AdminEngineService
    from app.club_legacy.geography import backfill_missing_continents

    session = Session(bind=bind)
    try:
        backfill_missing_continents(session)
        AdminEngineService(session)._seed_feature_flags()
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    from app.club_legacy.models import CLUB_LEGACY_TABLES

    bind = op.get_bind()
    for table in reversed(CLUB_LEGACY_TABLES):
        table.drop(bind, checkfirst=True)
    op.drop_column("club_profiles", "continent_code")
