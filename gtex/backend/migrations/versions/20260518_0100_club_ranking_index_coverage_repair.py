"""Repair club ranking single-column index coverage.

Revision ID: 20260518_0100_club_ranking_index_coverage_repair
Revises: 20260517_0099_award_gifts_phase3
Create Date: 2026-05-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260518_0100_club_ranking_index_coverage_repair"
down_revision = "20260517_0099_award_gifts_phase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_club_ranking_events_club_id",
        "club_ranking_events",
        ["club_id"],
    )
    op.create_index(
        "ix_club_ranking_abuse_flags_club_id",
        "club_ranking_abuse_flags",
        ["club_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_club_ranking_abuse_flags_club_id",
        table_name="club_ranking_abuse_flags",
    )
    op.drop_index(
        "ix_club_ranking_events_club_id",
        table_name="club_ranking_events",
    )
