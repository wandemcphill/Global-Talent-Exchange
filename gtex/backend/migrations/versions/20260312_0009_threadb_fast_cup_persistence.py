"""Add durable fast-cup persistence records."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0009"
down_revision = "20260312_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fast_cup_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("cup_id", sa.String(length=120), nullable=False),
        sa.Column("division", sa.String(length=16), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("buy_in", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_fast_cup_records"),
        sa.UniqueConstraint("cup_id", name="uq_fast_cup_records_cup_id"),
    )
    op.create_index("ix_fast_cup_records_cup_id", "fast_cup_records", ["cup_id"], unique=False)
    op.create_index("ix_fast_cup_records_division", "fast_cup_records", ["division"], unique=False)
    op.create_index("ix_fast_cup_records_size", "fast_cup_records", ["size"], unique=False)
    op.create_index("ix_fast_cup_records_kickoff_at", "fast_cup_records", ["kickoff_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fast_cup_records_kickoff_at", table_name="fast_cup_records")
    op.drop_index("ix_fast_cup_records_size", table_name="fast_cup_records")
    op.drop_index("ix_fast_cup_records_division", table_name="fast_cup_records")
    op.drop_index("ix_fast_cup_records_cup_id", table_name="fast_cup_records")
    op.drop_table("fast_cup_records")
