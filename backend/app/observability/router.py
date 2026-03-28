from __future__ import annotations

from datetime import timedelta
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_admin, get_session
from app.jobs.ops_jobs import OpsJobRunner
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog, FraudCase, RiskCaseStatus, RiskSeverity, SystemEvent, SystemEventSeverity
from app.models.wallet import LedgerEntry
from app.models.base import utcnow
from app.observability.schemas import (
    AlertFeedItem,
    AlertSnapshotView,
    AuditFeedItem,
    ConfigSnapshotView,
    FraudMonitoringView,
    MediaStorageSnapshot,
    MonitoringDashboardView,
    OpsJobResponse,
    PaymentMethodSnapshot,
    RealtimeOperationsView,
    SponsorshipSnapshot,
    TransactionStreamDashboardView,
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


@admin_router.post("/fan-updates", response_model=OpsJobResponse)
def run_fan_updates(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_fan_update_cycle()
    return OpsJobResponse(result=result)


@admin_router.post("/media-generation", response_model=OpsJobResponse)
def run_media_generation(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_media_generation_cycle()
    return OpsJobResponse(result=result)


@admin_router.post("/identity-evolution", response_model=OpsJobResponse)
def run_identity_evolution(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_identity_evolution_cycle()
    return OpsJobResponse(result=result)


@admin_router.post("/broadcast-revenue", response_model=OpsJobResponse)
def run_broadcast_revenue(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_broadcast_revenue_cycle()
    return OpsJobResponse(result=result)


@admin_router.post("/broadcast-expiration", response_model=OpsJobResponse)
def run_broadcast_expiration(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_broadcast_expiration_cycle()
    return OpsJobResponse(result=result)


@admin_router.post("/ownership-groups/reputation", response_model=OpsJobResponse)
def run_ownership_group_reputation(
    request: Request,
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_ownership_group_reputation_cycle()
    return OpsJobResponse(result=result)


@admin_router.post("/club-market-valuations", response_model=OpsJobResponse)
def run_club_market_valuations(
    request: Request,
    limit: int = Query(default=250, ge=1, le=1000),
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_club_market_valuation_refresh(limit=limit)
    return OpsJobResponse(result=result)


@admin_router.post("/national-team-rental-cleanup", response_model=OpsJobResponse)
def run_national_team_rental_cleanup(
    request: Request,
    competition_id: str | None = Query(default=None),
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_national_team_rental_cleanup(competition_id=competition_id)
    return OpsJobResponse(result=result)


@admin_router.post("/tournament-storylines", response_model=OpsJobResponse)
def run_tournament_storylines(
    request: Request,
    competition_id: str | None = Query(default=None),
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_tournament_storyline_generation(competition_id=competition_id)
    return OpsJobResponse(result=result)


@admin_router.post("/stadium-ad-rotation", response_model=OpsJobResponse)
def run_stadium_ad_rotation(
    request: Request,
    competition_id: str | None = Query(default=None),
    _session: Session = Depends(get_session),
    _admin=Depends(get_current_admin),
) -> OpsJobResponse:
    result = _job_runner(request).run_stadium_ad_rotation(competition_id=competition_id)
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


@admin_router.get("/alerts", response_model=AlertSnapshotView)
def get_alert_snapshot(
    request: Request,
    _admin=Depends(get_current_admin),
) -> AlertSnapshotView:
    snapshot = request.app.state.alert_system.snapshot()
    return AlertSnapshotView(
        total_alerts=snapshot.total_alerts,
        by_severity=dict(snapshot.by_severity),
        by_type=dict(snapshot.by_type),
        recent_alerts=[
            AlertFeedItem(
                alert_id=item.alert_id,
                event_name=item.event_name,
                severity=item.severity,
                alert_type=item.alert_type,
                title=item.title,
                body=item.body,
                user_id=item.user_id,
                created_at=item.created_at,
                metadata=dict(item.metadata),
            )
            for item in snapshot.recent_alerts
        ],
    )


@admin_router.get("/dashboard", response_model=MonitoringDashboardView)
def get_monitoring_dashboard(
    request: Request,
    _admin=Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> MonitoringDashboardView:
    settings = request.app.state.settings
    realtime_snapshot = request.app.state.realtime.snapshot()
    alert_snapshot = request.app.state.alert_system.snapshot()
    since = utcnow() - timedelta(hours=24)

    pending_outbox_events = session.scalar(
        select(func.count()).select_from(EventOutbox).where(EventOutbox.status == "pending")
    ) or 0
    processed_outbox_events = session.scalar(
        select(func.count()).select_from(EventOutbox).where(EventOutbox.status == "processed")
    ) or 0
    recent_transactions_24h = session.scalar(
        select(func.count(func.distinct(LedgerEntry.transaction_id))).where(LedgerEntry.created_at >= since)
    ) or 0
    latest_transaction_at = session.scalar(select(func.max(LedgerEntry.created_at)))
    reason_rows = session.execute(
        select(
            LedgerEntry.reason,
            func.count(func.distinct(LedgerEntry.transaction_id)),
        )
        .where(LedgerEntry.created_at >= since)
        .group_by(LedgerEntry.reason)
    ).all()
    recent_transactions_by_reason = {
        (reason.value if hasattr(reason, "value") else str(reason)): int(count)
        for reason, count in reason_rows
    }

    open_statuses = (RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW)
    open_fraud_cases = session.scalar(
        select(func.count()).select_from(FraudCase).where(FraudCase.status.in_(open_statuses))
    ) or 0
    high_severity_open_fraud_cases = session.scalar(
        select(func.count()).select_from(FraudCase).where(
            FraudCase.status.in_(open_statuses),
            FraudCase.severity.in_((RiskSeverity.HIGH, RiskSeverity.CRITICAL)),
        )
    ) or 0
    critical_system_events = session.scalar(
        select(func.count()).select_from(SystemEvent).where(SystemEvent.severity == SystemEventSeverity.CRITICAL)
    ) or 0

    alert_view = AlertSnapshotView(
        total_alerts=alert_snapshot.total_alerts,
        by_severity=dict(alert_snapshot.by_severity),
        by_type=dict(alert_snapshot.by_type),
        recent_alerts=[
            AlertFeedItem(
                alert_id=item.alert_id,
                event_name=item.event_name,
                severity=item.severity,
                alert_type=item.alert_type,
                title=item.title,
                body=item.body,
                user_id=item.user_id,
                created_at=item.created_at,
                metadata=dict(item.metadata),
            )
            for item in alert_snapshot.recent_alerts
        ],
    )
    return MonitoringDashboardView(
        transaction_stream=TransactionStreamDashboardView(
            kafka_enabled=settings.kafka_enabled,
            outbox_relay_enabled=settings.outbox_relay_enabled,
            topic_prefix=settings.kafka_topic_prefix,
            pending_outbox_events=int(pending_outbox_events),
            processed_outbox_events=int(processed_outbox_events),
            recent_transactions_24h=int(recent_transactions_24h),
            recent_transactions_by_reason=recent_transactions_by_reason,
            latest_transaction_at=latest_transaction_at,
        ),
        realtime=RealtimeOperationsView(
            total_events=realtime_snapshot.total_events,
            channels=dict(realtime_snapshot.channels),
            active_wallet_connections=realtime_snapshot.active_wallet_connections,
            tracked_wallet_streams=realtime_snapshot.tracked_wallet_streams,
            delivered_messages=realtime_snapshot.delivered_messages,
        ),
        fraud=FraudMonitoringView(
            open_fraud_cases=int(open_fraud_cases),
            high_severity_open_fraud_cases=int(high_severity_open_fraud_cases),
            critical_system_events=int(critical_system_events),
            recent_alert_counts=dict(alert_snapshot.by_type),
        ),
        alerts=alert_view,
    )


__all__ = ["router", "admin_router"]
