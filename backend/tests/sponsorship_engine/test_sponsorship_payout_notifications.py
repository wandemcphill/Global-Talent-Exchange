from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.notification_record import NotificationRecord
from app.models.user import User, UserRole
from app.sponsorship_engine.service import SponsorshipEngineService


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def test_sponsorship_payout_publishes_matrix_notification() -> None:
    session = _session()
    try:
        owner = User(
            id="owner-sponsor-notify",
            email="owner-sponsor-notify@example.com",
            username="owner-sponsor-notify",
            password_hash="x",
            role=UserRole.USER,
        )
        admin = User(
            id="admin-sponsor-notify",
            email="admin-sponsor-notify@example.com",
            username="admin-sponsor-notify",
            password_hash="x",
            role=UserRole.ADMIN,
        )
        club = ClubProfile(
            id="club-sponsor-notify",
            owner_user_id=owner.id,
            club_name="Sponsor Notify FC",
            short_name="SNF",
            slug="sponsor-notify-fc",
            primary_color="#111111",
            secondary_color="#ffffff",
            accent_color="#ff9900",
            visibility="public",
        )
        package = ClubSponsorshipPackage(
            id="package-sponsor-notify",
            code="notify-shirt-front",
            name="Notify Shirt Front",
            asset_type=SponsorshipAssetType.JERSEY_FRONT,
            base_amount_minor=120000,
            currency="CREDITS",
            default_duration_months=1,
            payout_schedule="monthly",
            description="Test package",
        )
        now = datetime.now(UTC)
        contract = ClubSponsorshipContract(
            id="contract-sponsor-notify",
            club_id=club.id,
            package_id=package.id,
            asset_type=SponsorshipAssetType.JERSEY_FRONT,
            sponsor_name="Notify Bank",
            status=SponsorshipStatus.ACTIVE,
            contract_amount_minor=120000,
            currency="CREDITS",
            duration_months=1,
            payout_schedule="monthly",
            start_at=now,
            end_at=now + timedelta(days=30),
            moderation_required=False,
            moderation_status="approved",
            settled_amount_minor=0,
            outstanding_amount_minor=120000,
        )
        payout = ClubSponsorshipPayout(
            id="payout-sponsor-notify",
            contract_id=contract.id,
            due_at=now,
            amount_minor=120000,
            status="pending",
        )
        session.add_all([owner, admin, club, package, contract, payout])
        session.commit()

        _contract, settled_payout, credited_amount, destination_user_id = SponsorshipEngineService(session).settle_next_payout(
            actor=admin,
            contract_id=contract.id,
        )
        session.commit()

        assert settled_payout.status == "settled"
        assert str(credited_amount) == "1200.0000"
        assert destination_user_id == owner.id
        notification = session.scalar(
            select(NotificationRecord).where(
                NotificationRecord.user_id == owner.id,
                NotificationRecord.resource_id == payout.id,
            )
        )
        assert notification is not None
        assert notification.template_key == "sponsorship.paid"
        assert notification.metadata_json["contract_id"] == contract.id
    finally:
        bind = session.get_bind()
        session.close()
        bind.dispose()
