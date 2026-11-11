from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.admin.capabilities import AdminCapability
from app.admin_godmode.service import AdminGodModeService
from app.auth.dependencies import get_current_admin, get_session
from app.auth.service import AuthService
from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.notification_record import NotificationRecord
from app.models.user import User, UserRole
from app.models.wallet import LedgerAccount, LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.sponsorship_engine.router import admin_router
from app.sponsorship_engine.schemas import (
    SPONSORSHIP_AMOUNT_CAP_ERROR,
    SponsorshipLeadCreateRequest,
    capped_sponsorship_amount_minor,
)
from app.sponsorship_engine.service import (
    SPONSORSHIP_FEE_ACCOUNT_CODE,
    SponsorshipEngineError,
    SponsorshipEngineService,
)
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.support.secrets import TEST_PASSWORD


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def _close(session: Session) -> None:
    bind = session.get_bind()
    session.close()
    bind.dispose()


def _add_club_owner(session: Session, suffix: str) -> tuple[User, User, ClubProfile, ClubSponsorshipPackage]:
    owner = User(
        id=f"owner-{suffix}",
        email=f"owner-{suffix}@example.com",
        username=f"owner-{suffix}",
        password_hash="x",
        role=UserRole.USER,
    )
    admin = User(
        id=f"admin-{suffix}",
        email=f"admin-{suffix}@example.com",
        username=f"admin-{suffix}",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    club = ClubProfile(
        id=f"club-{suffix}",
        owner_user_id=owner.id,
        club_name=f"Sponsor {suffix}",
        short_name="SNF",
        slug=f"sponsor-{suffix}",
        primary_color="#111111",
        secondary_color="#ffffff",
        accent_color="#ff9900",
        visibility="public",
    )
    package = ClubSponsorshipPackage(
        id=f"package-{suffix}",
        code=f"pkg-{suffix}",
        name="Notify Shirt Front",
        asset_type=SponsorshipAssetType.JERSEY_FRONT,
        base_amount_minor=120000,
        currency="CREDITS",
        default_duration_months=1,
        payout_schedule="monthly",
        description="Test package",
    )
    session.add_all([owner, admin, club, package])
    session.commit()
    return owner, admin, club, package


def _add_contract(
    session: Session,
    *,
    suffix: str,
    club: ClubProfile,
    package: ClubSponsorshipPackage,
    status: SponsorshipStatus,
    amount_minor: int = 120000,
) -> tuple[ClubSponsorshipContract, ClubSponsorshipPayout]:
    now = datetime.now(UTC)
    contract = ClubSponsorshipContract(
        id=f"contract-{suffix}",
        club_id=club.id,
        package_id=package.id,
        asset_type=SponsorshipAssetType.JERSEY_FRONT,
        sponsor_name="Notify Bank",
        status=status,
        contract_amount_minor=amount_minor,
        currency="CREDITS",
        duration_months=1,
        payout_schedule="monthly",
        start_at=now,
        end_at=now + timedelta(days=30),
        moderation_required=status != SponsorshipStatus.ACTIVE,
        moderation_status="approved" if status == SponsorshipStatus.ACTIVE else "pending_review",
        settled_amount_minor=0,
        outstanding_amount_minor=amount_minor,
    )
    payout = ClubSponsorshipPayout(
        id=f"payout-{suffix}",
        contract_id=contract.id,
        due_at=now,
        amount_minor=amount_minor,
        status="pending",
    )
    session.add_all([contract, payout])
    session.commit()
    return contract, payout


def _fund_platform_fan_coin(session: Session, actor: User, amount: Decimal, *, reference: str) -> LedgerAccount:
    wallet = WalletService()
    platform = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    issuance = wallet.ensure_named_system_account(
        session,
        code="platform:credit:sponsorship_test_issuance",
        label="Sponsorship Test Issuance",
        unit=LedgerUnit.CREDIT,
        allow_negative=True,
    )
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=issuance, amount=-amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            LedgerPosting(account=platform, amount=amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=reference,
        description="Fund platform Fan Coin account for sponsorship settlement",
        actor=actor,
    )
    session.commit()
    return platform


def _owner_fan_coin_credits(session: Session, owner: User) -> list[LedgerEntry]:
    wallet = WalletService()
    account = wallet.get_user_account(session, owner, LedgerUnit.CREDIT)
    return list(
        session.scalars(
            select(LedgerEntry).where(LedgerEntry.account_id == account.id, LedgerEntry.amount > 0)
        ).all()
    )


def _balance(session: Session, account: LedgerAccount) -> Decimal:
    return WalletService().get_balance(session, account)


def _request_payload(club_id: str, package_code: str, custom_amount_minor: int | None) -> SimpleNamespace:
    return SimpleNamespace(
        club_id=club_id,
        package_code=package_code,
        sponsor_name="Cap Sponsor",
        sponsor_email=None,
        sponsor_company=None,
        custom_amount_minor=custom_amount_minor,
        duration_months=1,
        payout_schedule="monthly",
        proposal_note="",
        custom_copy=None,
        custom_logo_url=None,
        metadata_json={},
    )


def test_custom_amount_schema_rejects_zero_and_caps_at_package() -> None:
    with pytest.raises(ValidationError):
        SponsorshipLeadCreateRequest(
            club_id="club-cap",
            package_code="pkg-cap",
            sponsor_name="Cap Sponsor",
            custom_amount_minor=0,
        )
    with pytest.raises(ValidationError):
        SponsorshipLeadCreateRequest(
            club_id="club-cap",
            package_code="pkg-cap",
            sponsor_name="Cap Sponsor",
            custom_amount_minor=-1,
        )

    discounted = SponsorshipLeadCreateRequest(
        club_id="club-cap",
        package_code="pkg-cap",
        sponsor_name="Cap Sponsor",
        custom_amount_minor=1000,
    )
    assert discounted.resolve_contract_amount_minor(120000) == 1000
    omitted = SponsorshipLeadCreateRequest(
        club_id="club-cap",
        package_code="pkg-cap",
        sponsor_name="Cap Sponsor",
    )
    assert omitted.custom_amount_minor is None
    assert omitted.resolve_contract_amount_minor(120000) == 120000
    with pytest.raises(ValueError, match="cannot exceed"):
        capped_sponsorship_amount_minor(120001, 120000)
    with pytest.raises(ValueError, match="greater than zero"):
        capped_sponsorship_amount_minor(0, 120000)


def test_request_contract_rejects_zero_and_amounts_above_the_package() -> None:
    session = _session()
    try:
        owner, _admin, club, package = _add_club_owner(session, "cap")
        service = SponsorshipEngineService(session)
        with pytest.raises(SponsorshipEngineError, match="greater than zero"):
            service.request_contract(
                actor=owner,
                payload=_request_payload(club.id, package.code, 0),
            )
        with pytest.raises(SponsorshipEngineError, match="cannot exceed"):
            service.request_contract(
                actor=owner,
                payload=_request_payload(club.id, package.code, package.base_amount_minor + 1),
            )
        assert session.scalar(select(ClubSponsorshipContract.id)) is None

        _lead, contract = service.request_contract(
            actor=owner,
            payload=_request_payload(club.id, package.code, None),
        )
        session.commit()
        assert contract.contract_amount_minor == package.base_amount_minor
        assert contract.status == SponsorshipStatus.PENDING_APPROVAL
        assert contract.contract_amount_minor <= package.base_amount_minor
    finally:
        _close(session)


def test_pending_contract_does_not_credit_owner_even_when_platform_is_funded() -> None:
    session = _session()
    try:
        owner, admin, club, package = _add_club_owner(session, "pending")
        contract, payout = _add_contract(
            session,
            suffix="pending",
            club=club,
            package=package,
            status=SponsorshipStatus.PENDING_APPROVAL,
        )
        platform = _fund_platform_fan_coin(
            session,
            admin,
            Decimal("1200.0000"),
            reference="fund-pending-platform",
        )
        funded_balance = _balance(session, platform)

        with pytest.raises(SponsorshipEngineError, match="approved active"):
            SponsorshipEngineService(session).settle_next_payout(actor=admin, contract_id=contract.id)

        assert _owner_fan_coin_credits(session, owner) == []
        assert payout.status == "pending"
        assert _balance(session, platform) == funded_balance
        assert platform.allow_negative is True
    finally:
        _close(session)


@pytest.mark.parametrize(
    "status",
    [SponsorshipStatus.PAUSED, SponsorshipStatus.CANCELLED, SponsorshipStatus.DRAFT],
)
def test_inactive_contract_does_not_credit_owner(status: SponsorshipStatus) -> None:
    session = _session()
    try:
        owner, admin, club, package = _add_club_owner(session, f"inactive-{status.value}")
        contract, payout = _add_contract(
            session,
            suffix=f"inactive-{status.value}",
            club=club,
            package=package,
            status=status,
        )
        platform = _fund_platform_fan_coin(
            session,
            admin,
            Decimal("1200.0000"),
            reference=f"fund-inactive-{status.value}",
        )

        with pytest.raises(SponsorshipEngineError, match="approved active"):
            SponsorshipEngineService(session).settle_next_payout(actor=admin, contract_id=contract.id)

        assert _owner_fan_coin_credits(session, owner) == []
        assert payout.status == "pending"
        assert _balance(session, platform) == Decimal("1200.0000")
    finally:
        _close(session)


def test_unfunded_active_contract_does_not_credit_owner() -> None:
    session = _session()
    try:
        owner, admin, club, package = _add_club_owner(session, "unfunded")
        contract, payout = _add_contract(
            session,
            suffix="unfunded",
            club=club,
            package=package,
            status=SponsorshipStatus.ACTIVE,
        )

        with pytest.raises(SponsorshipEngineError, match="Platform Fan Coin balance"):
            SponsorshipEngineService(session).settle_next_payout(actor=admin, contract_id=contract.id)

        assert _owner_fan_coin_credits(session, owner) == []
        assert payout.status == "pending"
        platform = session.scalar(select(LedgerAccount).where(LedgerAccount.code == "platform:credit:clearing"))
        assert platform is not None
        assert platform.allow_negative is True
        assert _balance(session, platform) >= Decimal("0.0000")
    finally:
        _close(session)


def test_owner_share_alone_does_not_settle_when_fee_is_unfunded() -> None:
    session = _session()
    try:
        owner, admin, club, package = _add_club_owner(session, "partial")
        contract, payout = _add_contract(
            session,
            suffix="partial",
            club=club,
            package=package,
            status=SponsorshipStatus.ACTIVE,
        )
        platform = _fund_platform_fan_coin(
            session,
            admin,
            Decimal("720.0000"),
            reference="fund-partial-platform",
        )

        with pytest.raises(SponsorshipEngineError, match="Platform Fan Coin balance"):
            SponsorshipEngineService(session).settle_next_payout(actor=admin, contract_id=contract.id)

        assert _owner_fan_coin_credits(session, owner) == []
        assert payout.status == "pending"
        assert _balance(session, platform) == Decimal("720.0000")
        assert platform.allow_negative is True
        fee_account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == SPONSORSHIP_FEE_ACCOUNT_CODE))
        assert fee_account is None
    finally:
        _close(session)


def test_sponsorship_payout_publishes_matrix_notification() -> None:
    session = _session()
    try:
        owner, admin, club, package = _add_club_owner(session, "sponsor-notify")
        contract, payout = _add_contract(
            session,
            suffix="sponsor-notify",
            club=club,
            package=package,
            status=SponsorshipStatus.ACTIVE,
        )
        platform = _fund_platform_fan_coin(
            session,
            admin,
            Decimal("1200.0000"),
            reference="fund-sponsor-notify",
        )

        _contract, settled_payout, credited_amount, destination_user_id = SponsorshipEngineService(
            session
        ).settle_next_payout(
            actor=admin,
            contract_id=contract.id,
        )
        session.commit()

        assert settled_payout.status == "settled"
        assert str(credited_amount) == "720.0000"
        assert destination_user_id == owner.id
        assert _balance(session, platform) == Decimal("0.0000")
        assert platform.allow_negative is True
        owner_account = WalletService().get_user_account(session, owner, LedgerUnit.CREDIT)
        assert _balance(session, owner_account) == Decimal("720.0000")
        fee_account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == SPONSORSHIP_FEE_ACCOUNT_CODE))
        assert fee_account is not None
        assert fee_account.allow_negative is False
        assert _balance(session, fee_account) == Decimal("480.0000")
        settlement_entries = list(
            session.scalars(
                select(LedgerEntry).where(LedgerEntry.reference == f"sponsorship:{contract.id}:{payout.id}")
            ).all()
        )
        assert sum((entry.amount for entry in settlement_entries), Decimal("0.0000")) == Decimal("0.0000")
        assert {entry.amount for entry in settlement_entries} == {
            Decimal("720.0000"),
            Decimal("480.0000"),
            Decimal("-1200.0000"),
        }
        notification = session.scalar(
            select(NotificationRecord).where(
                NotificationRecord.user_id == owner.id,
                NotificationRecord.resource_id == payout.id,
            )
        )
        assert notification is not None
        assert notification.template_key == "sponsorship.paid"
        assert notification.metadata_json["contract_id"] == contract.id
        assert notification.metadata_json["owner_share"] == "720.0000"
        assert notification.metadata_json["platform_fee"] == "480.0000"
    finally:
        _close(session)


@contextmanager
def _settle_client(
    tmp_path: Path,
    *,
    role_name: str | None,
    permissions: list[str] | None,
) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    admin = AuthService().ensure_admin_user(
        session,
        email="settle-admin@example.com",
        password=TEST_PASSWORD,
        username="settle_admin",
        display_name="Settle Admin",
        role=UserRole.ADMIN,
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin
    if role_name is not None or permissions is not None:
        AdminGodModeService(wallet_service=WalletService()).upsert_admin_assignment(
            app,
            session,
            admin=admin,
            role_name=role_name,
            permissions=list(permissions or []),
            is_enabled=True,
        )
        session.commit()

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        session.close()
        engine.dispose()


def test_settle_next_rejects_admin_without_payment_rail_capability(tmp_path: Path) -> None:
    with _settle_client(tmp_path, role_name="support_admin", permissions=[]) as client:
        response = client.post("/admin/sponsorship/contracts/missing-contract/settle-next")

    assert response.status_code == 403
    assert response.json()["detail"] == f"Permission {AdminCapability.MANAGE_PAYMENT_RAILS.value} is required for this action."


def test_settle_next_payment_rail_admin_passes_capability_gate(tmp_path: Path) -> None:
    with _settle_client(tmp_path, role_name=None, permissions=["manage_payment_rails"]) as client:
        response = client.post("/admin/sponsorship/contracts/missing-contract/settle-next")

    assert response.status_code == 400
    assert response.json()["detail"] == "Contract was not found."
