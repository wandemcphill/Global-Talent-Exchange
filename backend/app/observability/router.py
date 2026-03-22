from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_admin, get_session
from app.jobs.ops_jobs import OpsJobRunner
from app.models.risk_ops import AuditLog
from app.observability.schemas import (
    AuditFeedItem,
    ConfigSnapshotView,
    MediaStorageSnapshot,
    OpsJobResponse,
    PaymentMethodSnapshot,
    SponsorshipSnapshot,
)
from app.services.payment_gateway_service import PaymentGatewayService


router = APIRouter(prefix="/observability", tags=["observability"])
admin_router = APIRouter(prefix="/admin/ops", tags=["admin-ops"])


def _job_runner(request: Request) -> OpsJobRunner:
    return OpsJobRunner(
        session_factory=request.app.state.session_factory,
        settings=request.app.state.settings,
        market_engine=getattr(request.app.state, "market_engine", None),
    )


@router.get("/config", response_model=ConfigSnapshotView)
def read_config_snapshot(
    request: Request,
    session: Session = Depends(get_session),
) -> ConfigSnapshotView:
    settings = request.app.state.settings
    payment_methods = PaymentGatewayService(session=session, settings=settings).list_methods()
    return ConfigSnapshotView(
        media_storage=MediaStorageSnapshot(
            storage_root=str(settings.media_storage.storage_root),
            highlight_temp_prefix=settings.media_storage.highlight_temp_prefix,
            highlight_archive_prefix=settings.media_storage.highlight_archive_prefix,
            highlight_export_prefix=settings.media_storage.highlight_export_prefix,
            highlight_temp_ttl_hours=settings.media_storage.highlight_temp_ttl_hours,
            highlight_archive_ttl_days=settings.media_storage.highlight_archive_ttl_days,
            download_expiry_minutes=settings.media_storage.download_expiry_minutes,
            download_rate_limit_count=settings.media_storage.download_rate_limit_count,
            download_rate_limit_window_minutes=settings.media_storage.download_rate_limit_window_minutes,
        ),
        sponsorship=SponsorshipSnapshot(
            default_campaign=settings.sponsorship_inventory.default_campaign,
            surfaces=list(settings.sponsorship_inventory.surfaces),
            campaign_codes=[campaign.code for campaign in settings.sponsorship_inventory.campaigns],
        ),
        payments=PaymentMethodSnapshot(
            total_methods=len(payment_methods),
            live_methods=sum(1 for item in payment_methods if item.is_live),
            providers=[item.provider_key for item in payment_methods],
        ),
    )


@admin_router.post("/media-retention", response_model=OpsJobResponse)
def run_media_retention(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_media_retention()
    return OpsJobResponse(result=result)


@admin_router.post("/integrity-scan", response_model=OpsJobResponse)
def run_integrity_scan(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_integrity_scan()
    return OpsJobResponse(result=result)


@admin_router.get("/audit", response_model=list[AuditFeedItem])
def list_audit_feed(
    actor_user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _admin=Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[AuditFeedItem]:
    stmt = select(AuditLog).options(selectinload(AuditLog.actor_user))
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        stmt = stmt.where(AuditLog.action_key == action)
    if target_type:
        stmt = stmt.where(AuditLog.resource_type == target_type)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    rows = list(session.scalars(stmt).all())
    return [
        AuditFeedItem(
            id=row.id,
            actor_user_id=row.actor_user_id,
            actor_email=row.actor_user.email if row.actor_user else None,
            action=row.action_key,
            target_type=row.resource_type,
            target_id=row.resource_id,
            timestamp=row.created_at,
            outcome=row.outcome,
            detail=row.detail,
            metadata_summary=row.metadata_json,
        )
        for row in rows
    ]


__all__ = ["router", "admin_router"]
