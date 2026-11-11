from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ads_engine.brand_schemas import (
    AdminConversionEventRequest,
    AdminMusicRightsVerificationRequest,
    BrandAdEventResponse,
    BrandAdvertiserProfileUpsertRequest,
    BrandAdvertiserProfileView,
    BrandCampaignEventRequest,
    BrandCampaignHistoryView,
    BrandCampaignReviewRequest,
    BrandCampaignUpsertRequest,
    BrandCampaignView,
    CampaignReportView,
    CampaignReportsResponse,
    PublicMusicPromotionsResponse,
    PublicMusicPromotionView,
)
from app.ads_engine.schemas import PublicBrandAdCampaignsResponse, PublicBrandAdCampaignView
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
from app.models.commercial_network import AdvertiserWorkspace
from app.models.user import User

router = APIRouter(prefix="/ads/brand", tags=["brand-advertiser"])
public_router = APIRouter(tags=["public-ads"])


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite-naive test values and PostgreSQL aware values for safe comparisons."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _profile_for(session: Session, user_id: str) -> BrandAdvertiserProfile | None:
    return session.scalar(select(BrandAdvertiserProfile).where(BrandAdvertiserProfile.user_id == user_id))


def _campaign_for_owner(session: Session, campaign_id: str, user_id: str) -> BrandAdCampaign:
    campaign = session.scalar(
        select(BrandAdCampaign).where(
            BrandAdCampaign.id == campaign_id,
            BrandAdCampaign.advertiser_id == user_id,
        )
    )
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return campaign


def _event_counts(
    session: Session,
    campaign_ids: list[str],
    *,
    include_client_analytics: bool = False,
) -> dict[str, dict[str, int]]:
    """Count events per campaign.

    Rows with event_source="client" are anonymous analytics. Spend and delivery
    throttling ignore them unless include_client_analytics is set for reports.
    """
    if not campaign_ids:
        return {}
    from sqlalchemy.exc import SQLAlchemyError

    try:
        statement = (
            select(BrandAdEvent.campaign_id, BrandAdEvent.event_type, func.count(BrandAdEvent.id))
            .where(BrandAdEvent.campaign_id.in_(campaign_ids))
            .group_by(BrandAdEvent.campaign_id, BrandAdEvent.event_type)
        )
        if not include_client_analytics:
            statement = statement.where(BrandAdEvent.event_source != "client")
        rows = session.execute(statement).all()
        result: dict[str, dict[str, int]] = {}
        for campaign_id, event_type, count in rows:
            result.setdefault(campaign_id, {})[event_type] = int(count)
        return result
    except SQLAlchemyError:
        return {}


def _estimated_spend(campaign: BrandAdCampaign, counts: dict[str, int]) -> Decimal:
    """Spend from server-delivered events only. Caller counts must exclude event_source="client"."""
    price = Decimal(campaign.unit_price or 0)
    if campaign.pricing_model == "CPC":
        amount = Decimal(counts.get("click", 0)) * price
    else:
        amount = (Decimal(counts.get("impression", 0)) / Decimal(1000)) * price
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _report(
    campaign: BrandAdCampaign,
    counts: dict[str, int],
    billable_counts: dict[str, int],
) -> CampaignReportView:
    impressions = counts.get("impression", 0)
    clicks = counts.get("click", 0)
    conversions = counts.get("conversion", 0)
    spend = _estimated_spend(campaign, billable_counts)
    budget = Decimal(campaign.budget_amount or 0)
    return CampaignReportView(
        campaign_id=campaign.id,
        campaign_name=campaign.headline,
        status=campaign.status,
        currency=campaign.currency,
        budget_amount=budget,
        pricing_model=campaign.pricing_model,
        unit_price=Decimal(campaign.unit_price or 0),
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        ctr_percent=round((clicks / impressions) * 100, 2) if impressions else 0.0,
        estimated_spend=spend,
        estimated_budget_remaining=max(Decimal("0"), budget - spend),
    )


def _is_campaign_budget_exhausted(session: Session, campaign: BrandAdCampaign) -> bool:
    if campaign.pricing_model in {"PACKAGE", "DURATION_NGN", "SUBSCRIPTION_NGN"}:
        return False
    budget = Decimal(campaign.budget_amount or 0)
    if budget <= Decimal("0"):
        return False
    counts = _event_counts(session, [campaign.id], include_client_analytics=False).get(campaign.id, {})
    spend = _estimated_spend(campaign, counts)
    return spend >= budget


def _live_campaign_statement(*, campaign_type: str, now: datetime):
    return (
        select(BrandAdCampaign)
        .where(
            BrandAdCampaign.campaign_type == campaign_type,
            BrandAdCampaign.status.in_(("approved", "active")),
            BrandAdCampaign.is_approved.is_(True),
            BrandAdCampaign.is_active.is_(True),
            BrandAdCampaign.payment_status == "paid",
            BrandAdCampaign.start_at <= now,
            BrandAdCampaign.end_at > now,
        )
        .order_by(BrandAdCampaign.priority.desc(), BrandAdCampaign.start_at.asc(), BrandAdCampaign.id.asc())
    )


@router.get("/profile", response_model=BrandAdvertiserProfileView | None)
def get_advertiser_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = _profile_for(session, current_user.id)
    return profile


@router.put("/profile", response_model=BrandAdvertiserProfileView)
def upsert_advertiser_profile(
    payload: BrandAdvertiserProfileUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = _profile_for(session, current_user.id)
    values = payload.model_dump()
    if profile is None:
        profile = BrandAdvertiserProfile(user_id=current_user.id, **values)
        session.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)
    session.commit()
    session.refresh(profile)
    return profile


@router.get("/campaigns", response_model=list[BrandCampaignView])
def list_advertiser_campaigns(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaigns = session.scalars(
        select(BrandAdCampaign)
        .where(BrandAdCampaign.advertiser_id == current_user.id)
        .order_by(BrandAdCampaign.updated_at.desc(), BrandAdCampaign.id.asc())
    ).all()
    return campaigns


@router.post("/campaigns", response_model=BrandCampaignView, status_code=status.HTTP_201_CREATED)
def create_advertiser_campaign(
    payload: BrandCampaignUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if _profile_for(session, current_user.id) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Complete your advertiser profile before creating a campaign."
        )
    values = payload.model_dump()
    values.pop("payment_status", None)
    campaign = BrandAdCampaign(
        advertiser_id=current_user.id,
        **values,
        priority=100,
        is_approved=False,
        is_active=False,
        status="draft",
        payment_status="unpaid",
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=BrandCampaignView)
def update_advertiser_campaign(
    campaign_id: str,
    payload: BrandCampaignUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign = _campaign_for_owner(session, campaign_id, current_user.id)
    if campaign.status not in {"draft", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only draft or rejected campaigns can be edited."
        )
    for key, value in payload.model_dump().items():
        if key == "payment_status":
            continue
        setattr(campaign, key, value)
    campaign.is_approved = False
    campaign.is_active = False
    campaign.status = "draft"
    campaign.reviewed_at = None
    campaign.reviewed_by_user_id = None
    campaign.review_note = None
    session.commit()
    session.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/submit", response_model=BrandCampaignView)
def submit_advertiser_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign = _campaign_for_owner(session, campaign_id, current_user.id)
    if campaign.status not in {"draft", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only draft or rejected campaigns can be submitted."
        )
    if _as_utc(campaign.end_at) <= _now() or _as_utc(campaign.start_at) >= _as_utc(campaign.end_at):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Campaign schedule is not valid.")
    previous = campaign.status
    campaign.status = "pending"
    campaign.is_approved = False
    campaign.is_active = False
    campaign.submitted_at = _now()
    campaign.review_note = None
    session.add(
        BrandAdReviewEvent(
            campaign_id=campaign.id,
            actor_user_id=current_user.id,
            action="submitted",
            note=None,
            from_status=previous,
            to_status="pending",
        )
    )
    session.commit()
    session.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}/history", response_model=list[BrandCampaignHistoryView])
def advertiser_campaign_history(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _campaign_for_owner(session, campaign_id, current_user.id)
    return session.scalars(
        select(BrandAdReviewEvent)
        .where(BrandAdReviewEvent.campaign_id == campaign_id)
        .order_by(BrandAdReviewEvent.created_at.desc(), BrandAdReviewEvent.id.asc())
    ).all()


@router.get("/admin/campaigns/{campaign_id}/history", response_model=list[BrandCampaignHistoryView])
def admin_campaign_history(
    campaign_id: str,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    if session.get(BrandAdCampaign, campaign_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return session.scalars(
        select(BrandAdReviewEvent)
        .where(BrandAdReviewEvent.campaign_id == campaign_id)
        .order_by(BrandAdReviewEvent.created_at.desc(), BrandAdReviewEvent.id.asc())
    ).all()


@router.get("/reports", response_model=CampaignReportsResponse)
def advertiser_campaign_reports(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaigns = session.scalars(select(BrandAdCampaign).where(BrandAdCampaign.advertiser_id == current_user.id)).all()
    campaign_ids = [campaign.id for campaign in campaigns]
    analytics = _event_counts(session, campaign_ids, include_client_analytics=True)
    billable = _event_counts(session, campaign_ids, include_client_analytics=False)
    return CampaignReportsResponse(
        reports=[
            _report(campaign, analytics.get(campaign.id, {}), billable.get(campaign.id, {})) for campaign in campaigns
        ],
        generated_at=_now(),
    )


@router.get("/admin/campaigns", response_model=list[BrandCampaignView])
def admin_list_brand_campaigns(
    status_filter: Literal["draft", "pending", "approved", "rejected", "paused", "archived"] | None = Query(
        default=None, alias="status"
    ),
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    statement = select(BrandAdCampaign).order_by(BrandAdCampaign.updated_at.desc(), BrandAdCampaign.id.asc())
    if status_filter:
        statement = statement.where(BrandAdCampaign.status == status_filter)
    return session.scalars(statement).all()


@router.get("/admin/reports", response_model=CampaignReportsResponse)
def admin_campaign_reports(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    campaigns = session.scalars(select(BrandAdCampaign)).all()
    campaign_ids = [campaign.id for campaign in campaigns]
    analytics = _event_counts(session, campaign_ids, include_client_analytics=True)
    billable = _event_counts(session, campaign_ids, include_client_analytics=False)
    return CampaignReportsResponse(
        reports=[
            _report(campaign, analytics.get(campaign.id, {}), billable.get(campaign.id, {})) for campaign in campaigns
        ],
        generated_at=_now(),
    )


@router.post("/admin/campaigns/{campaign_id}/review", response_model=BrandCampaignView)
def admin_review_brand_campaign(
    campaign_id: str,
    payload: BrandCampaignReviewRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    campaign = session.get(BrandAdCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    previous = campaign.status
    now = _now()
    if payload.action == "approve":
        if previous not in {"pending", "paused"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Only pending or paused campaigns can be approved."
            )
        if _as_utc(campaign.end_at) <= now:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Expired campaigns cannot be approved.")
        if campaign.payment_status != "paid":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign must be paid before it can be approved.",
            )
        campaign.status = "approved"
        campaign.is_approved = True
        campaign.is_active = True
    elif payload.action == "reject":
        if previous != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending campaigns can be rejected.")
        campaign.status = "rejected"
        campaign.is_approved = False
        campaign.is_active = False
    elif payload.action == "pause":
        if previous != "approved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only approved campaigns can be paused.")
        campaign.status = "paused"
        campaign.is_active = False
    else:
        campaign.status = "archived"
        campaign.is_active = False
        campaign.is_approved = False
        campaign.archived_at = now
    campaign.reviewed_at = now
    campaign.reviewed_by_user_id = admin.id
    campaign.review_note = payload.note
    session.add(
        BrandAdReviewEvent(
            campaign_id=campaign.id,
            actor_user_id=admin.id,
            action=payload.action,
            note=payload.note,
            from_status=previous,
            to_status=campaign.status,
        )
    )
    session.commit()
    session.refresh(campaign)
    return campaign


@router.put("/admin/campaigns/{campaign_id}/music-rights", response_model=BrandCampaignView)
def admin_verify_music_rights(
    campaign_id: str,
    payload: AdminMusicRightsVerificationRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    campaign = session.get(BrandAdCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.campaign_type != "music":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Music rights verification only applies to music campaigns.",
        )
    previous_verified = campaign.music_rights_verified
    campaign.music_rights_verified = payload.music_rights_verified
    campaign.music_rights_holder = payload.music_rights_holder
    campaign.music_license_doc_url = payload.music_license_doc_url
    session.add(
        BrandAdReviewEvent(
            campaign_id=campaign.id,
            actor_user_id=admin.id,
            action="verify_music_rights",
            note=payload.note,
            from_status=f"rights_verified:{previous_verified}",
            to_status=f"rights_verified:{campaign.music_rights_verified}",
        )
    )
    session.commit()
    session.refresh(campaign)
    return campaign


@router.post("/admin/campaigns/{campaign_id}/conversions", response_model=BrandAdEventResponse)
def admin_record_conversion(
    campaign_id: str,
    payload: AdminConversionEventRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
):
    campaign = session.get(BrandAdCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    event = BrandAdEvent(
        campaign_id=campaign.id,
        event_type="conversion",
        idempotency_key=payload.idempotency_key,
        user_id=None,
        event_source="admin",
        metadata_json=payload.metadata_json,
    )
    session.add(event)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(BrandAdEvent).where(BrandAdEvent.idempotency_key == payload.idempotency_key))
        if existing is None or existing.campaign_id != campaign.id or existing.event_type != "conversion":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Idempotency key already belongs to another event."
            )
        return BrandAdEventResponse(accepted=True, duplicate=True)
    return BrandAdEventResponse(accepted=True, duplicate=False)


@public_router.get("/music/promotions", response_model=PublicMusicPromotionsResponse)
def get_public_music_promotions(
    response: Response,
    session: Session = Depends(get_session),
):
    now = _now()
    rows = session.scalars(_live_campaign_statement(campaign_type="music", now=now).limit(100)).all()
    candidate_ids = [row.id for row in rows]
    counts_by_campaign = (
        _event_counts(session, candidate_ids, include_client_analytics=False) if candidate_ids else {}
    )
    promotions = []
    for row in rows:
        if row.payment_status != "paid":
            continue
        if row.music_target_type not in {"track", "artist", "playlist"}:
            continue
        if not row.music_target_id or not _safe_http_url(row.destination_url):
            continue
        # Phase 5: Only deliver music promotions with verified rights clearance
        if not row.music_rights_verified:
            continue
        # Phase 5: Pacing / throttling - exclude budget-exhausted campaigns
        if row.pricing_model in {"CPM", "CPC"}:
            budget = Decimal(row.budget_amount or 0)
            if budget > Decimal("0"):
                spend = _estimated_spend(row, counts_by_campaign.get(row.id, {}))
                if spend >= budget:
                    continue
        audio_url = row.music_audio_url or (
            f"/api/v2/public/ads/media/{row.music_audio_asset_id}" if row.music_audio_asset_id else None
        )
        artwork_url = row.music_artwork_url or (
            f"/api/v2/public/ads/media/{row.music_artwork_asset_id}" if row.music_artwork_asset_id else row.logo_url
        )
        promotions.append(
            PublicMusicPromotionView(
                campaign_id=row.id,
                brand_name=row.brand_name,
                headline=row.headline,
                description=row.description or "",
                destination_url=row.destination_url,
                creative_url=row.creative_url if _safe_media_or_http_url(row.creative_url) else None,
                audio_url=audio_url if _safe_media_or_http_url(audio_url) else None,
                artwork_url=artwork_url if _safe_media_or_http_url(artwork_url) else None,
                explicit_content=bool(row.music_explicit_content),
                target_type=row.music_target_type,
                target_id=row.music_target_id,
                track_title=row.music_title,
                artist_name=row.music_artist_name,
                playlist_name=row.music_playlist_name,
                genre=row.music_genre,
                music_rights_verified=row.music_rights_verified,
                music_rights_holder=row.music_rights_holder,
            )
        )
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    return PublicMusicPromotionsResponse(promotions=promotions, generated_at=now)


def _safe_http_url(value: str | None) -> bool:
    from urllib.parse import urlsplit

    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.netloc)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


def _safe_media_or_http_url(value: str | None) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    cleaned = value.strip()
    if cleaned.startswith(("/api/v2/public/ads/media/", "/public/ads/media/", "/api/public/ads/media/")):
        return True
    return _safe_http_url(cleaned)


@public_router.get("/stadium/inventory", response_model=PublicBrandAdCampaignsResponse)
def get_public_stadium_inventory(
    response: Response,
    limit: int = Query(default=25, ge=1, le=50),
    session: Session = Depends(get_session),
) -> PublicBrandAdCampaignsResponse:
    """Live, paid, approved sponsor inventory for the 3D stadium perimeter LED boards.

    Stricter than the generic public campaign feed: only commercial-network brand campaigns that are
    approved, *paid*, inside their delivery window, owned by an active workspace, not budget exhausted
    and booked for the ``stadium_perimeter`` placement are returned. Never fabricates inventory; an empty
    list tells the renderer to use house creatives.
    """
    now = _now()
    candidates = session.scalars(_live_campaign_statement(campaign_type="brand", now=now).limit(limit * 4)).all()
    counts_by_campaign = _event_counts(session, [c.id for c in candidates], include_client_analytics=False)

    workspace_status: dict[str, str | None] = {}
    inventory: list[PublicBrandAdCampaignView] = []
    for campaign in candidates:
        if len(inventory) >= limit:
            break
        if campaign.payment_status != "paid":
            continue
        placements = list(campaign.placements_json or [])
        if campaign.placement and campaign.placement not in placements:
            placements.insert(0, campaign.placement)
        if "stadium_perimeter" not in placements:
            continue
        if not _safe_http_url(campaign.destination_url):
            continue
        if campaign.workspace_id:
            if campaign.workspace_id not in workspace_status:
                workspace = session.get(AdvertiserWorkspace, campaign.workspace_id)
                workspace_status[campaign.workspace_id] = workspace.status if workspace is not None else None
            if workspace_status[campaign.workspace_id] != "active":
                continue
        if campaign.pricing_model in {"CPM", "CPC"}:
            budget = Decimal(campaign.budget_amount or 0)
            if budget > Decimal("0") and _estimated_spend(campaign, counts_by_campaign.get(campaign.id, {})) >= budget:
                continue

        creative_url = campaign.creative_url or (
            f"/api/v2/public/ads/media/{campaign.creative_asset_id}" if campaign.creative_asset_id else None
        )
        logo_url = campaign.logo_url or (
            f"/api/v2/public/ads/media/{campaign.logo_asset_id}" if campaign.logo_asset_id else None
        )
        media_type = (campaign.creative_media_type or "").lower()
        # LED canvas renders stills; silent video creatives are not drawn on the perimeter boards.
        if media_type and not media_type.startswith("image/"):
            creative_url = None
        inventory.append(
            PublicBrandAdCampaignView(
                id=campaign.id,
                brand_name=campaign.brand_name,
                headline=campaign.headline,
                description=campaign.description or "",
                placement="stadium_perimeter",
                placements=placements,
                destination_url=campaign.destination_url,
                logo_url=logo_url if _safe_media_or_http_url(logo_url) else None,
                creative_url=creative_url if _safe_media_or_http_url(creative_url) else None,
                creative_media_type=campaign.creative_media_type,
                is_silent_creative=True,
                sponsored_label="Sponsored",
                priority=campaign.priority,
            )
        )
    response.headers["Cache-Control"] = "public, max-age=15, stale-while-revalidate=30"
    return PublicBrandAdCampaignsResponse(campaigns=inventory, generated_at=now)


def record_server_brand_delivery(
    session: Session,
    campaign: BrandAdCampaign,
    *,
    event_type: Literal["impression", "click"],
    idempotency_key: str,
) -> bool:
    """Record one billable delivery the server actually served.

    Client analytics must not call this. The idempotency key is counted at most once.
    """
    if event_type not in {"impression", "click"}:
        raise ValueError("Server delivery events must be impression or click.")
    existing = session.scalar(select(BrandAdEvent).where(BrandAdEvent.idempotency_key == idempotency_key))
    if existing is not None:
        return False
    session.add(
        BrandAdEvent(
            campaign_id=campaign.id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            user_id=None,
            event_source="server",
            metadata_json={},
        )
    )
    session.flush()
    return True


@public_router.post("/events", response_model=BrandAdEventResponse)
def record_public_brand_ad_event(
    payload: BrandCampaignEventRequest,
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
):
    campaign = session.get(BrandAdCampaign, payload.campaign_id)
    now = _now()
    if (
        campaign is None
        or campaign.campaign_type not in {"brand", "music"}
        or campaign.status not in {"approved", "active"}
        or not campaign.is_approved
        or not campaign.is_active
        or _as_utc(campaign.start_at) > now
        or _as_utc(campaign.end_at) <= now
        or campaign.payment_status != "paid"
        or not _safe_http_url(campaign.destination_url)
        or _is_campaign_budget_exhausted(session, campaign)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live campaign not found.")
    event = BrandAdEvent(
        campaign_id=campaign.id,
        event_type=payload.event_type,
        idempotency_key=payload.idempotency_key,
        user_id=current_user.id if current_user else None,
        event_source="client",
        metadata_json=payload.metadata_json,
    )
    session.add(event)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(select(BrandAdEvent).where(BrandAdEvent.idempotency_key == payload.idempotency_key))
        if existing is None or existing.campaign_id != campaign.id or existing.event_type != payload.event_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Idempotency key already belongs to another event."
            )
        return BrandAdEventResponse(accepted=True, duplicate=True)
    return BrandAdEventResponse(accepted=True, duplicate=False)
