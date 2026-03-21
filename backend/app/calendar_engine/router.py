from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.calendar_engine.schemas import (
    CalendarDashboardView,
    CalendarEventCreateRequest,
    CalendarEventView,
    CalendarSeasonCreateRequest,
    CalendarSeasonView,
    CompetitionLifecycleRunView,
    HostedCompetitionLaunchRequest,
    NationalCompetitionLaunchRequest,
    PauseStatusView,
)
from app.calendar_engine.service import CalendarEngineError, CalendarEngineService
from app.models.user import User

router = APIRouter(prefix="/calendar-engine", tags=["calendar-engine"])
admin_router = APIRouter(prefix="/admin/calendar-engine", tags=["calendar-engine-admin"])


@router.get("/dashboard", response_model=CalendarDashboardView)
def get_dashboard(session: Session = Depends(get_session)) -> CalendarDashboardView:
    service = CalendarEngineService(session)
    payload = service.dashboard()
    return CalendarDashboardView(
        seasons=[CalendarSeasonView.model_validate(item, from_attributes=True) for item in payload["seasons"]],
        active_events=[CalendarEventView.model_validate(item, from_attributes=True) for item in payload["active_events"]],
        active_pause_status=PauseStatusView.model_validate(payload["active_pause_status"]),
        recent_lifecycle_runs=[CompetitionLifecycleRunView.model_validate(item, from_attributes=True) for item in payload["recent_lifecycle_runs"]],
    )


@router.get("/seasons", response_model=list[CalendarSeasonView])
def list_seasons(active_only: bool = Query(default=False), session: Session = Depends(get_session)) -> list[CalendarSeasonView]:
    return [CalendarSeasonView.model_validate(item, from_attributes=True) for item in CalendarEngineService(session).list_seasons(active_only=active_only)]


@router.get("/events", response_model=list[CalendarEventView])
def list_events(
    active_only: bool = Query(default=False),
    as_of: date | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    family: str | None = Query(default=None),
    visibility: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
) -> list[CalendarEventView]:
    return [
        CalendarEventView.model_validate(item, from_attributes=True)
        for item in CalendarEngineService(session).list_events(
            active_only=active_only,
            as_of=as_of,
            source_type=source_type,
            source_id=source_id,
            family=family,
            visibility=visibility,
            status=status_filter,
        )
    ]


@router.get("/pause-status", response_model=PauseStatusView)
def get_pause_status(as_of: date | None = Query(default=None), session: Session = Depends(get_session)) -> PauseStatusView:
    return PauseStatusView.model_validate(CalendarEngineService(session).current_pause_status(as_of=as_of))


@router.get("/lifecycle-runs", response_model=list[CompetitionLifecycleRunView])
def list_lifecycle_runs(session: Session = Depends(get_session)) -> list[CompetitionLifecycleRunView]:
    return [CompetitionLifecycleRunView.model_validate(item, from_attributes=True) for item in CalendarEngineService(session).list_lifecycle_runs()]


@admin_router.post("/seasons", response_model=CalendarSeasonView)
def create_season(
    payload: CalendarSeasonCreateRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CalendarSeasonView:
    service = CalendarEngineService(session)
    try:
        season = service.create_season(payload=payload, actor=actor)
    except CalendarEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(season)
    return CalendarSeasonView.model_validate(season, from_attributes=True)


@admin_router.post("/events", response_model=CalendarEventView)
def create_event(
    payload: CalendarEventCreateRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CalendarEventView:
    service = CalendarEngineService(session)
    try:
        event = service.create_event(payload=payload, actor=actor)
    except CalendarEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(event)
    return CalendarEventView.model_validate(event, from_attributes=True)


@admin_router.post("/hosted-competitions/{competition_id}/launch", response_model=CompetitionLifecycleRunView)
def launch_hosted_competition(
    competition_id: str,
    payload: HostedCompetitionLaunchRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CompetitionLifecycleRunView:
    service = CalendarEngineService(session)
    try:
        _, run = service.launch_hosted_competition(competition_id=competition_id, actor=actor, payload=payload)
    except CalendarEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(run)
    return CompetitionLifecycleRunView.model_validate(run, from_attributes=True)


@admin_router.post("/national-competitions/{competition_id}/launch", response_model=CompetitionLifecycleRunView)
def launch_national_competition(
    competition_id: str,
    payload: NationalCompetitionLaunchRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CompetitionLifecycleRunView:
    service = CalendarEngineService(session)
    try:
        _, run = service.launch_national_competition(competition_id=competition_id, actor=actor, payload=payload)
    except CalendarEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(run)
    return CompetitionLifecycleRunView.model_validate(run, from_attributes=True)
