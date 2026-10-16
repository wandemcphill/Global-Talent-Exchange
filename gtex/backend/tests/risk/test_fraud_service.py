from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import load_model_modules
from app.core.events import InMemoryEventPublisher
from app.models.base import Base
from app.models.risk_ops import FraudCase, SystemEvent
from app.models.treasury import RateDirection
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.risk.fraud_service import FraudDetectionService
from app.treasury.service import TreasuryService
from app.wallets.rail_service import WalletRailService
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


def _configure_treasury(session) -> None:
    settings = TreasuryService().ensure_settings(session)
    settings.deposit_rate_value = Decimal("1.0000")
    settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_deposit = Decimal("0.0000")
    settings.max_deposit = Decimal("100000.0000")
    session.flush()


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


def test_fraud_service_flags_duplicate_deposit_candidate_from_purchase_order_reference_reuse(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    publisher = InMemoryEventPublisher()
    publisher.subscribe(
        FraudDetectionService(
            session_factory=session_factory,
            event_publisher=publisher,
        ).handle_event
    )

    with session_factory() as session:
        user = _create_user(session, suffix="candidate")
        _configure_treasury(session)
        rail_service = WalletRailService(
            session,
            wallet_service=WalletService(event_publisher=publisher),
            event_publisher=publisher,
        )
        settings = TreasuryService().ensure_settings(session)
        order_one = rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("120.0000"),
            input_unit="fiat",
            provider_key="paystack",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="dup-deposit-candidate-ref",
        )
        rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("120.0000"),
            input_unit="fiat",
            provider_key="paystack",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="dup-deposit-candidate-ref",
        )
        rail_service.settle_purchase_order(order=order_one, actor=user)
        session.commit()

    with session_factory() as session:
        fraud_case = session.scalar(
            select(FraudCase).where(FraudCase.fraud_type == "duplicate_deposit_candidate")
        )

    assert fraud_case is not None
    assert fraud_case.metadata_json["external_reference"] == "dup-deposit-candidate-ref"
    assert fraud_case.metadata_json["purchase_order_count"] == 2
    engine.dispose()


def test_fraud_service_flags_duplicate_deposit_replay_when_reference_credits_twice(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    publisher = InMemoryEventPublisher()
    publisher.subscribe(
        FraudDetectionService(
            session_factory=session_factory,
            event_publisher=publisher,
        ).handle_event
    )

    with session_factory() as session:
        user = _create_user(session, suffix="replay")
        _configure_treasury(session)
        rail_service = WalletRailService(
            session,
            wallet_service=WalletService(event_publisher=publisher),
            event_publisher=publisher,
        )
        settings = TreasuryService().ensure_settings(session)
        first_order = rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("150.0000"),
            input_unit="fiat",
            provider_key="korapay",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="dup-deposit-replay-ref",
        )
        second_order = rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=Decimal("150.0000"),
            input_unit="fiat",
            provider_key="korapay",
            source_scope="wallet",
            unit=LedgerUnit.COIN,
            processor_mode="automatic_gateway",
            payout_channel="gateway",
            provider_reference="dup-deposit-replay-ref",
        )
        rail_service.settle_purchase_order(order=first_order, actor=user)
        session.commit()

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "fraud-service-replay@example.com"))
        assert user is not None
        rail_service = WalletRailService(
            session,
            wallet_service=WalletService(event_publisher=publisher),
            event_publisher=publisher,
        )
        second_order = session.get(type(second_order), second_order.id)
        assert second_order is not None
        rail_service.settle_purchase_order(order=second_order, actor=user)
        session.commit()

    with session_factory() as session:
        replay_case = session.scalar(
            select(FraudCase).where(FraudCase.fraud_type == "duplicate_deposit_replay")
        )

    assert replay_case is not None
    assert replay_case.metadata_json["external_reference"] == "dup-deposit-replay-ref"
    assert replay_case.metadata_json["duplicate_transaction_count"] == 2
    engine.dispose()
