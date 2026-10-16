from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.core.database import ensure_database_schema_current


def test_wallet_ledger_hardening_migration_creates_wallet_and_transaction_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'wallet-ledger-hardening.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    ensure_database_schema_current(engine)

    inspector = inspect(engine)
    assert inspector.has_table("wallets")
    assert inspector.has_table("transactions")
    assert inspector.has_table("ledger_balance_projections")
    assert inspector.has_table("ledger_entries")

    wallet_columns = {column["name"] for column in inspector.get_columns("wallets")}
    assert {
        "owner_user_id",
        "code",
        "label",
        "unit",
        "kind",
        "allow_negative",
        "is_active",
    } <= wallet_columns

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    assert {
        "status",
        "reason",
        "source_tag",
        "reference",
        "external_reference",
        "description",
        "idempotency_key",
        "metadata_json",
        "created_by_user_id",
        "created_at",
        "committed_at",
        "failed_at",
    } <= transaction_columns

    projection_columns = {column["name"] for column in inspector.get_columns("ledger_balance_projections")}
    assert {
        "account_id",
        "owner_user_id",
        "unit",
        "balance",
        "last_transaction_id",
    } <= projection_columns

    ledger_entry_columns = {column["name"] for column in inspector.get_columns("ledger_entries")}
    assert {
        "transaction_id",
        "account_id",
        "amount",
        "unit",
        "source_tag",
        "reason",
        "transaction_type",
    } <= ledger_entry_columns

    ledger_entry_foreign_keys = inspector.get_foreign_keys("ledger_entries")
    assert any(foreign_key.get("referred_table") == "transactions" for foreign_key in ledger_entry_foreign_keys)

    engine.dispose()
