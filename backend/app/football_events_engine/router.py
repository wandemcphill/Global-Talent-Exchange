from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.football_events_engine.schemas import (
    EventCategoryToggleRequest,
    EventEffectRuleUpsertRequest,
    EventEffectRuleView,
    EventFeedIngestionRequestModel,
    EventIngestionJobView,
    EventReviewRequest,
    EventSeverityOverrideRequest,
    ExpireEffectsRequest,
    PlayerDemandSignalView,
    PlayerFormModifierView,
    PlayerRealWorldImpactView,
    RealWorldFootballEventCreateRequest,
    RealWorldFootballEventView,
    TrendingPlayerFlagView,
)
from backend.app.football_events_engine.service import (
    EventCategoryToggle,
    EventEffectRuleUpsert,
    EventFeedIngestionRequest,
    RealWorldFootballEventCreate,
    RealWorldFootballEventError,
    RealWorldFootballEventNotFoundError,
    RealWorldFootballEventService,
    RealWorldFootballEventValidationError,
)
from backend.app.models.user import User

router = APIRouter(prefix="/football-events", tags=["football-events"])
admin_router = APIRouter(prefix="/admin/football-events", tags=["admin-football-events"])


def _service(session: Session) -> RealWorldFootballEventService:
    return RealWorldFootballEventService(session)


def _raise_event_http(exc: RealWorldFootballEventError) -> None:
    if isinstance(exc, RealWorldFootballEventNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RealWorldFootballEventValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _to_create_payload(payload: RealWorldFootballEventCreateRequest) -> RealWorldFootballEventCreate:
    return RealWorldFootballEventCreate(
        event_type=payload.event_type,
        player_id=payload.player_id,
        occurred_at=payload.occurred_at,
        source_type=payload.source_type,
        source_label=payload.source_label,
        external_event_id=payload.external_event_id,
        title=payload.title,
        summary=payload.summary,
        severity=payload.severity,
        current_club_id=payload.current_club_id,
        competition_id=payload.competition_id,
        requires_admin_review=payload.requires_admin_review,
        metadata=payload.metadata,
        raw_payload=payload.raw_payload,
    )


def _event_view(service: RealWorldFootballEventService, event) -> RealWorldFootballEventView:
    metadata = event.metadata_json or {}
    return RealWorldFootballEventView(
        id=event.id,
        ingestion_job_id=event.ingestion_job_id,
        player_id=event.player_id,
        current_club_id=event.current_club_id,
        competition_id=event.competition_id,
        event_type=event.event_type,
        source_type=event.source_type,
        source_label=event.source_label,
        external_event_id=event.external_event_id,
        approval_status=event.approval_status,
        requires_admin_review=event.requires_admin_review,
        title=event.title,
        summary=event.summary,
        severity=event.severity,
        effect_severity_override=event.effect_severity_override,
        occurred_at=event.occurred_at,
        approved_by_user_id=event.approved_by_user_id,
        approved_at=event.approved_at,
        rejected_by_user_id=event.rejected_by_user_id,
        rejected_at=event.rejected_at,
        review_notes=event.review_notes,
        effects_applied_at=event.effects_applied_at,
        metadata_json=metadata,
        normalized_payload_json=event.normalized_payload_json,
        story_feed_item_id=metadata.get("story_feed_item_id"),
        calendar_event_id=metadata.get("calendar_event_id"),
        affected_card_ids=list(service.get_player_impact(event.player_id).affected_card_ids),
        active_flag_count=sum(1 for item in event.trending_flags if item.status == "active"),
        active_modifier_count=sum(1 for item in event.form_modifiers if item.status == "active"),
        active_demand_signal_count=sum(1 for item in event.demand_signals if item.status == "active"),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("/players/{player_id}/impact", response_model=PlayerRealWorldImpactView)
def get_player_impact(player_id: str, session: Session = Depends(get_session)) -> PlayerRealWorldImpactView:
    service = _service(session)
    try:
        impact = service.get_player_impact(player_id)
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    return PlayerRealWorldImpactView(
        player_id=impact.player_id,
        active_flags=[TrendingPlayerFlagView.model_validate(item, from_attributes=True) for item in impact.active_flags],
        active_form_modifiers=[PlayerFormModifierView.model_validate(item, from_attributes=True) for item in impact.active_form_modifiers],
        active_demand_signals=[PlayerDemandSignalView.model_validate(item, from_attributes=True) for item in impact.active_demand_signals],
        active_flag_codes=list(impact.active_flag_codes),
        affected_card_ids=list(impact.affected_card_ids),
        recommendation_priority_delta=impact.recommendation_priority_delta,
        market_buzz_score=impact.market_buzz_score,
        gameplay_effect_total=impact.gameplay_effect_total,
        market_effect_total=impact.market_effect_total,
    )


@router.get("/players/{player_id}/events", response_model=list[RealWorldFootballEventView])
def list_player_events(
    player_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[RealWorldFootballEventView]:
    service = _service(session)
    try:
        return [_event_view(service, item) for item in service.list_player_events(player_id, approved_only=True, limit=limit)]
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)


@admin_router.get("/events", response_model=list[RealWorldFootballEventView])
def list_events(
    _: User = Depends(get_current_admin),
    approval_status: str | None = Query(default=None),
    player_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[RealWorldFootballEventView]:
    service = _service(session)
    try:
        return [_event_view(service, item) for item in service.list_events(approval_status=approval_status, player_id=player_id, event_type=event_type, limit=limit)]
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)


@admin_router.post("/events", response_model=RealWorldFootballEventView, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: RealWorldFootballEventCreateRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RealWorldFootballEventView:
    service = _service(session)
    try:
        event = service.create_event(_to_create_payload(payload), actor=actor)
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    session.commit()
    session.refresh(event)
    return _event_view(service, event)


@admin_router.post("/events/import", response_model=EventIngestionJobView, status_code=status.HTTP_201_CREATED)
def import_events(
    payload: EventFeedIngestionRequestModel,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> EventIngestionJobView:
    service = _service(session)
    try:
        job = service.ingest_feed(
            EventFeedIngestionRequest(
                source_label=payload.source_label,
                source_type=payload.source_type,
                events=tuple(_to_create_payload(item) for item in payload.events),
            ),
            actor=actor,
        )
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    session.commit()
    session.refresh(job)
    return EventIngestionJobView.model_validate(job, from_attributes=True)


@admin_router.post("/events/{event_id}/review", response_model=RealWorldFootballEventView)
def review_event(
    event_id: str,
    payload: EventReviewRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RealWorldFootballEventView:
    service = _service(session)
    try:
        event = service.review_event(event_id, actor=actor, approve=payload.approve, notes=payload.notes)
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    session.commit()
    session.refresh(event)
    return _event_view(service, event)


@admin_router.post("/events/{event_id}/severity", response_model=RealWorldFootballEventView)
def override_severity(
    event_id: str,
    payload: EventSeverityOverrideRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RealWorldFootballEventView:
    service = _service(session)
    try:
        event = service.override_event_severity(event_id, actor=actor, severity=payload.severity)
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    session.commit()
    session.refresh(event)
    return _event_view(service, event)


@admin_router.get("/rules", response_model=list[EventEffectRuleView])
def list_rules(
    _: User = Depends(get_current_admin),
    event_type: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> list[EventEffectRuleView]:
    service = _service(session)
    try:
        return [EventEffectRuleView.model_validate(item, from_attributes=True) for item in service.list_rules(event_type=event_type, active_only=active_only)]
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)


@admin_router.post("/rules", response_model=EventEffectRuleView)
def upsert_rule(
    payload: EventEffectRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> EventEffectRuleView:
    service = _service(session)
    try:
        rule = service.upsert_effect_rule(
            EventEffectRuleUpsert(
                event_type=payload.event_type,
                effect_type=payload.effect_type,
                effect_code=payload.effect_code,
                label=payload.label,
                is_enabled=payload.is_enabled,
                approval_required=payload.approval_required,
                base_magnitude=payload.base_magnitude,
                duration_hours=payload.duration_hours,
                priority=payload.priority,
                gameplay_enabled=payload.gameplay_enabled,
                market_enabled=payload.market_enabled,
                recommendation_enabled=payload.recommendation_enabled,
                config=payload.config,
            ),
            actor=actor,
        )
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    session.commit()
    session.refresh(rule)
    return EventEffectRuleView.model_validate(rule, from_attributes=True)


@admin_router.post("/categories", response_model=list[EventEffectRuleView])
def toggle_category(
    payload: EventCategoryToggleRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[EventEffectRuleView]:
    service = _service(session)
    try:
        rules = service.set_event_category_enabled(EventCategoryToggle(event_type=payload.event_type, is_enabled=payload.is_enabled), actor=actor)
    except RealWorldFootballEventError as exc:
        _raise_event_http(exc)
    session.commit()
    return [EventEffectRuleView.model_validate(item, from_attributes=True) for item in rules]


@admin_router.post("/effects/expire")
def expire_effects(
    payload: ExpireEffectsRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    service = _service(session)
    result = service.expire_effects(as_of=payload.as_of)
    session.commit()
    return result


api_router = APIRouter(prefix="/api")
api_router.include_router(router)

combined_router = APIRouter(tags=["football-events"])
combined_router.include_router(router)
combined_router.include_router(api_router)

router = combined_router
