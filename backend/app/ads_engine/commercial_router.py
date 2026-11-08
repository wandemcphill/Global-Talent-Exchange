from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ads_engine.commercial_schemas import (
    AdPlacementSpecAdminUpdateRequest,
    AdPlacementSpecView,
    AdPricingPackageAdminUpsertRequest,
    AdPricingPackageView,
    AdminCampaignModerationRequest,
    AdminWorkspaceActionRequest,
    AdvertiserAuthResponse,
    AdvertiserClientBrandCreateRequest,
    AdvertiserClientBrandView,
    AdvertiserLoginRequest,
    AdvertiserMediaAssetView,
    AdvertiserMemberInviteRequest,
    AdvertiserMemberView,
    AdvertiserRegisterRequest,
    AdvertiserWorkspaceUpdateRequest,
    AdvertiserWorkspaceView,
    BrandCampaignWizardCreateRequest,
    CommercialCampaignView,
    CommercialPriceCalculationRequest,
    CommercialPriceCalculationResponse,
    MediaAssetKind,
    MusicPromotionWizardCreateRequest,
    MusicRotationFeedResponse,
    PaymentInitiateRequest,
    PaymentRecordView,
    RefundCreateRequest,
    RefundRecordView,
    SubscriptionActionRequest,
    SubscriptionView,
    format_ngn_from_minor,
)
from app.ads_engine.commercial_service import CommercialNetworkService, _utcnow
from app.auth.dependencies import (
    get_current_advertiser_user,
    get_current_commercial_admin,
    get_current_finance_admin,
    get_session,
)
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent
from app.models.commercial_network import (
    AdvertiserInvoice,
    AdvertiserMediaAsset,
    AdvertiserPaymentRecord,
    AdvertiserRefundRecord,
    AdvertiserSubscription,
    AdvertiserWorkspace,
    CommercialAuditLog,
)
from app.models.user import User

public_commercial_router = APIRouter(tags=["public-commercial-network"])
advertiser_router = APIRouter(prefix="/advertiser", tags=["advertiser-portal"])
admin_commercial_router = APIRouter(prefix="/admin/advertising", tags=["commercial-admin"])


# ------------------------------------------------------------------
# 1. Public Commercial Network & Media Delivery Routes
# ------------------------------------------------------------------
@public_commercial_router.get("/placements", response_model=list[AdPlacementSpecView])
def list_public_ad_placements(
    division: Literal["brand", "music"] | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[AdPlacementSpecView]:
    service = CommercialNetworkService(session)
    result = service.list_placements(division=division, public_only=True)
    session.commit()
    return result


@public_commercial_router.get("/packages", response_model=list[AdPricingPackageView])
def list_public_pricing_packages(
    division: Literal["brand", "music"] | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[AdPricingPackageView]:
    service = CommercialNetworkService(session)
    result = service.list_pricing_packages(division=division, active_only=True)
    session.commit()
    return result


@public_commercial_router.post("/calculate-price", response_model=CommercialPriceCalculationResponse)
def calculate_public_campaign_price(
    payload: CommercialPriceCalculationRequest,
    session: Session = Depends(get_session),
) -> CommercialPriceCalculationResponse:
    service = CommercialNetworkService(session)
    result = service.calculate_price_ngn(payload)
    session.commit()
    return result


@public_commercial_router.get("/music/rotation", response_model=MusicRotationFeedResponse)
def get_public_music_rotation_feed(
    response: Response,
    limit: int = Query(default=20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> MusicRotationFeedResponse:
    service = CommercialNetworkService(session)
    feed = service.get_music_rotation_feed(limit=limit)
    session.commit()
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    return feed


@public_commercial_router.get("/media/{asset_id}")
def stream_public_advertiser_media_asset(
    asset_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> Response:
    asset = session.get(AdvertiserMediaAsset, asset_id)
    if asset is None or asset.validation_status != "valid":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found.")

    service = CommercialNetworkService(session)
    raw_bytes = service.get_media_asset_bytes(asset)
    total_len = len(raw_bytes)
    headers = {
        "Cache-Control": "public, max-age=86400",
        "X-Content-Type-Options": "nosniff",
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{asset.sanitized_filename}"',
    }

    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes=") and total_len > 0:
        try:
            range_spec = range_header[6:].split(",")[0].strip()
            start_str, end_str = range_spec.split("-", 1)
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else total_len - 1
            start = max(0, min(start, total_len - 1))
            end = max(start, min(end, total_len - 1))
            chunk = raw_bytes[start : end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{total_len}"
            headers["Content-Length"] = str(len(chunk))
            return Response(
                content=chunk,
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                media_type=asset.mime_type,
                headers=headers,
            )
        except Exception:
            pass

    headers["Content-Length"] = str(total_len)
    return Response(content=raw_bytes, media_type=asset.mime_type, headers=headers)


@public_commercial_router.post("/webhooks/{provider}")
async def handle_commercial_payment_webhook(
    provider: Literal["paystack", "korapay"],
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    raw_body = await request.body()
    try:
        payload_dict = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    service = CommercialNetworkService(session)
    return service.handle_provider_webhook(
        provider=provider,
        raw_body=raw_body,
        headers=dict(request.headers),
        payload_dict=payload_dict,
    )


# ------------------------------------------------------------------
# 2. Advertiser Authentication & Workspace Portal Routes
# ------------------------------------------------------------------
@advertiser_router.post("/auth/register", response_model=AdvertiserAuthResponse, status_code=status.HTTP_201_CREATED)
def register_advertiser_account(
    payload: AdvertiserRegisterRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> AdvertiserAuthResponse:
    service = CommercialNetworkService(session)
    user, workspace, issued_session = service.register_advertiser(
        payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return AdvertiserAuthResponse(
        access_token=issued_session.access_token,
        refresh_token=issued_session.refresh_token,
        session_id=issued_session.session_id,
        expires_in=issued_session.expires_in,
        refresh_expires_in=issued_session.refresh_expires_in,
        landing_route="/advertiser/dashboard",
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
            "account_type": user.account_type.value,
        },
        workspace=service.serialize_workspace(workspace),
    )


@advertiser_router.post("/auth/login", response_model=AdvertiserAuthResponse)
def login_advertiser_account(
    payload: AdvertiserLoginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> AdvertiserAuthResponse:
    service = CommercialNetworkService(session)
    user, workspace, issued_session = service.login_advertiser(
        payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return AdvertiserAuthResponse(
        access_token=issued_session.access_token,
        refresh_token=issued_session.refresh_token,
        session_id=issued_session.session_id,
        expires_in=issued_session.expires_in,
        refresh_expires_in=issued_session.refresh_expires_in,
        landing_route="/advertiser/dashboard",
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
            "account_type": user.account_type.value,
        },
        workspace=service.serialize_workspace(workspace),
    )


@advertiser_router.get("/workspace")
def get_advertiser_workspace_overview(
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    workspace = service.require_active_workspace(current_user)
    service.refresh_expired_campaigns()
    campaigns = session.scalars(
        select(BrandAdCampaign)
        .where((BrandAdCampaign.workspace_id == workspace.id) | (BrandAdCampaign.advertiser_id == current_user.id))
        .order_by(BrandAdCampaign.created_at.desc())
    ).all()
    payments = service.list_workspace_payments(current_user)
    paid_minor_ngn = sum(p.amount_minor_ngn for p in payments if p.status == "paid")

    campaign_ids = [c.id for c in campaigns]
    total_impressions = 0
    total_clicks = 0
    total_plays = 0
    if campaign_ids:
        ev_counts = dict(
            session.execute(
                select(BrandAdEvent.event_type, func.count(BrandAdEvent.id))
                .where(BrandAdEvent.campaign_id.in_(campaign_ids))
                .group_by(BrandAdEvent.event_type)
            ).all()
        )
        total_impressions = int(ev_counts.get("impression", 0))
        total_clicks = int(ev_counts.get("click", 0))
        total_plays = int(ev_counts.get("play_started", 0))

    session.commit()
    return {
        "workspace": service.serialize_workspace(workspace).model_dump(mode="json"),
        "summary": {
            "total_campaigns": len(campaigns),
            "active_campaigns": sum(1 for c in campaigns if c.is_active),
            "brand_campaigns": sum(1 for c in campaigns if c.campaign_type == "brand"),
            "music_campaigns": sum(1 for c in campaigns if c.campaign_type == "music"),
            "total_paid_minor_ngn": paid_minor_ngn,
            "total_paid_formatted_ngn": format_ngn_from_minor(paid_minor_ngn) or "₦0.00",
            "impressions": total_impressions,
            "clicks": total_clicks,
            "plays_started": total_plays,
        },
        "members": [m.model_dump(mode="json") for m in service.list_members(current_user)],
        "client_brands": [b.model_dump(mode="json") for b in service.list_client_brands(current_user)],
    }


@advertiser_router.patch("/workspace", response_model=AdvertiserWorkspaceView)
def update_advertiser_workspace_details(
    payload: AdvertiserWorkspaceUpdateRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> AdvertiserWorkspaceView:
    service = CommercialNetworkService(session)
    return service.update_workspace(current_user, payload)


@advertiser_router.get("/members", response_model=list[AdvertiserMemberView])
def list_advertiser_workspace_members(
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> list[AdvertiserMemberView]:
    return CommercialNetworkService(session).list_members(current_user)


@advertiser_router.post("/members", response_model=AdvertiserMemberView, status_code=status.HTTP_201_CREATED)
def invite_advertiser_workspace_member(
    payload: AdvertiserMemberInviteRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> AdvertiserMemberView:
    return CommercialNetworkService(session).invite_member(current_user, payload)


@advertiser_router.get("/brands", response_model=list[AdvertiserClientBrandView])
def list_agency_client_brands(
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> list[AdvertiserClientBrandView]:
    return CommercialNetworkService(session).list_client_brands(current_user)


@advertiser_router.post("/brands", response_model=AdvertiserClientBrandView, status_code=status.HTTP_201_CREATED)
def create_agency_client_brand(
    payload: AdvertiserClientBrandCreateRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> AdvertiserClientBrandView:
    return CommercialNetworkService(session).create_client_brand(current_user, payload)


@advertiser_router.post("/media/upload", response_model=AdvertiserMediaAssetView, status_code=status.HTTP_201_CREATED)
async def upload_advertiser_media_asset(
    request: Request,
    file: UploadFile | None = File(default=None),
    asset_kind: MediaAssetKind = Form(default="brand_image"),
    x_asset_kind: str | None = Header(default=None),
    x_filename: str | None = Header(default=None),
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> AdvertiserMediaAssetView:
    resolved_kind = (x_asset_kind or asset_kind or "brand_image").strip()
    if resolved_kind not in {"logo", "brand_image", "brand_video", "music_audio", "music_artwork"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid asset_kind.")

    if file is not None:
        data = await file.read()
        filename = file.filename or x_filename or "upload.bin"
        content_type = file.content_type
    else:
        data = await request.body()
        filename = x_filename or "upload.bin"
        content_type = request.headers.get("content-type")

    service = CommercialNetworkService(session)
    return service.upload_media_asset(
        user=current_user,
        asset_kind=resolved_kind,
        filename=filename,
        declared_content_type=content_type,
        data=data,
    )


@advertiser_router.get("/campaigns", response_model=list[CommercialCampaignView])
def list_workspace_commercial_campaigns(
    division: Literal["brand", "music"] | None = Query(default=None),
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> list[CommercialCampaignView]:
    service = CommercialNetworkService(session)
    workspace = service.require_active_workspace(current_user)
    service.refresh_expired_campaigns()
    stmt = (
        select(BrandAdCampaign)
        .where((BrandAdCampaign.workspace_id == workspace.id) | (BrandAdCampaign.advertiser_id == current_user.id))
        .order_by(BrandAdCampaign.created_at.desc())
    )
    if division:
        stmt = stmt.where(BrandAdCampaign.campaign_type == division)
    rows = session.scalars(stmt).all()
    session.commit()
    return [service.serialize_campaign(row) for row in rows]


@advertiser_router.post("/campaigns/brand", response_model=CommercialCampaignView, status_code=status.HTTP_201_CREATED)
def create_brand_campaign_via_wizard(
    payload: BrandCampaignWizardCreateRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> CommercialCampaignView:
    service = CommercialNetworkService(session)
    return service.create_brand_campaign_wizard(user=current_user, payload=payload)


@advertiser_router.post("/campaigns/music", response_model=CommercialCampaignView, status_code=status.HTTP_201_CREATED)
def create_music_promotion_via_wizard(
    payload: MusicPromotionWizardCreateRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> CommercialCampaignView:
    service = CommercialNetworkService(session)
    return service.create_music_promotion_wizard(user=current_user, payload=payload)


@advertiser_router.get("/campaigns/{campaign_id}")
def get_workspace_campaign_detail_and_analytics(
    campaign_id: str,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    workspace = service.require_active_workspace(current_user)
    campaign = session.get(BrandAdCampaign, campaign_id)
    if campaign is None or (campaign.workspace_id != workspace.id and campaign.advertiser_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    analytics = service.get_campaign_analytics(campaign.id)
    history = session.scalars(
        select(BrandAdReviewEvent)
        .where(BrandAdReviewEvent.campaign_id == campaign.id)
        .order_by(BrandAdReviewEvent.created_at.desc())
    ).all()
    analytics["history"] = [
        {
            "id": ev.id,
            "action": ev.action,
            "from_status": ev.from_status,
            "to_status": ev.to_status,
            "note": ev.note,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in history
    ]
    return analytics


@advertiser_router.post("/campaigns/{campaign_id}/action", response_model=CommercialCampaignView)
def advertiser_campaign_lifecycle_action(
    campaign_id: str,
    action: Literal["pause", "resume", "archive"] = Query(...),
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> CommercialCampaignView:
    service = CommercialNetworkService(session)
    workspace = service.require_active_workspace(current_user)
    campaign = session.get(BrandAdCampaign, campaign_id)
    if campaign is None or (campaign.workspace_id != workspace.id and campaign.advertiser_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

    prev = campaign.status
    if action == "pause":
        campaign.is_active = False
        campaign.status = "paused"
    elif action == "resume":
        if not service.activate_campaign_if_ready(campaign):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign cannot be resumed until payment is verified and moderation is approved.",
            )
    elif action == "archive":
        campaign.is_active = False
        campaign.status = "archived"
        campaign.archived_at = _utcnow()

    session.add(
        BrandAdReviewEvent(
            campaign_id=campaign.id,
            actor_user_id=current_user.id,
            action=action,
            note=f"Advertiser triggered {action}",
            from_status=prev,
            to_status=campaign.status,
        )
    )
    session.commit()
    session.refresh(campaign)
    return service.serialize_campaign(campaign)


@advertiser_router.post("/payments/initiate", response_model=PaymentRecordView, status_code=status.HTTP_201_CREATED)
def initiate_advertiser_ngn_payment(
    payload: PaymentInitiateRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> PaymentRecordView:
    service = CommercialNetworkService(session)
    return service.initiate_campaign_payment(user=current_user, payload=payload)


@advertiser_router.post("/payments/{reference}/verify", response_model=PaymentRecordView)
def verify_advertiser_ngn_payment(
    reference: str,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> PaymentRecordView:
    service = CommercialNetworkService(session)
    workspace = service.require_active_workspace(current_user)
    payment = session.scalar(select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.reference == reference))
    if payment is None or payment.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
    return service.verify_payment_server_side(reference=reference, actor_user_id=current_user.id)


@advertiser_router.get("/billing")
def get_advertiser_billing_ledger(
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    payments = service.list_workspace_payments(current_user)
    invoices = service.list_workspace_invoices(current_user)
    subscriptions = service.list_workspace_subscriptions(current_user)
    return {
        "currency": "NGN",
        "payments": [p.model_dump(mode="json") for p in payments],
        "invoices": [i.model_dump(mode="json") for i in invoices],
        "subscriptions": [s.model_dump(mode="json") for s in subscriptions],
    }


@advertiser_router.post("/subscriptions/{subscription_id}/action", response_model=SubscriptionView)
def manage_advertiser_subscription(
    subscription_id: str,
    payload: SubscriptionActionRequest,
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> SubscriptionView:
    service = CommercialNetworkService(session)
    return service.manage_subscription(user=current_user, subscription_id=subscription_id, payload=payload)


@advertiser_router.get("/reports")
def get_advertiser_performance_reports(
    current_user: User = Depends(get_current_advertiser_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    workspace = service.require_active_workspace(current_user)
    campaigns = session.scalars(
        select(BrandAdCampaign)
        .where((BrandAdCampaign.workspace_id == workspace.id) | (BrandAdCampaign.advertiser_id == current_user.id))
        .order_by(BrandAdCampaign.created_at.desc())
    ).all()
    items = [service.get_campaign_analytics(c.id) for c in campaigns]
    return {
        "generated_at": _utcnow().isoformat(),
        "currency": "NGN",
        "workspace": service.serialize_workspace(workspace).model_dump(mode="json"),
        "campaign_reports": items,
    }


# ------------------------------------------------------------------
# 3. Commercial Administration Centre Routes
# ------------------------------------------------------------------
@admin_commercial_router.get("/overview")
def get_admin_commercial_overview(
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    service.ensure_default_catalog()
    service.refresh_expired_campaigns()

    workspaces = session.scalars(select(AdvertiserWorkspace)).all()
    campaigns = session.scalars(select(BrandAdCampaign)).all()
    payments = session.scalars(select(AdvertiserPaymentRecord)).all()
    paid_minor = sum(int(p.amount_minor_ngn) for p in payments if p.status == "paid")

    event_counts = dict(
        session.execute(
            select(BrandAdEvent.event_type, func.count(BrandAdEvent.id)).group_by(BrandAdEvent.event_type)
        ).all()
    )
    session.commit()
    return {
        "accounts_total": len(workspaces),
        "accounts_by_type": {
            "business": sum(1 for w in workspaces if w.account_type == "business"),
            "agency": sum(1 for w in workspaces if w.account_type == "agency"),
            "music": sum(1 for w in workspaces if w.account_type == "music"),
        },
        "campaigns_total": len(campaigns),
        "active_campaigns": sum(1 for c in campaigns if c.is_active),
        "pending_moderation": sum(
            1
            for c in campaigns
            if c.status in {"pending", "submitted", "under_review", "awaiting_payment"} and not c.is_approved
        ),
        "revenue_paid_minor_ngn": paid_minor,
        "revenue_paid_formatted_ngn": format_ngn_from_minor(paid_minor) or "₦0.00",
        "events": {
            "impressions": int(event_counts.get("impression", 0)),
            "viewable_impressions": int(event_counts.get("viewable_impression", 0)),
            "clicks": int(event_counts.get("click", 0)),
            "plays_started": int(event_counts.get("play_started", 0)),
            "qualified_listens": int(event_counts.get("qualified_listen", 0))
            + int(event_counts.get("milestone_50", 0)),
            "completed_listens": int(event_counts.get("completed", 0)) + int(event_counts.get("completed_listen", 0)),
        },
    }


@admin_commercial_router.get("/accounts", response_model=list[AdvertiserWorkspaceView])
def admin_list_advertiser_accounts(
    account_type: Literal["business", "agency", "music"] | None = Query(default=None),
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> list[AdvertiserWorkspaceView]:
    service = CommercialNetworkService(session)
    stmt = select(AdvertiserWorkspace).order_by(AdvertiserWorkspace.created_at.desc())
    if account_type:
        stmt = stmt.where(AdvertiserWorkspace.account_type == account_type)
    rows = session.scalars(stmt).all()
    return [service.serialize_workspace(r) for r in rows]


@admin_commercial_router.post("/accounts/{workspace_id}/action", response_model=AdvertiserWorkspaceView)
def admin_moderate_advertiser_account(
    workspace_id: str,
    payload: AdminWorkspaceActionRequest,
    admin_user: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> AdvertiserWorkspaceView:
    service = CommercialNetworkService(session)
    return service.admin_manage_workspace(admin_user=admin_user, workspace_id=workspace_id, payload=payload)


@admin_commercial_router.get("/campaigns", response_model=list[CommercialCampaignView])
def admin_list_commercial_campaigns(
    division: Literal["brand", "music"] | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> list[CommercialCampaignView]:
    service = CommercialNetworkService(session)
    stmt = select(BrandAdCampaign).order_by(BrandAdCampaign.updated_at.desc())
    if division:
        stmt = stmt.where(BrandAdCampaign.campaign_type == division)
    if status_filter:
        stmt = stmt.where(BrandAdCampaign.status == status_filter)
    rows = session.scalars(stmt).all()
    return [service.serialize_campaign(r) for r in rows]


@admin_commercial_router.post("/campaigns/{campaign_id}/moderate", response_model=CommercialCampaignView)
def admin_moderate_commercial_campaign(
    campaign_id: str,
    payload: AdminCampaignModerationRequest,
    admin_user: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> CommercialCampaignView:
    service = CommercialNetworkService(session)
    return service.admin_moderate_campaign(admin_user=admin_user, campaign_id=campaign_id, payload=payload)


@admin_commercial_router.get("/placements", response_model=list[AdPlacementSpecView])
def admin_list_all_placements(
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> list[AdPlacementSpecView]:
    service = CommercialNetworkService(session)
    res = service.list_placements(public_only=False)
    session.commit()
    return res


@admin_commercial_router.patch("/placements/{placement_key}", response_model=AdPlacementSpecView)
def admin_update_placement_spec(
    placement_key: str,
    payload: AdPlacementSpecAdminUpdateRequest,
    admin_user: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> AdPlacementSpecView:
    service = CommercialNetworkService(session)
    return service.admin_update_placement(admin_user=admin_user, placement_key=placement_key, payload=payload)


@admin_commercial_router.get("/pricing", response_model=list[AdPricingPackageView])
def admin_list_pricing_packages(
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> list[AdPricingPackageView]:
    service = CommercialNetworkService(session)
    res = service.list_pricing_packages(active_only=False)
    session.commit()
    return res


@admin_commercial_router.put("/pricing", response_model=AdPricingPackageView)
def admin_upsert_pricing_package(
    payload: AdPricingPackageAdminUpsertRequest,
    admin_user: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> AdPricingPackageView:
    service = CommercialNetworkService(session)
    return service.admin_upsert_pricing_package(admin_user=admin_user, payload=payload)


@admin_commercial_router.get("/payments")
def admin_list_commercial_payments(
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    payments = session.scalars(
        select(AdvertiserPaymentRecord).order_by(AdvertiserPaymentRecord.created_at.desc())
    ).all()
    invoices = session.scalars(select(AdvertiserInvoice).order_by(AdvertiserInvoice.created_at.desc())).all()
    subscriptions = session.scalars(
        select(AdvertiserSubscription).order_by(AdvertiserSubscription.created_at.desc())
    ).all()
    refunds = session.scalars(select(AdvertiserRefundRecord).order_by(AdvertiserRefundRecord.created_at.desc())).all()
    return {
        "currency": "NGN",
        "payments": [service.serialize_payment(p).model_dump(mode="json") for p in payments],
        "invoices": [service.serialize_invoice(i).model_dump(mode="json") for i in invoices],
        "subscriptions": [service.serialize_subscription(s).model_dump(mode="json") for s in subscriptions],
        "refunds": [
            RefundRecordView(
                id=r.id,
                payment_record_id=r.payment_record_id,
                workspace_id=r.workspace_id,
                campaign_id=r.campaign_id,
                amount_minor_ngn=int(r.amount_minor_ngn),
                amount_formatted_ngn=format_ngn_from_minor(int(r.amount_minor_ngn)) or "₦0.00",
                currency=r.currency,
                reason=r.reason,
                status=r.status,
                approved_by_user_id=r.approved_by_user_id,
                created_at=r.created_at,
            ).model_dump(mode="json")
            for r in refunds
        ],
    }


@admin_commercial_router.post("/payments/refund", response_model=RefundRecordView, status_code=status.HTTP_201_CREATED)
def admin_issue_commercial_refund(
    payload: RefundCreateRequest,
    finance_admin: User = Depends(get_current_finance_admin),
    session: Session = Depends(get_session),
) -> RefundRecordView:
    service = CommercialNetworkService(session)
    return service.create_admin_refund(finance_admin=finance_admin, payload=payload)


@admin_commercial_router.get("/analytics")
def admin_get_commercial_analytics(
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    campaigns = session.scalars(select(BrandAdCampaign).order_by(BrandAdCampaign.created_at.desc())).all()
    audit_logs = session.scalars(
        select(CommercialAuditLog).order_by(CommercialAuditLog.created_at.desc()).limit(100)
    ).all()
    return {
        "generated_at": _utcnow().isoformat(),
        "campaigns": [service.get_campaign_analytics(c.id) for c in campaigns],
        "audit_logs": [
            {
                "id": log.id,
                "actor_user_id": log.actor_user_id,
                "workspace_id": log.workspace_id,
                "campaign_id": log.campaign_id,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "action": log.action,
                "note": log.note,
                "metadata_json": log.metadata_json,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in audit_logs
        ],
    }


@admin_commercial_router.post("/media/backfill")
def admin_backfill_media_storage(
    _: User = Depends(get_current_commercial_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommercialNetworkService(session)
    return service.backfill_legacy_media_blobs()
