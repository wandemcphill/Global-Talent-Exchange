"""Add durable cross-currency economic conversions.

Revision ID: 20260821_0107_economic_conversions
Revises: 20260724_0106_player_potential
Create Date: 2026-08-21 22:50:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260821_0107_economic_conversions"
down_revision = "20260724_0106_player_potential"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economic_conversions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("conversion_key", sa.String(length=128), nullable=False),
        sa.Column(
            "conversion_type",
            sa.String(length=32),
            server_default="fancoin_gift",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("source_user_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=36), nullable=False),
        sa.Column("gift_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("source_unit", sa.String(length=16), nullable=False),
        sa.Column("destination_unit", sa.String(length=16), nullable=False),
        sa.Column("source_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column(
            "platform_fee_amount",
            sa.Numeric(20, 4),
            server_default="0",
            nullable=False,
        ),
        sa.Column("destination_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column(
            "conversion_rate",
            sa.Numeric(20, 8),
            server_default="1",
            nullable=False,
        ),
        sa.Column("source_ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column(
            "destination_ledger_transaction_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column("fee_rule_key", sa.String(length=128), nullable=True),
        sa.Column("fee_rule_version", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gift_transaction_id"],
            ["gift_transactions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversion_key",
            name="uq_economic_conversions_conversion_key",
        ),
        sa.UniqueConstraint("gift_transaction_id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_economic_conversions_idempotency_key",
        ),
    )
    op.create_index(
        "ix_economic_conversions_status",
        "economic_conversions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_economic_conversions_source_user_id",
        "economic_conversions",
        ["source_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_economic_conversions_recipient_user_id",
        "economic_conversions",
        ["recipient_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_economic_conversions_gift_transaction_id",
        "economic_conversions",
        ["gift_transaction_id"],
        unique=True,
    )
    op.create_index(
        "ix_economic_conversions_source_ledger_transaction_id",
        "economic_conversions",
        ["source_ledger_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_economic_conversions_destination_ledger_transaction_id",
        "economic_conversions",
        ["destination_ledger_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_economic_conversions_idempotency_key",
        "economic_conversions",
        ["idempotency_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_economic_conversions_idempotency_key",
        table_name="economic_conversions",
    )
    op.drop_index(
        "ix_economic_conversions_destination_ledger_transaction_id",
        table_name="economic_conversions",
    )
    op.drop_index(
        "ix_economic_conversions_source_ledger_transaction_id",
        table_name="economic_conversions",
    )
    op.drop_index(
        "ix_economic_conversions_gift_transaction_id",
        table_name="economic_conversions",
    )
    op.drop_index(
        "ix_economic_conversions_recipient_user_id",
        table_name="economic_conversions",
    )
    op.drop_index(
        "ix_economic_conversions_source_user_id",
        table_name="economic_conversions",
    )
    op.drop_index(
        "ix_economic_conversions_status",
        table_name="economic_conversions",
    )
    op.drop_table("economic_conversions")
