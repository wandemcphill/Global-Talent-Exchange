from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService
from app.core.database import load_model_modules
from app.models import AmlCase, Base, CountryFeaturePolicy, LedgerUnit
from app.models.fancoin_purchase_order import PurchaseOrderStatus
from app.models.risk_ops import SystemEvent
from app.models.treasury import PaymentMode, RateDirection
from app.treasury.service import TreasuryService
from app.wallets.providers.base import ProviderEvent, ProviderEventType
from app.wallets.providers.korapay import KoraPayProviderAdapter
from app.wallets.rail_service import WalletRailService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    load_model_modules()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session):
    user = AuthService().register_user(
        session,
        email="rails@example.com",
        username="railsuser",
        password=TEST_PASSWORD,
    )
    session.commit()
    return user


def _configure_deposit_settings(session) -> None:
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    settings.deposit_rate_value = Decimal("1.0000")
    settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_deposit = Decimal("0.0000")
    settings.max_deposit = Decimal("100000.0000")
    session.flush()


def test_purchase_order_lifecycle_and_fee_math(session) -> None:
    user = _create_user(session)
    _configure_deposit_settings(session)
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    rail_service = WalletRailService(session)
    order = rail_service.create_purchase_order(
        user=user,
        settings=settings,
        amount=Decimal("100.0000"),
        input_unit="fiat",
        provider_key="cards",
        source_scope="wallet",
        unit=LedgerUnit.CREDIT,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
    )
    assert order.fee_amount == Decimal("1.5000")
    assert order.net_amount == Decimal("98.5000")

    order = rail_service.settle_purchase_order(order=order, actor=user)
    user_account = rail_service.wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    clearing_account = rail_service.wallet_service.ensure_deposit_clearing_account(session, LedgerUnit.CREDIT)
    assert rail_service.wallet_service.get_balance(session, user_account) == Decimal("98.5000")
    assert rail_service.wallet_service.get_balance(session, clearing_account) == Decimal("-98.5000")

    order = rail_service.apply_purchase_order_status(order=order, status=PurchaseOrderStatus.REFUNDED, actor=user)
    assert order.status == PurchaseOrderStatus.REFUNDED
    assert rail_service.wallet_service.get_balance(session, user_account) == Decimal("0.0000")
    assert rail_service.wallet_service.get_balance(session, clearing_account) == Decimal("0.0000")


def test_purchase_order_risk_flags_aml_case(session) -> None:
    user = _create_user(session)
    _configure_deposit_settings(session)
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    rail_service = WalletRailService(session)
    rail_service.create_purchase_order(
        user=user,
        settings=settings,
        amount=Decimal("6000.0000"),
        input_unit="fiat",
        provider_key="cards",
        source_scope="wallet",
        unit=LedgerUnit.CREDIT,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
    )
    aml_case = session.scalar(select(AmlCase).where(AmlCase.user_id == user.id))
    assert aml_case is not None


def test_hybrid_mode_supports_manual_deposit_and_korapay_webhook(session) -> None:
    user = _create_user(session)
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
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    settings.deposit_mode = PaymentMode.HYBRID
    settings.deposit_rate_value = Decimal("1000.0000")
    settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_deposit = Decimal("0.0000")
    settings.max_deposit = Decimal("100000.0000")
    session.flush()

    manual_request = treasury.create_deposit_request(
        session,
        user=user,
        amount=Decimal("5000.0000"),
        input_unit="fiat",
    )

    rail_service = WalletRailService(session)
    order = rail_service.create_purchase_order(
        user=user,
        settings=settings,
        amount=Decimal("9000.0000"),
        input_unit="fiat",
        provider_key="korapay",
        source_scope="wallet",
        unit=LedgerUnit.COIN,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
        provider_reference="kora-ref-001",
    )
    event = KoraPayProviderAdapter().parse_webhook(
        {
            "event": "charge.success",
            "data": {
                "id": "kora-event-1",
                "reference": "kora-ref-001",
                "amount": "9000.0000",
                "currency": "NGN",
                "status": "success",
                "metadata": {"purchase_order_reference": order.reference},
            },
        }
    )
    assert event is not None

    settled = rail_service.handle_provider_event(event=event)

    assert manual_request.reference.startswith("DEP")
    assert settled is not None
    assert settled.status == PurchaseOrderStatus.SETTLED


def test_provider_webhook_does_not_auto_settle_duplicate_provider_reference(session) -> None:
    first_user = _create_user(session)
    second_user = AuthService().register_user(
        session,
        email="rails-duplicate@example.com",
        username="railsduplicate",
        password=TEST_PASSWORD,
    )
    _configure_deposit_settings(session)
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    rail_service = WalletRailService(session)
    first_order = rail_service.create_purchase_order(
        user=first_user,
        settings=settings,
        amount=Decimal("90.0000"),
        input_unit="fiat",
        provider_key="korapay",
        source_scope="wallet",
        unit=LedgerUnit.COIN,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
        provider_reference="dup-webhook-ref",
    )
    second_order = rail_service.create_purchase_order(
        user=second_user,
        settings=settings,
        amount=Decimal("90.0000"),
        input_unit="fiat",
        provider_key="korapay",
        source_scope="wallet",
        unit=LedgerUnit.COIN,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
        provider_reference="dup-webhook-ref",
    )

    settled = rail_service.handle_provider_event(
        event=ProviderEvent(
            provider_key="korapay",
            event_type=ProviderEventType.SETTLED,
            provider_reference="dup-webhook-ref",
            purchase_order_reference=None,
            event_id="dup-webhook-event-1",
            amount=Decimal("90.0000"),
            currency="NGN",
            raw_payload={"reference": "dup-webhook-ref"},
        )
    )

    duplicate_event = session.scalar(
        select(SystemEvent).where(
            SystemEvent.event_key == "purchase-order-duplicate-provider-reference-korapay-dup-webhook-ref"
        )
    )

    assert settled is None
    assert duplicate_event is not None
    assert first_order.status == PurchaseOrderStatus.PROCESSING
    assert second_order.status == PurchaseOrderStatus.PROCESSING
