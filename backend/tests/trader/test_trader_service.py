from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_wallet_user, get_session
from app.auth.schemas import TraderSignupRequest
from app.auth.service import AuthService
from app.models import Base
from app.models.coin_trader import CoinTraderProfile, CoinTraderProfileStatus
from app.models.trader import TraderMarket, TraderOrderSide, TraderSecurity
from app.models.user import PublicAccountType
from app.trader.router import api_router
from app.trader.service import TraderAccessError, TraderMarketNotFoundError, TraderService, _totp
from backend.tests.support.secrets import TEST_PASSWORD
from backend.tests.support.signup_payloads import trader_credential_pbkdf2


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


def _create_trader(session):
    return AuthService().register_user(
        session,
        email="trader@example.com",
        username="trader",
        password=TEST_PASSWORD,
        display_name="Trader",
        account_type=PublicAccountType.COIN_TRADER,
    )


def _create_football_user(session):
    return AuthService().register_user(
        session,
        email="football@example.com",
        username="football",
        password=TEST_PASSWORD,
        display_name="Football User",
        account_type=PublicAccountType.USER,
    )


def _current_totp(secret: str) -> str:
    return _totp(secret, int(time.time()) // 30)


def _approve_trader_profile(session, trader) -> CoinTraderProfile:
    now = datetime.now(timezone.utc)
    profile = CoinTraderProfile(
        user_id=trader.id,
        display_name=trader.display_name or trader.username,
        status=CoinTraderProfileStatus.APPROVED.value,
        verification_level="fully_verified",
        verified_at=now,
        approved_at=now,
    )
    session.add(profile)
    session.flush()
    return profile


def test_trader_orders_require_existing_market(session) -> None:
    trader = _create_trader(session)
    _approve_trader_profile(session, trader)
    service = TraderService(session)

    with pytest.raises(TraderMarketNotFoundError, match="Trader market not found"):
        service.place_order(
            trader,
            market_id="missing-market",
            side=TraderOrderSide.BUY,
            quantity=Decimal("1"),
            limit_price=Decimal("1.25"),
        )


def test_trader_orders_reject_unverified_trader(session) -> None:
    trader = _create_trader(session)
    service = TraderService(session)

    with pytest.raises(TraderAccessError, match="Coin trader desk profile not found"):
        service.place_order(
            trader,
            market_id="missing-market",
            side=TraderOrderSide.BUY,
            quantity=Decimal("1"),
            limit_price=Decimal("1.25"),
        )


def test_trader_order_creation_stays_in_coin_trader_lane(session) -> None:
    football_user = _create_football_user(session)
    market = TraderMarket(
        symbol="GTEX",
        display_name="GTEX Coin",
        asset_type="gtex_coin",
        price=Decimal("1.0000"),
        daily_change_percent=Decimal("0.0000"),
        market_cap=Decimal("1000000.0000"),
        volume_24h=Decimal("10000.0000"),
        liquidity_score=90,
    )
    session.add(market)
    session.flush()

    with pytest.raises(TraderAccessError, match="Coin trader account access is required"):
        TraderService(session).place_order(
            football_user,
            market_id=market.id,
            side=TraderOrderSide.BUY,
            quantity=Decimal("1"),
            limit_price=Decimal("1.25"),
        )


def test_trader_security_endpoint_forbids_non_trader(session) -> None:
    football_user = _create_football_user(session)
    app = FastAPI()
    app.include_router(api_router)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_wallet_user] = lambda: football_user

    with TestClient(app) as client:
        response = client.get("/api/v2/trader/security")

    assert response.status_code == 403
    assert response.json()["detail"] == "Coin trader account access is required for this action."


def test_trader_security_rejects_invalid_totp(session) -> None:
    trader = _create_trader(session)

    with pytest.raises(TraderAccessError, match="Invalid authenticator code"):
        TraderService(session).verify_totp_setup(
            trader,
            totp_secret="JBSWY3DPEHPK3PXP",  # pragma: allowlist secret
            totp_code="000000",
            recovery_phrase_hash=trader_credential_pbkdf2(
                "recovery", "alpha bravo charlie delta echo foxtrot golf hotel"
            ),
            security_pin_hash=trader_credential_pbkdf2("pin", "654321"),
        )

    assert session.scalar(select(TraderSecurity).where(TraderSecurity.user_id == trader.id)) is None


def test_trader_security_rejects_placeholder_or_malformed_hashes(session) -> None:
    trader = _create_trader(session)
    secret = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret
    service = TraderService(session)

    with pytest.raises(TraderAccessError, match="recovery credential"):
        service.verify_totp_setup(
            trader,
            totp_secret=secret,
            totp_code=_current_totp(secret),
            recovery_phrase_hash="client-confirmed-placeholder-value",
            security_pin_hash=trader_credential_pbkdf2("pin", "654321"),
        )

    with pytest.raises(TraderAccessError, match="pin credential"):
        service.verify_totp_setup(
            trader,
            totp_secret=secret,
            totp_code=_current_totp(secret),
            recovery_phrase_hash=trader_credential_pbkdf2(
                "recovery", "alpha bravo charlie delta echo foxtrot golf hotel"
            ),
            security_pin_hash="placeholder-pin-hash",
        )

    assert session.scalar(select(TraderSecurity).where(TraderSecurity.user_id == trader.id)) is None


def test_trader_security_verification_returns_backup_codes_once(session) -> None:
    trader = _create_trader(session)
    secret = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret
    service = TraderService(session)

    first = service.verify_totp_setup(
        trader,
        totp_secret=secret,
        totp_code=_current_totp(secret),
        recovery_phrase_hash=trader_credential_pbkdf2("recovery", "alpha bravo charlie delta echo foxtrot golf hotel"),
        security_pin_hash=trader_credential_pbkdf2("pin", "654321"),
    )
    second = service.verify_totp_setup(
        trader,
        totp_secret=secret,
        totp_code=_current_totp(secret),
        recovery_phrase_hash=trader_credential_pbkdf2("recovery", "india juliet kilo lima mike november oscar papa"),
        security_pin_hash=trader_credential_pbkdf2("pin", "987654"),
    )

    assert first["two_factor_enabled"] is True
    assert first["backup_code_count"] == 8
    assert len(first["backup_codes"]) == 8
    assert second["backup_code_count"] == 8
    assert second["backup_codes"] == []


def test_trader_security_does_not_persist_raw_totp_secret(session) -> None:
    trader = _create_trader(session)
    secret = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret
    recovery_hash = trader_credential_pbkdf2("recovery", "alpha bravo charlie delta echo foxtrot golf hotel")
    pin_hash = trader_credential_pbkdf2("pin", "654321")

    TraderService(session).verify_totp_setup(
        trader,
        totp_secret=secret,
        totp_code=_current_totp(secret),
        recovery_phrase_hash=recovery_hash,
        security_pin_hash=pin_hash,
    )
    security = session.scalar(select(TraderSecurity).where(TraderSecurity.user_id == trader.id))

    assert security is not None
    assert security.totp_secret_hash != secret
    assert secret not in security.totp_secret_hash
    assert security.totp_secret_hash.startswith("pbkdf2-sha256$210000$totp$")
    assert security.recovery_phrase_hash == recovery_hash
    assert security.security_pin_hash == pin_hash
    assert all(
        secret not in backup_code_hash and backup_code_hash.startswith("pbkdf2-sha256$210000$backup$")
        for backup_code_hash in security.backup_codes_json
    )


def test_trader_security_read_hides_backup_codes(session) -> None:
    trader = _create_trader(session)
    secret = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret
    service = TraderService(session)
    service.verify_totp_setup(
        trader,
        totp_secret=secret,
        totp_code=_current_totp(secret),
        recovery_phrase_hash=trader_credential_pbkdf2("recovery", "alpha bravo charlie delta echo foxtrot golf hotel"),
        security_pin_hash=trader_credential_pbkdf2("pin", "654321"),
    )

    summary = service.security_summary(trader)

    assert summary["two_factor_enabled"] is True
    assert summary["backup_code_count"] == 8
    assert "backup_codes" not in summary
    assert len(summary["recent_events"]) == 1


def test_trader_signup_schema_no_longer_requires_recovery_phrase_or_security_pin() -> None:
    payload = TraderSignupRequest(
        full_name="Trader User",
        trading_alias="easy_desk",
        email="easy@example.com",
        password=TEST_PASSWORD,
        phone_number="+2348012345678",
        country="NG",
        preferred_currency="NGN",
        trading_experience="beginner",
        totp_secret="JBSWY3DPEHPK3PXP",  # pragma: allowlist secret
        totp_code="123456",
    )

    assert payload.recovery_phrase_hash is None
    assert payload.security_pin_hash is None


def test_totp_setup_succeeds_without_recovery_phrase_or_security_pin(session) -> None:
    trader = _create_trader(session)
    secret = "JBSWY3DPEHPK3PXP"  # pragma: allowlist secret

    result = TraderService(session).verify_totp_setup(
        trader,
        totp_secret=secret,
        totp_code=_current_totp(secret),
    )
    security = session.scalar(select(TraderSecurity).where(TraderSecurity.user_id == trader.id))

    assert result["two_factor_enabled"] is True
    assert result["backup_code_count"] == 8
    assert len(result["backup_codes"]) == 8
    assert security is not None
    assert security.recovery_phrase_hash is None
    assert security.security_pin_hash is None
