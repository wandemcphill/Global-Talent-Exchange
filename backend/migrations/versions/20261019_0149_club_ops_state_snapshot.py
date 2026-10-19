"""Create durable ClubOps state snapshots.

Revision ID: 20261019_0149_club_ops_state_snapshot
Revises: 20261019_0148_reward_settlement_idempotency_guard

Revision ID: 20261019_0149_club_ops_state_snapshot
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261019_0149_club_ops_state_snapshot"
down_revision = "20261019_0148_reward_settlement_idempotency_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_ops_state_snapshots",
        sa.Column("state_key", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.bulk_insert(
        sa.table(
            "club_ops_state_snapshots",
            sa.column("state_key", sa.String(length=32)),
            sa.column("payload", sa.JSON()),
        ),
        [{"state_key": "global", "payload": {}}],
    )


def downgrade() -> None:
    op.drop_table("club_ops_state_snapshots")
