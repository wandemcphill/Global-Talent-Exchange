from __future__ import annotations

from alembic import command
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import pytest

from app.core.database import build_alembic_config
from app.models.base import Base
from app.models.club_finance_account import ClubFinanceAccount
from app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry


def test_alembic_upgrade_creates_club_ops_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'club_ops.db').as_posix()}"
    command.upgrade(build_alembic_config(database_url), "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        inspector = inspect(engine)
        assert {
            "club_finance_accounts",
            "club_finance_ledger_entries",
            "club_sponsorship_contracts",
            "academy_programs",
            "scout_assignments",
            "youth_pipeline_snapshots",
        }.issubset(set(inspector.get_table_names()))
    finally:
        engine.dispose()


def test_club_finance_ledger_is_append_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[ClubFinanceAccount.__table__, ClubFinanceLedgerEntry.__table__])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    try:
        with SessionLocal() as session:
            account = ClubFinanceAccount(club_id="club-1", account_type="operating_balance", currency="USD")
            session.add(account)
            session.commit()

            entry = ClubFinanceLedgerEntry(
                transaction_id="tx-1",
                club_id="club-1",
                account_id=account.id,
                account_type="operating_balance",
                entry_type="manual_admin_adjustment",
                amount_minor=100_000,
                currency="USD",
                metadata_json={"source": "opening"},
            )
            session.add(entry)
            session.commit()

            entry.description = "tampered"
            with pytest.raises(ValueError, match="append-only"):
                session.commit()
            session.rollback()

            persisted = session.get(ClubFinanceLedgerEntry, entry.id)
            assert persisted is not None
            session.delete(persisted)
            with pytest.raises(ValueError, match="append-only"):
                session.commit()
    finally:
        engine.dispose()
