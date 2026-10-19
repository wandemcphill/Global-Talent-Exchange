from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.enums.club_finance_account_type import ClubFinanceAccountType
from app.common.enums.club_finance_entry_type import ClubFinanceEntryType
from app.models.base import Base
from app.models.club_finance_account import ClubFinanceAccount
from app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry
from app.models.club_ops_state_snapshot import ClubOpsStateSnapshot
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, FinanceAccountRecord, LedgerEntryRecord


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False), engine


def test_club_ops_finance_state_survives_store_recreation_and_projects_to_orm() -> None:
    session_factory, engine = _session_factory()
    try:
        first_store = ClubOpsStore(session_factory=session_factory)
        finance = ClubFinanceService(store=first_store)
        finance.ensure_club_setup("club-persistence-test")
        finance.record_manual_adjustment(
            "club-persistence-test",
            amount_minor=1250,
            description="Durability regression test adjustment",
            reference_id="durability-test",
        )

        # A distinct store simulates a fresh service instance / worker process.
        second_store = ClubOpsStore(session_factory=session_factory)
        with second_store.lock:
            accounts = second_store.accounts_by_club["club-persistence-test"]
            assert accounts[ClubFinanceAccountType.OPERATING_BALANCE].balance_minor == 1_501_250
            ledger = second_store.ledger_by_club["club-persistence-test"]
            assert any(entry.reference_id == "durability-test" for entry in ledger)

        with session_factory() as session:
            snapshot = session.get(ClubOpsStateSnapshot, "global")
            assert snapshot is not None
            account = session.scalar(
                select(ClubFinanceAccount).where(
                    ClubFinanceAccount.club_id == "club-persistence-test",
                    ClubFinanceAccount.account_type == ClubFinanceAccountType.OPERATING_BALANCE,
                )
            )
            assert account is not None
            assert account.balance_minor == 1_501_250
            entry = session.scalar(
                select(ClubFinanceLedgerEntry).where(
                    ClubFinanceLedgerEntry.club_id == "club-persistence-test",
                    ClubFinanceLedgerEntry.reference_id == "durability-test",
                )
            )
            assert entry is not None
            assert entry.amount_minor == 1250

        # The first store must also reload the second store's committed snapshot,
        # rather than serving a stale process-local dictionary.
        with first_store.lock:
            assert first_store.accounts_by_club["club-persistence-test"][
                ClubFinanceAccountType.OPERATING_BALANCE
            ].balance_minor == 1_501_250
    finally:
        engine.dispose()
