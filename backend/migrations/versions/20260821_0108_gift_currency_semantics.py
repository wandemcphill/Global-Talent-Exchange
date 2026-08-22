"""Make gift source/destination currency semantics explicit.

Revision ID: 20260821_0108_gift_currency_semantics
Revises: 20260821_0107_economic_conversions
Create Date: 2026-08-21 22:58:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260821_0108_gift_currency_semantics"
down_revision = "20260821_0107_economic_conversions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gift_transactions",
        sa.Column("source_ledger_unit", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "gift_transactions",
        sa.Column("destination_ledger_unit", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "gift_transactions",
        sa.Column("economic_conversion_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "gift_transactions",
        sa.Column(
            "conversion_rate",
            sa.Numeric(20, 8),
            server_default="1",
            nullable=False,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE gift_transactions
            SET source_ledger_unit = ledger_unit,
                destination_ledger_unit = ledger_unit
            WHERE source_ledger_unit IS NULL
               OR destination_ledger_unit IS NULL
            """
        )
    )

    op.alter_column(
        "gift_transactions",
        "source_ledger_unit",
        nullable=False,
        server_default="credit",
    )
    op.alter_column(
        "gift_transactions",
        "destination_ledger_unit",
        nullable=False,
        server_default="coin",
    )

    op.create_foreign_key(
        "fk_gift_transactions_economic_conversion_id",
        "gift_transactions",
        "economic_conversions",
        ["economic_conversion_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_gift_transactions_economic_conversion_id",
        "gift_transactions",
        ["economic_conversion_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gift_transactions_economic_conversion_id",
        table_name="gift_transactions",
    )
    op.drop_constraint(
        "fk_gift_transactions_economic_conversion_id",
        "gift_transactions",
        type_="foreignkey",
    )
    op.drop_column("gift_transactions", "conversion_rate")
    op.drop_column("gift_transactions", "economic_conversion_id")
    op.drop_column("gift_transactions", "destination_ledger_unit")
    op.drop_column("gift_transactions", "source_ledger_unit")
