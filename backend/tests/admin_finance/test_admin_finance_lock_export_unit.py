from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_finance import router as admin_finance_router
from app.admin_finance.service import AdminFinanceService
from app.auth.service import AuthService
from app.models import Base, CountryFeaturePolicy
from app.models.creator_monetization import CreatorRevenueSettlement
from app.models.event_backbone import EventOutbox
from app.models.reward_settlement import RewardSettlement
from app.models.risk_ops import FraudCase, RiskSeverity
from app.models.treasury import PaymentMode, TreasuryAuditEvent
from app.models.wallet import LedgerUnit
from app.treasury.service import TreasuryConflictError, TreasuryService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.flush()
    return user


def _seed_policy(session) -> None:
    session.add(
        CountryFeaturePolicy(
            country_code="GLOBAL",
            bucket_type="default",
            deposits_enabled=True,
            market_trading_enabled=True,
            platform_reward_withdrawals_enabled=True,
            user_hosted_gift_withdrawals_enabled=True,
            gtex_competition_gift_withdrawals_enabled=True,
            national_reward_withdrawals_enabled=True,
            one_time_region_change_after_days=180,
            active=True,
        )
    )
    session.flush()


def _submitted_deposit(session):
    _seed_policy(session)
    user = _create_user(session, email="lock-export-user@example.com", username="lockexportuser")
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    settings.deposit_mode = PaymentMode.MANUAL
    deposit = treasury.create_deposit_request(
        session,
        user=user,
        amount=Decimal("10000.0000"),
        input_unit="fiat",
    )
    treasury.submit_deposit_request(
        session,
        user=user,
        deposit_request_id=deposit.id,
        payer_name=user.email,
        sender_bank="GTEX Unit Bank",
        transfer_reference=f"TR-{deposit.reference}",
        proof_attachment_id=None,
    )
    session.flush()
    return treasury, user, deposit


def test_locked_by_other_queue_item_disables_controls_and_blocks_mutation(session) -> None:
    treasury, user, deposit = _submitted_deposit(session)
    actor = _create_user(session, email="queue-actor@example.com", username="queueactor")
    locker = _create_user(session, email="queue-locker@example.com", username="queuelocker")
    treasury.acquire_admin_lock(
        session,
        actor=locker,
        resource_type="deposit_request",
        resource_id=deposit.id,
        ttl_seconds=300,
    )

    service = AdminFinanceService(session=session, treasury_service=treasury)
    item = service._serialize_deposit_queue_item(deposit, "pending", user=user, actor=actor)

    assert item["lock_state"]["state"] == "locked_by_other"
    assert item["action_state"] == "blocked"
    assert item["blocked_reason"].startswith("Locked by queue-locker@example.com")
    assert item["action_controls"]["approve"]["enabled"] is False
    assert item["action_controls"]["approve"]["action_state"] == "blocked"
    assert item["action_controls"]["approve"]["disabled_reason"].startswith("Locked by queue-locker@example.com")

    with pytest.raises(TreasuryConflictError, match="Locked by queue-locker@example.com"):
        service.approve_payment_queue_deposit(
            actor=actor,
            deposit_id=deposit.id,
            admin_notes="blocked approval",
        )


def test_deposit_queue_route_maps_lock_conflict_to_409(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class _FakePaymentQueueService:
        def approve_payment_queue_deposit(self, *, actor, deposit_id, admin_notes):
            del actor, deposit_id, admin_notes
            raise TreasuryConflictError("Locked by other-admin@example.com.")

    monkeypatch.setattr(admin_finance_router, "_require_payment_queue_permission", lambda request, actor: None)
    monkeypatch.setattr(admin_finance_router, "_queue_service", lambda request, session: _FakePaymentQueueService())

    session = _FakeSession()
    with pytest.raises(Exception) as exc:
        admin_finance_router._run_deposit_queue_action(
            SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace()))),
            session,
            SimpleNamespace(id="admin-operator"),
            "deposit-locked",
            {"admin_notes": "blocked by lock"},
            "approve",
        )

    assert getattr(exc.value, "status_code", None) == 409
    assert "Locked by other-admin@example.com" in str(getattr(exc.value, "detail", ""))
    assert session.commits == 0
    assert session.rollbacks == 1


def test_bulk_action_and_export_status_are_audited_and_exports_materialize_artifacts(session) -> None:
    treasury, _user, deposit = _submitted_deposit(session)
    actor = _create_user(session, email="bulk-export-admin@example.com", username="bulkexportadmin")
    service = AdminFinanceService(session=session, treasury_service=treasury)

    bulk = service.request_admin_bulk_action(
        actor=actor,
        item_type="deposit",
        action="approve",
        item_ids=[deposit.id],
        admin_notes="queue bulk approval",
    )

    assert bulk["status"] == "queued"
    assert bulk["queued_count"] == 1
    assert bulk["blocked_count"] == 0
    assert bulk["audit_reference"]
    bulk_status = service.get_admin_bulk_action_status(bulk_action_id=bulk["bulk_action_id"])
    assert bulk_status["audit_reference"] == bulk["audit_reference"]

    export = service.request_admin_export(
        actor=actor,
        export_type="payment_queue",
        export_format="csv",
        filters={"limit": 25},
    )
    assert export["status"] == "ready"
    assert export["download_url"].endswith(f"/exports/{export['export_id']}/download")
    assert export["blocked_reason"] is None
    assert export["audit_reference"]
    assert export["requested_audit_reference"] != export["audit_reference"]

    queued_status = service.get_admin_export_status(export_id=export["export_id"])
    assert queued_status["status"] == "ready"
    assert queued_status["requested_audit_reference"] == export["requested_audit_reference"]

    ready_status = service.complete_admin_export(actor=actor, export_id=export["export_id"])
    assert ready_status["status"] == "ready"
    assert ready_status["download_url"].endswith(f"/exports/{export['export_id']}/download")
    assert ready_status["blocked_reason"] is None
    assert ready_status["requested_audit_reference"] == export["requested_audit_reference"]
    assert ready_status["audit_reference"] == export["audit_reference"]
    assert ready_status["artifact"]["row_count"] >= 1

    artifact = service.get_admin_export_artifact(export_id=export["export_id"])
    assert artifact["content_type"] == "text/csv"
    assert deposit.reference in artifact["content"]

    bulk_audit = session.scalar(
        select(TreasuryAuditEvent).where(
            TreasuryAuditEvent.resource_type == "admin_bulk_action",
            TreasuryAuditEvent.resource_id == bulk["bulk_action_id"],
            TreasuryAuditEvent.event_type == "admin.bulk_action.requested",
        )
    )
    export_audit = session.scalar(
        select(TreasuryAuditEvent).where(
            TreasuryAuditEvent.resource_type == "admin_export",
            TreasuryAuditEvent.resource_id == export["export_id"],
            TreasuryAuditEvent.event_type == "admin.export.ready",
        )
    )
    assert bulk_audit is not None
    assert bulk_audit.payload["item_ids"] == [deposit.id]
    assert export_audit is not None
    assert export_audit.payload["status"] == "ready"
    assert export_audit.payload["artifact"]["content_type"] == "text/csv"
    assert deposit.reference in export_audit.payload["artifact"]["content"]

    export_ready_event = session.scalar(
        select(EventOutbox).where(
            EventOutbox.event_type == "admin.export.ready",
            EventOutbox.aggregate_type == "admin_export",
            EventOutbox.aggregate_id == export["export_id"],
        )
    )
    assert export_ready_event is not None
    assert export_ready_event.producer == "admin_finance"
    assert export_ready_event.headers_json["audit_reference"] == export["audit_reference"]
    assert export_ready_event.payload_json["status"] == "ready"
    assert export_ready_event.payload_json["artifact"]["row_count"] >= 1
    assert "content" not in export_ready_event.payload_json["artifact"]


def test_fraud_export_materializes_canonical_fraud_rows_and_ready_audit(session) -> None:
    treasury, _user, _deposit = _submitted_deposit(session)
    fraud_user = _create_user(session, email="fraud-export-user@example.com", username="fraudexportuser")
    actor = _create_user(session, email="fraud-export-admin@example.com", username="fraudexportadmin")
    case = FraudCase(
        user_id=fraud_user.id,
        case_key="fraud-case-export-1",
        fraud_type="duplicate_deposit_candidate",
        title="Duplicate deposit candidate",
        description="Provider reference appeared more than once.",
        severity=RiskSeverity.HIGH,
        confidence_score=Decimal("91.50"),
        metadata_json={"provider_reference": "dup-ref-1"},
    )
    session.add(case)
    session.flush()
    service = AdminFinanceService(session=session, treasury_service=treasury)

    export = service.request_admin_export(
        actor=actor,
        export_type="fraud",
        export_format="json",
        filters={},
    )

    assert export["status"] == "ready"
    assert export["blocked_reason"] is None
    assert export["artifact"]["row_count"] == 1
    artifact = service.get_admin_export_artifact(export_id=export["export_id"])
    payload = json.loads(artifact["content"])
    assert payload["rows"][0]["source"] == "fraud_case"
    assert payload["rows"][0]["case_key"] == "fraud-case-export-1"
    assert payload["rows"][0]["user_email"] == "fraud-export-user@example.com"

    ready_audit = session.scalar(
        select(TreasuryAuditEvent).where(
            TreasuryAuditEvent.resource_type == "admin_export",
            TreasuryAuditEvent.resource_id == export["export_id"],
            TreasuryAuditEvent.event_type == "admin.export.ready",
        )
    )
    assert ready_audit is not None
    assert ready_audit.payload["status"] == "ready"
    assert ready_audit.payload["artifact"]["row_count"] == 1


def test_settlements_export_materializes_reward_settlement_rows(session) -> None:
    treasury, user, _deposit = _submitted_deposit(session)
    actor = _create_user(session, email="settlement-export-admin@example.com", username="settlementexportadmin")
    settlement = RewardSettlement(
        user_id=user.id,
        competition_key="competition:cup-final",
        reward_source="gtex_promotional_pool",
        title="Cup final reward",
        gross_amount=Decimal("125.0000"),
        platform_fee_amount=Decimal("5.0000"),
        net_amount=Decimal("120.0000"),
        ledger_unit=LedgerUnit.CREDIT,
        ledger_transaction_id="ledger-settlement-1",
        note="Settled from canonical reward engine table.",
        settled_by_user_id=actor.id,
    )
    session.add(settlement)
    session.flush()
    service = AdminFinanceService(session=session, treasury_service=treasury)

    export = service.request_admin_export(
        actor=actor,
        export_type="settlements",
        export_format="csv",
        filters={"competition_key": "competition:cup-final"},
    )

    assert export["status"] == "ready"
    assert export["blocked_reason"] is None
    assert export["artifact"]["row_count"] == 1
    artifact = service.get_admin_export_artifact(export_id=export["export_id"])
    assert artifact["content_type"] == "text/csv"
    assert "Cup final reward" in artifact["content"]
    assert "120.0000" in artifact["content"]


def test_settlements_export_materializes_creator_revenue_settlement_rows(session) -> None:
    treasury, _user, _deposit = _submitted_deposit(session)
    actor = _create_user(session, email="creator-settlement-admin@example.com", username="creatorsettlementadmin")
    settlement = CreatorRevenueSettlement(
        id="creator-settlement-export-1",
        season_id="creator-season-export-1",
        competition_id="creator-competition-export-1",
        match_id="creator-match-export-1",
        home_club_id="creator-home-club-export-1",
        away_club_id="creator-away-club-export-1",
        total_revenue_coin=Decimal("90.0000"),
        total_creator_share_coin=Decimal("54.0000"),
        total_platform_share_coin=Decimal("36.0000"),
        home_creator_share_coin=Decimal("30.0000"),
        away_creator_share_coin=Decimal("24.0000"),
        review_status="approved",
        reviewed_by_user_id=actor.id,
        review_note="Canonical creator settlement export.",
    )
    session.add(settlement)
    session.flush()
    service = AdminFinanceService(session=session, treasury_service=treasury)

    export = service.request_admin_export(
        actor=actor,
        export_type="settlements",
        export_format="json",
        filters={"competition_id": "creator-competition-export-1"},
    )

    assert export["status"] == "ready"
    assert export["blocked_reason"] is None
    assert export["artifact"]["row_count"] == 1
    artifact = service.get_admin_export_artifact(export_id=export["export_id"])
    payload = json.loads(artifact["content"])
    assert payload["rows"][0]["source"] == "creator_revenue_settlement"
    assert payload["rows"][0]["id"] == "creator-settlement-export-1"
    assert payload["rows"][0]["competition_id"] == "creator-competition-export-1"
    assert payload["rows"][0]["home_creator_share_coin"] == "30.0000"
    assert payload["rows"][0]["away_creator_share_coin"] == "24.0000"


def test_admin_export_download_route_returns_artifact_when_ready(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class _FakePaymentQueueService:
        def complete_admin_export(self, *, actor, export_id):
            del actor
            return {
                "export_id": export_id,
                "status": "ready",
                "export_type": "payment_queue",
                "format": "csv",
                "filters": {},
                "requested_at": "2026-06-03T00:00:00+00:00",
                "completed_at": "2026-06-03T00:00:01+00:00",
                "download_url": f"/api/v2/admin/finance/exports/{export_id}/download",
                "blocked_reason": None,
                "audit_reference": "audit-ready",
            }

        def get_admin_export_artifact(self, *, export_id):
            return {
                "filename": f"{export_id.lower()}.csv",
                "content_type": "text/csv",
                "content": "id,status\nrow-1,ready\n",
            }

    monkeypatch.setattr(admin_finance_router, "_require_payment_queue_permission", lambda request, actor: None)
    monkeypatch.setattr(admin_finance_router, "_queue_service", lambda request, session: _FakePaymentQueueService())

    session = _FakeSession()
    response = admin_finance_router.download_admin_export(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace()))),
        "EXPORT-READY",
        SimpleNamespace(id="admin-operator"),
        session,
    )

    assert response.status_code == 200
    assert response.media_type == "text/csv"
    assert response.body == b"id,status\nrow-1,ready\n"
    assert response.headers["x-gtex-audit-ref"] == "audit-ready"
    assert session.commits == 1
    assert session.rollbacks == 0


def test_admin_export_download_route_returns_blocked_state_without_generator(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class _FakePaymentQueueService:
        def complete_admin_export(self, *, actor, export_id):
            del actor
            return {
                "export_id": export_id,
                "status": "blocked",
                "export_type": "fraud",
                "format": "json",
                "filters": {},
                "requested_at": "2026-06-03T00:00:00+00:00",
                "completed_at": "2026-06-03T00:00:01+00:00",
                "download_url": None,
                "blocked_reason": "Admin finance fraud export is blocked: no backend artifact truth is available.",
                "audit_reference": "audit-blocked",
            }

    monkeypatch.setattr(admin_finance_router, "_require_payment_queue_permission", lambda request, actor: None)
    monkeypatch.setattr(admin_finance_router, "_queue_service", lambda request, session: _FakePaymentQueueService())

    session = _FakeSession()
    response = admin_finance_router.download_admin_export(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace()))),
        "EXPORT-BLOCKED",
        SimpleNamespace(id="admin-operator"),
        session,
    )

    assert response.status_code == 409
    payload = json.loads(response.body)
    assert payload["status"] == "blocked"
    assert "fraud export is blocked" in payload["blocked_reason"]
    assert session.commits == 1
    assert session.rollbacks == 0
