"""Make gift source/destination currency semantics explicit.

Revision ID: 20260821_0108_gift_currency_semantics
Revises: 20260821_0107_economic_conversions
Create Date: 2026-08-21 22:58:00.000000

Uses batch_alter_table throughout: SQLite supports neither ALTER COLUMN nor
ADD CONSTRAINT, so the original plain op.alter_column / op.create_foreign_key
calls aborted `alembic upgrade head` on every SQLite database. Batch mode
recreates the table on SQLite and passes straight through on PostgreSQL, so the
resulting schema is identical on both backends.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260821_0108_gift_currency_semantics"
down_revision = "20260821_0107_economic_conversions"
branch_labels = None
depends_on = None

_LEDGER_UNIT = sa.String(length=16)


def upgrade() -> None:
    with op.batch_alter_table("gift_transactions") as batch_op:
        batch_op.add_column(sa.Column("source_ledger_unit", _LEDGER_UNIT, nullable=True))
        batch_op.add_column(sa.Column("destination_ledger_unit", _LEDGER_UNIT, nullable=True))
        batch_op.add_column(sa.Column("economic_conversion_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "conversion_rate",
                sa.Numeric(20, 8),
                server_default="1",
                nullable=False,
            )
        )

    # COALESCE guards the NOT NULL promotion below: a legacy row with a NULL
    # ledger_unit would otherwise leave the new columns NULL and abort the
    # alter_column that follows.
    op.execute(sa.text("""
            UPDATE gift_transactions
            SET source_ledger_unit = COALESCE(source_ledger_unit, ledger_unit, 'credit'),
                destination_ledger_unit = COALESCE(destination_ledger_unit, ledger_unit, 'coin')
            WHERE source_ledger_unit IS NULL
               OR destination_ledger_unit IS NULL
            """))

    with op.batch_alter_table("gift_transactions") as batch_op:
        batch_op.alter_column(
            "source_ledger_unit",
            existing_type=_LEDGER_UNIT,
            nullable=False,
            server_default="credit",
        )
        batch_op.alter_column(
            "destination_ledger_unit",
            existing_type=_LEDGER_UNIT,
            nullable=False,
            server_default="coin",
        )
        batch_op.create_foreign_key(
            "fk_gift_transactions_economic_conversion_id",
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
    with op.batch_alter_table("gift_transactions") as batch_op:
        batch_op.drop_constraint(
            "fk_gift_transactions_economic_conversion_id",
            type_="foreignkey",
        )
        batch_op.drop_column("conversion_rate")
        batch_op.drop_column("economic_conversion_id")
        batch_op.drop_column("destination_ledger_unit")
        batch_op.drop_column("source_ledger_unit")
