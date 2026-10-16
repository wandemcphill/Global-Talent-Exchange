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
    duplicate_checks = (
        (
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
            "jackpot payout ledger references",
            sa.text("""
                SELECT reference, COUNT(*)
                FROM transactions
                WHERE reference LIKE 'gtex-jackpot-payout:%'
                GROUP BY reference
                HAVING COUNT(*) > 1
                """),
            {},
        ),
    )
    for label, query, params in duplicate_checks:
        rows = connection.execute(query, params).fetchall()
        if rows:
            raise RuntimeError(f"Cannot install Jackpot database guards: duplicate {label} exist: {rows}")


def upgrade() -> None:
    connection = op.get_bind()
    _assert_no_duplicates(connection)

    op.create_index(
        "uq_gtex_jackpot_open_pool",
        "gtex_jackpot_rounds",
        ["pool_key"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "uq_gtex_jackpot_payout_round_rank",
        "gtex_jackpot_payouts",
        ["round_id", "rank"],
        unique=True,
    )
    op.create_index(
        "uq_gtex_jackpot_contribution_source",
        "gtex_jackpot_contributions",
        ["source_type", "source_id", "participant_user_id"],
        unique=True,
        postgresql_where=sa.text("source_id IS NOT NULL"),
        sqlite_where=sa.text("source_id IS NOT NULL"),
    )
    op.create_index(
        "uq_gtex_jackpot_payout_ledger_reference",
        "transactions",
        ["reference"],
        unique=True,
        postgresql_where=sa.text("reference LIKE 'gtex-jackpot-payout:%'"),
        sqlite_where=sa.text("reference LIKE 'gtex-jackpot-payout:%'"),
    )


def downgrade() -> None:
    op.drop_index("uq_gtex_jackpot_payout_ledger_reference", table_name="transactions")
    op.drop_index("uq_gtex_jackpot_contribution_source", table_name="gtex_jackpot_contributions")
    op.drop_index("uq_gtex_jackpot_payout_round_rank", table_name="gtex_jackpot_payouts")
    op.drop_index("uq_gtex_jackpot_open_pool", table_name="gtex_jackpot_rounds")
