from __future__ import annotations

from decimal import Decimal
from shutil import copyfile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
import pytest

from app.auth.service import AuthService
from app.core.database import ensure_database_schema_current
from app.models import LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit, PaymentStatus
from app.models.wallet import LedgerBalanceProjection, LedgerTransaction, LedgerTransactionStatus
from app.wallets.service import (
    InsufficientBalanceError,
    LedgerError,
    LedgerPosting,
    UnbalancedTransactionError,
    WalletService,
)
from app.wallets.wallet_service import WalletTransactionPosting, WalletTransactionService


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int]] = []

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value
        self.set_calls.append((key, value, ttl_seconds))

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


@pytest.fixture(scope="session")
def migrated_wallet_service_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("wallet-service-db") / "template.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    engine.dispose()
    return db_path


@pytest.fixture()
def session(tmp_path, migrated_wallet_service_db):
    db_path = tmp_path / "wallet-service.db"
    copyfile(migrated_wallet_service_db, db_path)
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def _create_user(session):
    user = AuthService().register_user(
        session,
        email="wallet@example.com",
        username="walletuser",
        password="SuperSecret1",
    )
    session.commit()
    return user


def test_append_transaction_requires_balanced_postings(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)

    with pytest.raises(UnbalancedTransactionError, match="at least two postings"):
        service.append_transaction(
            session,
            postings=[LedgerPosting(account=user_account, amount=Decimal("10"))],
            reason=LedgerEntryReason.ADJUSTMENT,
        )


def test_verify_payment_event_credits_user_with_append_only_entries(session) -> None:
    user = _create_user(session)
    service = WalletService()
    payment_event = service.create_payment_event(
        session,
        user=user,
        provider="monnify",
        provider_reference="monnify-ref-001",
        amount=Decimal("50"),
        pack_code="starter-50",
    )
    service.verify_payment_event(session, payment_event, actor=user)
    session.commit()

    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    treasury_account = service.ensure_treasury_account(session, LedgerUnit.COIN)
    operations_account = service.ensure_operations_account(session, LedgerUnit.COIN)
    ledger_entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == payment_event.ledger_transaction_id)
    ).all()

    assert payment_event.status == PaymentStatus.VERIFIED
    assert len(ledger_entries) == 3
    assert service.get_balance(session, user_account) == Decimal("50.0000")
    assert service.get_balance(session, treasury_account) == Decimal("50.0000")
    assert service.get_balance(session, operations_account) == Decimal("-100.0000")
    assert {entry.transaction_type for entry in ledger_entries} == {LedgerTransactionType.DEPOSIT}

    ledger_entries[0].description = "tampered"
    with pytest.raises(ValueError, match="append-only"):
        session.commit()
    session.rollback()


def test_verify_payment_event_rejects_duplicate_verification(session) -> None:
    user = _create_user(session)
    service = WalletService()
    payment_event = service.create_payment_event(
        session,
        user=user,
        provider="monnify",
        provider_reference="monnify-ref-idempotent-001",
        amount=Decimal("25"),
        pack_code="starter-25",
    )
    service.verify_payment_event(session, payment_event, actor=user)
    session.commit()

    user_account = service.get_user_account(session, user, LedgerUnit.COIN)

    with pytest.raises(LedgerError, match="Only pending payment events can be verified"):
        service.verify_payment_event(session, payment_event, actor=user)
    session.rollback()

    assert service.get_balance(session, user_account) == Decimal("25.0000")
    assert session.scalar(select(func.count()).select_from(LedgerTransaction)) == 1


def test_append_transaction_rejects_negative_balance_for_user_accounts(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_deposit_clearing_account(session, LedgerUnit.COIN)

    with pytest.raises(InsufficientBalanceError, match="does not have enough balance"):
        service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("-1")),
                LedgerPosting(account=platform_account, amount=Decimal("1")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
        )


def test_quote_conversion_rejects_fan_coin_to_gtex_coin(session) -> None:
    service = WalletService()

    with pytest.raises(LedgerError, match="Fan Coin cannot be converted"):
        service.quote_conversion(source_unit=LedgerUnit.CREDIT, amount=Decimal("100"))


def test_append_transaction_creates_transaction_header_and_balance_projection(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)

    entries = service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("15")),
            LedgerPosting(account=platform_account, amount=Decimal("-15")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-header",
        actor=user,
        idempotency_key="wallet-seed-15",
        metadata={"seed": True},
    )
    session.commit()

    transaction = session.get(LedgerTransaction, entries[0].transaction_id)
    user_projection = session.scalar(
        select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == user_account.id)
    )
    platform_projection = session.scalar(
        select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == platform_account.id)
    )

    assert transaction is not None
    assert transaction.status == LedgerTransactionStatus.COMMITTED
    assert transaction.reference == "seed-header"
    assert transaction.idempotency_key == "wallet-seed-15"
    assert transaction.metadata_json == {"seed": True}
    assert user_projection is not None
    assert user_projection.balance == Decimal("15.0000")
    assert user_projection.last_transaction_id == transaction.id
    assert platform_projection is not None
    assert platform_projection.balance == Decimal("-15.0000")


def test_append_transaction_reuses_committed_transaction_for_same_idempotency_key(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)

    first_entries = service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("12")),
            LedgerPosting(account=platform_account, amount=Decimal("-12")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-idempotent",
        actor=user,
        idempotency_key="duplicate-safe-key",
    )
    session.commit()

    second_entries = service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("12")),
            LedgerPosting(account=platform_account, amount=Decimal("-12")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-idempotent",
        actor=user,
        idempotency_key="duplicate-safe-key",
    )
    session.commit()

    assert [entry.id for entry in second_entries] == [entry.id for entry in first_entries]
    assert service.get_balance(session, user_account) == Decimal("12.0000")
    assert session.scalar(select(func.count()).select_from(LedgerTransaction)) == 1


def test_get_balance_uses_post_commit_cache(session, monkeypatch) -> None:
    user = _create_user(session)
    cache_backend = FakeCacheBackend()
    service = WalletService(cache_backend=cache_backend)
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)

    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("9")),
            LedgerPosting(account=platform_account, amount=Decimal("-9")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-cache",
        actor=user,
    )

    assert cache_backend.values == {}

    session.commit()

    monkeypatch.setattr(
        service,
        "_get_or_build_balance_projection",
        lambda *_args, **_kwargs: pytest.fail("expected cached balance lookup"),
    )

    assert service.get_balance(session, user_account) == Decimal("9.0000")
    assert cache_backend.values[service._balance_cache_key(user_account.id)]


def test_get_wallet_summary_uses_write_through_cache(session, monkeypatch) -> None:
    user = _create_user(session)
    cache_backend = FakeCacheBackend()
    service = WalletService(cache_backend=cache_backend)
    user_account = service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = service.ensure_platform_account(session, LedgerUnit.CREDIT)

    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("15")),
            LedgerPosting(account=platform_account, amount=Decimal("-15")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-wallet-summary-cache",
        actor=user,
    )
    session.commit()

    monkeypatch.setattr(
        service,
        "get_user_account",
        lambda *_args, **_kwargs: pytest.fail("expected cached wallet summary lookup"),
    )
    monkeypatch.setattr(
        service,
        "_get_user_account_balance_by_kind",
        lambda *_args, **_kwargs: pytest.fail("expected cached wallet summary lookup"),
    )

    summary = service.get_wallet_summary(session, user, currency=LedgerUnit.CREDIT)

    assert summary.available_balance == Decimal("15.0000")
    assert summary.reserved_balance == Decimal("0.0000")
    assert cache_backend.values[service._wallet_summary_cache_key(user.id, LedgerUnit.CREDIT)]


def test_convert_wallet_units_moves_value_across_coin_and_credit_wallets(session) -> None:
    user = _create_user(session)
    service = WalletService()
    coin_account = service.get_user_account(session, user, LedgerUnit.COIN)
    credit_account = service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_coin = service.ensure_platform_account(session, LedgerUnit.COIN)

    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=coin_account, amount=Decimal("2")),
            LedgerPosting(account=platform_coin, amount=Decimal("-2")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-conversion",
        actor=user,
    )
    session.commit()

    result = service.convert_wallet_units(
        session,
        user=user,
        amount=Decimal("1"),
        source_unit=LedgerUnit.COIN,
        actor=user,
        idempotency_key="convert-1-coin",
    )
    session.commit()

    platform_credit = service.ensure_platform_account(session, LedgerUnit.CREDIT)

    assert result.source_amount == Decimal("1.0000")
    assert result.target_amount == Decimal("100.0000")
    assert service.get_balance(session, coin_account) == Decimal("1.0000")
    assert service.get_balance(session, credit_account) == Decimal("100.0000")
    assert service.get_balance(session, platform_coin) == Decimal("-1.0000")
    assert service.get_balance(session, platform_credit) == Decimal("-100.0000")


def test_wallet_transaction_service_rolls_back_unbalanced_transaction(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    session.commit()
    SessionLocal = sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
    transaction_service = WalletTransactionService(session_factory=SessionLocal, wallet_service=service)

    with pytest.raises(UnbalancedTransactionError, match="must net to zero"):
        transaction_service.post_transaction(
            postings=[
                WalletTransactionPosting(wallet_id=user_account.id, amount=Decimal("-10")),
                WalletTransactionPosting(wallet_id=platform_account.id, amount=Decimal("5")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="atomic-unbalanced",
        )

    session.expire_all()

    assert (
        session.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.reference == "atomic-unbalanced")
        )
        == 0
    )
    assert (
        session.scalar(
            select(func.count()).select_from(LedgerEntry).where(LedgerEntry.reference == "atomic-unbalanced")
        )
        == 0
    )


def test_wallet_transaction_service_reuses_idempotency_key_across_atomic_calls(session) -> None:
    user = _create_user(session)
    cache_backend = FakeCacheBackend()
    service = WalletService(cache_backend=cache_backend)
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    SessionLocal = sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
    transaction_service = WalletTransactionService(
        session_factory=SessionLocal,
        wallet_service=WalletService(cache_backend=cache_backend),
    )

    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("20")),
            LedgerPosting(account=platform_account, amount=Decimal("-20")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-atomic-idempotent",
        actor=user,
    )
    session.commit()

    first = transaction_service.post_transaction(
        postings=[
            WalletTransactionPosting(wallet_id=user_account.id, amount=Decimal("-4")),
            WalletTransactionPosting(wallet_id=platform_account.id, amount=Decimal("4")),
        ],
        reason=LedgerEntryReason.TRADE_SETTLEMENT,
        reference="atomic-idempotent",
        actor_user_id=user.id,
        idempotency_key="wallet-atomic-idempotent",
    )
    second = transaction_service.post_transaction(
        postings=[
            WalletTransactionPosting(wallet_id=user_account.id, amount=Decimal("-4")),
            WalletTransactionPosting(wallet_id=platform_account.id, amount=Decimal("4")),
        ],
        reason=LedgerEntryReason.TRADE_SETTLEMENT,
        reference="atomic-idempotent",
        actor_user_id=user.id,
        idempotency_key="wallet-atomic-idempotent",
    )

    session.expire_all()

    assert first.transaction_id == second.transaction_id
    assert service.get_balance(session, user_account) == Decimal("16.0000")
    assert (
        session.scalar(
            select(func.count())
            .select_from(LedgerTransaction)
            .where(LedgerTransaction.idempotency_key == "wallet-atomic-idempotent")
        )
        == 1
    )


def test_request_payout_holds_total_and_tracks_fee(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("100")),
            LedgerPosting(account=platform_account, amount=Decimal("-100")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-payout",
        actor=user,
    )
    result = service.request_payout(
        session,
        user=user,
        amount=Decimal("20"),
        destination_reference="bank:0012345678",
        withdrawal_fee_bps=1000,
        minimum_fee=Decimal("0.0000"),
        source_scope="trade",
        actor=user,
    )
    session.commit()

    escrow_account = service.get_user_escrow_account(session, user, LedgerUnit.COIN)
    hold_entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == result.payout_request.hold_transaction_id)
    ).all()
    assert result.fee_amount == Decimal("2.0000")
    assert result.total_debit == Decimal("22.0000")
    assert service.get_balance(session, user_account) == Decimal("78.0000")
    assert service.get_balance(session, escrow_account) == Decimal("22.0000")
    assert {entry.transaction_type for entry in hold_entries} == {LedgerTransactionType.WITHDRAWAL}
    assert sum(
        entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT
    ) == Decimal("0.0000")
    assert sum(
        entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN
    ) == Decimal("0.0000")
    assert sorted(entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT) == [
        Decimal("-20.0000"),
        Decimal("20.0000"),
    ]
    assert sorted(
        entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN
    ) == [
        Decimal("-2.0000"),
        Decimal("2.0000"),
    ]


def test_complete_payout_request_tags_only_fee_entries_as_fee_burn(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("100")),
            LedgerPosting(account=platform_account, amount=Decimal("-100")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-complete-payout",
        actor=user,
    )
    result = service.request_payout(
        session,
        user=user,
        amount=Decimal("20"),
        destination_reference="bank:0012345678",
        withdrawal_fee_bps=1000,
        minimum_fee=Decimal("0.0000"),
        source_scope="trade",
        actor=user,
    )
    payout_request = service.complete_payout_request(session, result.payout_request, actor=user)
    session.commit()

    settlement_entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == payout_request.settlement_transaction_id)
    ).all()
    assert {entry.transaction_type for entry in settlement_entries} == {LedgerTransactionType.WITHDRAWAL}
    assert sorted(
        entry.amount for entry in settlement_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT
    ) == [
        Decimal("-20.0000"),
        Decimal("20.0000"),
    ]
    assert sorted(
        entry.amount for entry in settlement_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN
    ) == [
        Decimal("-2.0000"),
        Decimal("2.0000"),
    ]


def test_request_competition_payout_requires_reward_balance(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("50")),
            LedgerPosting(account=platform_account, amount=Decimal("-50")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-wallet",
        actor=user,
    )
    with pytest.raises(InsufficientBalanceError, match="Competition reward balance"):
        service.request_payout(
            session,
            user=user,
            amount=Decimal("10"),
            destination_reference="bank:0012345678",
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("0.0000"),
            source_scope="competition",
            actor=user,
        )


def test_request_payout_rejects_unknown_source_scope(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("25")),
            LedgerPosting(account=platform_account, amount=Decimal("-25")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-scope",
        actor=user,
    )
    with pytest.raises(
        LedgerError,
        match="Withdrawal source must be trade, competition, user_hosted_gift, gtex_competition_gift, or national_reward",
    ):
        service.request_payout(
            session,
            user=user,
            amount=Decimal("5"),
            destination_reference="bank:0012345678",
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("0.0000"),
            source_scope="bonus",
            actor=user,
        )
