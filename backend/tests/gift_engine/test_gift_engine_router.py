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
from app.auth.dependencies import get_current_user, get_session
from app.auth.service import AuthService
from app.gift_engine.router import router
from app.models import Base, GiftCatalogItem, LedgerEntryReason, LedgerUnit, RevenueShareRule
from app.models.user import User
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


def _create_user(session: Session, *, email: str, username: str) -> User:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
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
        reference=f"seed-gifts:{user.id}",
        actor=user,
    )
    session.commit()


@pytest.fixture()
def state(session: Session) -> dict[str, User]:
    AdminEngineService(session).seed_defaults()
    sender = _create_user(session, email="sender@example.com", username="sender")
    recipient = _create_user(session, email="recipient@example.com", username="recipient")
    _fund_fan_coin(session, sender, Decimal("100.0000"))
    session.add(
        GiftCatalogItem(
            key="fire",
            display_name="Fire",
            fancoin_price=Decimal("2.0000"),
            active=True,
        )
    )
    session.add(
        RevenueShareRule(
            rule_key="gift-default",
            scope="gift",
            title="Gift default",
            description=None,
            platform_share_bps=3000,
            creator_share_bps=0,
            recipient_share_bps=None,
            burn_bps=0,
            priority=10,
            active=True,
        )
    )
    session.commit()
    return {"current_user": sender, "recipient": recipient}


@pytest.fixture()
def client(session: Session, state: dict[str, User]) -> Iterator[TestClient]:
    application = FastAPI()
    application.include_router(router, prefix="/api")

    def override_session() -> Iterator[Session]:
        yield session

    def override_user() -> User:
        return state["current_user"]

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = override_user
    with TestClient(application) as test_client:
        yield test_client


def test_send_gift_and_summary_flow(client: TestClient, state: dict[str, User]) -> None:
    recipient = state["recipient"]

    response = client.post(
        "/api/gift-engine/send",
        json={
            "recipient_user_id": recipient.id,
            "gift_key": "fire",
            "quantity": "2.0000",
            "note": "For the knockout drama",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["gift_key"] == "fire"
    assert payload["gross_amount"] == "4.0000"
    assert payload["platform_rake_amount"] == "1.2000"
    assert payload["recipient_net_amount"] == "2.8000"

    sender_summary = client.get("/api/gift-engine/me/summary")
    assert sender_summary.status_code == 200, sender_summary.text
    assert sender_summary.json()["sent_total"] == "4.0000"
    assert sender_summary.json()["rake_total"] == "1.2000"

    state["current_user"] = recipient
    recipient_summary = client.get("/api/gift-engine/me/summary")
    assert recipient_summary.status_code == 200, recipient_summary.text
    assert recipient_summary.json()["received_total"] == "2.8000"


def test_send_gift_rejects_self_send(client: TestClient, state: dict[str, User]) -> None:
    sender = state["current_user"]
    response = client.post(
        "/api/gift-engine/send",
        json={
            "recipient_user_id": sender.id,
            "gift_key": "fire",
            "quantity": "1.0000",
        },
    )
    assert response.status_code == 400
    assert "cannot send gifts to themselves" in response.text.lower()
