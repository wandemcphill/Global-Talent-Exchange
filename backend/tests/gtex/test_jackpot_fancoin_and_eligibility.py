from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.gtex.config import load_gtex_settings
from app.gtex.schemas import JackpotContributionRequest
from app.gtex.service import JackpotService
from app.gtex.store import InMemoryStateStore
from app.models import (
    Base,
    GtexContributionSourceType,
    GtexJackpotRoundStatus,
    GtexJackpotTriggerMode,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
)
from app.wallets.service import LedgerPosting, WalletService


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


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def test_fancoin_jackpot_pool_uses_credit_unit(session) -> None:
    wallet_service = WalletService()
    state_store = InMemoryStateStore()
    settings = load_gtex_settings({"GTEX_JACKPOT_THRESHOLD_AMOUNT": "100.0000"})
    jackpot_service = JackpotService(
        settings=settings,
        wallet_service=wallet_service,
        state_store=state_store,
    )

    user = _create_user(session, email="fancoin-user@example.com", username="fancoin-user")

    # Seed user platform clearing for CREDIT (FanCoin)
    platform_clearing_credit = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    operations_credit = wallet_service.ensure_operations_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=operations_credit, amount=-Decimal("100.0000")),
            LedgerPosting(account=platform_clearing_credit, amount=Decimal("100.0000")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference="seed-fancoin-platform",
        description="Seed platform clearing for FanCoin",
    )
    session.commit()

    # Record ticket contribution into fancoin pool
    contribution = jackpot_service.record_contribution(
        session,
        participant_user_id=user.id,
        source_type=GtexContributionSourceType.PLATFORM_ACTIVITY,
        source_id="ticket-123",
        entry_fee=Decimal("10.0000"),
        contribution_amount=Decimal("1.5000"),
        pool_key="fancoin",
    )
    session.commit()

    assert contribution.round.pool_key == "fancoin"

    # Verify lottery pool funding entries are in LedgerUnit.CREDIT (FanCoin)
    fancoin_entries = list(
        session.scalars(
            select(LedgerEntry).where(
                LedgerEntry.external_reference == "ticket-123"
            )
        ).all()
    )
    assert len(fancoin_entries) > 0
    for entry in fancoin_entries:
        assert entry.unit == LedgerUnit.CREDIT

    # Ensure NO LedgerEntry in LedgerUnit.COIN was generated for this ticket contribution
    coin_entries = list(
        session.scalars(
            select(LedgerEntry).where(
                LedgerEntry.external_reference == "ticket-123",
                LedgerEntry.unit == LedgerUnit.COIN,
            )
        ).all()
    )
    assert len(coin_entries) == 0

    # Manually trigger round and verify payout is in LedgerUnit.CREDIT
    round_record = contribution.round
    round_record.current_balance = Decimal("1.5000")
    jackpot_service.trigger_round(
        session,
        round_record=round_record,
        trigger_mode=GtexJackpotTriggerMode.MANUAL,
    )
    session.commit()

    assert round_record.status == GtexJackpotRoundStatus.SETTLED
    assert round_record.winning_user_id == user.id

    # Verify user received CREDIT payout
    user_credit_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    user_credit_balance = wallet_service.get_balance(session, user_credit_account)
    assert user_credit_balance == Decimal("1.5000")

    # Verify user COIN balance remains zero
    user_coin_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    user_coin_balance = wallet_service.get_balance(session, user_coin_account)
    assert user_coin_balance == Decimal("0.0000")


def test_eligibility_score_clamping_and_schema_validation(session) -> None:
    wallet_service = WalletService()
    state_store = InMemoryStateStore()
    settings = load_gtex_settings()
    jackpot_service = JackpotService(
        settings=settings,
        wallet_service=wallet_service,
        state_store=state_store,
    )

    user = _create_user(session, email="odds-user@example.com", username="odds-user")

    # Test schema rejection when eligibility_score > 5.0000
    with pytest.raises(ValueError):
        JackpotContributionRequest(
            source_type="platform_activity",
            source_id="test-source",
            entry_fee=Decimal("10.0000"),
            eligibility_score=Decimal("100000.0000"),
        )

    # Test service clamping when raw value > 5.0000 is supplied
    contribution = jackpot_service.record_contribution(
        session,
        participant_user_id=user.id,
        source_type=GtexContributionSourceType.PLATFORM_ACTIVITY,
        source_id="source-clamp-1",
        entry_fee=Decimal("10.0000"),
        eligibility_score=Decimal("99999.0000"),
    )
    session.commit()

    assert contribution.eligibility_score == Decimal("5.0000")
