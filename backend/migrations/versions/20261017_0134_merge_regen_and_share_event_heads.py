"""Merge the independently developed regen-market and share-event migration heads.

Revision ID: 20261017_0134_merge_regen_and_share_event_heads
Revises: 20261016_0130_share_event_actor_fingerprint, 20261017_0133_player_share_price_snapshots

Both branches extend the same 0129 migration. This no-op merge revision restores
a single Alembic head before subsequent migrations are added.
"""

from __future__ import annotations

revision = "20261017_0134_merge_regen_and_share_event_heads"
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
