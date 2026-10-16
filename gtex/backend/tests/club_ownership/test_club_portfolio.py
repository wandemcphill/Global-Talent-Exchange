from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.club_ownership.service import ClubOwnershipService
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


def _session():
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


def _club(session, owner: User, name: str, slug: str) -> ClubProfile:
    club = ClubProfile(
        owner_user_id=owner.id,
        club_name=name,
        slug=slug,
        primary_color="#112244",
        secondary_color="#ddeeff",
        accent_color="#ff6600",
    )
    session.add(club)
    session.flush()
    return club


def test_club_portfolio_is_empty_for_a_user_with_no_club_shares() -> None:
    engine, session = _session()
    try:
        user = User(email="a@example.com", username="a", password_hash="h")
        session.add(user)
        session.flush()
        view = ClubOwnershipService(session).list_user_club_portfolio(user=user)
        assert view.club_count == 0
        assert view.holdings == []
        assert view.total_market_value_coin == Decimal("0.0000")
        assert view.total_unrealized_pl_coin == Decimal("0.0000")
    finally:
        session.close()
        engine.dispose()


def test_club_portfolio_values_holdings_at_the_live_share_price() -> None:
    engine, session = _session()
    try:
        owner = User(email="owner@example.com", username="owner", password_hash="h")
        investor = User(email="inv@example.com", username="inv", password_hash="h")
        session.add_all([owner, investor])
        session.flush()
        club_a = _club(session, owner, "Port Harcourt Dynamos", "ph-dynamos")
        club_b = _club(session, owner, "Kano Comets", "kano-comets")

        wallet_service = WalletService()
        _seed_balance(session, wallet_service, investor, Decimal("500.0000"))
        session.commit()

        service = ClubOwnershipService(session, wallet_service=wallet_service)
        service.buy_tokens(club_id=club_a.id, buyer=investor, quantity=30)
        service.buy_tokens(club_id=club_b.id, buyer=investor, quantity=10)
        session.commit()

        view = service.list_user_club_portfolio(user=investor)
        assert view.club_count == 2
        by_name = {item.club_name: item for item in view.holdings}
        dynamos = by_name["Port Harcourt Dynamos"]
        assert dynamos.tokens_owned == 30
        assert dynamos.share_price_coin > Decimal("0.0000")
        assert dynamos.market_value_coin == (dynamos.share_price_coin * Decimal("30")).quantize(Decimal("0.0001"))
        assert dynamos.ownership_pct is not None
        assert view.total_market_value_coin == sum(
            (item.market_value_coin for item in view.holdings), Decimal("0.0000")
        )
    finally:
        session.close()
        engine.dispose()
