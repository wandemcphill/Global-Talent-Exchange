from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.competitive_integrity.schemas import (
    CompetitiveMatchCreateRequest,
    CompetitiveMatchExecuteRequest,
    CompetitiveMatchExecutionView,
    CompetitiveMatchView,
    CompetitiveNotificationView,
    FastGamePlayRequest,
    FastGameResultView,
    FastGameRunStartRequest,
    FastGameRunView,
    ManagerCandidateView,
    ManagerCreateRequest,
    ManagerUpdateInstructionsRequest,
    ManagerView,
    NotificationEventRequest,
    WorkerRunResultView,
)
from app.competitive_integrity.service import (
    AutomationRejectedError,
    CompetitiveIntegrityError,
    CompetitiveIntegrityService,
    ManagerLockedError,
)
from app.models.user import User

router = APIRouter(tags=["competitive-integrity"])
legacy_router = APIRouter(prefix="/competitive-integrity", tags=["competitive-integrity"])
api_router = APIRouter(prefix="/api/competitive-integrity", tags=["competitive-integrity"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
api_notifications_router = APIRouter(prefix="/api/notifications", tags=["notifications"])
admin_router = APIRouter(prefix="/api/admin/competitive-integrity", tags=["admin-competitive-integrity"])


def get_service(session: Session = Depends(get_session)) -> CompetitiveIntegrityService:
    return CompetitiveIntegrityService(session=session)


def _raise_integrity_error(exc: Exception) -> None:
    if isinstance(exc, AutomationRejectedError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ManagerLockedError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, CompetitiveIntegrityError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@legacy_router.get("/managers", response_model=list[ManagerView])
@api_router.get("/managers", response_model=list[ManagerView])
def list_managers(
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
) -> list[ManagerView]:
    return service.list_managers(actor=current_user)


@legacy_router.get("/managers/candidates", response_model=list[ManagerCandidateView])
@api_router.get("/managers/candidates", response_model=list[ManagerCandidateView])
def list_manager_candidates(
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
) -> list[ManagerCandidateView]:
    return service.list_manager_candidates(actor=current_user)


@legacy_router.post("/managers", response_model=ManagerView, status_code=status.HTTP_201_CREATED)
@api_router.post("/managers", response_model=ManagerView, status_code=status.HTTP_201_CREATED)
def upsert_manager(
    payload: ManagerCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> ManagerView:
    try:
        manager = service.upsert_manager(actor=current_user, payload=payload)
        session.commit()
        return manager
    except Exception as exc:  # pragma: no cover - centralized mapping
        _raise_integrity_error(exc)


@legacy_router.put("/managers/{manager_id}/instructions", response_model=ManagerView)
@api_router.put("/managers/{manager_id}/instructions", response_model=ManagerView)
def update_manager_instructions(
    manager_id: str,
    payload: ManagerUpdateInstructionsRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> ManagerView:
    try:
        manager = service.update_manager_instructions(actor=current_user, manager_id=manager_id, payload=payload)
        session.commit()
        return manager
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.post("/matches", response_model=CompetitiveMatchView, status_code=status.HTTP_201_CREATED)
@api_router.post("/matches", response_model=CompetitiveMatchView, status_code=status.HTTP_201_CREATED)
def schedule_match(
    payload: CompetitiveMatchCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> CompetitiveMatchView:
    try:
        match = service.schedule_match(actor=current_user, payload=payload)
        session.commit()
        return match
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.get("/matches/{match_id}", response_model=CompetitiveMatchView)
@api_router.get("/matches/{match_id}", response_model=CompetitiveMatchView)
def get_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
) -> CompetitiveMatchView:
    try:
        return service.get_match(actor=current_user, match_id=match_id)
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.post("/matches/{match_id}/execute", response_model=CompetitiveMatchExecutionView)
@api_router.post("/matches/{match_id}/execute", response_model=CompetitiveMatchExecutionView)
def execute_match(
    match_id: str,
    payload: CompetitiveMatchExecuteRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> CompetitiveMatchExecutionView:
    try:
        result = service.execute_match(actor=current_user, match_id=match_id, payload=payload)
        session.commit()
        return result
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.post("/fast-game/runs", response_model=FastGameRunView, status_code=status.HTTP_201_CREATED)
@api_router.post("/fast-game/runs", response_model=FastGameRunView, status_code=status.HTTP_201_CREATED)
def start_fast_game_run(
    payload: FastGameRunStartRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> FastGameRunView:
    try:
        run = service.start_run(actor=current_user, payload=payload)
        session.commit()
        return run
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.get("/fast-game/runs/{run_id}", response_model=FastGameRunView)
@api_router.get("/fast-game/runs/{run_id}", response_model=FastGameRunView)
def get_fast_game_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
) -> FastGameRunView:
    try:
        return service.get_run(actor=current_user, run_id=run_id)
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.post("/fast-game/runs/{run_id}/play", response_model=FastGameResultView)
@api_router.post("/fast-game/runs/{run_id}/play", response_model=FastGameResultView)
def play_fast_game(
    run_id: str,
    payload: FastGamePlayRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> FastGameResultView:
    try:
        result = service.play_fast_game(actor=current_user, run_id=run_id, payload=payload)
        session.commit()
        return result
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@legacy_router.post("/notifications/events", response_model=CompetitiveNotificationView, status_code=status.HTTP_201_CREATED)
@api_router.post("/notifications/events", response_model=CompetitiveNotificationView, status_code=status.HTTP_201_CREATED)
def create_notification_event(
    payload: NotificationEventRequest,
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> CompetitiveNotificationView:
    try:
        item = service.create_notification_event(actor=current_user, payload=payload)
        session.commit()
        return item
    except Exception as exc:  # pragma: no cover
        _raise_integrity_error(exc)


@notifications_router.get("", response_model=list[CompetitiveNotificationView])
@api_notifications_router.get("", response_model=list[CompetitiveNotificationView])
def list_notifications(
    current_user: User = Depends(get_current_user),
    service: CompetitiveIntegrityService = Depends(get_service),
) -> list[CompetitiveNotificationView]:
    return service.list_notifications(actor=current_user)


@admin_router.post("/workers/run-once", response_model=WorkerRunResultView)
def run_workers_once(
    _admin: User = Depends(get_current_admin),
    service: CompetitiveIntegrityService = Depends(get_service),
    session: Session = Depends(get_session),
) -> WorkerRunResultView:
    result = service.run_workers_once()
    session.commit()
    return result


router.include_router(legacy_router)
router.include_router(api_router)
router.include_router(notifications_router)
router.include_router(api_notifications_router)
router.include_router(admin_router)


__all__ = ["router"]
