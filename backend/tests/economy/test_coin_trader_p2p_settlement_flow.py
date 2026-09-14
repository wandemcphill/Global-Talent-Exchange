from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.coin_traders.schemas import CoinTradeOrderCreateRequest, CoinTradeProofRequest
from app.coin_traders.service import CoinTraderService
from app.models.base import Base
from app.models.coin_trader import CoinTradeDirection, CoinTraderProfile, CoinTraderProfileStatus, CoinTraderRate, CoinTraderTier
from app.models.treasury import TreasurySettings
from app.models.user import User, UserRole
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerEntryReason, LedgerPosting, LedgerUnit
from app.wallets.service import WalletService


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _user(session, user_id: str, role: UserRole) -> User:
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


def _seed_coin(session, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    source = LedgerAccount(
        code=f"test:{user.id}:coin-funding",
        label=f"Funding for {user.username}",
        unit=LedgerUnit.COIN,
        kind=LedgerAccountKind.SYSTEM,
        allow_negative=True,
    )
    destination = wallet.get_user_account(session, user, LedgerUnit.COIN)
    session.add(source)
    session.flush()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=source, amount=-amount),
            LedgerPosting(account=destination, amount=amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"test-seed:{user.id}:coin",
    )
    session.commit()


def test_coin_trader_user_buy_roundtrip_moves_one_coin_balance_once() -> None:
    session = _make_session()
    try:
        buyer = _user(session, "coin-buyer", UserRole.USER)
        trader = _user(session, "coin-trader", UserRole.COIN_TRADER)
        _seed_coin(session, trader, Decimal("100.0000"))

        treasury = session.scalar(session.query(TreasurySettings)) if False else None
        del treasury
        settings = TreasurySettings(settings_key="default")
        settings.currency_code = "NGN"
        settings.deposit_rate_value = Decimal("1000.0000")
        settings.withdrawal_rate_value = Decimal("1000.0000")
        settings.min_trader_buy_rate_fiat = Decimal("1.0000")
        settings.max_trader_buy_rate_fiat = Decimal("5000.0000")
        settings.min_trader_sell_rate_fiat = Decimal("1.0000")
        settings.max_trader_sell_rate_fiat = Decimal("5000.0000")
        settings.max_trader_spread_fiat = Decimal("5000.0000")
        settings.max_buy_above_withdrawal_fiat = Decimal("5000.0000")
        settings.max_sell_below_deposit_fiat = Decimal("5000.0000")
        settings.min_deposit = Decimal("1.0000")
        settings.max_deposit = Decimal("100000000.0000")
        settings.min_withdrawal = Decimal("1.0000")
        settings.max_withdrawal = Decimal("100000000.0000")
        session.add(settings)
        session.flush()

        profile = CoinTraderProfile(
            user_id=trader.id,
            display_name="Roundtrip Trader",
            country_code="NG",
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
        rate = CoinTraderRate(
            trader_profile_id=profile.id,
            coin_unit=LedgerUnit.COIN,
            fiat_currency="NGN",
            buy_rate_fiat=Decimal("950.0000"),
            sell_rate_fiat=Decimal("1050.0000"),
            min_coin_amount=Decimal("1.0000"),
            max_coin_amount=Decimal("100.0000"),
            available_liquidity=Decimal("100.0000"),
            is_active=True,
        )
        session.add(rate)
        session.commit()

        service = CoinTraderService(session)
        order = service.create_order(
            CoinTradeOrderCreateRequest(
                trader_profile_id=profile.id,
                direction=CoinTradeDirection.USER_BUYS,
                coin_unit=LedgerUnit.COIN,
                coin_amount=Decimal("10.0000"),
                fiat_currency="NGN",
                payment_method="bank_transfer",
                idempotency_key="coin-p2p-roundtrip-01",
            ),
            actor=buyer,
        )
        service.accept_order(order.id, actor=trader)
        service.submit_proof(
            order.id,
            CoinTradeProofRequest(proof_reference="bank-ref-001"),
            actor=buyer,
        )
        settled = service.confirm_and_release(order.id, actor=trader)
        session.commit()

        buyer_account = WalletService().get_user_account(session, buyer, LedgerUnit.COIN)
        trader_account = WalletService().get_user_account(session, trader, LedgerUnit.COIN)
        assert settled.status == "released"
        assert WalletService().get_balance(session, buyer_account) == Decimal("10.0000")
        assert WalletService().get_balance(session, trader_account) == Decimal("90.0000")
    finally:
        session.close()
