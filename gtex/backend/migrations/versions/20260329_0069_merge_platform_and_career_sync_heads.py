"""Merge parallel 0068 revisions.

Revision ID: 20260329_0069_merge_platform_and_career_sync_heads
Revises: 20260329_0068_gtex_universe_career_sync, 20260329_0068_platform_experience_and_national_regen_seed
Create Date: 2026-03-29 22:58:00.000000
"""

from __future__ import annotations


revision = "20260329_0069_merge_platform_and_career_sync_heads"
down_revision = (
    "20260329_0068_gtex_universe_career_sync",
    "20260329_0068_platform_experience_and_national_regen_seed",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
