from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_admin, get_session
from app.core.database import load_model_modules
from app.core.events import InMemoryEventPublisher
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.observability.alert_system import AlertSystem
from app.observability.router import admin_router
from app.realtime.service import RealtimeHub
from app.risk.fraud_service import FraudDetectionService
from app.wallets.service import LedgerPosting, WalletService


def test_monitoring_dashboard_reports_transaction_and_fraud_signals(tmp_path) -> None:
    database_path = tmp_path / "monitoring-dashboard.db"
    load_model_modules()
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    publisher = InMemoryEventPublisher()
    alert_system = AlertSystem()
    realtime = RealtimeHub()
    publisher.subscribe(alert_system.handle_event)
    publisher.subscribe(realtime.handle_event)
    publisher.subscribe(
        FraudDetectionService(
            session_factory=session_factory,
            event_publisher=publisher,
        ).handle_event
    )

    with session_factory() as session:
        admin = User(
            email="monitoring-admin@example.com",
            username="monitoring_admin",
            password_hash="test-password-hash",
            role=UserRole.ADMIN,
        )
        user = User(
            email="monitoring-user@example.com",
            username="monitoring_user",
            password_hash="test-password-hash",
        )
        session.add_all([admin, user])
        session.commit()
        admin_id = admin.id
        user_id = user.id

    with session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        wallet_service = WalletService(event_publisher=publisher)
        user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount="2400.0000"),
                LedgerPosting(account=platform_account, amount="-2400.0000"),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            reference="monitoring-dashboard-test",
        )
        session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.state.settings = SimpleNamespace(
        kafka_enabled=False,
        outbox_relay_enabled=True,
        kafka_topic_prefix="gtex",
    )
    app.state.alert_system = alert_system
    app.state.realtime = realtime

    def _admin_override():
        with session_factory() as session:
            return session.get(User, admin_id)

    def _session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_current_admin] = _admin_override
    app.dependency_overrides[get_session] = _session_override

    client = TestClient(app)
    response = client.get("/admin/ops/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["transaction_stream"]["recent_transactions_24h"] >= 1
    assert body["fraud"]["open_fraud_cases"] >= 1
    assert "large_wallet_movement" in body["alerts"]["by_type"]

    engine.dispose()
