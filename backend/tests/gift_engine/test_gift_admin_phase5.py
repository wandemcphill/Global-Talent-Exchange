from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_engine.service import AdminEngineService
from app.auth.dependencies import get_current_admin, get_session
from app.auth.service import AuthService
from app.gift_engine.router import admin_gifts_router
from app.gift_engine.service import GiftEngineService
from app.models import Base, GiftAbuseFlag, LedgerEntryReason, LedgerUnit
from app.models.user import User, UserRole
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def _create_user(session: Session, *, email: str, username: str, role: UserRole = UserRole.USER) -> User:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    user.role = role
    session.commit()
    return user


def _fund_fan_coin(session: Session, user: User, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"seed-phase5-admin-gifts:{user.id}",
        actor=user,
    )
    session.commit()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    admin = _create_user(
        session,
        email="gift-admin@example.com",
        username="gift-admin",
        role=UserRole.SUPER_ADMIN,
    )
    app = FastAPI()
    app.include_router(admin_gifts_router)

    def _get_session() -> Iterator[Session]:
        yield session

    def _get_current_admin() -> User:
        return admin

    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_current_admin] = _get_current_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_can_manage_catalog_events_flags_and_refunds(client: TestClient, session: Session) -> None:
    AdminEngineService(session).seed_defaults()
    sender = _create_user(session, email="sender-phase5@example.com", username="sender-phase5")
    recipient = _create_user(session, email="recipient-phase5@example.com", username="recipient-phase5")
    _fund_fan_coin(session, sender, Decimal("100.0000"))

    catalog_response = client.post(
        "/admin/gifts/catalog",
        json={
            "code": "phase5_award",
            "display_name": "Phase 5 Award",
            "fallback_display_name": "Phase 5 Safe Award",
            "cost_amount": "10.0000",
            "rarity": "legendary",
            "tier": "legendary",
            "animation_key": "world_best_award",
            "is_award_pack": True,
            "legal_status": "configurable",
        },
    )
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload["code"] == "phase5_award"
    assert catalog_payload["is_award_pack"] is True
    assert catalog_payload["legal_status"] == "configurable"

    transaction = GiftEngineService(session).send_gift(
        sender=sender,
        recipient_user_id=recipient.id,
        gift_key="phase5_award",
        quantity=Decimal("1.0000"),
        idempotency_key="phase5-admin-event",
    )
    session.add(
        GiftAbuseFlag(
            flag_key="phase5-admin-flag",
            sender_user_id=sender.id,
            recipient_type="user",
            recipient_id=recipient.id,
            gift_transaction_id=transaction.id,
            flag_type="wash_gifting",
            severity="high",
            description="Phase 5 admin review flag.",
            metadata_json={"phase": 5},
        )
    )
    session.commit()

    events_response = client.get("/admin/gifts/events")
    assert events_response.status_code == 200
    events_payload = events_response.json()
    assert events_payload[0]["gift_key"] == "phase5_award"
    assert events_payload[0]["status"] == "settled"

    flags_response = client.get("/admin/gifts/abuse-flags")
    assert flags_response.status_code == 200
    assert flags_response.json()[0]["flag_type"] == "wash_gifting"

    refund_response = client.post(f"/admin/gifts/events/{transaction.id}/refund")
    assert refund_response.status_code == 200
    assert refund_response.json()["status"] == "refunded"

    second_refund_response = client.post(f"/admin/gifts/events/{transaction.id}/refund")
    assert second_refund_response.status_code == 200
    assert second_refund_response.json()["status"] == "refunded"
