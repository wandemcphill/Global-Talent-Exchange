from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.coin_traders.schemas import CoinTraderAdminLiquidityRequest
from app.coin_traders.service import CoinTraderService
from app.models.base import Base
from app.models.coin_trader import CoinTraderProfile, CoinTraderProfileStatus, CoinTraderTier
from app.models.user import User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerUnit,
)
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _create_user(session, *, user_id: str, role: UserRole) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="test-hash",  # pragma: allowlist secret
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _create_trader(session, *, trader: User) -> CoinTraderProfile:
    profile = CoinTraderProfile(
        user_id=trader.id,
        display_name="Test Coin Trader",
        status=CoinTraderProfileStatus.APPROVED.value,
        tier=CoinTraderTier.GOLD.value,
        terms_json={},
        payment_methods_json=[],
        bank_accounts_json=[],
        liquidity_snapshot_json={},
        metadata_json={},
    )
    session.add(profile)
    session.flush()
    return profile


def _seed_liquidity_pool(session, amount: Decimal) -> LedgerAccount:
    wallet = WalletService()
    pool = LedgerAccount(
        code="platform:coin:liquidity_pool",
        label="Platform Coin Liquidity Pool",
        unit=LedgerUnit.COIN,
        kind=LedgerAccountKind.SYSTEM,
        allow_negative=False,
    )
    funding = LedgerAccount(
        code="test:coin:liquidity_funding",
        label="Test Coin Liquidity Funding",
        unit=LedgerUnit.COIN,
        kind=LedgerAccountKind.SYSTEM,
        allow_negative=True,
    )
    session.add_all([pool, funding])
    session.flush()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=funding, amount=-amount),
            LedgerPosting(account=pool, amount=amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference="test-liquidity-seed",
    )
    session.commit()
    return pool


def test_admin_issue_liquidity_cannot_create_coin_from_a_negative_pool(session) -> None:
    admin = _create_user(session, user_id="liquidity-admin", role=UserRole.ADMIN)
    trader = _create_user(session, user_id="liquidity-trader", role=UserRole.COIN_TRADER)
    profile = _create_trader(session, trader=trader)
    pool = _seed_liquidity_pool(session, Decimal("100.0000"))

    request = CoinTraderAdminLiquidityRequest(
        coin_unit=LedgerUnit.COIN,
        amount=Decimal("150.0000"),
        idempotency_key="liquidity-overdraw-01",
    )

    with pytest.raises(InsufficientBalanceError):
        CoinTraderService(session).admin_issue_liquidity(profile.id, request, admin=admin)

    trader_account = WalletService().get_user_account(session, trader, LedgerUnit.COIN)
    assert WalletService().get_balance(session, pool) == Decimal("100.0000")
    assert WalletService().get_balance(session, trader_account) == Decimal("0.0000")
    assert session.scalar(select(func.count(LedgerTransaction.id))) == 1


def test_admin_issue_liquidity_is_idempotent_and_cannot_rebind_the_key(session) -> None:
    admin = _create_user(session, user_id="liquidity-admin-replay", role=UserRole.ADMIN)
    trader = _create_user(session, user_id="liquidity-trader-replay", role=UserRole.COIN_TRADER)
    profile = _create_trader(session, trader=trader)
    pool = _seed_liquidity_pool(session, Decimal("100.0000"))
    service = CoinTraderService(session)
    request = CoinTraderAdminLiquidityRequest(
        coin_unit=LedgerUnit.COIN,
        amount=Decimal("25.0000"),
        idempotency_key="liquidity-replay-01",
        reference="admin-liquidity-replay",
    )

    first = service.admin_issue_liquidity(profile.id, request, admin=admin)
    second = service.admin_issue_liquidity(profile.id, request, admin=admin)

    trader_account = WalletService().get_user_account(session, trader, LedgerUnit.COIN)
    assert first.transaction_id == second.transaction_id
    assert WalletService().get_balance(session, pool) == Decimal("75.0000")
    assert WalletService().get_balance(session, trader_account) == Decimal("25.0000")
    assert session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == "coin-trader-liquidity:" + profile.id + ":issue:liquidity-replay-01"
        )
    ) == 1

    mismatched = CoinTraderAdminLiquidityRequest(
        coin_unit=LedgerUnit.COIN,
        amount=Decimal("40.0000"),
        idempotency_key="liquidity-replay-01",
        reference="admin-liquidity-replay",
    )
    with pytest.raises(Exception, match="already been used for a different transfer"):
        service.admin_issue_liquidity(profile.id, mismatched, admin=admin)

    assert WalletService().get_balance(session, pool) == Decimal("75.0000")
    assert WalletService().get_balance(session, trader_account) == Decimal("25.0000")
