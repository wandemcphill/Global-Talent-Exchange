"""Add replay protection to withdrawal submission.

Revision ID: 20260828_0115_payout_request_idempotency
Revises: 20260827_0114_economic_policy_authority

PHASE_A_WITHDRAWAL_CONTRACT acceptance test 10 requires a withdrawal request
to be idempotent. Nothing carried the caller's intent, so two identical
submissions produced two holds and two payout rows. The column is nullable so
historical rows and internal callers that supply no key remain valid; the
unique index is what actually prevents the duplicate.

batch_alter_table is used for the index so SQLite (which cannot ALTER) and
PostgreSQL both end up with the same schema.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260828_0115_payout_request_idempotency"
down_revision = "20260827_0114_economic_policy_authority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("payout_requests") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))

    op.create_index(
        "ix_payout_requests_idempotency_key",
        "payout_requests",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_payout_requests_idempotency_key", table_name="payout_requests")
    with op.batch_alter_table("payout_requests") as batch_op:
        batch_op.drop_column("idempotency_key")
