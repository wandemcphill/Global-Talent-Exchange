"""Database guards for the canonical GTEX Jackpot economy.

Revision ID: 20260914_0123_jackpot_database_guards
Revises: 20260914_0122_coin_trader_liquidity_backing
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260914_0123_jackpot_database_guards"
down_revision = "20260914_0122_coin_trader_liquidity_backing"
branch_labels = None
depends_on = None


OPEN_STATUS = "open"


def _assert_no_duplicates(connection) -> None:
    inspector = sa.inspect(connection)
    ledger_table = "transactions" if inspector.has_table("transactions") else "ledger_transactions"
    duplicate_checks = (
        (
            "gtex_jackpot_rounds",
            "open jackpot rounds",
            sa.text("""
                SELECT pool_key, COUNT(*)
                FROM gtex_jackpot_rounds
                WHERE status = :status
                GROUP BY pool_key
                HAVING COUNT(*) > 1
                """),
            {"status": OPEN_STATUS},
        ),
        (
            "gtex_jackpot_payouts",
            "jackpot payout ranks",
            sa.text("""
                SELECT round_id, rank, COUNT(*)
                FROM gtex_jackpot_payouts
                GROUP BY round_id, rank
                HAVING COUNT(*) > 1
                """),
            {},
        ),
        (
            "gtex_jackpot_contributions",
            "jackpot contribution source identities",
            sa.text("""
                SELECT source_type, source_id, participant_user_id, COUNT(*)
                FROM gtex_jackpot_contributions
                WHERE source_id IS NOT NULL
                GROUP BY source_type, source_id, participant_user_id
                HAVING COUNT(*) > 1
                """),
            {},
        ),
        (
            ledger_table,
            "jackpot payout ledger references",
            sa.text(f"""
                SELECT reference, COUNT(*)
                FROM {ledger_table}
                WHERE reference LIKE 'gtex-jackpot-payout:%'
                GROUP BY reference
                HAVING COUNT(*) > 1
                """),
            {},
        ),
    )
    for table_name, label, query, params in duplicate_checks:
        if not inspector.has_table(table_name):
            continue
        rows = connection.execute(query, params).fetchall()
        if rows:
            raise RuntimeError(f"Cannot install Jackpot database guards: duplicate {label} exist: {rows}")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    _assert_no_duplicates(connection)

    if inspector.has_table("gtex_jackpot_rounds"):
        op.create_index(
            "uq_gtex_jackpot_open_pool",
            "gtex_jackpot_rounds",
            ["pool_key"],
            unique=True,
            postgresql_where=sa.text("status = 'open'"),
            sqlite_where=sa.text("status = 'open'"),
        )
    if inspector.has_table("gtex_jackpot_payouts"):
        op.create_index(
            "uq_gtex_jackpot_payout_round_rank",
            "gtex_jackpot_payouts",
            ["round_id", "rank"],
            unique=True,
        )
    if inspector.has_table("gtex_jackpot_contributions"):
        op.create_index(
            "uq_gtex_jackpot_contribution_source",
            "gtex_jackpot_contributions",
            ["source_type", "source_id", "participant_user_id"],
            unique=True,
            postgresql_where=sa.text("source_id IS NOT NULL"),
            sqlite_where=sa.text("source_id IS NOT NULL"),
        )

    ledger_table = "transactions" if inspector.has_table("transactions") else "ledger_transactions"
    if inspector.has_table(ledger_table):
        op.create_index(
            "uq_gtex_jackpot_payout_ledger_reference",
            ledger_table,
            ["reference"],
            unique=True,
            postgresql_where=sa.text("reference LIKE 'gtex-jackpot-payout:%'"),
            sqlite_where=sa.text("reference LIKE 'gtex-jackpot-payout:%'"),
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    ledger_table = "transactions" if inspector.has_table("transactions") else "ledger_transactions"
    if inspector.has_table(ledger_table):
        op.drop_index("uq_gtex_jackpot_payout_ledger_reference", table_name=ledger_table)
    if inspector.has_table("gtex_jackpot_contributions"):
        op.drop_index("uq_gtex_jackpot_contribution_source", table_name="gtex_jackpot_contributions")
    if inspector.has_table("gtex_jackpot_payouts"):
        op.drop_index("uq_gtex_jackpot_payout_round_rank", table_name="gtex_jackpot_payouts")
    if inspector.has_table("gtex_jackpot_rounds"):
        op.drop_index("uq_gtex_jackpot_open_pool", table_name="gtex_jackpot_rounds")
