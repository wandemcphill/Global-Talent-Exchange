"""Add anonymous-actor fingerprint columns to share events.

Revision ID: 20261016_0130_share_event_actor_fingerprint
Revises: 20261013_0129_open_default_launch_flags

Supports server-side dedupe of unauthenticated share-event writes without
storing client IPs in the clear.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261016_0130_share_event_actor_fingerprint"
down_revision = "20261013_0129_open_default_launch_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "challenge_share_events",
        sa.Column("actor_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_challenge_share_events_actor_fingerprint",
        "challenge_share_events",
        ["actor_fingerprint"],
    )
    op.add_column(
        "match_share_events",
        sa.Column("actor_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_match_share_events_actor_fingerprint",
        "match_share_events",
        ["actor_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_match_share_events_actor_fingerprint", table_name="match_share_events")
    op.drop_column("match_share_events", "actor_fingerprint")
    op.drop_index("ix_challenge_share_events_actor_fingerprint", table_name="challenge_share_events")
    op.drop_column("challenge_share_events", "actor_fingerprint")
