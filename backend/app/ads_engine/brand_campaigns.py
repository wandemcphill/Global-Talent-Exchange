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
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
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


def _event_counts(session: Session, campaign_ids: list[str]) -> dict[str, dict[str, int]]:
    if not campaign_ids:
        return {}
    from sqlalchemy.exc import SQLAlchemyError

    try:
        rows = session.execute(
            select(BrandAdEvent.campaign_id, BrandAdEvent.event_type, func.count(BrandAdEvent.id))
            .where(BrandAdEvent.campaign_id.in_(campaign_ids))
            .group_by(BrandAdEvent.campaign_id, BrandAdEvent.event_type)
        ).all()
        result: dict[str, dict[str, int]] = {}
        for campaign_id, event_type, count in rows:
            result.setdefault(campaign_id, {})[event_type] = int(count)
        return result
    except SQLAlchemyError:
        return {}


def _estimated_spend(campaign: BrandAdCampaign, counts: dict[str, int]) -> Decimal:
    price = Decimal(campaign.unit_price or 0)
    if campaign.pricing_model == "CPC":
        amount = Decimal(counts.get("click", 0)) * price
    else:
        amount = (Decimal(counts.get("impression", 0)) / Decimal(1000)) * price
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _report(campaign: BrandAdCampaign, counts: dict[str, int]) -> CampaignReportView:
    impressions = counts.get("impression", 0)
    clicks = counts.get("click", 0)
    conversions = counts.get("conversion", 0)
    spend = _estimated_spend(campaign, counts)
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
    budget = Decimal(campaign.budget_amount or 0)
    if budget <= Decimal("0"):
        return False
    counts = _event_counts(session, [campaign.id]).get(campaign.id, {})
    spend = _estimated_spend(campaign, counts)
    return spend >= budget


def _live_campaign_statement(*, campaign_type: str, now: datetime):
    return (
        select(BrandAdCampaign)
        .where(
            BrandAdCampaign.campaign_type == campaign_type,
            BrandAdCampaign.status == "approved",
            BrandAdCampaign.is_approved.is_(True),
            BrandAdCampaign.is_active.is_(True),
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
    campaign = BrandAdCampaign(
        advertiser_id=current_user.id,
        **values,
        priority=100,
        is_approved=False,
        is_active=False,
        status="draft",
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
    counts = _event_counts(session, [campaign.id for campaign in campaigns])
    return CampaignReportsResponse(
        reports=[_report(campaign, counts.get(campaign.id, {})) for campaign in campaigns],
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
    counts = _event_counts(session, [campaign.id for campaign in campaigns])
    return CampaignReportsResponse(
        reports=[_report(campaign, counts.get(campaign.id, {})) for campaign in campaigns],
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
    counts_by_campaign = _event_counts(session, candidate_ids) if candidate_ids else {}
    promotions = []
    for row in rows:
        if row.music_target_type not in {"track", "artist", "playlist"}:
            continue
        if not row.music_target_id or not _safe_http_url(row.destination_url):
            continue
        # Phase 5: Only deliver music promotions with verified rights clearance
        if not row.music_rights_verified:
            continue
        # Phase 5: Pacing / throttling - exclude budget-exhausted campaigns
        budget = Decimal(row.budget_amount or 0)
        if budget > Decimal("0"):
            spend = _estimated_spend(row, counts_by_campaign.get(row.id, {}))
            if spend >= budget:
                continue
        promotions.append(
            PublicMusicPromotionView(
                campaign_id=row.id,
                brand_name=row.brand_name,
                headline=row.headline,
                description=row.description or "",
                destination_url=row.destination_url,
                creative_url=row.creative_url if _safe_http_url(row.creative_url) else None,
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
        or campaign.status != "approved"
        or not campaign.is_approved
        or not campaign.is_active
        or _as_utc(campaign.start_at) > now
        or _as_utc(campaign.end_at) <= now
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
