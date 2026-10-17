"""Merge Alembic heads after share-event fingerprint and price snapshots.

Revision ID: 20261017_0134_merge_share_event_and_price_snapshot_heads
Revises: 20261016_0130_share_event_actor_fingerprint, 20261017_0133_player_share_price_snapshots
"""

from __future__ import annotations

revision = "20261017_0134_merge_share_event_and_price_snapshot_heads"
down_revision = (
    "20261016_0130_share_event_actor_fingerprint",
    "20261017_0133_player_share_price_snapshots",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
