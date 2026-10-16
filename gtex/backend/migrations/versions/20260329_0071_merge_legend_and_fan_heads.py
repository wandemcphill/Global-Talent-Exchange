"""Merge the parallel 0070 legend and fan experience heads.

Revision ID: 20260329_0071_merge_legend_and_fan_heads
Revises: 20260329_0070_fan_experience_mega_pack, 20260329_0070_legend_layer
Create Date: 2026-03-29 23:50:00.000000
"""

from __future__ import annotations


revision = "20260329_0071_merge_legend_and_fan_heads"
down_revision = (
    "20260329_0070_fan_experience_mega_pack",
    "20260329_0070_legend_layer",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
