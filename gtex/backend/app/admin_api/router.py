from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.capabilities import AdminCapability, note_admin_read, require_admin_capability
from app.admin_godmode.service import AdminGodModeService
from app.auth.dependencies import get_session
from app.manager_market.service import ManagerMarketService
from app.models.event_backbone import CompetitionQueueRecord
from app.models.user import User
from app.models.wallet import LedgerEntry, LedgerEntryReason
from app.operations_readiness.schemas import OperationsReadinessSnapshot
from app.operations_readiness.service import OperationsReadinessService
from app.orders.models import Order, OrderStatus
from app.wallets.service import WalletService

from .schemas import (
    AdminCompetitionsCanonicalView,
    AdminPaymentRailsCanonicalView,
    AdminQueueJobView,
    AdminQueuesCanonicalView,
    AdminSettlementLedgerEntryView,
    AdminSettlementsCanonicalView,
    AdminTreasuryCanonicalView,
)

router = APIRouter(prefix="/api/admin", tags=["admin-api"])


@router.get("/readiness", response_model=OperationsReadinessSnapshot)
def get_admin_readiness(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin_capability(AdminCapability.VIEW_AUDIT_LOG)),
) -> OperationsReadinessSnapshot:
    note_admin_read(request, "admin.readiness.read")
    return OperationsReadinessService(session).snapshot()


@router.get("/treasury", response_model=AdminTreasuryCanonicalView)
def get_admin_treasury(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin_capability(AdminCapability.MANAGE_TREASURY_WITHDRAWALS)),
) -> AdminTreasuryCanonicalView:
    service = _godmode_service(request)
    note_admin_read(request, "admin.treasury.read")
    return AdminTreasuryCanonicalView(
        summary=service.get_treasury_summary(request.app, session),
        dashboard=service.get_treasury_dashboard(request.app, session),
        withdrawals=service.get_withdrawal_summary(request.app, session),
    )


@router.get("/payment-rails", response_model=AdminPaymentRailsCanonicalView)
def get_admin_payment_rails(
    request: Request,
    _: User = Depends(require_admin_capability(AdminCapability.MANAGE_PAYMENT_RAILS)),
) -> AdminPaymentRailsCanonicalView:
    service = _godmode_service(request)
    rails = service.get_payment_rails(request.app)
    note_admin_read(request, "admin.payment_rails.read")
    return AdminPaymentRailsCanonicalView(
        rails=rails.rails,
        reason=rails.reason,
        health=service.get_payment_rail_health(request.app),
    )


@router.get("/queues", response_model=AdminQueuesCanonicalView)
def get_admin_queues(
    request: Request,
    queue_name: str | None = Query(default=None, min_length=1, max_length=64),
    job_limit: int = Query(default=50, ge=0, le=250),
    session: Session = Depends(get_session),
    _: User = Depends(require_admin_capability(AdminCapability.VIEW_AUDIT_LOG)),
) -> AdminQueuesCanonicalView:
    readiness = OperationsReadinessService(session).snapshot()
    jobs = _list_competition_queue_jobs(session, queue_name=queue_name, limit=job_limit)
    totals = dict(readiness.totals)
    totals["competition_jobs"] = _count_competition_queue_jobs(session, queue_name=queue_name)
    note_admin_read(
        request,
        "admin.queues.read",
        queue_name=queue_name,
        job_limit=job_limit,
    )
    return AdminQueuesCanonicalView(
        generated_at=readiness.generated_at,
        totals=totals,
        operations_queues=readiness.queues,
        jobs=jobs,
    )


@router.get("/settlements", response_model=AdminSettlementsCanonicalView)
def get_admin_settlements(
    request: Request,
    recent_limit: int = Query(default=50, ge=1, le=250),
    session: Session = Depends(get_session),
    _: User = Depends(require_admin_capability(AdminCapability.MANAGE_TREASURY_WITHDRAWALS)),
) -> AdminSettlementsCanonicalView:
    note_admin_read(request, "admin.settlements.read", recent_limit=recent_limit)
    return AdminSettlementsCanonicalView(
        order_status_counts=_order_status_counts(session),
        ledger_reason_counts=_settlement_reason_counts(session),
        recent_entries=_recent_settlement_entries(session, limit=recent_limit),
    )


@router.get("/competitions", response_model=AdminCompetitionsCanonicalView)
def get_admin_competitions(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin_capability(AdminCapability.MANAGE_COMPETITIONS)),
) -> AdminCompetitionsCanonicalView:
    godmode_service = _godmode_service(request)
    manager_service = ManagerMarketService(wallet_service=_wallet_service(request))
    note_admin_read(request, "admin.competitions.read")
    return AdminCompetitionsCanonicalView(
        controls=godmode_service.get_competition_controls(request.app),
        manager_competitions=manager_service.list_competitions(request.app, session),
    )


def _godmode_service(request: Request) -> AdminGodModeService:
    return AdminGodModeService(wallet_service=_wallet_service(request))


def _wallet_service(request: Request) -> WalletService:
    return WalletService(
        event_publisher=getattr(request.app.state, "event_publisher", None),
        cache_backend=getattr(request.app.state, "cache_backend", None),
    )


def _list_competition_queue_jobs(
    session: Session,
    *,
    queue_name: str | None,
    limit: int,
) -> list[AdminQueueJobView]:
    if limit <= 0:
        return []
    stmt = select(CompetitionQueueRecord)
    if queue_name is not None:
        stmt = stmt.where(CompetitionQueueRecord.queue_name == queue_name)
    records = session.scalars(
        stmt.order_by(CompetitionQueueRecord.published_at.desc(), CompetitionQueueRecord.id.desc()).limit(limit)
    ).all()
    return [
        AdminQueueJobView(
            id=record.id,
            queue_name=record.queue_name,
            job_name=record.job_name,
            idempotency_key=record.idempotency_key,
            aggregate_id=record.aggregate_id,
            partition_key=record.partition_key,
            status=record.status,
            published_at=record.published_at,
            payload=_safe_mapping(record.payload_json),
            metadata=_safe_mapping(record.metadata_json),
        )
        for record in records
    ]


def _count_competition_queue_jobs(session: Session, *, queue_name: str | None) -> int:
    stmt = select(func.count()).select_from(CompetitionQueueRecord)
    if queue_name is not None:
        stmt = stmt.where(CompetitionQueueRecord.queue_name == queue_name)
    return int(session.scalar(stmt) or 0)


def _order_status_counts(session: Session) -> dict[str, int]:
    return {
        status.value: int(session.scalar(select(func.count()).select_from(Order).where(Order.status == status)) or 0)
        for status in OrderStatus
    }


def _settlement_reason_counts(session: Session) -> dict[str, int]:
    return {
        reason.value: int(
            session.scalar(select(func.count()).select_from(LedgerEntry).where(LedgerEntry.reason == reason)) or 0
        )
        for reason in _SETTLEMENT_LEDGER_REASONS
    }


def _recent_settlement_entries(session: Session, *, limit: int) -> list[AdminSettlementLedgerEntryView]:
    records = session.scalars(
        select(LedgerEntry)
        .where(LedgerEntry.reason.in_(_SETTLEMENT_LEDGER_REASONS))
        .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminSettlementLedgerEntryView(
            id=entry.id,
            transaction_id=entry.transaction_id,
            amount=entry.amount,
            unit=_enum_value(entry.unit),
            reason=_enum_value(entry.reason),
            transaction_type=_enum_value(entry.transaction_type),
            source_tag=_enum_value(entry.source_tag),
            reference=entry.reference,
            external_reference=entry.external_reference,
            description=entry.description,
            created_at=entry.created_at,
        )
        for entry in records
    ]


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _safe_mapping(value: Any) -> dict[str, Any]:
    safe_value = _safe_payload(value)
    return safe_value if isinstance(safe_value, dict) else {}


def _safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe_payload(item) for key, item in value.items() if not _looks_sensitive(str(key))}
    if isinstance(value, list):
        return [_safe_payload(item) for item in value]
    return value


def _looks_sensitive(key: str) -> bool:
    normalized = key.lower()
    return any(token in normalized for token in ("secret", "token", "password", "credential"))


_SETTLEMENT_LEDGER_REASONS = (
    LedgerEntryReason.TRADE_SETTLEMENT,
    LedgerEntryReason.WITHDRAWAL_SETTLEMENT,
    LedgerEntryReason.COMPETITION_REWARD,
)


__all__ = ["router"]
