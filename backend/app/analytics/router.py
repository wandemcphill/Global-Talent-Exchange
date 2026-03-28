from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
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
