from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.tests.support.secrets import TEST_PASSWORD_HASH
from app.auth.dependencies import get_current_admin, get_session
from app.core.database import load_model_modules
from app.core.events import InMemoryEventPublisher
from app.live_matches.service import ensure_live_match_hub
from app.models.event_backbone import CompetitionQueueRecord, EventOutbox
from app.models.base import Base
from app.models.risk_ops import AuditLog
from app.models.treasury import TreasuryAuditEvent
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.observability.alert_system import AlertSystem
from app.observability.router import admin_router
from app.realtime.service import RealtimeHub
from app.risk.fraud_service import FraudDetectionService
from app.wallets.service import LedgerPosting, WalletService


class _HealthyCacheBackend:
    enabled = True

    @staticmethod
    def ping() -> bool:
        return True


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
            password_hash=TEST_PASSWORD_HASH,
            role=UserRole.ADMIN,
        )
        user = User(
            email="monitoring-user@example.com",
            username="monitoring_user",
            password_hash=TEST_PASSWORD_HASH,
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


def test_platform_infra_dashboard_reports_runtime_contracts(tmp_path) -> None:
    database_path = tmp_path / "platform-infra-dashboard.db"
    load_model_modules()
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        admin = User(
            email="platform-infra-admin@example.com",
            username="platform_infra_admin",
            password_hash=TEST_PASSWORD_HASH,
            role=UserRole.ADMIN,
        )
        session.add(admin)
        session.flush()
        admin_id = admin.id

        for index in range(6):
            session.add(
                CompetitionQueueRecord(
                    queue_name="match_simulation",
                    job_name="simulate_match",
                    idempotency_key=f"match-job-{index}",
                    aggregate_id=f"match-{index}",
                    partition_key=f"match-{index}",
                    status="queued",
                    payload_json={},
                    metadata_json={},
                )
            )
        session.add(
            CompetitionQueueRecord(
                queue_name="treasury_events",
                job_name="reconcile_deposit",
                idempotency_key="treasury-job-1",
                aggregate_id="deposit-1",
                partition_key="deposit-1",
                status="queued",
                payload_json={},
                metadata_json={},
            )
        )
        session.add(
            EventOutbox(
                event_id="outbox-event-1",
                event_type="match.updated",
                aggregate_type="match",
                aggregate_id="match-1",
                partition_key="match-1",
                payload_json={},
                headers_json={},
                status="pending",
            )
        )
        session.add(
            EventOutbox(
                event_id="outbox-event-2",
                event_type="treasury.reconciled",
                aggregate_type="treasury",
                aggregate_id="batch-1",
                partition_key="batch-1",
                payload_json={},
                headers_json={},
                status="processed",
            )
        )
        session.add(
            AuditLog(
                actor_user_id=admin_id,
                action_key="api.rate_limited",
                resource_type="http_request",
                resource_id=None,
                outcome="blocked",
                detail="Rate limit tripped for auth.",
                metadata_json={"scope": "auth"},
            )
        )
        session.add(
            AuditLog(
                actor_user_id=admin_id,
                action_key="ops.scale.reviewed",
                resource_type="ops_job",
                resource_id="worker-autoscaling",
                outcome="success",
                detail="Autoscaling recommendation reviewed.",
                metadata_json={},
            )
        )
        session.add(
            TreasuryAuditEvent(
                event_type="treasury.withdrawal.batch.created",
                actor_user_id=admin_id,
                actor_email=admin.email,
                resource_type="withdrawal_batch",
                resource_id="batch-1",
                summary="Created withdrawal batch batch-1.",
                payload={"batch_id": "batch-1"},
            )
        )
        session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.state.settings = SimpleNamespace(
        kafka_enabled=True,
        outbox_relay_enabled=True,
        kafka_topic_prefix="gtex",
    )
    app.state.cache_backend = _HealthyCacheBackend()
    app.state.api_queue_consumer = object()

    live_hub = ensure_live_match_hub(app)
    live_hub._matches["live-match-1"] = object()
    live_hub._matches["live-match-2"] = object()
    live_hub.halt_match("halted-match-1", reason="operator review")

    def _admin_override():
        with session_factory() as session:
            return session.get(User, admin_id)

    def _session_override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_current_admin] = _admin_override
    app.dependency_overrides[get_session] = _session_override

    client = TestClient(app)
    response = client.get("/admin/ops/platform-infra")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cache"]["enabled"] is True
    assert body["cache"]["healthy"] is True
    assert body["cache"]["live_matches_in_memory"] == 2
    assert body["cache"]["halted_matches"] == 1
    assert body["event_streaming"]["kafka_enabled"] is True
    assert body["event_streaming"]["pending_outbox_events"] == 1
    assert body["event_streaming"]["processed_outbox_events"] == 1
    assert body["event_streaming"]["durable_queue_records"] == 7
    assert body["event_streaming"]["queue_depth_by_name"]["match_simulation"] == 6
    assert body["event_streaming"]["api_queue_consumer_active"] is True
    assert body["autoscaling"]["mode"] == "kafka"
    assert body["autoscaling"]["queued_jobs"] == 6
    assert body["autoscaling"]["active_live_matches"] == 2
    assert body["autoscaling"]["desired_workers"] == 2
    assert body["autoscaling"]["scale_out_recommended"] is True
    assert body["rate_limiting"]["enabled"] is True
    assert any(rule["scope"] == "auth" for rule in body["rate_limiting"]["rules"])
    assert body["audit"]["audit_logs_24h"] == 2
    assert body["audit"]["treasury_audit_events_24h"] == 1
    assert body["audit"]["blocked_rate_limit_events_24h"] == 1
    assert body["audit"]["top_actions"]["api.rate_limited"] == 1

    engine.dispose()
