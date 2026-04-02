from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.events import InMemoryEventPublisher
from app.models.base import Base
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog, FraudCase, RiskSignal
from app.models.user import User
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
from app.risk.security_monitoring_service import SecurityMonitoringService
from app.wallets.service import LedgerPosting, WalletService


def _build_session_factory(tmp_path):
    del tmp_path
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            AuditLog.__table__,
            FraudCase.__table__,
            RiskSignal.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            EventOutbox.__table__,
        ],
    )
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _create_user(session, *, suffix: str) -> User:
    user = User(
        email=f"security-monitor-{suffix}@example.com",
        username=f"security_monitor_{suffix}",
        password_hash="test-password-hash",
    )
    session.add(user)
    session.flush()
    return user


def test_security_monitoring_records_login_attempts_and_flags_shared_device(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    monitoring = SecurityMonitoringService(session_factory=session_factory)

    with session_factory() as session:
        first_user = _create_user(session, suffix="one")
        second_user = _create_user(session, suffix="two")
        session.commit()
        first_user_id = first_user.id
        second_user_id = second_user.id

    monitoring.record_login_attempt(
        email="security-monitor-one@example.com",
        success=True,
        user_id=first_user_id,
        ip_address="198.51.100.10",
        user_agent="SecurityMonitor/1.0",
        device_id="device-cluster-1",
        path="/auth/login",
    )
    monitoring.record_login_attempt(
        email="security-monitor-two@example.com",
        success=True,
        user_id=second_user_id,
        ip_address="198.51.100.10",
        user_agent="SecurityMonitor/1.0",
        device_id="device-cluster-1",
        path="/auth/login",
    )

    with session_factory() as session:
        audit_logs = session.scalars(select(AuditLog).where(AuditLog.action_key == "auth.login.attempt")).all()
        fraud_cases = session.scalars(
            select(FraudCase).where(FraudCase.fraud_type == "multi_account_activity")
        ).all()

    assert len(audit_logs) == 2
    assert {case.user_id for case in fraud_cases} == {first_user_id, second_user_id}
    assert all(case.metadata_json["device_id"] == "device-cluster-1" for case in fraud_cases)
    engine.dispose()


def test_security_monitoring_logs_trade_activity_and_flags_rapid_trading_loops(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    publisher = InMemoryEventPublisher()
    publisher.subscribe(SecurityMonitoringService(session_factory=session_factory).handle_event)

    with session_factory() as session:
        user = _create_user(session, suffix="trade-loop")
        wallet_service = WalletService(event_publisher=publisher)
        user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("5000.0000")),
                LedgerPosting(account=platform_account, amount=Decimal("-5000.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="seed-security-monitoring",
            actor=user,
        )
        session.commit()

        trade_steps = (
            ("buy", Decimal("100.0000"), LedgerSourceTag.PLAYER_SHARE_PURCHASE, LedgerTransactionType.TRADE_BUY),
            ("sell", Decimal("120.0000"), LedgerSourceTag.PLAYER_SHARE_SALE, LedgerTransactionType.TRADE_SELL),
            ("buy", Decimal("90.0000"), LedgerSourceTag.PLAYER_SHARE_PURCHASE, LedgerTransactionType.TRADE_BUY),
            ("sell", Decimal("130.0000"), LedgerSourceTag.PLAYER_SHARE_SALE, LedgerTransactionType.TRADE_SELL),
        )
        for index, (side, amount, source_tag, transaction_type) in enumerate(trade_steps, start=1):
            signed_amount = -amount if side == "buy" else amount
            wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(
                        account=user_account,
                        amount=signed_amount,
                        source_tag=source_tag,
                        transaction_type=transaction_type,
                    ),
                    LedgerPosting(
                        account=platform_account,
                        amount=-signed_amount,
                        source_tag=source_tag,
                        transaction_type=transaction_type,
                    ),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=source_tag,
                reference=f"player-share-{side}:player-77:{index}",
                actor=user,
            )
            session.commit()
        user_id = user.id

    with session_factory() as session:
        trade_audits = session.scalars(select(AuditLog).where(AuditLog.action_key == "trade.executed")).all()
        rapid_loop_case = session.scalar(
            select(FraudCase).where(FraudCase.fraud_type == "rapid_trading_loop", FraudCase.user_id == user_id)
        )

    assert len(trade_audits) >= 4
    assert rapid_loop_case is not None
    assert rapid_loop_case.metadata_json["asset_key"] == "player-77"
    engine.dispose()


def test_security_monitoring_flags_abnormal_realized_trade_profit(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    publisher = InMemoryEventPublisher()
    publisher.subscribe(SecurityMonitoringService(session_factory=session_factory).handle_event)

    with session_factory() as session:
        user = _create_user(session, suffix="profit")
        wallet_service = WalletService(event_publisher=publisher)
        user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("4000.0000")),
                LedgerPosting(account=platform_account, amount=Decimal("-4000.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="seed-abnormal-profit",
            actor=user,
        )
        session.commit()
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=user_account,
                    amount=Decimal("-100.0000"),
                    source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
                LedgerPosting(
                    account=platform_account,
                    amount=Decimal("100.0000"),
                    source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
            reference="player-share-buy:player-900:1",
            actor=user,
        )
        session.commit()
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=user_account,
                    amount=Decimal("2100.0000"),
                    source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
                    transaction_type=LedgerTransactionType.TRADE_SELL,
                ),
                LedgerPosting(
                    account=platform_account,
                    amount=Decimal("-2100.0000"),
                    source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
                    transaction_type=LedgerTransactionType.TRADE_SELL,
                ),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
            reference="player-share-sell:player-900:2",
            actor=user,
        )
        session.commit()
        user_id = user.id

    with session_factory() as session:
        abnormal_profit_case = session.scalar(
            select(FraudCase).where(FraudCase.fraud_type == "abnormal_profit", FraudCase.user_id == user_id)
        )

    assert abnormal_profit_case is not None
    assert abnormal_profit_case.metadata_json["profit"] == "2000.0000"
    engine.dispose()
