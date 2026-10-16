"""Merge parallel 0066 revisions.

Revision ID: 20260329_0067_merge_global_consistency_heads
Revises: 20260329_0066_global_system_consistency, 20260329_0066_media_betting_global_events
Create Date: 2026-03-29 18:25:00.000000
"""

from __future__ import annotations


revision = "20260329_0067_merge_global_consistency_heads"
down_revision = (
    "20260329_0066_global_system_consistency",
    "20260329_0066_media_betting_global_events",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
