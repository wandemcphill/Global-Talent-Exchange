"""Add layered value fields for Phase 5 snapshots."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260311_0004"
down_revision = "20260311_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_value_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "football_truth_value_credits",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "market_signal_value_credits",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    op.execute(
        sa.text(
            """
            UPDATE player_value_snapshots
            SET football_truth_value_credits = target_credits,
                market_signal_value_credits = target_credits
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("player_value_snapshots") as batch_op:
        batch_op.drop_column("market_signal_value_credits")
        batch_op.drop_column("football_truth_value_credits")
