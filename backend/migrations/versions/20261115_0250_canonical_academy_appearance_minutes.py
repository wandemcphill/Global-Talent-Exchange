"""Persist actual first-team minutes for academy graduates.

Revision ID: 20261115_0250_canonical_academy_appearance_minutes
Revises: 20261114_0249_merge_institution_and_fan_coin_revisions
Create Date: 2026-11-15 09:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261115_0250_canonical_academy_appearance_minutes"
down_revision = "20261114_0249_merge_institution_and_fan_coin_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_club_academy_graduates" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("owner_club_academy_graduates")}
    if "first_team_minutes" not in columns:
        op.add_column(
            "owner_club_academy_graduates",
            sa.Column("first_team_minutes", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_club_academy_graduates" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("owner_club_academy_graduates")}
    if "first_team_minutes" in columns:
        op.drop_column("owner_club_academy_graduates", "first_team_minutes")
