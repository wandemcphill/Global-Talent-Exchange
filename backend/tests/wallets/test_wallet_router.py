from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.router import register_user
from backend.app.auth.schemas import RegisterRequest
from backend.app.models import Base
from backend.app.models.treasury import PaymentMode
from backend.app.models.policy import CountryFeaturePolicy
from backend.app.models.user import User
from backend.app.treasury.service import TreasuryService
from backend.app.wallets.router import create_payment_event, list_wallet_accounts
from backend.app.wallets.schemas import PaymentEventCreate


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


def _register_and_load_user(session) -> User:
    response = register_user(
        RegisterRequest(
            email="fan@example.com",
            region_code="NG",
            username="fanuser",
            password="SuperSecret1",
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
            provider="monnify",
            provider_reference="monnify-ref-001",
            amount=Decimal("50"),
            pack_code="starter-50",
        ),
        session=session,
        current_user=current_user,
    )
    assert payload.status.value == "pending"
    assert Decimal(payload.amount) == Decimal("50.0000")
