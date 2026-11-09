from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.club_ownership.service import ClubOwnershipService
from app.coin_traders.service import CoinTraderService
from app.coin_traders.schemas import CoinTraderAdminLiquidityRequest
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.coin_trader import (
    CoinTraderProfile,
    CoinTraderProfileStatus,
    CoinTraderTier,
)
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.wallet import (
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


def _test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, SessionLocal()


def _seed_balance(session, wallet_service: WalletService, user: User, amount: Decimal) -> None:
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    operations_account = wallet_service.ensure_operations_account(session, LedgerUnit.COIN)
    reference = f"seed-balance:{user.id}"
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=operations_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        transaction_type=LedgerTransactionType.ADJUSTMENT,
        reference=reference,
        description="Seeded wallet balance for test.",
        external_reference=reference,
        actor=user,
        idempotency_key=reference,
    )


def test_club_token_buyback_anti_arbitrage_protection() -> None:
    """Verify that instant round-trip buy-and-sell of club tokens cannot drain the treasury.

    The 2.5% protocol spread and demand-pressure adjustment ensure that round-tripping
    guarantees negative yield, protecting the club treasury from risk-free extraction.
    """
    engine, session = _test_session()
    try:
        owner = User(email="owner@dynamos.com", username="owner", password_hash="hash")
        investor = User(email="investor@hedge.com", username="investor", password_hash="hash")
        session.add_all([owner, investor])
        session.flush()

        club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Kano Pillars FC",
            slug="kano-pillars",
            primary_color="#003366",
            secondary_color="#ffff00",
            accent_color="#ffffff",
        )
        session.add(club)
        session.flush()

        wallet_service = WalletService()
        initial_investor_coins = Decimal("5000.0000")
        _seed_balance(session, wallet_service, investor, initial_investor_coins)
        session.commit()

        service = ClubOwnershipService(session, wallet_service=wallet_service)
        investor_account = wallet_service.get_user_account(session, investor, LedgerUnit.COIN)

        # 1. Investor buys 500 tokens
        buy_result = service.buy_tokens(club_id=club.id, buyer=investor, quantity=500)
        investor_balance_after_buy = wallet_service.get_balance(session, investor_account)
        spent_on_buy = initial_investor_coins - investor_balance_after_buy
        treasury_after_buy = Decimal(buy_result.treasury.balance_coin)

        assert buy_result.holding.tokens_owned == 500
        assert spent_on_buy > Decimal("0.0000")
        assert treasury_after_buy >= spent_on_buy

        # 2. Immediately attempt to sell the 500 tokens back to the club treasury
        sell_result = service.sell_tokens(club_id=club.id, seller=investor, quantity=500)
        investor_balance_after_sell = wallet_service.get_balance(session, investor_account)
        treasury_after_sell = Decimal(sell_result.treasury.balance_coin)

        # 3. Security invariant checks:
        # A) Round-trip return must be strictly negative (no risk-free profit or free tokens)
        assert (
            investor_balance_after_sell < initial_investor_coins
        ), "Investor made profit or broke even on instant round-trip"
        # B) Club treasury retained liquidity surplus from protocol buyback fee
        assert treasury_after_sell > Decimal("0.0000"), "Club treasury was drained"
        # C) Net payout reflected protocol fee deduction
        assert sell_result.gross_amount_coin < spent_on_buy
        assert sell_result.holding.tokens_owned == 0
    finally:
        session.close()
        engine.dispose()


def test_coin_trader_idempotent_escrow_release_and_pool_protection() -> None:
    """Verify that CoinTraderService release operations are idempotent and pool overdraw is blocked."""
    engine, session = _test_session()
    try:
        admin = User(
            id="admin-sec",
            email="admin@test.com",
            username="admin",
            password_hash="x",
            role=UserRole.ADMIN,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        trader = User(
            id="trader-sec",
            email="trader@test.com",
            username="trader",
            password_hash="x",
            role=UserRole.USER,
            account_type=PublicAccountType.COIN_TRADER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        session.add_all([admin, trader])
        session.flush()

        profile = CoinTraderProfile(
            user_id=trader.id,
            display_name="Security Desk",
            status=CoinTraderProfileStatus.APPROVED.value,
            tier=CoinTraderTier.GOLD.value,
            verified_at=datetime.now(timezone.utc),
            terms_json={},
            payment_methods_json=[],
            bank_accounts_json=[],
            liquidity_snapshot_json={},
            metadata_json={},
        )
        session.add(profile)
        session.flush()

        # Seed pool with 100 COIN
        wallet_service = WalletService()
        pool = wallet_service.ensure_market_liquidity_account(session, LedgerUnit.COIN)
        operations = wallet_service.ensure_operations_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=pool, amount=Decimal("100.0000")),
                LedgerPosting(account=operations, amount=Decimal("-100.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="seed-pool",
            description="Seed test pool",
            external_reference="seed-pool",
            idempotency_key="seed-pool",
        )
        session.commit()

        service = CoinTraderService(session, wallet_service=wallet_service)

        # 1. Overdraw attempt: Request 150 COIN when pool only has 100 COIN
        overdraw_req = CoinTraderAdminLiquidityRequest(
            coin_unit=LedgerUnit.COIN,
            amount=Decimal("150.0000"),
            idempotency_key="overdraw-req-01",
        )
        with pytest.raises(InsufficientBalanceError):
            service.admin_issue_liquidity(profile.id, overdraw_req, admin=admin)

        # Pool balance unchanged
        assert wallet_service.get_balance(session, pool) == Decimal("100.0000")

        # 2. Legitimate issue of 50 COIN
        legit_req = CoinTraderAdminLiquidityRequest(
            coin_unit=LedgerUnit.COIN,
            amount=Decimal("50.0000"),
            idempotency_key="legit-req-01",
        )
        res1 = service.admin_issue_liquidity(profile.id, legit_req, admin=admin)
        assert wallet_service.get_balance(session, pool) == Decimal("50.0000")

        # 3. Idempotent replay: Replaying the exact same request returns existing transaction without double-debiting
        res2 = service.admin_issue_liquidity(profile.id, legit_req, admin=admin)
        assert res1.transaction_id == res2.transaction_id
        assert wallet_service.get_balance(session, pool) == Decimal(
            "50.0000"
        ), "Pool double-debited on idempotency replay"
    finally:
        session.close()
        engine.dispose()
