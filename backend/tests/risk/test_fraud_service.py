from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import load_model_modules
from app.core.events import InMemoryEventPublisher
from app.models.base import Base
from app.models.risk_ops import FraudCase, SystemEvent
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.risk.fraud_service import FraudDetectionService
from app.wallets.service import LedgerPosting, WalletService


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'fraud-service.db').as_posix()}"
    load_model_modules()
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _create_user(session, *, suffix: str = "1") -> User:
    user = User(
        email=f"fraud-service-{suffix}@example.com",
        username=f"fraud_service_{suffix}",
        password_hash="test-password-hash",
    )
    session.add(user)
    session.flush()
    return user


def test_fraud_service_creates_case_and_alert_for_large_wallet_movement(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    publisher = InMemoryEventPublisher()
    publisher.subscribe(
        FraudDetectionService(
            session_factory=session_factory,
            event_publisher=publisher,
        ).handle_event
    )

    with session_factory() as session:
        user = _create_user(session)
        service = WalletService(event_publisher=publisher)
        user_account = service.get_user_account(session, user, LedgerUnit.CREDIT)
        platform_account = service.ensure_platform_account(session, LedgerUnit.CREDIT)
        service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount="2200.0000"),
                LedgerPosting(account=platform_account, amount="-2200.0000"),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            reference="fraud-large-movement",
        )
        session.commit()

    with session_factory() as session:
        fraud_cases = session.scalars(select(FraudCase)).all()
        system_events = session.scalars(select(SystemEvent)).all()

    assert any(case.fraud_type == "large_wallet_movement" for case in fraud_cases)
    assert len(system_events) >= 1
    assert any(event.name == "risk.fraud.detected" for event in publisher.published_events)
    engine.dispose()
