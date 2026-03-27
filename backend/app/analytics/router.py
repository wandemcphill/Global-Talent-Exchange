from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.players.match_learning_service import PlayerMatchLearningService

from .schemas import (
    AnalyticsEventCreate,
    AnalyticsEventView,
    AnalyticsFunnelView,
    AnalyticsSummaryView,
    PlayerMatchAnalyticsView,
    PlayerMatchWeightRefreshView,
)
from .service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
admin_router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


@router.post("/events", response_model=AnalyticsEventView, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: AnalyticsEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsEventView:
    service = AnalyticsService()
    event = service.track_event(session, name=payload.name, user_id=current_user.id, metadata=payload.metadata)
    session.commit()
    session.refresh(event)
    return AnalyticsEventView.model_validate(event)


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
