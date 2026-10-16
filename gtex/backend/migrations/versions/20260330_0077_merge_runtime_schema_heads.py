"""Merge runtime schema repair heads.

Revision ID: 20260330_0077_merge_runtime_schema_heads
Revises: 20260330_0075_competition_discovery_perf_indexes, 20260330_0076_regen_tracking_schema_repair
Create Date: 2026-03-30 10:05:00.000000
"""

from __future__ import annotations


revision = "20260330_0077_merge_runtime_schema_heads"
down_revision = (
    "20260330_0075_competition_discovery_perf_indexes",
    "20260330_0076_regen_tracking_schema_repair",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
