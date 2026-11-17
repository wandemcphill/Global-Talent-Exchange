"""Widen event_outbox.event_id so canonical match ids fit.

Canonical execution ids are `{match_id}:r{revision}:s{step}:{event_type}`.
A UUID match id plus that suffix is longer than varchar(36). SQLite does not
enforce the length, so the failure only appears on PostgreSQL.

Revision ID: 20261118_0266_widen_event_outbox_event_id
Revises: 20261117_0261_first_deposit_referral_affiliate
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261118_0266_widen_event_outbox_event_id"
down_revision = "20261117_0261_first_deposit_referral_affiliate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("event_outbox") as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("event_outbox") as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.String(length=255),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
