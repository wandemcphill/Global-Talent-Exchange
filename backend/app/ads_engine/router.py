from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.ads_engine.schemas import (
    SponsoredClipCreateRequest,
    SponsoredClipPerformanceResponse,
    SponsoredClipPerformanceView,
    SponsoredFeedResponse,
)
from app.ads_engine.service import SponsoredClipService, SponsoredClipServiceError
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User

router = APIRouter()
ads_router = APIRouter(prefix="/ads", tags=["ads"])
feed_router = APIRouter(prefix="/feed", tags=["feed"])


def _service(request: Request, session: Session) -> SponsoredClipService:
    return SponsoredClipService(session=session, app=request.app)


@ads_router.post("/create", response_model=SponsoredClipPerformanceView, status_code=status.HTTP_201_CREATED)
def create_sponsored_clip(
    payload: SponsoredClipCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> SponsoredClipPerformanceView:
    service = _service(request, session)
    try:
        ad = service.create_sponsored_clip(payload)
    except SponsoredClipServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(ad)
    return service.performance_view(ad)


@ads_router.get("/performance", response_model=SponsoredClipPerformanceResponse)
def get_ads_performance(
    request: Request,
    ad_id: str | None = None,
    advertiser_id: str | None = None,
    active_only: bool = False,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> SponsoredClipPerformanceResponse:
    return _service(request, session).build_performance_response(
        ad_id=ad_id,
        advertiser_id=advertiser_id,
        active_only=active_only,
    )


@feed_router.get("/sponsored", response_model=SponsoredFeedResponse)
def get_sponsored_feed(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    refresh: bool = False,
    session_id: str | None = None,
    region: str | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SponsoredFeedResponse:
    response = _service(request, session).build_sponsored_feed(
        user=current_user,
        limit=limit,
        refresh=refresh,
        session_id=session_id,
        region=region,
    )
    session.commit()
    return response


router.include_router(ads_router)
router.include_router(feed_router)
