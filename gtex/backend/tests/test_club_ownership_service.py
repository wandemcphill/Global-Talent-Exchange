from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.club_ownership.schemas import ClubGovernanceProposalRequest, ClubGovernanceVoteRequest
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


def test_club_ownership_service_supports_market_governance_and_match_settlement() -> None:
    engine, session = _session()
    try:
        owner = User(email="owner@example.com", username="owner", password_hash="hash")
        investor = User(email="investor@example.com", username="investor", password_hash="hash")
        session.add_all([owner, investor])
        session.flush()

        club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Port Harcourt Dynamos",
            slug="ph-dynamos",
            primary_color="#112244",
            secondary_color="#ddeeff",
            accent_color="#ff6600",
        )
        session.add(club)
        session.flush()

        wallet_service = WalletService()
        _seed_balance(session, wallet_service, investor, Decimal("250.0000"))
        session.commit()

        service = ClubOwnershipService(session, wallet_service=wallet_service)
        buy_result = service.buy_tokens(club_id=club.id, buyer=investor, quantity=25)
        assert buy_result.holding is not None
        assert buy_result.holding.tokens_owned == 25
        assert buy_result.treasury.balance_coin > Decimal("0.0000")

        proposal_result = service.create_proposal(
            club_id=club.id,
            proposer=investor,
            payload=ClubGovernanceProposalRequest(
                title="Switch to 4-2-3-1",
                summary="Use an attacking 4-2-3-1 shape.",
                proposal_kind="formation",
                formation="4-2-3-1",
                playstyle="attacking",
                quorum_token_weight=10,
            ),
        )
        assert proposal_result.proposal.status == "open"

        vote_result = service.vote_on_proposal(
            club_id=club.id,
            voter=investor,
            payload=ClubGovernanceVoteRequest(
                proposal_id=proposal_result.proposal.id,
                choice="yes",
            ),
        )
        assert vote_result.executed is True
        assert vote_result.governance.formation == "4-2-3-1"
        assert vote_result.proposal.status == "accepted"

        investor_account = wallet_service.get_user_account(session, investor, LedgerUnit.COIN)
        balance_before_settlement = wallet_service.get_balance(session, investor_account)

        service.settle_match_result(
            match_id="match-ownership-1",
            home_club_id=club.id,
            away_club_id=None,
            home_score=2,
            away_score=0,
        )
        session.commit()

        balance_after_settlement = wallet_service.get_balance(session, investor_account)
        treasury = service.get_treasury_view(club_id=club.id)
        ownership = service.get_ownership_view(club_id=club.id, user=investor)

        assert any(item.entry_type == "match_winnings" for item in treasury.recent_entries)
        assert treasury.recent_dividends
        assert balance_after_settlement > balance_before_settlement
        assert ownership.governance.fan_mandate_summary is not None
        assert ownership.token.price >= Decimal("1.0000")
    finally:
        session.close()
        engine.dispose()
