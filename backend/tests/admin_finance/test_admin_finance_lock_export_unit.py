from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.admin_finance import router as admin_finance_router
from app.admin_finance.schemas import AdminExportRequest
from app.admin_finance.service import AdminFinanceService
from app.auth.service import AuthService
from app.models import CountryFeaturePolicy
from app.models.creator_monetization import CreatorRevenueSettlement
from app.models.event_backbone import EventOutbox
from app.models.reward_settlement import RewardSettlement
from app.models.risk_ops import FraudCase, RiskSeverity
from app.models.treasury import PaymentMode, TreasuryAuditEvent
from app.models.wallet import LedgerUnit
from app.treasury.service import TreasuryConflictError, TreasuryService


@pytest.fixture()
def session(gtex_db_session):
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    yield gtex_db_session


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
    assert export["status"] == "queued"
    assert export["download_url"] is None
    assert export["blocked_reason"] is None
    assert export["audit_reference"]
    assert export["requested_audit_reference"] == export["audit_reference"]

    queued_status = service.get_admin_export_status(export_id=export["export_id"])
    assert queued_status["status"] == "queued"
    assert queued_status["requested_audit_reference"] == export["requested_audit_reference"]

    ready_status = service.complete_admin_export(actor=actor, export_id=export["export_id"])
    assert ready_status["status"] == "ready"
    assert ready_status["download_url"].endswith(f"/exports/{export['export_id']}/download")
    assert ready_status["blocked_reason"] is None
    assert ready_status["requested_audit_reference"] == export["requested_audit_reference"]
    assert ready_status["audit_reference"] != export["audit_reference"]
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
    assert export_audit.payload["admin_user_id"] == actor.id
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
    assert export_ready_event.headers_json["audit_reference"] == ready_status["audit_reference"]
    assert export_ready_event.payload_json["status"] == "ready"
    assert export_ready_event.payload_json["admin_user_id"] == actor.id
    assert export_ready_event.payload_json["artifact"]["row_count"] >= 1
    assert "content" not in export_ready_event.payload_json["artifact"]


def test_admin_export_request_idempotency_reuses_existing_request(session) -> None:
    treasury, _user, _deposit = _submitted_deposit(session)
    actor = _create_user(session, email="idempotent-export-admin@example.com", username="idempotentexportadmin")
    service = AdminFinanceService(session=session, treasury_service=treasury)

    first = service.request_admin_export(
        actor=actor,
        export_type="payment_queue",
        export_format="csv",
        filters={"limit": 25},
        idempotency_key="admin-export-idempotent-1",
    )
    second = service.request_admin_export(
        actor=actor,
        export_type="payment_queue",
        export_format="csv",
        filters={"limit": 25},
        idempotency_key="admin-export-idempotent-1",
    )

    assert first["export_id"] == second["export_id"]
    assert first["status"] == "queued"
    assert second["status"] == "queued"
    assert second["enqueue_required"] is False

    requested_audits = session.scalars(
        select(TreasuryAuditEvent).where(
            TreasuryAuditEvent.resource_type == "admin_export",
            TreasuryAuditEvent.resource_id == first["export_id"],
            TreasuryAuditEvent.event_type == "admin.export.requested",
        )
    ).all()
    assert len(requested_audits) == 1

    with pytest.raises(ValueError, match="Idempotency key already used"):
        service.request_admin_export(
            actor=actor,
            export_type="payment_queue",
            export_format="csv",
            filters={"limit": 50},
            idempotency_key="admin-export-idempotent-1",
        )

    ready = service.complete_admin_export(actor=actor, export_id=first["export_id"])
    third = service.request_admin_export(
        actor=actor,
        export_type="payment_queue",
        export_format="csv",
        filters={"limit": 25},
        idempotency_key="admin-export-idempotent-1",
    )

    assert ready["status"] == "ready"
    assert third["export_id"] == first["export_id"]
    assert third["status"] == "ready"
    assert third["enqueue_required"] is False


def test_admin_export_worker_failure_is_audited_and_notified(session, monkeypatch) -> None:
    treasury, _user, _deposit = _submitted_deposit(session)
    actor = _create_user(session, email="failed-export-admin@example.com", username="failedexportadmin")
    service = AdminFinanceService(session=session, treasury_service=treasury)
    queued = service.request_admin_export(
        actor=actor,
        export_type="payment_queue",
        export_format="csv",
        filters={"limit": 25},
    )

    def _fail_artifact_build(self, **_kwargs):
        del self
        raise RuntimeError("artifact generator unavailable")

    monkeypatch.setattr(AdminFinanceService, "_build_admin_export_artifact", _fail_artifact_build)

    failed = service.complete_admin_export(actor=actor, export_id=queued["export_id"])

    assert failed["status"] == "failed"
    assert failed["download_url"] is None
    assert failed["failure_reason"] == "artifact generator unavailable"
    with pytest.raises(ValueError, match="Export artifact was not found"):
        service.get_admin_export_artifact(export_id=queued["export_id"])

    failed_audit = session.scalar(
        select(TreasuryAuditEvent).where(
            TreasuryAuditEvent.resource_type == "admin_export",
            TreasuryAuditEvent.resource_id == queued["export_id"],
            TreasuryAuditEvent.event_type == "admin.export.failed",
        )
    )
    assert failed_audit is not None
    assert failed_audit.payload["status"] == "failed"
    assert failed_audit.payload["failure_reason"] == "artifact generator unavailable"

    failed_event = session.scalar(
        select(EventOutbox).where(
            EventOutbox.event_type == "admin.export.failed",
            EventOutbox.aggregate_type == "admin_export",
            EventOutbox.aggregate_id == queued["export_id"],
        )
    )
    assert failed_event is not None
    assert failed_event.payload_json["status"] == "failed"
    assert "artifact" not in failed_event.payload_json


def test_admin_finance_export_worker_completes_queued_export(session, monkeypatch) -> None:
    from app.workers import jobs

    class _SessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc, traceback):
            return False

    treasury, _user, _deposit = _submitted_deposit(session)
    actor = _create_user(session, email="worker-export-admin@example.com", username="workerexportadmin")
    service = AdminFinanceService(session=session, treasury_service=treasury)
    queued = service.request_admin_export(
        actor=actor,
        export_type="payment_queue",
        export_format="csv",
        filters={"limit": 25},
    )
    monkeypatch.setattr(
        jobs,
        "_TASK_CONTEXT",
        SimpleNamespace(database=SimpleNamespace(session_factory=lambda: _SessionContext())),
    )

    result = jobs.admin_finance_export_job(export_id=queued["export_id"], actor_user_id=actor.id)

    assert result["status"] == "ready"
    assert result["download_url"].endswith(f"/exports/{queued['export_id']}/download")
    assert service.get_admin_export_status(export_id=queued["export_id"])["status"] == "ready"


def test_admin_export_request_route_enqueues_worker_without_materializing(monkeypatch) -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class _FakeTaskQueue:
        def __init__(self) -> None:
            self.enqueued: list[dict[str, object]] = []

        def enqueue(self, **kwargs):
            self.enqueued.append(kwargs)
            return SimpleNamespace(job_id=kwargs["job_id"])

    class _FakePaymentQueueService:
        completed = False

        def request_admin_export(self, *, actor, export_type, export_format, filters, idempotency_key):
            assert actor.id == "admin-operator"
            assert export_type == "payment_queue"
            assert export_format == "csv"
            assert filters == {"limit": 25}
            assert idempotency_key == "export-route-idempotent-1"
            return {
                "export_id": "EXPORT-ROUTE-QUEUED",
                "status": "queued",
                "export_type": "payment_queue",
                "format": "csv",
                "filters": filters,
                "requested_at": "2026-06-03T00:00:00+00:00",
                "completed_at": None,
                "download_url": None,
                "blocked_reason": None,
                "failure_reason": None,
                "audit_reference": "audit-requested",
                "requested_audit_reference": "audit-requested",
                "enqueue_required": True,
            }

        def complete_admin_export(self, *, actor, export_id):
            del actor, export_id
            self.completed = True
            raise AssertionError("request route must not complete exports inline")

    fake_queue = _FakeTaskQueue()
    fake_service = _FakePaymentQueueService()
    monkeypatch.setattr(admin_finance_router, "_require_payment_queue_permission", lambda request, actor: None)
    monkeypatch.setattr(admin_finance_router, "_queue_service", lambda request, session: fake_service)

    response = admin_finance_router.request_admin_export(
        SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(settings=SimpleNamespace(), task_queue=fake_queue),
            )
        ),
        AdminExportRequest(
            export_type="payment_queue",
            format="csv",
            filters={"limit": 25},
            idempotency_key="export-route-idempotent-1",
        ),
        SimpleNamespace(id="admin-operator"),
        _FakeSession(),
    )

    assert response.status == "queued"
    assert fake_service.completed is False
    assert len(fake_queue.enqueued) == 1
    assert fake_queue.enqueued[0]["job_id"] == "admin-finance-export:EXPORT-ROUTE-QUEUED"
    assert fake_queue.enqueued[0]["kwargs"] == {
        "export_id": "EXPORT-ROUTE-QUEUED",
        "actor_user_id": "admin-operator",
    }


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

    queued_export = service.request_admin_export(
        actor=actor,
        export_type="fraud",
        export_format="json",
        filters={},
    )
    assert queued_export["status"] == "queued"
    export = service.complete_admin_export(actor=actor, export_id=queued_export["export_id"])

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

    queued_export = service.request_admin_export(
        actor=actor,
        export_type="settlements",
        export_format="csv",
        filters={"competition_key": "competition:cup-final"},
    )
    assert queued_export["status"] == "queued"
    export = service.complete_admin_export(actor=actor, export_id=queued_export["export_id"])

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

    queued_export = service.request_admin_export(
        actor=actor,
        export_type="settlements",
        export_format="json",
        filters={"competition_id": "creator-competition-export-1"},
    )
    assert queued_export["status"] == "queued"
    export = service.complete_admin_export(actor=actor, export_id=queued_export["export_id"])

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
        def get_admin_export_status(self, *, export_id):
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
    assert session.commits == 0
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
        def get_admin_export_status(self, *, export_id):
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
    assert session.commits == 0
    assert session.rollbacks == 0
