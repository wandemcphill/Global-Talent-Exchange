from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.manager_marketplace.service import ManagerMarketplaceService
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.event_backbone import EventOutbox
from app.models.manager_marketplace import ManagerContract, ManagerContractStatus, ManagerControlMode, ManagerProfile
from app.models.risk_ops import AuditLog
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerTransactionType,
    LedgerUnit,
)
from app.replay_archive.persistence import ReplayArchiveRecordRow
from app.wallets.service import LedgerPosting, WalletService


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    LedgerAccount.__table__.create(engine)
    LedgerBalanceProjection.__table__.create(engine)
    LedgerTransaction.__table__.create(engine)
    LedgerEntry.__table__.create(engine)
    EventOutbox.__table__.create(engine)
    AuditLog.__table__.create(engine)
    ClubProfile.__table__.create(engine)
    ManagerProfile.__table__.create(engine)
    ManagerContract.__table__.create(engine)
    CompetitionMatch.__table__.create(engine)
    ReplayArchiveRecordRow.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def _seed_marketplace(session: Session) -> tuple[User, ManagerProfile]:
    owner = User(
        id="club-owner",
        email="owner@example.com",
        username="clubowner",
        display_name="Club Owner",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    manager = User(
        id="human-manager",
        email="manager@example.com",
        username="humancoach",
        display_name="Human Coach",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    club = ClubProfile(
        id="club-home",
        owner_user_id=owner.id,
        club_name="Home FC",
        short_name="HFC",
        slug="home-fc",
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#00aaff",
    )
    profile = ManagerProfile(
        id="manager-profile-1",
        manager_id=manager.id,
        bio="Front-foot coach",
        preferred_style="attacking",
        control_mode=ManagerControlMode.HUMAN,
        matches_managed=2,
        wins=2,
        losses=0,
        reputation_score=0,
        hourly_fee=Decimal("100.00"),
        is_available=True,
    )
    session.add_all([owner, manager, club, profile])
    session.flush()
    wallet = WalletService()
    owner_account = wallet.get_user_account(session, owner, LedgerUnit.CREDIT)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(
                account=platform_account,
                amount=Decimal("-1000.00"),
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
            ),
            LedgerPosting(
                account=owner_account,
                amount=Decimal("1000.00"),
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
            ),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference="seed-manager-hire-fancoin",
        description="Seed manager marketplace Fan Coin",
        actor=owner,
        idempotency_key="seed-manager-hire-fancoin",
        transaction_type=LedgerTransactionType.ADJUSTMENT,
    )
    session.commit()
    return owner, profile


def test_hire_release_and_match_updates_work_for_manager_marketplace() -> None:
    session = _build_session()
    try:
        owner, profile = _seed_marketplace(session)
        service = ManagerMarketplaceService(session)

        hire_result = service.hire_manager(owner, profile.id)
        assert hire_result.contract.status is ManagerContractStatus.ACTIVE
        assert hire_result.profile.availability is False

        match_profile = service.build_match_manager_profile(club_id="club-home")
        assert match_profile is not None
        assert match_profile["display_name"] == "Human Coach"
        assert "high_press_attack" in match_profile["tactics"]

        service.record_match_outcome(
            home_club_id="club-home",
            away_club_id=None,
            winner_club_id="club-home",
        )
        session.refresh(profile)
        assert profile.matches_managed == 3
        assert profile.wins == 3
        assert profile.reputation_score == 10
        assert profile.hourly_fee == Decimal("105.00")

        release_result = service.release_manager(owner, profile.id)
        assert release_result.contract.status is ManagerContractStatus.ENDED
        assert release_result.profile.availability is True
    finally:
        session.close()
