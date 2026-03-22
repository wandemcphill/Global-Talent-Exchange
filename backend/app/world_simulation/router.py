from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.world_simulation.schemas import (
    ClubWorldContextView,
    ClubWorldProfileUpsertRequest,
    CompetitionWorldContextView,
    FootballCultureUpsertRequest,
    FootballCultureView,
    WorldNarrativeUpsertRequest,
    WorldNarrativeView,
)
from app.world_simulation.service import FootballWorldError, FootballWorldService

router = APIRouter(prefix="/api/world", tags=["world-simulation"])
admin_router = APIRouter(prefix="/admin/world", tags=["admin-world-simulation"])


def get_service(session: Session = Depends(get_session)) -> FootballWorldService:
    return FootballWorldService(session)


def _raise(exc: FootballWorldError) -> None:
    detail = str(exc)
    if detail.endswith("_not_found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


@router.get("/cultures", response_model=list[FootballCultureView])
def list_cultures(
    country_code: str | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=20, ge=1, le=100),
    service: FootballWorldService = Depends(get_service),
) -> list[FootballCultureView]:
    cultures = service.list_cultures(
        country_code=country_code,
        scope_type=scope_type,
        active_only=active_only,
        limit=limit,
    )
    return [FootballCultureView.model_validate(item) for item in cultures]


@router.get("/clubs/{club_id}/context", response_model=ClubWorldContextView)
def get_club_context(club_id: str, service: FootballWorldService = Depends(get_service)) -> ClubWorldContextView:
    try:
        payload = service.club_context(club_id)
    except FootballWorldError as exc:
        _raise(exc)
    return ClubWorldContextView.model_validate(payload)


@router.get("/competitions/{competition_id}/context", response_model=CompetitionWorldContextView)
def get_competition_context(
    competition_id: str,
    service: FootballWorldService = Depends(get_service),
) -> CompetitionWorldContextView:
    try:
        payload = service.competition_context(competition_id)
    except FootballWorldError as exc:
        _raise(exc)
    return CompetitionWorldContextView.model_validate(payload)


@router.get("/narratives", response_model=list[WorldNarrativeView])
def list_narratives(
    club_id: str | None = Query(default=None),
    competition_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: FootballWorldService = Depends(get_service),
) -> list[WorldNarrativeView]:
    narratives = service.list_narratives(club_id=club_id, competition_id=competition_id, limit=limit)
    return [WorldNarrativeView.model_validate(item) for item in narratives]


@admin_router.put("/cultures/{culture_key}", response_model=FootballCultureView)
def upsert_culture(
    culture_key: str,
    payload: FootballCultureUpsertRequest,
    _: object = Depends(get_current_admin),
    service: FootballWorldService = Depends(get_service),
) -> FootballCultureView:
    try:
        culture = service.upsert_culture(culture_key=culture_key, payload=payload)
        service.session.commit()
    except FootballWorldError as exc:
        _raise(exc)
    return FootballCultureView.model_validate(culture)


@admin_router.put("/clubs/{club_id}/context", response_model=ClubWorldContextView)
def upsert_club_context(
    club_id: str,
    payload: ClubWorldProfileUpsertRequest,
    _: object = Depends(get_current_admin),
    service: FootballWorldService = Depends(get_service),
) -> ClubWorldContextView:
    try:
        body = service.upsert_club_world_profile(club_id=club_id, payload=payload)
        service.session.commit()
    except FootballWorldError as exc:
        _raise(exc)
    return ClubWorldContextView.model_validate(body)


@admin_router.put("/narratives/{narrative_slug}", response_model=WorldNarrativeView)
def upsert_narrative(
    narrative_slug: str,
    payload: WorldNarrativeUpsertRequest,
    _: object = Depends(get_current_admin),
    service: FootballWorldService = Depends(get_service),
) -> WorldNarrativeView:
    try:
        narrative = service.upsert_narrative_arc(narrative_slug=narrative_slug, payload=payload)
        service.session.commit()
    except FootballWorldError as exc:
        _raise(exc)
    return WorldNarrativeView.model_validate(narrative)
