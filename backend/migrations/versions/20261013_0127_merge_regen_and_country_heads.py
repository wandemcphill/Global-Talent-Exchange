"""Merge Alembic heads after regen endorsement and country-pool index.

Revision ID: 20261013_0127_merge_regen_and_country_heads
Revises: 20261013_0126_regen_endorsement_deals, 20260916_0118_player_country_pool_index
"""

from __future__ import annotations

revision = "20261013_0127_merge_regen_and_country_heads"
down_revision = (
    "20261013_0126_regen_endorsement_deals",
    "20260916_0118_player_country_pool_index",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
