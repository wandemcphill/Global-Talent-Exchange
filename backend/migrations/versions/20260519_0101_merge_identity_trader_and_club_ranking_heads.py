"""Merge identity trader and club ranking migration heads.

Revision ID: 20260519_0101_merge_identity_trader_and_club_ranking_heads
Revises: 20260518_0090_identity_trader_rebuild, 20260518_0100_club_ranking_index_coverage_repair
Create Date: 2026-05-19 16:45:00.000000
"""

from __future__ import annotations

revision = "20260519_0101_merge_identity_trader_and_club_ranking_heads"
down_revision = (
    "20260518_0090_identity_trader_rebuild",
    "20260518_0100_club_ranking_index_coverage_repair",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
