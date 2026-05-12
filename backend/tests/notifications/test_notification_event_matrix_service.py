from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.notification_center import NotificationPreference
from app.models.notification_record import NotificationRecord
from app.models.user import KycStatus, User, UserRole
from app.notifications.service import NotificationEventMatrixService

pytestmark = pytest.mark.notifications_fast


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            NotificationPreference.__table__,
            NotificationRecord.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        _seed(db_session)
        yield db_session
    engine.dispose()


def test_event_matrix_publisher_creates_deduped_records(session: Session) -> None:
    records = NotificationEventMatrixService(session).publish_event(
        event_key="club_readiness_complete",
        target_user_ids=("user-one", "user-one", "missing-user"),
        resource_id="club-1",
        metadata_json={"club_id": "club-1"},
    )

    assert len(records) == 1
    record = records[0]
    assert record.user_id == "user-one"
    assert record.topic == "club"
    assert record.template_key == "club.readiness.complete"
    assert record.resource_type == "club_readiness_complete"
    assert record.resource_id == "club-1"
    assert record.metadata_json["deep_link_route"] == "/app/club"


def test_event_matrix_publisher_respects_notification_preferences(session: Session) -> None:
    records = NotificationEventMatrixService(session).publish_event(
        event_key="payment_confirmed",
        target_user_ids=("user-one", "user-muted"),
        resource_id="payment-1",
        message="Payment confirmed for your wallet.",
    )

    assert [record.user_id for record in records] == ["user-one"]
    assert records[0].message == "Payment confirmed for your wallet."


def test_event_matrix_covers_combined_batch_product_loops(session: Session) -> None:
    service = NotificationEventMatrixService(session)
    event_keys = {item.event_key for item in service.list_matrix()}

    assert {
        "squad_registration_locked",
        "staff_hired",
        "academy_contract_offered",
        "academy_prospect_promoted",
        "sponsorship_application_received",
        "sponsor_asset_needs_review",
        "federation_vote_opened",
        "federation_sanction_created",
        "federation_sanction_resolved",
        "prediction_settled",
        "fan_war_reward",
        "clip_approved",
        "clip_blocked",
        "broadcast_package_purchased",
        "creator_clip_revenue_paid",
        "ticket_resale_sold",
        "ticket_attendance_reward",
        "card_pack_opened",
        "card_listing_sold",
        "feature_flag_changed",
        "kill_switch_enabled",
        "beta_access_granted",
        "beta_access_revoked",
        "operations_readiness_blocked",
    }.issubset(event_keys)

    records = service.publish_event(
        event_key="clip_approved",
        target_user_ids=("user-one",),
        resource_id="clip-1",
    )

    assert records[0].topic == "broadcast"
    assert records[0].metadata_json["deep_link_route"] == "/news"


def _seed(session: Session) -> None:
    session.add_all(
        [
            User(
                id="user-one",
                email="one@example.com",
                username="one",
                display_name="One",
                password_hash="x",
                role=UserRole.USER,
                kyc_status=KycStatus.FULLY_VERIFIED,
            ),
            User(
                id="user-muted",
                email="muted@example.com",
                username="muted",
                display_name="Muted",
                password_hash="x",
                role=UserRole.USER,
                kyc_status=KycStatus.FULLY_VERIFIED,
            ),
            NotificationPreference(
                id="pref-muted",
                user_id="user-muted",
                allow_wallet=False,
            ),
        ]
    )
    session.commit()
