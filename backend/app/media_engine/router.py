from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi import Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.media_engine.schemas import (
    CreatorAnalyticsDashboardView,
    CreatorAnalyticsTopGifterView,
    CreatorBroadcastModeView,
    CreatorBroadcastPurchaseRequest,
    CreatorBroadcastPurchaseView,
    CreatorMatchAccessView,
    CreatorMatchGiftRequest,
    CreatorMatchGiftView,
    CreatorMatchStadiumOfferView,
    CreatorRevenueSettlementView,
    CreatorSeasonPassCreateRequest,
    CreatorSeasonPassView,
    CreatorStadiumConfigUpdateRequest,
    CreatorStadiumControlUpdateRequest,
    CreatorStadiumControlView,
    CreatorStadiumLevelUpdateRequest,
    CreatorStadiumMonetizationView,
    CreatorStadiumPlacementCreateRequest,
    CreatorStadiumPlacementView,
    CreatorStadiumPricingView,
    CreatorStadiumProfileView,
    CreatorStadiumTicketPurchaseRequest,
    CreatorStadiumTicketPurchaseView,
    HighlightShareAmplificationRequest,
    HighlightShareAmplificationView,
    HighlightShareExportRequest,
    HighlightShareExportView,
    HighlightShareTemplateView,
    MatchRevenueSnapshotView,
    MatchViewCreateRequest,
    MatchViewView,
    MediaAssetView,
    MediaDownloadRequest,
    MediaDownloadResponse,
    PremiumVideoPurchaseRequest,
    PremiumVideoPurchaseView,
    RevenueSnapshotCreateRequest,
)
from app.media_engine.service import MediaEngineError, MediaEngineService
from app.models.user import User
from app.services.creator_analytics_service import CreatorAnalyticsDashboard, CreatorAnalyticsService, CreatorTopGifterMetric
from app.services.creator_broadcast_service import CreatorBroadcastError, CreatorBroadcastQuote, CreatorBroadcastService
from app.services.creator_revenue_service import CreatorRevenueService
from app.services.creator_stadium_service import CreatorMatchStadiumOffer, CreatorStadiumBundle, CreatorStadiumError, CreatorStadiumService
from app.services.media_access_service import MediaAccessError, MediaAccessService
from app.services.highlight_share_service import HighlightShareError, HighlightShareService
from app.services.signing_service import SignedTokenService
from app.services.storage_media_service import MediaStorageService
from app.services.sponsorship_placement_service import SponsorshipPlacementService
from app.analytics.service import AnalyticsService
from app.storage import LocalObjectStorage, StorageNotFound

router = APIRouter(prefix='/media-engine', tags=['media-engine'])
admin_router = APIRouter(prefix='/admin/media-engine', tags=['admin-media-engine'])


def _view(item) -> MatchViewView:
    return MatchViewView.model_validate(item, from_attributes=True)


def _purchase(item) -> PremiumVideoPurchaseView:
    return PremiumVideoPurchaseView.model_validate(item, from_attributes=True)


def _snapshot(item) -> MatchRevenueSnapshotView:
    return MatchRevenueSnapshotView.model_validate(item, from_attributes=True)


def _asset(item) -> MediaAssetView:
    return MediaAssetView(
        storage_key=item.storage_key,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        metadata=item.metadata,
        expires_at=item.expires_at,
    )


def _share_export(item: HighlightShareExportView | object) -> HighlightShareExportView:
    export = item
    metadata = getattr(export, "metadata_json", None) or {}
    export_asset = metadata.get("export_asset", {})
    return HighlightShareExportView(
        export_id=getattr(export, "id"),
        storage_key=getattr(export, "export_storage_key"),
        content_type=export_asset.get("content_type", "application/zip"),
        size_bytes=int(export_asset.get("size_bytes", 0)),
        template_code=metadata.get("template", {}).get("code"),
        aspect_ratio=getattr(export, "aspect_ratio"),
        share_title=getattr(export, "share_title"),
        watermark_label=getattr(export, "watermark_label"),
        metadata=metadata,
        created_at=getattr(export, "created_at"),
    )


def _share_amplification(item) -> HighlightShareAmplificationView:
    return HighlightShareAmplificationView(
        id=item.id,
        export_id=item.export_id,
        story_feed_item_id=item.story_feed_item_id,
        channel=item.channel,
        status=item.status,
        subject_type=item.subject_type,
        subject_id=item.subject_id,
        title=item.title,
        caption=item.caption,
        metadata_json=item.metadata_json or {},
        created_at=item.created_at,
    )


def _creator_mode(item) -> CreatorBroadcastModeView:
    return CreatorBroadcastModeView(
        mode_key=item.mode_key,
        name=item.name,
        description=item.description,
        min_duration_minutes=item.min_duration_minutes,
        max_duration_minutes=item.max_duration_minutes,
        min_price_coin=item.min_price_coin,
        max_price_coin=item.max_price_coin,
        metadata_json=item.metadata_json,
    )


def _creator_access(item: CreatorBroadcastQuote) -> CreatorMatchAccessView:
    return CreatorMatchAccessView(
        match_id=item.context.match.id,
        competition_id=item.context.competition.id,
        season_id=item.context.season.id,
        home_club_id=item.context.match.home_club_id,
        away_club_id=item.context.match.away_club_id,
        mode_key=item.mode.mode_key,
        mode_name=item.mode.name,
        duration_minutes=item.duration_minutes,
        price_coin=item.price_coin,
        has_access=item.access.has_access,
        access_source=item.access.source,
        pass_club_id=item.access.season_pass.club_id if item.access.season_pass is not None else None,
        stadium_ticket_type=item.access.stadium_ticket.ticket_type if item.access.stadium_ticket is not None else None,
        includes_premium_seating=bool(
            item.access.stadium_ticket.includes_premium_seating if item.access.stadium_ticket is not None else False
        ),
        metadata_json={
            "creator_league_only": True,
            "season_tier_id": item.context.season_tier.id,
        },
    )


def _creator_purchase(item) -> CreatorBroadcastPurchaseView:
    return CreatorBroadcastPurchaseView.model_validate(item, from_attributes=True)


def _creator_pass(item) -> CreatorSeasonPassView:
    return CreatorSeasonPassView.model_validate(item, from_attributes=True)


def _creator_stadium_control(item) -> CreatorStadiumControlView:
    return CreatorStadiumControlView.model_validate(item, from_attributes=True)


def _creator_stadium_profile(item) -> CreatorStadiumProfileView:
    return CreatorStadiumProfileView.model_validate(item, from_attributes=True)


def _creator_stadium_pricing(item) -> CreatorStadiumPricingView:
    return CreatorStadiumPricingView.model_validate(item, from_attributes=True)


def _creator_stadium_placement(item) -> CreatorStadiumPlacementView:
    return CreatorStadiumPlacementView.model_validate(item, from_attributes=True)


def _creator_stadium_ticket(item) -> CreatorStadiumTicketPurchaseView:
    return CreatorStadiumTicketPurchaseView.model_validate(item, from_attributes=True)


def _creator_stadium_bundle(item: CreatorStadiumBundle, *, season_id: str) -> CreatorStadiumMonetizationView:
    return CreatorStadiumMonetizationView(
        season_id=season_id,
        club_id=item.profile.club_id,
        control=_creator_stadium_control(item.control),
        stadium=_creator_stadium_profile(item.profile),
        pricing=_creator_stadium_pricing(item.pricing) if item.pricing is not None else None,
    )


def _creator_match_stadium_offer(item: CreatorMatchStadiumOffer) -> CreatorMatchStadiumOfferView:
    return CreatorMatchStadiumOfferView(
        match_id=item.context.match.id,
        competition_id=item.context.competition.id,
        season_id=item.context.season.id,
        club_id=item.context.match.home_club_id,
        stadium=_creator_stadium_profile(item.profile),
        pricing=_creator_stadium_pricing(item.pricing),
        control=_creator_stadium_control(item.control),
        remaining_capacity=item.remaining_capacity,
        remaining_vip_capacity=item.remaining_vip_capacity,
        placements=[_creator_stadium_placement(placement) for placement in item.placements],
        metadata_json={
            "creator_league_only": True,
            "live_video_match_access": True,
            "custom_club_chants": item.pricing.custom_chants_enabled,
            "custom_club_visuals": item.pricing.custom_visuals_enabled,
            "shareholder_ticket_access_opens_at": item.shareholder_ticket_access_opens_at,
            "public_ticket_access_opens_at": item.public_ticket_access_opens_at,
            "ticket_access_phase": item.ticket_access_phase,
            "actor_has_shareholder_access": item.actor_has_shareholder_access,
        },
    )


def _creator_gift(item) -> CreatorMatchGiftView:
    return CreatorMatchGiftView.model_validate(item, from_attributes=True)


def _creator_settlement(item) -> CreatorRevenueSettlementView:
    return CreatorRevenueSettlementView.model_validate(item, from_attributes=True)


def _creator_top_gifter(item: CreatorTopGifterMetric) -> CreatorAnalyticsTopGifterView:
    return CreatorAnalyticsTopGifterView(
        user_id=item.user_id,
        username=item.username,
        display_name=item.display_name,
        total_gift_coin=item.total_gift_coin,
        gift_count=item.gift_count,
    )


def _creator_dashboard(item: CreatorAnalyticsDashboard) -> CreatorAnalyticsDashboardView:
    return CreatorAnalyticsDashboardView(
        match_id=item.context.match.id,
        competition_id=item.context.competition.id,
        season_id=item.context.season.id,
        club_id=item.club_id,
        total_viewers=item.total_viewers,
        video_viewers=item.video_viewers,
        gift_totals_coin=item.gift_totals_coin,
        top_gifters=[_creator_top_gifter(gifter) for gifter in item.top_gifters],
        fan_engagement_pct=item.fan_engagement_pct,
        engaged_fans=item.engaged_fans,
        total_watch_seconds=item.total_watch_seconds,
        metadata_json={
            "creator_league_only": True,
            "season_tier_id": item.context.season_tier.id,
        },
    )


def _storage_service(request: Request) -> MediaStorageService:
    settings = request.app.state.settings
    storage = LocalObjectStorage(settings.media_storage.storage_root)
    return MediaStorageService(storage=storage, config=settings.media_storage)


def _access_service(request: Request, session: Session) -> MediaAccessService:
    settings = request.app.state.settings
    signer = SignedTokenService(settings.media_signing_secret, purpose="media_download")
    return MediaAccessService(
        session=session,
        settings=settings,
        storage_service=_storage_service(request),
        signer=signer,
        event_publisher=getattr(request.app.state, "event_publisher", None),
    )


def _media_service(session: Session, request: Request | None = None) -> MediaEngineService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return MediaEngineService(session, event_publisher=request.app.state.event_publisher)
    return MediaEngineService(session)


def _highlight_share_service(request: Request, session: Session) -> HighlightShareService:
    placement_service = SponsorshipPlacementService(session=session, settings=request.app.state.settings, analytics=AnalyticsService())
    return HighlightShareService(
        session=session,
        storage_service=_storage_service(request),
        placement_service=placement_service,
    )


@router.post('/views', response_model=MatchViewView, status_code=201)
def create_view(payload: MatchViewCreateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MatchViewView:
    try:
        item = MediaEngineService(session).record_view(actor=user, match_key=payload.match_key, competition_key=payload.competition_key, watch_seconds=payload.watch_seconds, premium_unlocked=payload.premium_unlocked)
        session.commit()
        return _view(item)
    except MediaEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/purchases', response_model=PremiumVideoPurchaseView, status_code=201)
def purchase_video(payload: PremiumVideoPurchaseRequest, request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> PremiumVideoPurchaseView:
    try:
        item = _media_service(session, request).purchase_video(actor=user, match_key=payload.match_key, competition_key=payload.competition_key)
        session.commit()
        return _purchase(item)
    except MediaEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/me/purchases', response_model=list[PremiumVideoPurchaseView])
def list_my_purchases(request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[PremiumVideoPurchaseView]:
    return [_purchase(item) for item in _media_service(session, request).list_purchases(actor=user)]


@router.get('/creator-league/broadcast-modes', response_model=list[CreatorBroadcastModeView])
def list_creator_broadcast_modes(
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CreatorBroadcastModeView]:
    return [_creator_mode(item) for item in CreatorBroadcastService(session).list_mode_configs()]


@router.get('/creator-league/matches/{match_id}/access', response_model=CreatorMatchAccessView)
def get_creator_match_access(
    match_id: str,
    duration_minutes: int = 90,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorMatchAccessView:
    try:
        quote = CreatorBroadcastService(session).quote_for_match(
            actor=user,
            match_id=match_id,
            duration_minutes=duration_minutes,
        )
        return _creator_access(quote)
    except CreatorBroadcastError as exc:
        raise _creator_http_error(exc) from exc


@router.post('/creator-league/matches/{match_id}/purchase', response_model=CreatorBroadcastPurchaseView, status_code=201)
def purchase_creator_match_broadcast(
    match_id: str,
    payload: CreatorBroadcastPurchaseRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorBroadcastPurchaseView:
    try:
        item = CreatorBroadcastService(session).purchase_broadcast(
            actor=user,
            match_id=match_id,
            duration_minutes=payload.duration_minutes,
        )
        session.commit()
        return _creator_purchase(item)
    except CreatorBroadcastError as exc:
        session.rollback()
        raise _creator_http_error(exc) from exc


@router.post('/creator-league/season-passes', response_model=CreatorSeasonPassView, status_code=201)
def purchase_creator_season_pass(
    payload: CreatorSeasonPassCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorSeasonPassView:
    try:
        item = CreatorBroadcastService(session).purchase_season_pass(
            actor=user,
            season_id=payload.season_id,
            club_id=payload.club_id,
        )
        session.commit()
        return _creator_pass(item)
    except CreatorBroadcastError as exc:
        session.rollback()
        raise _creator_http_error(exc) from exc


@router.get('/creator-league/season-passes/me', response_model=list[CreatorSeasonPassView])
def list_my_creator_season_passes(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CreatorSeasonPassView]:
    return [_creator_pass(item) for item in CreatorBroadcastService(session).list_passes(actor=user)]


@router.get('/creator-league/clubs/{club_id}/stadium', response_model=CreatorStadiumMonetizationView)
def get_creator_club_stadium(
    club_id: str,
    season_id: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorStadiumMonetizationView:
    try:
        bundle = CreatorStadiumService(session).get_club_bundle(club_id=club_id, season_id=season_id)
        return _creator_stadium_bundle(bundle, season_id=season_id)
    except CreatorStadiumError as exc:
        raise _creator_stadium_http_error(exc) from exc


@router.put('/creator-league/clubs/{club_id}/stadium', response_model=CreatorStadiumMonetizationView)
def configure_creator_club_stadium(
    club_id: str,
    payload: CreatorStadiumConfigUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorStadiumMonetizationView:
    try:
        bundle = CreatorStadiumService(session).configure_club_stadium(
            actor=user,
            club_id=club_id,
            season_id=payload.season_id,
            matchday_ticket_price_coin=payload.matchday_ticket_price_coin,
            season_pass_price_coin=payload.season_pass_price_coin,
            vip_ticket_price_coin=payload.vip_ticket_price_coin,
            visual_upgrade_level=payload.visual_upgrade_level,
            custom_chant_text=payload.custom_chant_text,
            custom_visuals_json=payload.custom_visuals_json,
        )
        session.commit()
        return _creator_stadium_bundle(bundle, season_id=payload.season_id)
    except CreatorStadiumError as exc:
        session.rollback()
        raise _creator_stadium_http_error(exc) from exc


@router.get('/creator-league/matches/{match_id}/stadium', response_model=CreatorMatchStadiumOfferView)
def get_creator_match_stadium_offer(
    match_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorMatchStadiumOfferView:
    try:
        offer = CreatorStadiumService(session).get_match_offer(match_id=match_id, actor=user)
        return _creator_match_stadium_offer(offer)
    except CreatorStadiumError as exc:
        raise _creator_stadium_http_error(exc) from exc


@router.post('/creator-league/matches/{match_id}/tickets', response_model=CreatorStadiumTicketPurchaseView, status_code=201)
def purchase_creator_match_ticket(
    match_id: str,
    payload: CreatorStadiumTicketPurchaseRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorStadiumTicketPurchaseView:
    try:
        item = CreatorStadiumService(session).purchase_match_ticket(
            actor=user,
            match_id=match_id,
            ticket_type=payload.ticket_type,
        )
        session.commit()
        return _creator_stadium_ticket(item)
    except CreatorStadiumError as exc:
        session.rollback()
        raise _creator_stadium_http_error(exc) from exc


@router.get('/creator-league/matches/{match_id}/stadium/placements', response_model=list[CreatorStadiumPlacementView])
def list_creator_match_stadium_placements(
    match_id: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[CreatorStadiumPlacementView]:
    try:
        items = CreatorStadiumService(session).list_match_placements(match_id=match_id)
        return [_creator_stadium_placement(item) for item in items]
    except CreatorStadiumError as exc:
        raise _creator_stadium_http_error(exc) from exc


@router.post('/creator-league/matches/{match_id}/stadium/placements', response_model=CreatorStadiumPlacementView, status_code=201)
def create_creator_match_stadium_placement(
    match_id: str,
    payload: CreatorStadiumPlacementCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorStadiumPlacementView:
    try:
        item = CreatorStadiumService(session).create_match_placement(
            actor=user,
            match_id=match_id,
            placement_type=payload.placement_type,
            slot_key=payload.slot_key,
            sponsor_name=payload.sponsor_name,
            price_coin=payload.price_coin,
            creative_asset_url=payload.creative_asset_url,
            copy_text=payload.copy_text,
            audit_note=payload.audit_note,
        )
        session.commit()
        return _creator_stadium_placement(item)
    except CreatorStadiumError as exc:
        session.rollback()
        raise _creator_stadium_http_error(exc) from exc


@router.post('/creator-league/matches/{match_id}/gifts', response_model=CreatorMatchGiftView, status_code=201)
def send_creator_match_gift(
    match_id: str,
    payload: CreatorMatchGiftRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorMatchGiftView:
    try:
        item = CreatorBroadcastService(session).send_match_gift(
            actor=user,
            match_id=match_id,
            club_id=payload.club_id,
            amount_coin=payload.amount_coin,
            gift_label=payload.gift_label,
            note=payload.note,
        )
        session.commit()
        return _creator_gift(item)
    except CreatorBroadcastError as exc:
        session.rollback()
        raise _creator_http_error(exc) from exc


@router.get('/creator-league/matches/{match_id}/analytics', response_model=CreatorAnalyticsDashboardView)
def get_creator_match_analytics(
    match_id: str,
    club_id: str | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CreatorAnalyticsDashboardView:
    try:
        dashboard = CreatorAnalyticsService(session).build_match_dashboard(
            actor=user,
            match_id=match_id,
            club_id=club_id,
        )
        return _creator_dashboard(dashboard)
    except CreatorBroadcastError as exc:
        raise _creator_http_error(exc) from exc


@router.get('/matches/{match_key}/snapshot', response_model=MatchRevenueSnapshotView)
def get_snapshot(match_key: str, _user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MatchRevenueSnapshotView:
    return _snapshot(MediaEngineService(session).build_snapshot(match_key=match_key))


@admin_router.post('/creator-league/matches/{match_id}/settlement', response_model=CreatorRevenueSettlementView)
def settle_creator_match_revenue(
    match_id: str,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CreatorRevenueSettlementView:
    try:
        item = CreatorRevenueService(session).build_match_settlement(match_id=match_id, actor_user_id=admin.id)
        session.commit()
        return _creator_settlement(item)
    except CreatorBroadcastError as exc:
        session.rollback()
        raise _creator_http_error(exc) from exc


@admin_router.get('/creator-league/matches/{match_id}/analytics', response_model=CreatorAnalyticsDashboardView)
def get_admin_creator_match_analytics(
    match_id: str,
    club_id: str | None = None,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CreatorAnalyticsDashboardView:
    try:
        dashboard = CreatorAnalyticsService(session).build_match_dashboard(
            actor=admin,
            match_id=match_id,
            club_id=club_id,
        )
        return _creator_dashboard(dashboard)
    except CreatorBroadcastError as exc:
        raise _creator_http_error(exc) from exc


@admin_router.get('/creator-league/stadium-controls', response_model=CreatorStadiumControlView)
def get_creator_stadium_controls(
    _admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CreatorStadiumControlView:
    return _creator_stadium_control(CreatorStadiumService(session).get_admin_control())


@admin_router.put('/creator-league/stadium-controls', response_model=CreatorStadiumControlView)
def update_creator_stadium_controls(
    payload: CreatorStadiumControlUpdateRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CreatorStadiumControlView:
    try:
        item = CreatorStadiumService(session).update_admin_control(
            actor=admin,
            max_matchday_ticket_price_coin=payload.max_matchday_ticket_price_coin,
            max_season_pass_price_coin=payload.max_season_pass_price_coin,
            max_vip_ticket_price_coin=payload.max_vip_ticket_price_coin,
            max_stadium_level=payload.max_stadium_level,
            vip_seat_ratio_bps=payload.vip_seat_ratio_bps,
            max_in_stadium_ad_slots=payload.max_in_stadium_ad_slots,
            max_sponsor_banner_slots=payload.max_sponsor_banner_slots,
            ad_placement_enabled=payload.ad_placement_enabled,
            ticket_sales_enabled=payload.ticket_sales_enabled,
            max_placement_price_coin=payload.max_placement_price_coin,
        )
        session.commit()
        return _creator_stadium_control(item)
    except CreatorStadiumError as exc:
        session.rollback()
        raise _creator_stadium_http_error(exc) from exc


@admin_router.put('/creator-league/clubs/{club_id}/stadium-level', response_model=CreatorStadiumProfileView)
def update_creator_stadium_level(
    club_id: str,
    payload: CreatorStadiumLevelUpdateRequest,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CreatorStadiumProfileView:
    try:
        item = CreatorStadiumService(session).update_stadium_level(actor=admin, club_id=club_id, level=payload.level)
        session.commit()
        return _creator_stadium_profile(item)
    except CreatorStadiumError as exc:
        session.rollback()
        raise _creator_stadium_http_error(exc) from exc


@admin_router.post('/snapshots', response_model=MatchRevenueSnapshotView)
def create_snapshot(payload: RevenueSnapshotCreateRequest, _admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> MatchRevenueSnapshotView:
    item = MediaEngineService(session).build_snapshot(match_key=payload.match_key, competition_key=payload.competition_key, home_club_id=payload.home_club_id, away_club_id=payload.away_club_id)
    session.commit()
    return _snapshot(item)


@admin_router.post('/highlights', response_model=MediaAssetView, status_code=201)
async def upload_highlight(
    request: Request,
    file: UploadFile = File(...),
    match_key: str = Form(...),
    clip_label: str | None = Form(default=None),
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> MediaAssetView:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Highlight file is empty.")
    service = _storage_service(request)
    asset = service.store_temporary_highlight(
        match_key=match_key,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        clip_label=clip_label,
    )
    session.commit()
    return _asset(asset)


@admin_router.post('/highlights/{storage_key:path}/archive', response_model=MediaAssetView)
def archive_highlight(
    storage_key: str,
    request: Request,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> MediaAssetView:
    service = _storage_service(request)
    try:
        asset = service.archive_highlight(storage_key=storage_key)
    except StorageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return _asset(asset)


@admin_router.post('/exports', response_model=MediaAssetView, status_code=201)
async def upload_export_package(
    request: Request,
    file: UploadFile = File(...),
    match_key: str = Form(...),
    export_label: str | None = Form(default=None),
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> MediaAssetView:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Export file is empty.")
    service = _storage_service(request)
    asset = service.store_export_package(
        match_key=match_key,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        export_label=export_label,
    )
    session.commit()
    return _asset(asset)


@router.get('/share-templates', response_model=list[HighlightShareTemplateView])
def list_share_templates(request: Request, _user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[HighlightShareTemplateView]:
    service = _highlight_share_service(request, session)
    return [HighlightShareTemplateView.model_validate(item, from_attributes=True) for item in service.list_templates(active_only=True)]


@router.get('/me/share-exports', response_model=list[HighlightShareExportView])
def list_share_exports(
    request: Request,
    match_key: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[HighlightShareExportView]:
    service = _highlight_share_service(request, session)
    return [_share_export(item) for item in service.list_exports(actor=user, match_key=match_key, limit=limit)]


@router.post('/share-exports', response_model=HighlightShareExportView, status_code=201)
def create_share_export(
    payload: HighlightShareExportRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> HighlightShareExportView:
    service = _highlight_share_service(request, session)
    try:
        export, asset = service.generate_export(actor=user, payload=payload)
    except (HighlightShareError, StorageNotFound) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return HighlightShareExportView(
        export_id=export.id,
        storage_key=asset.storage_key,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        template_code=(export.metadata_json or {}).get("template", {}).get("code"),
        aspect_ratio=export.aspect_ratio,
        share_title=export.share_title,
        watermark_label=export.watermark_label,
        metadata=export.metadata_json,
        created_at=export.created_at,
    )


@router.get('/share-exports/{export_id}/amplifications', response_model=list[HighlightShareAmplificationView])
def list_share_export_amplifications(
    export_id: str,
    request: Request,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[HighlightShareAmplificationView]:
    service = _highlight_share_service(request, session)
    try:
        items = service.list_amplifications(actor=user, export_id=export_id, limit=limit)
    except HighlightShareError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_share_amplification(item) for item in items]


@router.post('/share-exports/{export_id}/amplifications', response_model=HighlightShareAmplificationView, status_code=201)
def create_share_export_amplification(
    export_id: str,
    payload: HighlightShareAmplificationRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> HighlightShareAmplificationView:
    service = _highlight_share_service(request, session)
    try:
        item = service.amplify_export(actor=user, export_id=export_id, payload=payload)
    except HighlightShareError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return _share_amplification(item)


@router.post('/downloads', response_model=MediaDownloadResponse)
def request_download(
    payload: MediaDownloadRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MediaDownloadResponse:
    try:
        ticket = _access_service(request, session).issue_download(
            actor=user,
            storage_key=payload.storage_key,
            match_key=payload.match_key,
            download_kind=payload.download_kind,
            premium_required=payload.premium_required,
            watermark_label=payload.watermark_label,
            watermark_metadata=payload.watermark_metadata,
        )
    except (MediaAccessError, StorageNotFound) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return MediaDownloadResponse(
        storage_key=ticket.storage_key,
        download_url=ticket.download_url,
        expires_at=ticket.expires_at,
        content_type=ticket.content_type,
        filename=ticket.filename,
        metadata=ticket.metadata,
    )


@router.get('/downloads/{token}')
def download_signed_media(
    token: str,
    request: Request,
    session: Session = Depends(get_session),
):
    service = _access_service(request, session)
    try:
        resolved = service.resolve_download(token=token)
    except MediaAccessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage = service.storage_service.storage
    try:
        path = storage.open_file(key=resolved.storage_key)
    except StorageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return FileResponse(path, media_type=resolved.content_type, filename=resolved.filename)


def _creator_http_error(exc: CreatorBroadcastError) -> HTTPException:
    if exc.reason in {"analytics_access_denied", "analytics_creator_scope_denied"}:
        return HTTPException(status_code=403, detail=exc.detail)
    if exc.reason in {
        "insufficient_balance",
        "spending_controls_blocked",
        "broadcast_sales_disabled",
        "season_pass_sales_disabled",
        "match_gifting_disabled",
    }:
        return HTTPException(status_code=409, detail=exc.detail)
    if exc.reason in {"match_not_found", "competition_not_found", "season_not_found"}:
        return HTTPException(status_code=404, detail=exc.detail)
    return HTTPException(status_code=400, detail=exc.detail)


def _creator_stadium_http_error(exc: CreatorStadiumError) -> HTTPException:
    if exc.reason in {"creator_scope_denied"}:
        return HTTPException(status_code=403, detail=exc.detail)
    if exc.reason in {
        "insufficient_balance",
        "spending_controls_blocked",
        "stadium_sold_out",
        "vip_seating_sold_out",
        "stadium_ticket_already_owned",
        "placement_slot_limit_reached",
        "ticket_sales_disabled",
        "placement_price_cap_exceeded",
    }:
        return HTTPException(status_code=409, detail=exc.detail)
    if exc.reason in {"season_not_found", "creator_profile_missing", "stadium_pricing_not_configured"}:
        return HTTPException(status_code=404, detail=exc.detail)
    return HTTPException(status_code=400, detail=exc.detail)
