from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.core.database import get_session
from app.fast_cups.api.router import router
from app.fast_cups.models.domain import FastCup, FastCupDivision, FastCupEntrant
from app.fast_cups.services.ecosystem import FastCupEcosystemService
from app.models.club_profile import ClubProfile
from app.models.event_backbone import EventOutbox
from app.models.fast_cup_finance import FastCupPayout, FastCupRegistration
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
from app.wallets.service import LedgerPosting, WalletService

BASE_NOW = datetime(2026, 7, 1, 12, 2, tzinfo=UTC)


def _build_entrant(
    index: int,
    *,
    division: FastCupDivision,
    registered_at: datetime,
) -> FastCupEntrant:
    prefix = "academy" if division is FastCupDivision.ACADEMY else "senior"
    return FastCupEntrant(
        club_id=f"{prefix}-club-{index:03d}",
        club_name=f"{prefix.title()} Club {index:03d}",
        division=division,
        rating=5000 - index,
        registered_at=registered_at,
    )


def _select_cup(
    ecosystem: FastCupEcosystemService,
    *,
    now: datetime,
    division: FastCupDivision,
    size: int,
) -> FastCup:
    cups = ecosystem.list_upcoming_cups(now=now, horizon_intervals=4)
    return next(cup for cup in cups if cup.division is division and cup.size == size)


def _fill_cup(ecosystem: FastCupEcosystemService, cup: FastCup) -> FastCup:
    join_at = cup.slot.registration_opens_at + timedelta(minutes=3)
    updated = cup
    for index in range(1, cup.size + 1):
        updated = ecosystem.join_cup(
            cup_id=updated.cup_id,
            entrant=_build_entrant(index, division=updated.division, registered_at=join_at),
            now=join_at,
        )
    return updated


@pytest.fixture()
def base_now() -> datetime:
    return BASE_NOW


@pytest.fixture()
def ecosystem() -> FastCupEcosystemService:
    return FastCupEcosystemService()


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    ClubProfile.__table__.create(engine)
    LedgerAccount.__table__.create(engine)
    LedgerBalanceProjection.__table__.create(engine)
    LedgerTransaction.__table__.create(engine)
    LedgerEntry.__table__.create(engine)
    EventOutbox.__table__.create(engine)
    AuditLog.__table__.create(engine)
    FastCupRegistration.__table__.create(engine)
    FastCupPayout.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def _seed_fast_cup_actor(session: Session) -> User:
    actor = User(
        id="fast-cup-owner",
        email="fastcup@example.com",
        username="fastcupowner",
        display_name="Fast Cup Owner",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    clubs = [
        ClubProfile(
            id=f"senior-club-{index:03d}",
            owner_user_id=actor.id,
            club_name=f"Senior Club {index:03d}",
            short_name=f"SC{index:03d}",
            slug=f"senior-club-{index:03d}",
            primary_color="#102030",
            secondary_color="#ffffff",
            accent_color="#a6ff00",
        )
        for index in range(1, 33)
    ]
    session.add_all([actor, *clubs])
    session.flush()

    wallet = WalletService()
    user_account = wallet.get_user_account(session, actor, LedgerUnit.CREDIT)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(
                account=platform_account,
                amount=Decimal("-1000000.0000"),
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
            ),
            LedgerPosting(
                account=user_account,
                amount=Decimal("1000000.0000"),
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
            ),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference="seed-fast-cup-fancoin",
        description="Seed Fast Cup Fan Coin",
        actor=actor,
        idempotency_key="seed-fast-cup-fancoin",
        transaction_type=LedgerTransactionType.ADJUSTMENT,
    )
    session.commit()
    return actor


@pytest.fixture()
def api_client(ecosystem: FastCupEcosystemService, base_now: datetime) -> TestClient:
    session = _build_session()
    actor = _seed_fast_cup_actor(session)

    def override_session():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: session.get(User, actor.id)
    app.state.fast_cup_ecosystem = ecosystem
    app.state.fast_cup_now = base_now
    app.include_router(router)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture()
def build_entrant():
    return _build_entrant


@pytest.fixture()
def select_cup():
    return _select_cup


@pytest.fixture()
def fill_cup():
    return _fill_cup
