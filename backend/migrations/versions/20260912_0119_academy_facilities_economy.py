"""Phase 6E: Academy and facilities economic fields.

Revision ID: 20260912_0119_academy_facilities_economy
Revises: 20260911_0118_released_share_supply

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260912_0119_academy_facilities_economy"
down_revision = "20260911_0118_released_share_supply"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "club_facilities",
        sa.Column("youth_recruitment_level", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "club_facilities",
        sa.Column("in_progress_upgrades_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "club_facilities",
        sa.Column("facility_effects_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "academy_profiles",
        sa.Column("capacity_limit", sa.Integer(), nullable=False, server_default="15"),
    )


def downgrade() -> None:
    op.drop_column("academy_profiles", "capacity_limit")
    op.drop_column("club_facilities", "facility_effects_json")
    op.drop_column("club_facilities", "in_progress_upgrades_json")
    op.drop_column("club_facilities", "youth_recruitment_level")
