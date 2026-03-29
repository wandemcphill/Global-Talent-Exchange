"""Merge parallel 0060 revisions.

Revision ID: 20260329_0061_merge_parallel_heads
Revises: 20260329_0060_creator_attention_earnings, 20260329_0060_scale_backbone, 20260329_0060_tournament_engine
Create Date: 2026-03-29 09:20:00.000000
"""

from __future__ import annotations


revision = "20260329_0061_merge_parallel_heads"
down_revision = (
    "20260329_0060_creator_attention_earnings",
    "20260329_0060_scale_backbone",
    "20260329_0060_tournament_engine",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
