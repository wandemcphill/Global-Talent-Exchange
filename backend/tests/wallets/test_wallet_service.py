from __future__ import annotations

from decimal import Decimal
import json

from sqlalchemy import func, select
import pytest

from app.auth.service import AuthService
from app.models import LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit, PaymentStatus
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerTransaction, LedgerTransactionStatus
from app.wallets.service import (
    InsufficientBalanceError,
    LedgerError,
    LedgerPosting,
    UnbalancedTransactionError,
    WalletBalanceUnavailableError,
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


@pytest.fixture()
def session(gtex_db_session):
    # Shared full-schema engine with per-test rollback; avoids per-file migration/copy setup.
    yield gtex_db_session


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
        provider="korapay",
        provider_reference="korapay-ref-001",
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
        provider="korapay",
        provider_reference="korapay-ref-idempotent-001",
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
    assert summary.locked_balance == Decimal("0.0000")
    assert summary.pending_withdrawal_balance == Decimal("0.0000")
    assert summary.lock_reasons == ()
    assert cache_backend.values[service._wallet_summary_cache_key(user.id, LedgerUnit.CREDIT)]


def test_get_wallet_summary_blocks_explicit_null_cached_balance(session) -> None:
    user = _create_user(session)
    cache_backend = FakeCacheBackend()
    service = WalletService(cache_backend=cache_backend)
    cache_backend.values[service._wallet_summary_cache_key(user.id, LedgerUnit.COIN)] = json.dumps(
        {
            "user_id": user.id,
            "currency": LedgerUnit.COIN.value,
            "balance": None,
            "locked": "0.0000",
            "total": "0.0000",
        }
    )

    with pytest.raises(WalletBalanceUnavailableError, match="Balance data unavailable"):
        service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)


def test_get_balance_blocks_explicit_null_cached_balance(session) -> None:
    user = _create_user(session)
    cache_backend = FakeCacheBackend()
    service = WalletService(cache_backend=cache_backend)
    account = service.get_user_account(session, user, LedgerUnit.COIN)
    session.commit()
    cache_backend.values[service._balance_cache_key(account.id)] = json.dumps(
        {
            "account_id": account.id,
            "account_code": account.code,
            "owner_user_id": user.id,
            "unit": LedgerUnit.COIN.value,
            "balance": None,
        }
    )

    with pytest.raises(WalletBalanceUnavailableError, match="Balance data unavailable"):
        service.get_balance(session, account)


def test_get_wallet_summary_derives_structured_transfer_bid_lock_reasons(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("120")),
            LedgerPosting(account=platform_account, amount=Decimal("-120")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-transfer-bid-lock",
        actor=user,
    )
    session.commit()

    service.reserve_transfer_bid_funds(
        session,
        user=user,
        transfer_bid_id="bid-structured-1",
        amount=Decimal("35"),
        unit=LedgerUnit.COIN,
        actor=user,
    )
    session.commit()

    summary = service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)

    assert summary.available_balance == Decimal("85.0000")
    assert summary.reserved_balance == Decimal("35.0000")
    assert summary.locked_balance == Decimal("35.0000")
    assert summary.pending_withdrawal_balance == Decimal("0.0000")
    assert len(summary.lock_reasons) == 1
    reason = summary.lock_reasons[0]
    assert reason.code == "transfer_bid_reservation"
    assert reason.label == "Transfer bid reservations"
    assert reason.amount == Decimal("35.0000")
    assert reason.currency == LedgerUnit.COIN
    assert reason.source == "transfer_bid"
    assert reason.reference == "transfer_bid:bid-structured-1"


def test_replace_transfer_bid_reservation_leaves_exact_replacement_hold(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("120")),
            LedgerPosting(account=platform_account, amount=Decimal("-120")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-transfer-bid-replace",
        actor=user,
    )
    session.commit()

    service.reserve_transfer_bid_funds(
        session,
        user=user,
        transfer_bid_id="bid-replace-1",
        amount=Decimal("35"),
        unit=LedgerUnit.COIN,
        actor=user,
    )
    session.commit()

    service.replace_transfer_bid_reservation(
        session,
        user=user,
        transfer_bid_id="bid-replace-1",
        replacement_amount=Decimal("55"),
        unit=LedgerUnit.COIN,
        release_reason="counter",
        actor=user,
    )
    session.commit()

    assert service.get_transfer_bid_reserved_amount(
        session,
        user=user,
        transfer_bid_id="bid-replace-1",
        unit=LedgerUnit.COIN,
    ) == Decimal("55.0000")
    summary = service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)

    assert summary.available_balance == Decimal("65.0000")
    assert summary.reserved_balance == Decimal("55.0000")
    assert summary.locked_balance == Decimal("55.0000")
    assert len(summary.lock_reasons) == 1
    reason = summary.lock_reasons[0]
    assert reason.code == "transfer_bid_reservation"
    assert reason.amount == Decimal("55.0000")
    assert reason.reference == "transfer_bid:bid-replace-1"


def test_release_transfer_bid_reservation_withdrawn_is_idempotent(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("75")),
            LedgerPosting(account=platform_account, amount=Decimal("-75")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-transfer-bid-withdrawn",
        actor=user,
    )
    session.commit()

    service.reserve_transfer_bid_funds(
        session,
        user=user,
        transfer_bid_id="bid-withdrawn-1",
        amount=Decimal("25"),
        unit=LedgerUnit.COIN,
        actor=user,
    )
    session.commit()

    first_release = service.release_transfer_bid_reservation(
        session,
        user=user,
        transfer_bid_id="bid-withdrawn-1",
        release_reason="withdrawn",
        unit=LedgerUnit.COIN,
        actor=user,
    )
    session.commit()
    transaction_count_after_release = session.scalar(
        select(func.count()).select_from(LedgerTransaction)
    )

    second_release = service.release_transfer_bid_reservation(
        session,
        user=user,
        transfer_bid_id="bid-withdrawn-1",
        release_reason="withdrawn",
        unit=LedgerUnit.COIN,
        actor=user,
    )
    session.commit()

    assert first_release
    assert second_release == []
    assert session.scalar(select(func.count()).select_from(LedgerTransaction)) == transaction_count_after_release
    assert service.get_transfer_bid_reserved_amount(
        session,
        user=user,
        transfer_bid_id="bid-withdrawn-1",
        unit=LedgerUnit.COIN,
    ) == Decimal("0.0000")
    summary = service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    assert summary.available_balance == Decimal("75.0000")
    assert summary.reserved_balance == Decimal("0.0000")
    assert summary.locked_balance == Decimal("0.0000")
    assert summary.lock_reasons == ()


def test_get_wallet_summary_derives_pending_withdrawal_balance_from_backend_payouts(session) -> None:
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
        reference="seed-withdrawal-lock",
        actor=user,
    )
    session.commit()

    service.request_payout(
        session,
        user=user,
        amount=Decimal("20"),
        destination_reference="bank:test",
        unit=LedgerUnit.COIN,
        source_scope="trade",
        actor=user,
    )
    session.commit()

    summary = service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)

    assert summary.available_balance == Decimal("80.0000")
    assert summary.reserved_balance == Decimal("20.0000")
    assert summary.locked_balance == Decimal("20.0000")
    assert summary.pending_withdrawal_balance == Decimal("20.0000")
    assert len(summary.lock_reasons) == 1
    reason = summary.lock_reasons[0]
    assert reason.code == "withdrawal_hold"
    assert reason.label == "Withdrawal holds"
    assert reason.amount == Decimal("20.0000")
    assert reason.currency == LedgerUnit.COIN
    assert reason.source == "withdrawal"


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


def test_wallet_transaction_service_rolls_back_unbalanced_transaction(gtex_db_session_factory) -> None:
    SessionLocal = gtex_db_session_factory
    with SessionLocal() as session:
        user = _create_user(session)
        service = WalletService()
        user_account = service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
        session.commit()
        user_account_id = user_account.id
        platform_account_id = platform_account.id

    service = WalletService()
    transaction_service = WalletTransactionService(session_factory=SessionLocal, wallet_service=service)

    with pytest.raises(UnbalancedTransactionError, match="must net to zero"):
        transaction_service.post_transaction(
            postings=[
                WalletTransactionPosting(wallet_id=user_account_id, amount=Decimal("-10")),
                WalletTransactionPosting(wallet_id=platform_account_id, amount=Decimal("5")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="atomic-unbalanced",
        )

    with SessionLocal() as session:
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


def test_wallet_transaction_service_reuses_idempotency_key_across_atomic_calls(gtex_db_session_factory) -> None:
    SessionLocal = gtex_db_session_factory
    cache_backend = FakeCacheBackend()
    transaction_service = WalletTransactionService(
        session_factory=SessionLocal,
        wallet_service=WalletService(cache_backend=cache_backend),
    )

    with SessionLocal() as session:
        user = _create_user(session)
        service = WalletService(cache_backend=cache_backend)
        user_account = service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
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
        user_id = user.id
        user_account_id = user_account.id
        platform_account_id = platform_account.id

    first = transaction_service.post_transaction(
        postings=[
            WalletTransactionPosting(wallet_id=user_account_id, amount=Decimal("-4")),
            WalletTransactionPosting(wallet_id=platform_account_id, amount=Decimal("4")),
        ],
        reason=LedgerEntryReason.TRADE_SETTLEMENT,
        reference="atomic-idempotent",
        actor_user_id=user_id,
        idempotency_key="wallet-atomic-idempotent",
    )
    second = transaction_service.post_transaction(
        postings=[
            WalletTransactionPosting(wallet_id=user_account_id, amount=Decimal("-4")),
            WalletTransactionPosting(wallet_id=platform_account_id, amount=Decimal("4")),
        ],
        reason=LedgerEntryReason.TRADE_SETTLEMENT,
        reference="atomic-idempotent",
        actor_user_id=user_id,
        idempotency_key="wallet-atomic-idempotent",
    )

    with SessionLocal() as session:
        service = WalletService(cache_backend=cache_backend)
        user_account = session.get(LedgerAccount, user_account_id)
        assert user_account is not None
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
    assert result.net_amount == Decimal("18.0000")
    assert result.total_debit == Decimal("20.0000")
    assert result.payout_request.amount == Decimal("18.0000")
    assert service.get_balance(session, user_account) == Decimal("80.0000")
    assert service.get_balance(session, escrow_account) == Decimal("20.0000")
    assert {entry.transaction_type for entry in hold_entries} == {LedgerTransactionType.WITHDRAWAL}
    assert sum(
        entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT
    ) == Decimal("0.0000")
    assert sum(
        entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN
    ) == Decimal("0.0000")
    assert sorted(entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT) == [
        Decimal("-18.0000"),
        Decimal("18.0000"),
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
        Decimal("-18.0000"),
        Decimal("18.0000"),
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


def test_request_competition_payout_reserves_gross_reward_and_net_payout(session) -> None:
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
        reason=LedgerEntryReason.COMPETITION_REWARD,
        reference="seed-competition-reward",
        actor=user,
    )

    result = service.request_payout(
        session,
        user=user,
        amount=Decimal("20"),
        destination_reference="bank:reward",
        withdrawal_fee_bps=1000,
        minimum_fee=Decimal("0.0000"),
        source_scope="competition",
        actor=user,
    )
    session.commit()

    assert result.gross_amount == Decimal("20.0000")
    assert result.fee_amount == Decimal("2.0000")
    assert result.net_amount == Decimal("18.0000")
    assert result.total_debit == Decimal("20.0000")
    assert result.payout_request.amount == Decimal("18.0000")
    assert service.competition_reward_withdrawable_balance(session, user) == Decimal("30.0000")


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
