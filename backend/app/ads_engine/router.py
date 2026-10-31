from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.ads_engine.schemas import (
    SponsoredClipCreateRequest,
    SponsoredClipPerformanceResponse,
    SponsoredClipPerformanceView,
    SponsoredFeedResponse,
    PublicBrandAdCampaignView,
    PublicBrandAdCampaignsResponse,
)
from app.ads_engine.service import SponsoredClipService, SponsoredClipServiceError
from app.ads_engine.brand_campaigns import (
    router as brand_campaigns_router,
    public_router as brand_campaigns_public_router,
)
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
router.include_router(brand_campaigns_router)


public_router = APIRouter(prefix="/public/ads", tags=["public-ads"])
public_router.include_router(brand_campaigns_public_router)


def _is_safe_public_http_url(value: str | None) -> bool:
    from urllib.parse import urlsplit

    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.netloc)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


@public_router.get("/campaigns", response_model=PublicBrandAdCampaignsResponse)
def get_public_brand_ad_campaigns(
    response: Response,
    placement: str | None = Query(
        default=None,
        pattern="^(homepage_rail|homepage_hero|partner_showcase|auth_canvas)$",
    ),
    limit: int = Query(default=60, ge=1, le=100),
    session: Session = Depends(get_session),
) -> PublicBrandAdCampaignsResponse:
    """Return approved brand campaigns that are live inside their delivery window."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.brand_ad_campaign import BrandAdCampaign

    now = datetime.now(UTC)
    statement = (
        select(BrandAdCampaign)
        .where(
            BrandAdCampaign.campaign_type == "brand",
            BrandAdCampaign.status == "approved",
            BrandAdCampaign.is_approved.is_(True),
            BrandAdCampaign.is_active.is_(True),
            BrandAdCampaign.start_at <= now,
            BrandAdCampaign.end_at > now,
        )
        .order_by(
            BrandAdCampaign.priority.desc(),
            BrandAdCampaign.start_at.asc(),
            BrandAdCampaign.id.asc(),
        )
        .limit(limit)
    )
    if placement:
        statement = statement.where(BrandAdCampaign.placement == placement)

    campaigns: list[PublicBrandAdCampaignView] = []
    for campaign in session.scalars(statement).all():
        if not _is_safe_public_http_url(campaign.destination_url):
            continue
        campaigns.append(
            PublicBrandAdCampaignView(
                id=campaign.id,
                brand_name=campaign.brand_name,
                headline=campaign.headline,
                description=campaign.description or "",
                placement=campaign.placement,
                destination_url=campaign.destination_url,
                logo_url=campaign.logo_url if _is_safe_public_http_url(campaign.logo_url) else None,
                creative_url=(campaign.creative_url if _is_safe_public_http_url(campaign.creative_url) else None),
                priority=campaign.priority,
            )
        )

    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    return PublicBrandAdCampaignsResponse(campaigns=campaigns, generated_at=now)
