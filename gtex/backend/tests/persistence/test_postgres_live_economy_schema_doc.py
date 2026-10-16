from __future__ import annotations

from app.core.config import BACKEND_ROOT


def test_postgres_live_economy_schema_covers_thread_a_core_tables() -> None:
    sql = (BACKEND_ROOT / "docs" / "architecture" / "postgres_live_economy_schema.sql").read_text(
        encoding="utf-8"
    )

    required_table_snippets = (
        "CREATE TABLE IF NOT EXISTS wallets (",
        "CREATE TABLE IF NOT EXISTS transactions (",
        "CREATE TABLE IF NOT EXISTS ledger_entries (",
        "CREATE TABLE IF NOT EXISTS ledger_balance_projections (",
        "CREATE TABLE IF NOT EXISTS match_participants (",
        "CREATE TABLE IF NOT EXISTS player_share_markets (",
        "CREATE TABLE IF NOT EXISTS player_share_holdings (",
        "CREATE TABLE IF NOT EXISTS player_share_events (",
        "CREATE TABLE IF NOT EXISTS player_orders (",
        "CREATE TABLE IF NOT EXISTS player_order_fills (",
        "CREATE TABLE IF NOT EXISTS club_share_markets (",
        "CREATE TABLE IF NOT EXISTS club_share_holdings (",
        "CREATE TABLE IF NOT EXISTS club_share_distributions (",
        "CREATE TABLE IF NOT EXISTS club_share_payouts (",
        "CREATE TABLE IF NOT EXISTS season_passes (",
        "CREATE TABLE IF NOT EXISTS season_pass_claims (",
        "CREATE TABLE IF NOT EXISTS season_pass_xp_grants (",
        "CREATE TABLE IF NOT EXISTS lottery_runs (",
    )
    for snippet in required_table_snippets:
        assert snippet in sql

    required_column_snippets = (
        "code text NOT NULL UNIQUE",
        "owner_scope text NOT NULL DEFAULT 'user'",
        "treasury_balance_minor bigint NOT NULL DEFAULT 0",
        "valuation_minor bigint NOT NULL DEFAULT 0",
        "current_value_minor bigint NOT NULL DEFAULT 0",
        "match_type text NOT NULL DEFAULT 'gtex_hosted'",
        "entry_fee_minor bigint NOT NULL DEFAULT 0",
        "prize_pool_minor bigint NOT NULL DEFAULT 0",
        "trigger_reference text NOT NULL UNIQUE",
    )
    for snippet in required_column_snippets:
        assert snippet in sql
