from __future__ import annotations

from decimal import Decimal
import json
from shutil import copyfile
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import pytest

from app.auth.router import register_user
from app.auth.schemas import RegisterRequest
from app.core.database import ensure_database_schema_current
from app.models.treasury import PaymentMode
from app.models.policy import CountryFeaturePolicy
from app.models.user import User
from app.models.user_wallet import WalletTransactionRecord
from app.treasury.service import TreasuryService
from app.wallets.router import (
    create_purchase_order,
    create_purchase_order_quote,
    create_payment_event,
    create_wallet_conversion,
    get_wallet_profile,
    initiate_wallet_top_up,
    list_wallet_accounts,
    list_wallet_transactions,
    quote_wallet_conversion,
    verify_wallet_top_up,
)
from app.wallets.schemas import (
    PaymentEventCreate,
    PurchaseOrderCreateRequest,
    PurchaseOrderQuoteRequest,
    WalletConversionQuoteRequest,
    WalletConversionRequest,
    WalletTopUpInitiateRequest,
    WalletTopUpVerifyRequest,
)
from app.wallets.service import LedgerPosting, WalletService
from app.models.wallet import LedgerEntryReason, LedgerUnit


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


@pytest.fixture(scope="session")
def migrated_wallet_router_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("wallet-router-db") / "template.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    engine.dispose()
    return db_path


@pytest.fixture()
def session(tmp_path, migrated_wallet_router_db):
    db_path = tmp_path / "wallet-router.db"
    copyfile(migrated_wallet_router_db, db_path)
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def _register_and_load_user(session) -> User:
    response = register_user(
        RegisterRequest(
            email="fan@example.com",
            region_code="NG",
            username="fanuser",
            password="SuperSecret1",  # pragma: allowlist secret
        ),
        session,
    )
    return session.get(User, response.user.id)


def _seed_global_policy(session) -> None:
    session.add(
        CountryFeaturePolicy(
            country_code="GLOBAL",
            bucket_type="default",
            deposits_enabled=True,
            market_trading_enabled=True,
            platform_reward_withdrawals_enabled=True,
            user_hosted_gift_withdrawals_enabled=True,
            gtex_competition_gift_withdrawals_enabled=True,
            national_reward_withdrawals_enabled=True,
            one_time_region_change_after_days=180,
            active=True,
        )
    )
    session.commit()


def _enable_automatic_deposits(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_mode = PaymentMode.AUTOMATIC
    session.commit()


def test_list_wallet_accounts_returns_default_coin_and_credit_accounts(session) -> None:
    current_user = _register_and_load_user(session)

    payload = list_wallet_accounts(session=session, current_user=current_user)
    assert {account.unit.value for account in payload} == {"coin", "credit"}
    assert {Decimal(account.balance) for account in payload} == {Decimal("0.0000")}


def test_create_payment_event_route_returns_pending_event(session) -> None:
    current_user = _register_and_load_user(session)
    _seed_global_policy(session)
    _enable_automatic_deposits(session)

    payload = create_payment_event(
        PaymentEventCreate(
            provider="paystack",
            provider_reference="paystack-ref-001",
            amount=Decimal("50"),
            pack_code="starter-50",
        ),
        session=session,
        current_user=current_user,
    )
    assert payload.status.value == "pending"
    assert Decimal(payload.amount) == Decimal("50.0000")


def test_quote_wallet_conversion_returns_fixed_rate_quote(session) -> None:
    current_user = _register_and_load_user(session)

    payload = quote_wallet_conversion(
        WalletConversionQuoteRequest(amount=Decimal("1"), source_unit=LedgerUnit.COIN),
        session=session,
        current_user=current_user,
    )

    assert payload.source_amount == Decimal("1.0000")
    assert payload.target_amount == Decimal("100.0000")
    assert payload.target_unit == LedgerUnit.CREDIT


def test_create_wallet_conversion_route_moves_balance(session) -> None:
    current_user = _register_and_load_user(session)
    wallet_service = WalletService()
    user_coin_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)
    platform_coin_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_coin_account, amount=Decimal("2")),
            LedgerPosting(account=platform_coin_account, amount=Decimal("-2")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-router-conversion",
        actor=current_user,
    )
    session.commit()

    payload = create_wallet_conversion(
        WalletConversionRequest(
            amount=Decimal("1"),
            source_unit=LedgerUnit.COIN,
            idempotency_key="router-convert-1-coin",
        ),
        session=session,
        current_user=current_user,
    )

    user_credit_account = wallet_service.get_user_account(session, current_user, LedgerUnit.CREDIT)
    assert payload.transaction_id
    assert payload.source_amount == Decimal("1.0000")
    assert payload.target_amount == Decimal("100.0000")
    assert wallet_service.get_balance(session, user_coin_account) == Decimal("1.0000")
    assert wallet_service.get_balance(session, user_credit_account) == Decimal("100.0000")


def test_create_wallet_conversion_route_refreshes_shared_wallet_summary_cache(session) -> None:
    current_user = _register_and_load_user(session)
    cache_backend = FakeCacheBackend()
    wallet_service = WalletService(cache_backend=cache_backend)
    user_coin_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)
    platform_coin_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_coin_account, amount=Decimal("2")),
            LedgerPosting(account=platform_coin_account, amount=Decimal("-2")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-router-conversion-cache",
        actor=current_user,
    )
    session.commit()
    wallet_service.get_wallet_summary(session, current_user, currency=LedgerUnit.COIN)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                event_publisher=None,
                cache_backend=cache_backend,
            )
        )
    )

    create_wallet_conversion(
        WalletConversionRequest(
            amount=Decimal("1"),
            source_unit=LedgerUnit.COIN,
            idempotency_key="router-convert-cache-1-coin",
        ),
        session=session,
        current_user=current_user,
        request=request,
    )

    coin_payload = json.loads(
        cache_backend.values[wallet_service._wallet_summary_cache_key(current_user.id, LedgerUnit.COIN)]
    )
    credit_payload = json.loads(
        cache_backend.values[wallet_service._wallet_summary_cache_key(current_user.id, LedgerUnit.CREDIT)]
    )

    assert coin_payload["balance"] == "1.0000"
    assert credit_payload["balance"] == "100.0000"


def test_wallet_top_up_flow_creates_transaction_and_updates_balance(session) -> None:
    current_user = _register_and_load_user(session)
    _seed_global_policy(session)
    _enable_automatic_deposits(session)

    initiated = initiate_wallet_top_up(
        WalletTopUpInitiateRequest(amount=Decimal("250")),
        session=session,
        current_user=current_user,
    )
    assert initiated.reference
    assert initiated.payment_link
    assert initiated.status == "pending"
    assert initiated.mock_mode is True

    pending_wallet = get_wallet_profile(session=session, current_user=current_user)
    pending_transactions = list_wallet_transactions(session=session, current_user=current_user)
    assert pending_wallet.balance == Decimal("0.0000")
    assert len(pending_transactions) == 1
    assert pending_transactions[0].reference == initiated.reference
    assert pending_transactions[0].status == "pending"

    verified = verify_wallet_top_up(
        WalletTopUpVerifyRequest(reference=initiated.reference),
        session=session,
        current_user=current_user,
    )
    session.expire_all()

    stored_transaction = session.scalar(
        select(WalletTransactionRecord).where(WalletTransactionRecord.reference == initiated.reference)
    )
    assert verified.wallet.balance == Decimal("246.2500")
    assert verified.wallet.currency == "coin"
    assert verified.transaction.status == "verified"
    assert stored_transaction is not None
    assert stored_transaction.status == "verified"


def test_wallet_top_up_can_credit_fan_coin_balance(session) -> None:
    current_user = _register_and_load_user(session)
    _seed_global_policy(session)
    _enable_automatic_deposits(session)

    initiated = initiate_wallet_top_up(
        WalletTopUpInitiateRequest(amount=Decimal("250"), unit=LedgerUnit.CREDIT),
        session=session,
        current_user=current_user,
    )

    assert initiated.currency == "credit"
    verified = verify_wallet_top_up(
        WalletTopUpVerifyRequest(reference=initiated.reference),
        session=session,
        current_user=current_user,
    )
    wallet_service = WalletService()
    fan_account = wallet_service.get_user_account(session, current_user, LedgerUnit.CREDIT)
    coin_account = wallet_service.get_user_account(session, current_user, LedgerUnit.COIN)

    assert verified.transaction.status == "verified"
    assert wallet_service.get_balance(session, fan_account) == Decimal("246.2500")
    assert wallet_service.get_balance(session, coin_account) == Decimal("0.0000")


def test_wallet_top_up_rejects_missing_paystack_secret_in_production(session, monkeypatch) -> None:
    current_user = _register_and_load_user(session)
    _seed_global_policy(session)
    _enable_automatic_deposits(session)
    monkeypatch.setenv("GTE_APP_ENV", "production")
    monkeypatch.delenv("GTE_PAYSTACK_SECRET_KEY", raising=False)
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        initiate_wallet_top_up(
            WalletTopUpInitiateRequest(amount=Decimal("250")),
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 400
    assert "Paystack is not configured" in str(exc_info.value.detail)


def test_purchase_order_quote_rejects_stub_provider(session) -> None:
    current_user = _register_and_load_user(session)
    _seed_global_policy(session)
    _enable_automatic_deposits(session)

    with pytest.raises(HTTPException) as exc_info:
        create_purchase_order_quote(
            PurchaseOrderQuoteRequest(
                amount=Decimal("25"),
                input_unit="fiat",
                provider_key="cards",
                unit=LedgerUnit.COIN,
            ),
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert "not currently available" in str(exc_info.value.detail)


def test_purchase_order_create_rejects_stub_provider(session) -> None:
    current_user = _register_and_load_user(session)
    _seed_global_policy(session)
    _enable_automatic_deposits(session)

    with pytest.raises(HTTPException) as exc_info:
        create_purchase_order(
            PurchaseOrderCreateRequest(
                amount=Decimal("25"),
                input_unit="fiat",
                provider_key="apple_pay",
                unit=LedgerUnit.COIN,
            ),
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert "not currently available" in str(exc_info.value.detail)
