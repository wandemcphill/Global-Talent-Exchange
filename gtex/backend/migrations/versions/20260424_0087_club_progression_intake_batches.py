"""Add season and reason auditing to academy intake batches.

Revision ID: 20260424_0087_club_progression_intake_batches
Revises: 20260424_0086_regen_creation_orders
Create Date: 2026-04-24 13:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260424_0087_club_progression_intake_batches"
down_revision = "20260424_0086_regen_creation_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("academy_intake_batches") as batch_op:
        batch_op.add_column(sa.Column("season_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "trigger_reason",
                sa.String(length=48),
                nullable=False,
                server_default="academy_manual",
            )
        )
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=160), nullable=True))
        batch_op.create_foreign_key(
            "fk_academy_intake_batches_season_id",
            "regen_universe_seasons",
            ["season_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_constraint("uq_academy_intake_batches_club_season", type_="unique")
        batch_op.create_unique_constraint(
            "uq_academy_intake_batches_club_season_reason",
            ["club_id", "season_label", "trigger_reason"],
        )
        batch_op.create_index("ix_academy_intake_batches_season_id", ["season_id"], unique=False)
        batch_op.create_index("ix_academy_intake_batches_trigger_reason", ["trigger_reason"], unique=False)
        batch_op.create_index("ix_academy_intake_batches_idempotency_key", ["idempotency_key"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("academy_intake_batches") as batch_op:
        batch_op.drop_index("ix_academy_intake_batches_idempotency_key")
        batch_op.drop_index("ix_academy_intake_batches_trigger_reason")
        batch_op.drop_index("ix_academy_intake_batches_season_id")
        batch_op.drop_constraint("uq_academy_intake_batches_club_season_reason", type_="unique")
        batch_op.create_unique_constraint(
            "uq_academy_intake_batches_club_season",
            ["club_id", "season_label"],
        )
        batch_op.drop_constraint("fk_academy_intake_batches_season_id", type_="foreignkey")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("trigger_reason")
        batch_op.drop_column("season_id")
