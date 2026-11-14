"""Autonomous staff personalities, Layer A decision records, and GM recruitment assignments.

Revision ID: 20261114_0246_autonomous_staff_and_living_club_decisions
Revises: 20261114_0245_attach_player_traits_and_playstyles
Create Date: 2026-11-14 16:06:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261114_0246_autonomous_staff_and_living_club_decisions"
down_revision = "20261114_0245_attach_player_traits_and_playstyles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.owner_console.models import (
        OwnerRecruitmentAssignment,
        OwnerStaffDecisionRecord,
    )

    bind = op.get_bind()
    for model in (
        OwnerStaffDecisionRecord,
        OwnerRecruitmentAssignment,
    ):
        model.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in (
        "owner_recruitment_assignments",
        "owner_staff_decision_records",
    ):
        if inspector.has_table(table_name):
            op.drop_table(table_name)
