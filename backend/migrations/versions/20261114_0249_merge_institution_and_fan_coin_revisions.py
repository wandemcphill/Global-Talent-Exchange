"""Merge living-institution indexes and Fan Coin severance migration heads.

Revision ID: 20261114_0249_merge_institution_and_fan_coin_revisions
Revises: 20261114_0248_living_institution_index_coverage, 20261114_0248_staff_severance_fan_coin
Create Date: 2026-11-14 20:30:00.000000
"""

from __future__ import annotations

revision = "20261114_0249_merge_institution_and_fan_coin_revisions"
down_revision = (
    "20261114_0248_living_institution_index_coverage",
    "20261114_0248_staff_severance_fan_coin",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
