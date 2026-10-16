from __future__ import annotations

from threading import Lock
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    IdentityContext,
    get_current_admin,
    get_current_user,
    require_identity,
)
from app.backbone.scale_events import enqueue_feed_cache_refresh
from app.core.config import get_settings
from app.core.event_backbone import defer_session_callback_until_commit
from app.db import get_session
from app.infinite_league.service import InfiniteLeagueRuntime, ensure_infinite_league_runtime
from app.models.analytics_event import AnalyticsEvent
from app.models.viral_moderation import ClipModerationEvent
from app.models.user import User
from app.models.user import UserRole
from app.services.creator_attention_earnings_service import build_creator_attention_earnings_service
from app.users.affinity_service import UserAffinityService
from app.viral.event_weighting import ClipEventWeightingMiddleware
from app.viral.accounts import PERSONAS, catalog_accounts
from app.viral.cascade import ensure_viral_cascade_engine
from app.viral.distribution_filter import ensure_distribution_filter_middleware
from app.viral.ingestion_runtime import (
    ClipEventIngestionUnavailable,
    ClipEventKafkaProducer,
    ClipEventQueueSaturated,
    ensure_viral_dispatch_runtime,
    shutdown_viral_dispatch_runtime,
)
from app.viral.ingestion_schemas import (
    CLIP_EVENT_TOPICS,
    ClipEvent,
    ClipEventIngestionAccepted,
    ClipEventType,
    parse_clip_events,
)
from app.viral.personalized_feed_service import build_personalized_feed_service
from app.viral.ranking_service import build_viral_ranking_service
from app.viral.schemas import (
    ClipModerationEventView,
    ClipReportRequest,
    PersonalizedFeedRefreshResponse,
    PersonalizedFeedResponse,
    ViralAccountCatalogItemView,
    ViralAccountCatalogResponse,
    ViralCascadesResponse,
    ViralClipView,
    ViralClipVariantsResponse,
    ViralClipWinnerResponse,
    ViralFeedResponse,
    ViralPersonaView,
    ViralSessionStateView,
    TrustFactorView,
    TrustProfileView,
    ViralTrendingResponse,
)
from app.viral.session_tracker import ensure_viral_session_tracker
from app.viral.service import ViralFeedError, ViralFeedService
from app.viral.trust import TrustState, ensure_trust_score_service
from app.runtime_config.service import ensure_runtime_config_loader
from app.feedback_engine.service import FeedbackEngine

router = APIRouter()
api_router = APIRouter(prefix="/api/viral", tags=["viral"])
feed_router = APIRouter(prefix="/feed", tags=["feed"])
public_router = APIRouter(prefix="/viral", tags=["viral"])


def _service_lock(request: Request) -> Lock:
    lock = getattr(request.app.state, "clip_event_ingestion_service_lock", None)
    if lock is None:
        lock = Lock()
        request.app.state.clip_event_ingestion_service_lock = lock
    return lock


def ensure_clip_event_ingestion_service(request: Request) -> ClipEventKafkaProducer:
    service = getattr(request.app.state, "clip_event_ingestion_service", None)
    if service is not None:
        return service
    with _service_lock(request):
        service = getattr(request.app.state, "clip_event_ingestion_service", None)
        if service is not None:
            return service
        settings = getattr(request.app.state, "settings", None) or get_settings()
        service = ClipEventKafkaProducer(settings=settings)
        service.start()
        request.app.state.clip_event_ingestion_service = service
        return service


def _has_table(session: Session, table_name: str) -> bool:
    try:
        return bool(inspect(session.connection()).has_table(table_name))
    except Exception:
        return False


def _resolve_clip_event_user_id(
    *,
    event: ClipEvent,
    session: Session,
) -> str | None:
    if event.user_id and session.get(User, event.user_id) is not None:
        return event.user_id
    return None


def _analytics_metadata_for_event(event: ClipEvent) -> dict[str, object]:
    metadata = event.metadata.model_dump(mode="json")
    metadata["clip_id"] = event.clip_id
    metadata["session_id"] = event.session_id
    metadata["event_type"] = event.kafka_topic
    if event.watch_time_ms is not None:
        metadata["watch_time_ms"] = int(event.watch_time_ms)
        metadata["watch_time_seconds"] = round(float(event.watch_time_ms) / 1000.0, 6)
    if event.video_length_ms is not None:
        metadata["video_length_ms"] = int(event.video_length_ms)
    return metadata


def startup(app, _context) -> None:
    from app.viral.worker import bind_viral_ranking_scheduler

    settings = getattr(app.state, "settings", None)
    if getattr(app.state, "clip_event_ingestion_service", None) is None and settings is not None:
        service = ClipEventKafkaProducer(settings=settings)
        service.start()
        app.state.clip_event_ingestion_service = service
    ensure_viral_dispatch_runtime(app)
    bind_viral_ranking_scheduler(app, _context)


def shutdown(app, _context) -> None:
    from app.viral.worker import shutdown_viral_ranking_scheduler

    shutdown_viral_dispatch_runtime(app)
    service = getattr(app.state, "clip_event_ingestion_service", None)
    if service is not None:
        service.stop()
        app.state.clip_event_ingestion_service = None
    shutdown_viral_ranking_scheduler(app, _context)


def _build_feed_service(*, request: Request, db_session: Session) -> ViralFeedService:
    settings = getattr(request.app.state, "settings", None) or get_settings()
    feedback_engine = FeedbackEngine(session=db_session)
    return ViralFeedService(
        session=db_session,
        settings=settings,
        cascade_engine=ensure_viral_cascade_engine(request.app, settings=settings),
        feedback_engine=feedback_engine,
        runtime_config_loader=ensure_runtime_config_loader(request.app),
    )


def _trust_profile_view(item: TrustState) -> TrustProfileView:
    factors = item.factors.as_dict()
    return TrustProfileView(
        user_id=item.user_id,
        trust_score=round(item.trust_score, 4),
        shadow_banned=bool(item.shadow_banned),
        monetization_eligible=bool(item.monetization_eligible),
        ranking_eligible=bool(item.ranking_eligible),
        suspicious_flags=list(item.suspicious_flags),
        suspicious_event_count=int(item.suspicious_event_count),
        healthy_event_count=int(item.healthy_event_count),
        factors=TrustFactorView(**factors),
        updated_at=item.updated_at,
    )


def _resolve_feed(
    *,
    request: Request,
    db_session: Session,
    limit: int,
    match_ids: str | None,
    favorite_team: str | None,
    favorite_event_types: str | None,
) -> tuple[ViralFeedResponse, list[str]]:
    resolved_match_ids = [item.strip() for item in (match_ids or "").split(",") if item.strip()]
    resolved_event_types = [item.strip() for item in (favorite_event_types or "").split(",") if item.strip()]
    runtime = ensure_infinite_league_runtime(request.app)
    if resolved_match_ids:
        runtime_match_ids = [item for item in resolved_match_ids if runtime.has_match(item)]
        db_match_ids = [item for item in resolved_match_ids if item not in runtime_match_ids]
        responses: list[ViralFeedResponse] = []
        if db_match_ids:
            try:
                responses.append(
                    _build_feed_service(request=request, db_session=db_session).build_feed(
                        limit=max(limit, 1),
                        match_ids=db_match_ids,
                        favorite_team=favorite_team,
                        favorite_event_types=resolved_event_types,
                    )
                )
            except ViralFeedError:
                pass
        if runtime_match_ids:
            responses.append(
                runtime.build_viral_feed(
                    limit=max(limit, 1),
                    match_ids=runtime_match_ids,
                    favorite_team=favorite_team,
                    favorite_event_types=resolved_event_types,
                )
            )
        if responses:
            merged = InfiniteLeagueRuntime.merge_viral_feeds(responses, limit=max(limit, 1))
            return _filter_blocked_feed(session=db_session, response=merged), resolved_event_types
    response = _build_feed_service(request=request, db_session=db_session).build_feed(
        limit=max(limit, 1),
        match_ids=resolved_match_ids,
        favorite_team=favorite_team,
        favorite_event_types=resolved_event_types,
    )
    if response.clips:
        return _filter_blocked_feed(session=db_session, response=response), resolved_event_types
    generated = runtime.build_viral_feed(
        limit=max(limit, 1),
        favorite_team=favorite_team,
        favorite_event_types=resolved_event_types,
    )
    return _filter_blocked_feed(session=db_session, response=generated), resolved_event_types


def _filter_blocked_feed(*, session: Session, response: ViralFeedResponse) -> ViralFeedResponse:
    clip_ids = [clip.clip_id for clip in response.clips]
    if not clip_ids:
        return response
    if not _has_table(session, ClipModerationEvent.__tablename__):
        return response
    blocked_ids = set(
        session.scalars(
            select(ClipModerationEvent.clip_id).where(
                ClipModerationEvent.clip_id.in_(clip_ids),
                ClipModerationEvent.status == "blocked",
            )
        ).all()
    )
    if not blocked_ids:
        return response
    return response.model_copy(update={"clips": [clip for clip in response.clips if clip.clip_id not in blocked_ids]})


def _find_clip(
    *,
    clip_id: str,
    request: Request,
    session: Session,
) -> ViralClipView | None:
    match_key = clip_id.split("::", 1)[0] if "::" in clip_id else None
    if match_key:
        try:
            feed = _build_feed_service(request=request, db_session=session).build_match_feed(match_key)
        except ViralFeedError:
            generated = ensure_infinite_league_runtime(request.app).build_match_viral_feed(match_key)
            feed = generated if generated is not None else None
        if feed is not None:
            for clip in feed.clips:
                if clip.clip_id == clip_id:
                    return clip
    feed, _ = _resolve_feed(
        request=request,
        db_session=session,
        limit=100,
        match_ids=match_key,
        favorite_team=None,
        favorite_event_types=None,
    )
    for clip in feed.clips:
        if clip.clip_id == clip_id:
            return clip
    return None


def _moderation_event_view(event: ClipModerationEvent) -> ClipModerationEventView:
    return ClipModerationEventView(
        id=event.id,
        clip_id=event.clip_id,
        reporter_user_id=event.reporter_user_id,
        action=event.action,
        status=event.status,
        reason=event.reason,
        resolved_by_user_id=event.resolved_by_user_id,
        metadata_json=dict(event.metadata_json or {}),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.post(
    "/events/clip",
    response_model=ClipEventIngestionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["viral-ingestion"],
)
async def ingest_clip_events(
    request: Request,
    producer: ClipEventKafkaProducer = Depends(ensure_clip_event_ingestion_service),
    identity: IdentityContext = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ClipEventIngestionAccepted:
    try:
        payload = await request.json()
        events = parse_clip_events(payload)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    normalized_events = []
    for event in events:
        if (event.user_id is not None and event.user_id != identity.user_id) or event.session_id != identity.session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Event identity does not match authenticated identity.",
            )
        authenticated_event = event.model_copy(update={"user_id": identity.user_id})
        normalized_events.append(
            authenticated_event.model_copy(
                update={
                    "user_id": _resolve_clip_event_user_id(
                        event=authenticated_event,
                        session=session,
                    ),
                    "session_id": identity.session_id,
                }
            )
        )
    client_host = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
    if client_host and "," in client_host:
        client_host = client_host.split(",", 1)[0].strip()
    if not client_host and request.client is not None:
        client_host = request.client.host
    weighted_events = ClipEventWeightingMiddleware(
        trust_service=ensure_trust_score_service(request.app, settings=getattr(request.app.state, "settings", None)),
    ).validate_and_weight(
        events=normalized_events,
        headers=request.headers,
        ip_address=client_host,
        session=session,
    )
    try:
        queue_depth = producer.enqueue_many(weighted_events)
    except ClipEventQueueSaturated as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ClipEventIngestionUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    analytics_table_exists = _has_table(session, AnalyticsEvent.__tablename__)
    affinity_service = UserAffinityService(session)
    feedback_engine = FeedbackEngine(session)
    creator_earnings_service = build_creator_attention_earnings_service(
        session=session,
        app=request.app,
    )
    for event in weighted_events:
        metadata = _analytics_metadata_for_event(event)
        if analytics_table_exists:
            session.add(
                AnalyticsEvent(
                    name=event.kafka_topic,
                    user_id=event.user_id,
                    metadata_json=metadata,
                )
            )
        affinity_service.process_event(event)
        feedback_engine.record_interaction_event(name=event.kafka_topic, metadata=metadata)
        if event.event_type in {ClipEventType.LIKE, ClipEventType.SHARE}:
            creator_earnings_service.track_engagement_event(
                name=event.kafka_topic,
                clip_id=event.clip_id,
                viewer_user_id=event.user_id,
                metadata=metadata,
                reference_key=f"clip-event:{event.event_id}",
            )
    session_tracker = ensure_viral_session_tracker(request.app)
    session_tracker.observe_many(weighted_events)
    if identity.user_id and session_tracker.should_request_refresh(session_id=identity.session_id):
        enqueue_feed_cache_refresh(
            session=session,
            user_id=identity.user_id,
            session_id=identity.session_id,
            limit=20,
            reason="clip_event_ingestion",
            producer="viral-router",
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda tracker=session_tracker, resolved_session_id=identity.session_id: (
                tracker.mark_refresh_requested(session_id=resolved_session_id)
            ),
        )
    session.commit()
    return ClipEventIngestionAccepted(
        accepted_events=len(weighted_events),
        queue_depth=queue_depth,
        topics=list(CLIP_EVENT_TOPICS),
    )


@api_router.get("/accounts", response_model=ViralAccountCatalogResponse)
def read_viral_accounts() -> ViralAccountCatalogResponse:
    return ViralAccountCatalogResponse(
        accounts=[
            ViralAccountCatalogItemView(
                handle=account.handle,
                niche=account.niche,
                target_audience=account.target_audience,
                focus_event_types=list(account.focus_event_types),
                persona=ViralPersonaView(
                    name=PERSONAS[account.persona_code].name,
                    tone=PERSONAS[account.persona_code].tone,
                ),
            )
            for account in catalog_accounts()
        ]
    )


@router.get(
    "/api/viral-feed",
    response_model=ViralFeedResponse,
    tags=["viral"],
    operation_id="read_viral_feed_legacy",
)
@api_router.get(
    "/feed",
    response_model=ViralFeedResponse,
    operation_id="read_viral_feed_api",
)
def read_viral_feed(
    request: Request,
    limit: int = 12,
    match_ids: str | None = None,
    favorite_team: str | None = None,
    favorite_event_types: str | None = None,
    session: Session = Depends(get_session),
) -> ViralFeedResponse:
    response, _resolved_event_types = _resolve_feed(
        request=request,
        db_session=session,
        limit=limit,
        match_ids=match_ids,
        favorite_team=favorite_team,
        favorite_event_types=favorite_event_types,
    )
    return response


@router.get("/api/clips/{clip_id}", response_model=ViralClipView, tags=["viral"])
def read_clip_detail(
    clip_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> ViralClipView:
    clip = _find_clip(clip_id=clip_id, request=request, session=session)
    if clip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip was not found.")
    return clip


@router.post("/api/clips/{clip_id}/report", response_model=ClipModerationEventView, tags=["viral"])
def report_clip(
    clip_id: str,
    payload: ClipReportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClipModerationEventView:
    event = ClipModerationEvent(
        clip_id=clip_id,
        reporter_user_id=current_user.id,
        action="reported",
        status="pending",
        reason=payload.reason,
        metadata_json=dict(payload.metadata or {}),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return _moderation_event_view(event)


@router.get("/api/admin/clips/moderation", response_model=list[ClipModerationEventView], tags=["admin-viral"])
def list_clip_moderation_events(
    status_filter: str = "pending",
    _admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[ClipModerationEventView]:
    stmt = select(ClipModerationEvent)
    if status_filter.strip().lower() != "all":
        stmt = stmt.where(ClipModerationEvent.status == status_filter.strip().lower())
    stmt = stmt.order_by(ClipModerationEvent.created_at.desc()).limit(200)
    return [_moderation_event_view(event) for event in session.scalars(stmt).all()]


@router.post("/api/admin/clips/{clip_id}/approve", response_model=ClipModerationEventView, tags=["admin-viral"])
def approve_clip(
    clip_id: str,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ClipModerationEventView:
    event = ClipModerationEvent(
        clip_id=clip_id,
        reporter_user_id=None,
        action="approved",
        status="approved",
        reason="Admin approved clip for distribution.",
        resolved_by_user_id=admin.id,
        metadata_json={},
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return _moderation_event_view(event)


@router.post("/api/admin/clips/{clip_id}/block", response_model=ClipModerationEventView, tags=["admin-viral"])
def block_clip(
    clip_id: str,
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ClipModerationEventView:
    event = ClipModerationEvent(
        clip_id=clip_id,
        reporter_user_id=None,
        action="blocked",
        status="blocked",
        reason="Admin blocked clip from distribution.",
        resolved_by_user_id=admin.id,
        metadata_json={"distribution_blocked": True},
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return _moderation_event_view(event)


@feed_router.get("/for-you", response_model=PersonalizedFeedResponse)
def read_personalized_feed(
    request: Request,
    limit: int = 20,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    identity: IdentityContext = Depends(require_identity),
    session: Session = Depends(get_session),
) -> PersonalizedFeedResponse:
    service = build_personalized_feed_service(app=request.app, session=session)
    response = service.get_for_you(
        user_id=current_user.id,
        limit=max(limit, 1),
        refresh=refresh,
        session_id=identity.session_id,
    )
    response = ensure_distribution_filter_middleware(request.app).deliver_personalized_feed_response(response)
    service.record_delivery(response)
    session.commit()
    return response


@feed_router.get("/following", response_model=PersonalizedFeedResponse)
def read_following_feed(
    request: Request,
    limit: int = 20,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    identity: IdentityContext = Depends(require_identity),
    session: Session = Depends(get_session),
) -> PersonalizedFeedResponse:
    service = build_personalized_feed_service(app=request.app, session=session)
    response = service.get_following(
        user_id=current_user.id,
        limit=max(limit, 1),
        refresh=refresh,
        session_id=identity.session_id,
    )
    response = ensure_distribution_filter_middleware(request.app).deliver_personalized_feed_response(response)
    service.record_delivery(response)
    session.commit()
    return response


@feed_router.get("/for-you/refresh", response_model=PersonalizedFeedRefreshResponse)
def refresh_personalized_feed(
    request: Request,
    cursor: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    identity: IdentityContext = Depends(require_identity),
    session: Session = Depends(get_session),
) -> PersonalizedFeedRefreshResponse:
    service = build_personalized_feed_service(app=request.app, session=session)
    response = service.refresh_for_you(
        user_id=current_user.id,
        cursor=cursor,
        limit=max(limit, 1),
        session_id=identity.session_id,
    )
    service.record_refresh_delivery(user_id=current_user.id, clips=response.new_items)
    session.commit()
    return response


@api_router.get("/feed/for-you", response_model=ViralFeedResponse)
def read_session_aware_viral_feed(
    request: Request,
    session_id: str,
    limit: int = 12,
    match_ids: str | None = None,
    favorite_team: str | None = None,
    favorite_event_types: str | None = None,
    session: Session = Depends(get_session),
) -> ViralFeedResponse:
    response, resolved_event_types = _resolve_feed(
        request=request,
        db_session=session,
        limit=limit,
        match_ids=match_ids,
        favorite_team=favorite_team,
        favorite_event_types=favorite_event_types,
    )
    return ensure_viral_session_tracker(request.app).personalize_feed(
        session_id=session_id,
        feed=response,
        favorite_team=favorite_team,
        favorite_event_types=resolved_event_types,
    )


@api_router.get("/sessions/{session_id}", response_model=ViralSessionStateView)
def read_viral_session_state(request: Request, session_id: str) -> ViralSessionStateView:
    return ensure_viral_session_tracker(request.app).get_state(session_id)


@router.get("/trust/me", response_model=TrustProfileView, tags=["trust"])
def read_my_trust_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> TrustProfileView:
    state = ensure_trust_score_service(
        request.app,
        settings=getattr(request.app.state, "settings", None),
    ).get_user_trust(user=current_user)
    return _trust_profile_view(state)


@router.get("/trust/{user_id}", response_model=TrustProfileView, tags=["trust"])
def read_user_trust_profile(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TrustProfileView:
    if current_user.id != user_id and current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You cannot inspect another user's trust profile."
        )
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    state = ensure_trust_score_service(
        request.app,
        settings=getattr(request.app.state, "settings", None),
    ).get_user_trust(user=user)
    return _trust_profile_view(state)


@api_router.get("/matches/{match_key}/clips", response_model=ViralFeedResponse)
def read_match_viral_clips(
    match_key: str,
    request: Request,
    favorite_team: str | None = None,
    favorite_event_types: str | None = None,
    session: Session = Depends(get_session),
) -> ViralFeedResponse:
    resolved_event_types = [item.strip() for item in (favorite_event_types or "").split(",") if item.strip()]
    try:
        feed = _build_feed_service(request=request, db_session=session).build_match_feed(
            match_key,
            favorite_team=favorite_team,
            favorite_event_types=resolved_event_types,
        )
        return _filter_blocked_feed(session=session, response=feed)
    except ViralFeedError as exc:
        generated = ensure_infinite_league_runtime(request.app).build_match_viral_feed(
            match_key,
            favorite_team=favorite_team,
            favorite_event_types=resolved_event_types,
        )
        if generated is not None:
            return _filter_blocked_feed(session=session, response=generated)
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.get("/clips/{clip_id}/variants", response_model=ViralClipVariantsResponse)
def read_clip_variants(
    clip_id: str,
    session: Session = Depends(get_session),
) -> ViralClipVariantsResponse:
    try:
        return ViralFeedService(session).get_clip_variants(clip_id)
    except ViralFeedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.get("/clips/{clip_id}/winner", response_model=ViralClipWinnerResponse)
def read_clip_winner(
    clip_id: str,
    session: Session = Depends(get_session),
) -> ViralClipWinnerResponse:
    try:
        return ViralFeedService(session).get_clip_winner(clip_id)
    except ViralFeedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.get("/clips/trending", response_model=ViralTrendingResponse)
@public_router.get("/clips/trending", response_model=ViralTrendingResponse)
def read_trending_clips(
    request: Request,
    limit: int = 20,
    refresh: bool = False,
    session: Session = Depends(get_session),
) -> ViralTrendingResponse:
    response = build_viral_ranking_service(app=request.app, session=session).get_trending(
        limit=max(limit, 1),
        refresh=refresh,
    )
    response = ensure_distribution_filter_middleware(request.app).deliver_trending_response(response)
    session.commit()
    return response


@api_router.get("/cascades", response_model=ViralCascadesResponse)
@public_router.get("/cascades", response_model=ViralCascadesResponse)
def read_viral_cascades(
    request: Request,
    limit: int = 50,
    refresh: bool = False,
    session: Session = Depends(get_session),
) -> ViralCascadesResponse:
    if refresh:
        build_viral_ranking_service(app=request.app, session=session).recompute(scope="all")
        session.commit()
    cascades = ensure_viral_cascade_engine(request.app).list_cascades(limit=max(limit, 1))
    return ViralCascadesResponse(
        cascades=cascades,
        generated_at=datetime.now(UTC),
    )


router.include_router(api_router)
router.include_router(feed_router)
router.include_router(public_router)
