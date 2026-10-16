"""Merge parallel March 26 feature heads.

Revision ID: 20260326_0035_merge_parallel_feature_heads
Revises: 20260326_0034_agent_marketplace_conversations, 20260326_0034_player_match_learning, 20260326_0034_role_based_access_control
Create Date: 2026-03-26 23:55:00.000000
"""

from __future__ import annotations


revision = "20260326_0035_merge_parallel_feature_heads"
down_revision = (
    "20260326_0034_agent_marketplace_conversations",
    "20260326_0034_player_match_learning",
    "20260326_0034_role_based_access_control",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
