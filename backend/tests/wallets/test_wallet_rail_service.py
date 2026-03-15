from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.service import AuthService
from backend.app.models import AmlCase, Base, LedgerUnit
from backend.app.models.fancoin_purchase_order import PurchaseOrderStatus
from backend.app.models.treasury import RateDirection
from backend.app.treasury.service import TreasuryService
from backend.app.wallets.rail_service import WalletRailService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session):
    user = AuthService().register_user(
        session,
        email="rails@example.com",
        username="railsuser",
        password="SuperSecret1",
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
    platform_account = rail_service.wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    assert rail_service.wallet_service.get_balance(session, user_account) == Decimal("98.5000")
    assert rail_service.wallet_service.get_balance(session, platform_account) == Decimal("-98.5000")

    order = rail_service.apply_purchase_order_status(order=order, status=PurchaseOrderStatus.REFUNDED, actor=user)
    assert order.status == PurchaseOrderStatus.REFUNDED
    assert rail_service.wallet_service.get_balance(session, user_account) == Decimal("0.0000")
    assert rail_service.wallet_service.get_balance(session, platform_account) == Decimal("0.0000")


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
