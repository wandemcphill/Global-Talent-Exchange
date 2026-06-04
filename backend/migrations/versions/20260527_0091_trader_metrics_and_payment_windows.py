"""Add trader metrics used by payment-window maintenance.

Revision ID: 20260527_0091_trader_metrics_and_payment_windows
Revises: 20260518_0090_identity_trader_rebuild
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260527_0091_trader_metrics_and_payment_windows"
down_revision = "20260518_0090_identity_trader_rebuild"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("trader_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("liquidity_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(
            sa.Column("completion_rate", sa.Numeric(7, 4), nullable=False, server_default="0.0000")
        )
        batch_op.add_column(
            sa.Column("average_release_seconds", sa.Numeric(12, 4), nullable=False, server_default="0.0000")
        )
        batch_op.add_column(sa.Column("rating_score", sa.Numeric(7, 4), nullable=False, server_default="0.0000"))
        batch_op.add_column(sa.Column("metrics_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("trader_profiles") as batch_op:
        batch_op.drop_column("metrics_updated_at")
        batch_op.drop_column("rating_score")
        batch_op.drop_column("average_release_seconds")
        batch_op.drop_column("completion_rate")
        batch_op.drop_column("liquidity_snapshot_json")
