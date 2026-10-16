"""Merge March 27 feature heads into a single Alembic head.

Revision ID: 20260327_0038_merge_feature_heads
Revises: 20260327_0036_gtex_competitive_integrity, 20260327_0037_gtex_engagement_systems, 20260327_0037_regen_ecosystem_foundation, 20260327_0037_regen_universe_documentary_and_dna
Create Date: 2026-03-27 14:25:00.000000
"""

from __future__ import annotations


revision = "20260327_0038_merge_feature_heads"
down_revision = (
    "20260327_0036_gtex_competitive_integrity",
    "20260327_0037_gtex_engagement_systems",
    "20260327_0037_regen_ecosystem_foundation",
    "20260327_0037_regen_universe_documentary_and_dna",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
