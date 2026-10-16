"""HTTP surface for the Global Talent Exchange.

Route order matters here: the static segments (`/talent/search`,
`/talent/compare`, `/talent/shortlists`) are declared before the
`/talent/{player_id}` catch-all so a shortlist request is never parsed as a
player id.

Read endpoints accept an optional identity. An anonymous caller gets the public
projection; a signed-in scout, the talent themselves, and an admin each get
progressively more, resolved by `app.talent.privacy`.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Never

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.admin.capabilities import AdminCapability, note_admin_read, require_admin_capability
from app.auth.dependencies import get_current_user, get_optional_current_user, get_session
from app.models.user import User
from app.talent.admin_service import TalentAdminService
from app.talent.constants import (
    SEARCH_DEFAULT_PAGE_SIZE,
    SEARCH_MAX_FILTER_VALUES,
    SEARCH_MAX_PAGE_SIZE,
    SEARCH_MAX_TEXT_LENGTH,
    SEARCH_MIN_TEXT_LENGTH,
    VerificationTier,
)
from app.talent.schemas import (
    ShortlistCreateRequest,
    ShortlistEntryCreateRequest,
    ShortlistEntryUpdateRequest,
    ShortlistListResponse,
    ShortlistUpdateRequest,
    ShortlistView,
    TalentAdminActionResponse,
    TalentCompareRequest,
    TalentCompareResponse,
    TalentCorrectionRequest,
    TalentFeatureRequest,
    TalentModerationLogResponse,
    TalentModerationRequest,
    TalentProfileResponse,
    TalentRankingResponse,
    TalentRecomputeRequest,
    TalentSearchPagination,
    TalentSearchRequest,
    TalentSearchResponse,
    TalentSignalsResponse,
    TalentVerificationHistoryResponse,
    TalentVerificationRequest,
    TalentVisibilityRequest,
)
from app.talent.service import (
    TalentAccessDeniedError,
    TalentExchangeError,
    TalentExchangeService,
    TalentNotFoundError,
    TalentSearchPage,
    TalentValidationError,
)

# A single shared dependency instance rather than one per route: it keeps the
# capability requirement in one place and gives tests a stable override key.
require_talent_admin = require_admin_capability(AdminCapability.MANAGE_TALENT_EXCHANGE)

router = APIRouter(prefix="/talent", tags=["talent"])
admin_router = APIRouter(prefix="/admin/talent", tags=["admin-talent"])


def get_service(session: Session = Depends(get_session)) -> TalentExchangeService:
    return TalentExchangeService(session)


def get_admin_service(session: Session = Depends(get_session)) -> TalentAdminService:
    return TalentAdminService(session)


def _raise_talent_error(exc: TalentExchangeError) -> Never:
    if isinstance(exc, TalentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, TalentAccessDeniedError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, TalentValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def _search_response(page: TalentSearchPage, *, viewer_scope: str) -> TalentSearchResponse:
    return TalentSearchResponse(
        items=list(page.items),
        pagination=TalentSearchPagination(
            page=page.page,
            per_page=page.per_page,
            total=page.total,
            total_pages=page.total_pages,
            has_next=page.has_next,
            has_previous=page.has_previous,
        ),
        sort=page.sort,
        viewer_scope=viewer_scope,
        applied_filters=page.applied_filters,
    )


def _run_search(
    service: TalentExchangeService, request_model: TalentSearchRequest, viewer: User | None
) -> TalentSearchResponse:
    try:
        page = service.search(request_model, viewer=viewer)
    except TalentExchangeError as exc:
        _raise_talent_error(exc)
    return _search_response(page, viewer_scope=str(page.applied_filters.get("viewer_scope", "public")))


# ----------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------


@router.get("/search", response_model=TalentSearchResponse)
def search_talent(
    q: str | None = Query(default=None, min_length=SEARCH_MIN_TEXT_LENGTH, max_length=SEARCH_MAX_TEXT_LENGTH),
    positions: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    preferred_positions: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    tactical_roles: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    preferred_foot: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=14, le=60),
    max_age: int | None = Query(default=None, ge=14, le=60),
    nationality_codes: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    location_country_codes: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    location_region: str | None = Query(default=None, max_length=120),
    availability: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    min_verification_tier: VerificationTier | None = Query(default=None),
    min_composite_score: float | None = Query(default=None, ge=0.0, le=100.0),
    max_composite_score: float | None = Query(default=None, ge=0.0, le=100.0),
    min_form_score: float | None = Query(default=None, ge=0.0, le=100.0),
    min_competition_level_score: float | None = Query(default=None, ge=0.0, le=100.0),
    min_experience_years: float | None = Query(default=None, ge=0.0, le=30.0),
    min_ranking_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    min_sample_size: int | None = Query(default=None, ge=0, le=1000),
    required_signals: list[str] | None = Query(default=None, max_length=SEARCH_MAX_FILTER_VALUES),
    featured_only: bool = Query(default=False),
    sort: str = Query(default="ranking"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=SEARCH_DEFAULT_PAGE_SIZE, ge=1, le=SEARCH_MAX_PAGE_SIZE),
    viewer: User | None = Depends(get_optional_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> TalentSearchResponse:
    try:
        request_model = TalentSearchRequest(
            q=q,
            positions=positions,
            preferred_positions=preferred_positions,
            tactical_roles=tactical_roles,
            preferred_foot=preferred_foot,
            min_age=min_age,
            max_age=max_age,
            nationality_codes=nationality_codes,
            location_country_codes=location_country_codes,
            location_region=location_region,
            availability=availability,
            min_verification_tier=min_verification_tier,
            min_composite_score=min_composite_score,
            max_composite_score=max_composite_score,
            min_form_score=min_form_score,
            min_competition_level_score=min_competition_level_score,
            min_experience_years=min_experience_years,
            min_ranking_confidence=min_ranking_confidence,
            min_sample_size=min_sample_size,
            required_signals=required_signals,
            featured_only=featured_only,
            sort=sort,
            page=page,
            per_page=per_page,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _run_search(service, request_model, viewer)


@router.post("/search", response_model=TalentSearchResponse)
def search_talent_advanced(
    payload: TalentSearchRequest,
    viewer: User | None = Depends(get_optional_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> TalentSearchResponse:
    return _run_search(service, payload, viewer)


@router.post("/compare", response_model=TalentCompareResponse)
def compare_talent(
    payload: TalentCompareRequest,
    viewer: User | None = Depends(get_optional_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> TalentCompareResponse:
    try:
        result = service.compare(payload.player_ids, viewer=viewer)
    except TalentExchangeError as exc:
        _raise_talent_error(exc)
    return TalentCompareResponse(**result)


# ----------------------------------------------------------------------
# Shortlists (scout workflow)
# ----------------------------------------------------------------------


@router.get("/shortlists", response_model=ShortlistListResponse)
def list_shortlists(
    include_entries: bool = Query(default=False),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> ShortlistListResponse:
    views = service.list_shortlists(owner=viewer, include_entries=include_entries)
    return ShortlistListResponse(shortlists=[ShortlistView(**view) for view in views])


@router.post("/shortlists", response_model=ShortlistView, status_code=status.HTTP_201_CREATED)
def create_shortlist(
    payload: ShortlistCreateRequest,
    session: Session = Depends(get_session),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> ShortlistView:
    try:
        shortlist = service.create_shortlist(
            owner=viewer,
            name=payload.name,
            description=payload.description,
            club_id=payload.club_id,
        )
        session.commit()
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    session.refresh(shortlist)
    return ShortlistView(**service.shortlist_view(shortlist, viewer=viewer))


@router.get("/shortlists/{shortlist_id}", response_model=ShortlistView)
def read_shortlist(
    shortlist_id: str,
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> ShortlistView:
    try:
        shortlist = service.get_owned_shortlist(shortlist_id, owner=viewer)
    except TalentExchangeError as exc:
        _raise_talent_error(exc)
    return ShortlistView(**service.shortlist_view(shortlist, viewer=viewer))


@router.patch("/shortlists/{shortlist_id}", response_model=ShortlistView)
def update_shortlist(
    shortlist_id: str,
    payload: ShortlistUpdateRequest,
    session: Session = Depends(get_session),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> ShortlistView:
    try:
        shortlist = service.update_shortlist(
            shortlist_id,
            owner=viewer,
            name=payload.name,
            description=payload.description,
            is_archived=payload.is_archived,
        )
        session.commit()
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    session.refresh(shortlist)
    return ShortlistView(**service.shortlist_view(shortlist, viewer=viewer))


@router.delete("/shortlists/{shortlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shortlist(
    shortlist_id: str,
    session: Session = Depends(get_session),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> Response:
    try:
        service.delete_shortlist(shortlist_id, owner=viewer)
        session.commit()
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/shortlists/{shortlist_id}/entries",
    response_model=ShortlistView,
    status_code=status.HTTP_201_CREATED,
)
def add_shortlist_entry(
    shortlist_id: str,
    payload: ShortlistEntryCreateRequest,
    session: Session = Depends(get_session),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> ShortlistView:
    try:
        service.add_shortlist_entry(
            shortlist_id,
            owner=viewer,
            player_id=payload.player_id,
            status=payload.status.value,
            priority=payload.priority,
            note=payload.note,
        )
        session.commit()
        shortlist = service.get_owned_shortlist(shortlist_id, owner=viewer)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return ShortlistView(**service.shortlist_view(shortlist, viewer=viewer))


@router.patch("/shortlists/{shortlist_id}/entries/{entry_id}", response_model=ShortlistView)
def update_shortlist_entry(
    shortlist_id: str,
    entry_id: str,
    payload: ShortlistEntryUpdateRequest,
    session: Session = Depends(get_session),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> ShortlistView:
    try:
        service.update_shortlist_entry(
            shortlist_id,
            entry_id,
            owner=viewer,
            status=None if payload.status is None else payload.status.value,
            priority=payload.priority,
            note=payload.note,
        )
        session.commit()
        shortlist = service.get_owned_shortlist(shortlist_id, owner=viewer)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return ShortlistView(**service.shortlist_view(shortlist, viewer=viewer))


@router.delete(
    "/shortlists/{shortlist_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_shortlist_entry(
    shortlist_id: str,
    entry_id: str,
    session: Session = Depends(get_session),
    viewer: User = Depends(get_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> Response:
    try:
        service.remove_shortlist_entry(shortlist_id, entry_id, owner=viewer)
        session.commit()
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------------
# Individual talent
# ----------------------------------------------------------------------


@router.get("/{player_id}", response_model=TalentProfileResponse)
def read_talent_profile(
    player_id: str,
    viewer: User | None = Depends(get_optional_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> TalentProfileResponse:
    try:
        profile = service.get_profile(player_id, viewer=viewer)
    except TalentExchangeError as exc:
        _raise_talent_error(exc)
    return TalentProfileResponse(profile=profile)


@router.get("/{player_id}/ranking", response_model=TalentRankingResponse)
def read_talent_ranking(
    player_id: str,
    viewer: User | None = Depends(get_optional_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> TalentRankingResponse:
    try:
        payload = service.get_ranking(player_id, viewer=viewer)
    except TalentExchangeError as exc:
        _raise_talent_error(exc)
    return TalentRankingResponse(**payload)


@router.get("/{player_id}/signals", response_model=TalentSignalsResponse)
def read_talent_signals(
    player_id: str,
    viewer: User | None = Depends(get_optional_current_user),
    service: TalentExchangeService = Depends(get_service),
) -> TalentSignalsResponse:
    try:
        payload = service.get_signals(player_id, viewer=viewer)
    except TalentExchangeError as exc:
        _raise_talent_error(exc)
    return TalentSignalsResponse(**payload)


# ----------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------


def _admin_action_response(profile_payload: dict[str, Any], action: str, recorded_at: str) -> TalentAdminActionResponse:
    return TalentAdminActionResponse(profile=profile_payload, action=action, recorded_at=recorded_at)


@admin_router.get("/{player_id}", response_model=TalentProfileResponse)
def admin_read_talent(
    player_id: str,
    request: Request,
    _: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentProfileResponse:
    note_admin_read(request, "admin.talent.read", player_id=player_id)
    try:
        return TalentProfileResponse(profile=service.admin_view(player_id))
    except TalentExchangeError as exc:
        _raise_talent_error(exc)


@admin_router.post("/{player_id}/sync", response_model=TalentProfileResponse)
def admin_sync_talent(
    player_id: str,
    owner_user_id: str | None = Body(default=None, embed=True),
    session: Session = Depends(get_session),
    _: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentProfileResponse:
    try:
        service.sync_from_player(player_id, owner_user_id=owner_user_id)
        session.commit()
        return TalentProfileResponse(profile=service.admin_view(player_id))
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)


@admin_router.post("/{player_id}/verification", response_model=TalentAdminActionResponse)
def admin_record_verification(
    player_id: str,
    payload: TalentVerificationRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentAdminActionResponse:
    try:
        service.record_verification(
            player_id,
            actor=actor,
            tier=payload.tier,
            decision=payload.decision,
            evidence_kind=payload.evidence_kind,
            evidence_reference=payload.evidence_reference,
            expires_at=payload.expires_at,
            reviewer_notes=payload.reviewer_notes,
        )
        session.commit()
        profile_payload = service.admin_view(player_id)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return _admin_action_response(
        profile_payload,
        f"verification:{payload.decision.value}:{payload.tier.value}",
        str(profile_payload.get("verification_reviewed_at") or ""),
    )


@admin_router.get("/{player_id}/verification", response_model=TalentVerificationHistoryResponse)
def admin_verification_history(
    player_id: str,
    request: Request,
    _: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentVerificationHistoryResponse:
    note_admin_read(request, "admin.talent.verification.read", player_id=player_id)
    try:
        return TalentVerificationHistoryResponse(**service.verification_history(player_id))
    except TalentExchangeError as exc:
        _raise_talent_error(exc)


@admin_router.post("/{player_id}/visibility", response_model=TalentAdminActionResponse)
def admin_set_visibility(
    player_id: str,
    payload: TalentVisibilityRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentAdminActionResponse:
    try:
        profile = service.set_visibility(
            player_id,
            actor=actor,
            visibility_state=payload.visibility_state,
            reason=payload.reason,
        )
        session.commit()
        profile_payload = service.admin_view(player_id)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return _admin_action_response(
        profile_payload, f"visibility:{payload.visibility_state.value}", profile.updated_at.isoformat()
    )


@admin_router.post("/{player_id}/moderation", response_model=TalentAdminActionResponse)
def admin_moderate(
    player_id: str,
    payload: TalentModerationRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentAdminActionResponse:
    try:
        profile = service.moderate(
            player_id,
            actor=actor,
            action=payload.action,
            moderation_state=payload.moderation_state,
            reason=payload.reason,
            internal_notes=payload.internal_notes,
        )
        session.commit()
        profile_payload = service.admin_view(player_id)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return _admin_action_response(profile_payload, payload.action.value, profile.updated_at.isoformat())


@admin_router.post("/{player_id}/feature", response_model=TalentAdminActionResponse)
def admin_set_featured(
    player_id: str,
    payload: TalentFeatureRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentAdminActionResponse:
    try:
        profile = service.set_featured(
            player_id,
            actor=actor,
            is_featured=payload.is_featured,
            featured_rank=payload.featured_rank,
            reason=payload.reason,
        )
        session.commit()
        profile_payload = service.admin_view(player_id)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return _admin_action_response(
        profile_payload,
        "feature" if payload.is_featured else "unfeature",
        profile.updated_at.isoformat(),
    )


@admin_router.post("/{player_id}/correction", response_model=TalentAdminActionResponse)
def admin_correct(
    player_id: str,
    payload: TalentCorrectionRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentAdminActionResponse:
    corrections = payload.model_dump(exclude_unset=True, exclude={"reason"})
    try:
        profile = service.correct(player_id, actor=actor, corrections=corrections, reason=payload.reason)
        session.commit()
        profile_payload = service.admin_view(player_id)
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return _admin_action_response(profile_payload, "correct", profile.updated_at.isoformat())


@admin_router.post("/{player_id}/recompute", response_model=TalentRankingResponse)
def admin_recompute(
    player_id: str,
    payload: TalentRecomputeRequest | None = None,
    session: Session = Depends(get_session),
    _: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentRankingResponse:
    as_of: date | None = payload.as_of if payload else None
    try:
        result = service.recompute(player_id, as_of=as_of)
        session.commit()
    except TalentExchangeError as exc:
        session.rollback()
        _raise_talent_error(exc)
    return TalentRankingResponse(**result)


@admin_router.get("/{player_id}/moderation-log", response_model=TalentModerationLogResponse)
def admin_moderation_log(
    player_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_talent_admin),
    service: TalentAdminService = Depends(get_admin_service),
) -> TalentModerationLogResponse:
    note_admin_read(request, "admin.talent.moderation_log.read", player_id=player_id)
    try:
        return TalentModerationLogResponse(**service.moderation_log(player_id, limit=limit))
    except TalentExchangeError as exc:
        _raise_talent_error(exc)


__all__ = ["admin_router", "router"]
