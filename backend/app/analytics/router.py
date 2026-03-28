from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.models.user import User
from app.players.match_learning_service import PlayerMatchLearningService
from app.schemas.referral_analytics import CreatorLeaderboardResponse
from app.services.creator_leaderboard_service import CreatorLeaderboardService
from app.services.device_fingerprint_service import DeviceFingerprintService
from app.services.referral_orchestrator import get_referral_orchestrator

from .schemas import (
    AnalyticsAgentLearningView,
    AnalyticsAnomalySummaryView,
    AnalyticsDeviceFingerprintView,
    AnalyticsEventCreate,
    AnalyticsEventView,
    AnalyticsFunnelView,
    FrontendAnalyticsEventCreate,
    ClipAnalyticsDetailView,
    ClipDashboardItemView,
    ClipDashboardResponse,
    ClipDropOffDashboardResponse,
    ClipDropOffItemView,
    ClipLifecycleStageView,
    AnalyticsMatchOutcomeView,
    AnalyticsPricePredictionResponse,
    AnalyticsSummaryView,
    AnalyticsUserSegmentationView,
    PlayerMatchAnalyticsView,
    PlayerMatchWeightRefreshView,
)
from .insight_service import AnalyticsInsightService
from .service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
admin_router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])
public_router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events", response_model=AnalyticsEventView, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: AnalyticsEventCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsEventView:
    service = AnalyticsService()
    fingerprint = DeviceFingerprintService().build(headers=request.headers)
    metadata = {
        **dict(payload.metadata),
        "device_fingerprint": fingerprint.fingerprint,
        "device_signal_sources": list(fingerprint.source_signals),
    }
    event = service.track_event(session, name=payload.name, user_id=current_user.id, metadata=metadata)
    session.commit()
    session.refresh(event)
    return AnalyticsEventView.model_validate(event)


@public_router.post("/frontend", response_model=AnalyticsEventView, status_code=status.HTTP_201_CREATED)
def create_frontend_event(
    payload: FrontendAnalyticsEventCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> AnalyticsEventView:
    service = AnalyticsService()
    fingerprint = DeviceFingerprintService().build(headers=request.headers)
    event_name = f"frontend.{payload.category.strip().lower()}.{payload.name.strip().lower()}".replace(" ", "_")[:64]
    metadata = {
        **dict(payload.metadata),
        "category": payload.category,
        "screen": payload.screen,
        "flow": payload.flow,
        "target": payload.target,
        "stage": payload.stage,
        "success": payload.success,
        "status_code": payload.status_code,
        "latency_ms": payload.latency_ms,
        "device_fingerprint": fingerprint.fingerprint,
        "device_signal_sources": list(fingerprint.source_signals),
    }
    event = service.track_event(
        session,
        name=event_name,
        user_id=current_user.id if current_user is not None else None,
        metadata=metadata,
    )
    session.commit()
    session.refresh(event)
    return AnalyticsEventView.model_validate(event)


@public_router.get("/clip/{clip_id}", response_model=ClipAnalyticsDetailView)
def read_clip_analytics(
    clip_id: str,
    session: Session = Depends(get_session),
) -> ClipAnalyticsDetailView:
    snapshot = AnalyticsService().clip_snapshot(session, clip_id=clip_id)
    analytics = snapshot["analytics"]
    lifecycle = snapshot["lifecycle"]
    return ClipAnalyticsDetailView(
        clip_id=clip_id,
        impressions=int(analytics["impressions"]),
        views=int(analytics["view_count"]),
        completions=int(analytics["completions"]),
        completion_rate=float(analytics["completion_rate"]),
        shares=int(analytics["shares"]),
        revenue=snapshot["revenue"],
        avg_watch_time_seconds=float(analytics["watch_time"]),
        drop_off_point_seconds=analytics.get("drop_off_point_seconds"),
        funnel=[
            ClipLifecycleStageView(stage="generated", count=int(lifecycle["generated"])),
            ClipLifecycleStageView(stage="viewed", count=int(lifecycle["viewed"])),
            ClipLifecycleStageView(stage="completed", count=int(lifecycle["completed"])),
            ClipLifecycleStageView(stage="shared", count=int(lifecycle["shared"])),
            ClipLifecycleStageView(stage="monetized", count=int(lifecycle["monetized"])),
        ],
    )


@router.get("/device-fingerprint", response_model=AnalyticsDeviceFingerprintView)
def get_device_fingerprint(
    request: Request,
    _: User = Depends(get_current_user),
) -> AnalyticsDeviceFingerprintView:
    fingerprint = DeviceFingerprintService().build(headers=request.headers)
    return AnalyticsDeviceFingerprintView(
        fingerprint=fingerprint.fingerprint,
        source_signals=list(fingerprint.source_signals),
    )


@router.get("/influencer-leaderboard", response_model=CreatorLeaderboardResponse)
def get_influencer_leaderboard(request: Request) -> CreatorLeaderboardResponse:
    orchestrator = get_referral_orchestrator(request)
    return CreatorLeaderboardService(orchestrator).build()


@admin_router.get("/summary", response_model=AnalyticsSummaryView)
def read_summary(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsSummaryView:
    service = AnalyticsService()
    since, totals = service.summary(session)
    return AnalyticsSummaryView(since=since, totals=totals)


@public_router.get("/dashboard/top-clips", response_model=ClipDashboardResponse)
def read_top_clip_dashboard(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> ClipDashboardResponse:
    items = AnalyticsService().clip_dashboard(session, limit=limit)
    return ClipDashboardResponse(
        generated_at=datetime.now(timezone.utc),
        items=[ClipDashboardItemView.model_validate(item) for item in items],
    )


@public_router.get("/dashboard/drop-off", response_model=ClipDropOffDashboardResponse)
def read_clip_drop_off_dashboard(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> ClipDropOffDashboardResponse:
    items = AnalyticsService().clip_drop_off_dashboard(session, limit=limit)
    return ClipDropOffDashboardResponse(
        generated_at=datetime.now(timezone.utc),
        items=[ClipDropOffItemView.model_validate(item) for item in items],
    )


@admin_router.get("/funnels", response_model=AnalyticsFunnelView)
def read_funnel(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsFunnelView:
    service = AnalyticsService()
    since, steps = service.funnel(session)
    return AnalyticsFunnelView(since=since, steps=steps)


@admin_router.get("/player-matching", response_model=PlayerMatchAnalyticsView)
def read_player_matching_summary(
    since_days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> PlayerMatchAnalyticsView:
    payload = PlayerMatchLearningService(session=session).build_admin_summary(since_days=since_days)
    return PlayerMatchAnalyticsView.model_validate(payload)


@admin_router.post("/player-matching/recompute-weights", response_model=PlayerMatchWeightRefreshView)
def recompute_player_matching_weights(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> PlayerMatchWeightRefreshView:
    payload = PlayerMatchLearningService(session=session).refresh_weights()
    session.commit()
    return PlayerMatchWeightRefreshView.model_validate(payload)


@admin_router.get("/agent-learning", response_model=AnalyticsAgentLearningView)
def read_agent_learning_summary(
    since_days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsAgentLearningView:
    payload = AnalyticsInsightService(session=session).agent_learning_summary(since_days=since_days)
    return AnalyticsAgentLearningView(
        mode=str(payload["mode"]),
        status=str(payload["status"]),
        since=payload["since"],
        analytics=PlayerMatchAnalyticsView.model_validate(payload["analytics"]),
    )


@admin_router.get("/price-predictions", response_model=AnalyticsPricePredictionResponse)
def read_price_predictions(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsPricePredictionResponse:
    payload = AnalyticsInsightService(session=session).price_predictions(limit=limit)
    return AnalyticsPricePredictionResponse.model_validate(
        {
            "generated_at": datetime.now(timezone.utc),
            "items": payload,
        }
    )


@admin_router.get("/user-segments", response_model=AnalyticsUserSegmentationView)
def read_user_segments(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsUserSegmentationView:
    payload = AnalyticsInsightService(session=session).user_segments()
    return AnalyticsUserSegmentationView.model_validate(payload)


@admin_router.get("/match-outcomes", response_model=AnalyticsMatchOutcomeView)
def read_match_outcomes(
    since_days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsMatchOutcomeView:
    payload = AnalyticsInsightService(session=session).match_outcome_analytics(since_days=since_days)
    return AnalyticsMatchOutcomeView.model_validate(payload)


@admin_router.get("/anomalies", response_model=AnalyticsAnomalySummaryView)
def read_anomaly_summary(
    since_days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AnalyticsAnomalySummaryView:
    service = AnalyticsInsightService(session=session)
    summary = service.anomaly_summary(since_days=since_days)
    integrity_scan = service.integrity_anomaly_scan(since_days=since_days)
    payload = {
        **summary,
        "matches_scanned": integrity_scan["matches_scanned"],
        "flagged_matches": integrity_scan["flagged_matches"],
        "top_findings": integrity_scan["top_findings"],
    }
    return AnalyticsAnomalySummaryView.model_validate(payload)
