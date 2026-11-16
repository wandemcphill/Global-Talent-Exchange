"""Regression tests for coin pricing, trader spread, and withdrawal rate fixes."""

from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.treasury import RateDirection, TreasurySettings
from app.models.user import KycStatus, PublicAccountType
from app.models.wallet import LedgerUnit
from app.owner_console import ledger, money
from app.treasury.schemas import TreasurySettingsUpdate
from app.treasury.service import TreasuryService
from app.wallets.rail_service import WalletRailService
from backend.tests.support.secrets import TEST_PASSWORD


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    load_model_modules()
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        yield db_session


def _create_user(
    session,
    *,
    email: str,
    username: str,
    account_type: PublicAccountType = PublicAccountType.USER,
    kyc_status: KycStatus = KycStatus.VERIFIED,
):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password=TEST_PASSWORD,
        account_type=account_type,
    )
    user.kyc_status = kyc_status
    session.flush()
    return user


def test_treasury_settings_column_defaults_match_rebalanced_spread(session) -> None:
    """Ensure freshly created TreasurySettings rows pick up rebalanced defaults."""
    settings = TreasurySettings()
    session.add(settings)
    session.flush()

    assert settings.fan_coin_deposit_rate_value == Decimal("4.0000")
    assert settings.trader_coin_purchase_rate_value == Decimal("50.0000")
    assert settings.trader_fan_coin_purchase_rate_value == Decimal("2.5000")
    assert settings.trader_withdrawal_rate_value == Decimal("50.0000")
    assert settings.min_trader_buy_rate_fiat == Decimal("48.0000")
    assert settings.max_trader_buy_rate_fiat == Decimal("50.0000")
    assert settings.min_trader_sell_rate_fiat == Decimal("53.0000")
    assert settings.max_trader_sell_rate_fiat == Decimal("59.0000")
    assert settings.max_trader_spread_fiat == Decimal("10.0000")
    assert settings.max_buy_above_withdrawal_fiat == Decimal("2.0000")
    assert settings.max_sell_below_deposit_fiat == Decimal("7.0000")


@pytest.mark.parametrize(
    "field_name",
    [
        "deposit_rate_value",
        "withdrawal_rate_value",
        "fan_coin_deposit_rate_value",
        "trader_coin_purchase_rate_value",
        "trader_fan_coin_purchase_rate_value",
        "trader_withdrawal_rate_value",
    ],
)
@pytest.mark.parametrize("bad_value", [Decimal("0"), Decimal("-1.0000")])
def test_treasury_settings_update_rejects_non_positive_exchange_rates(
    field_name: str,
    bad_value: Decimal,
) -> None:
    """Exchange rate overrides must stay strictly positive while guardrails may be zero."""
    with pytest.raises(ValidationError):
        TreasurySettingsUpdate(**{field_name: bad_value})

    accepted = TreasurySettingsUpdate(min_deposit=Decimal("0.0000"), **{field_name: Decimal("1.0000")})
    assert getattr(accepted, field_name) == Decimal("1.0000")
    assert accepted.min_deposit == Decimal("0.0000")


def test_owner_console_treasury_rates_and_withdrawal_use_trader_rate(session, monkeypatch) -> None:
    """Owner console withdrawals apply trader_withdrawal_rate_value only to COIN_TRADER users."""
    monkeypatch.setenv("GTEX_WITHDRAWAL_COUNTRIES", "NG")
    monkeypatch.setenv("GTEX_KYC_THRESHOLD_COIN", "100")
    monkeypatch.setenv("GTEX_WITHDRAWAL_MIN_INTEGRITY", "50")

    settings = TreasuryService().ensure_settings(session)
    settings.withdrawal_rate_value = Decimal("48.0000")
    settings.withdrawal_rate_direction = RateDirection.FIAT_PER_COIN
    settings.trader_withdrawal_rate_value = Decimal("50.0000")
    session.flush()

    rates = money.treasury_rates(session)
    assert rates["withdrawal_rate"] == Decimal("48.0000")
    assert rates["trader_withdrawal_rate"] == Decimal("50.0000")

    normal_user = _create_user(session, email="normal-wd@example.com", username="normalwd")
    trader_user = _create_user(
        session,
        email="trader-wd@example.com",
        username="traderwd",
        account_type=PublicAccountType.COIN_TRADER,
    )

    for idx, account in enumerate((normal_user, trader_user), start=1):
        session.add(
            ClubProfile(
                owner_user_id=account.id,
                club_name=f"Withdrawal Club {idx}",
                slug=f"withdrawal-club-{idx}",
                primary_color="#000000",
                secondary_color="#FFFFFF",
                accent_color="#111111",
                country_code="NG",
            )
        )
        ledger.record(
            session,
            event_type="deposit",
            source=ledger.PAYSTACK,
            destination=ledger.user_account(account.id),
            currency=ledger.GTEX,
            gross=Decimal("50.00"),
            status="completed",
            user_id=account.id,
            balance_class="deposited",
        )
    session.flush()

    payload = {
        "amount_coin": 10,
        "bank_name": "GTBank",
        "account_number": "0123456789",
        "account_name": "Test Owner",
    }
    normal_withdrawal = money.request_withdrawal(session, normal_user, payload)
    trader_withdrawal = money.request_withdrawal(session, trader_user, payload)

    assert normal_withdrawal.amount_ngn == Decimal("480.00")
    assert trader_withdrawal.amount_ngn == Decimal("500.00")


def test_quote_purchase_order_uses_resolved_rate_direction_for_processor_fee(session) -> None:
    """Processor fee conversion must use the order's resolved rate_direction, not deposit_rate_direction."""
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_rate_direction = RateDirection.COIN_PER_FIAT
    settings.deposit_rate_value = Decimal("1.0000")
    settings.trader_coin_purchase_rate_value = Decimal("59.0000")
    settings.deposit_fee_bps = 0
    session.flush()

    quote = WalletRailService(session).quote_purchase_order(
        settings=settings,
        amount=Decimal("4000.0000"),
        input_unit="coin",
        provider_key="paystack",
        source_scope="trader_liquidity",
        unit=LedgerUnit.COIN,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
    )

    assert quote.rate_direction == RateDirection.FIAT_PER_COIN
    assert quote.total_fiat_charged == Decimal("236000.0000")
    # Paystack checkout fee on NGN 236,000 hits NGN 2,000 cap -> 2000 / 59 = 33.8983 coin
    assert quote.processor_fee == Decimal("33.8983")
