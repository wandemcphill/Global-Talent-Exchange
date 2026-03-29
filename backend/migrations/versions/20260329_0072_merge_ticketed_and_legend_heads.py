"""Merge ticketed-live-events and legend-layer heads.

Revision ID: 20260329_0072_merge_ticketed_and_legend_heads
Revises: 20260329_0069_ticketed_live_events_merge_heads, 20260329_0071_merge_legend_and_fan_heads
Create Date: 2026-03-29 23:58:00.000000
"""

from __future__ import annotations


revision = "20260329_0072_merge_ticketed_and_legend_heads"
down_revision = (
    "20260329_0069_ticketed_live_events_merge_heads",
    "20260329_0071_merge_legend_and_fan_heads",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
