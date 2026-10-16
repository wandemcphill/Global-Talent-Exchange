from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.access_control import OrganizationRole
from app.models.club_profile import ClubProfile
from app.models.user import User

from .schemas import (
    ClubLifecycleAdvanceRequest,
    ClubLifecycleView,
    ClubOperatingDashboardView,
    ClubReadinessView,
    SquadRegistrationUpsertRequest,
    SquadRegistrationView,
)
from .service import ClubLifecycleError, ClubLifecycleService

router = APIRouter(prefix="/clubs", tags=["club-lifecycle"])


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, ClubLifecycleError):
        detail = str(error)
        status_code = status.HTTP_409_CONFLICT if detail.endswith("_locked") or detail.startswith("club_not") else status.HTTP_400_BAD_REQUEST
        if detail.endswith("_not_found"):
            status_code = status.HTTP_404_NOT_FOUND
        return HTTPException(status_code=status_code, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _require_club_operator(session: Session, club_id: str, current_user: User) -> ClubProfile:
    try:
        return AccessControlService(session).require_club_access(
            user=current_user,
            club_id=club_id,
            allowed_roles={OrganizationRole.CLUB},
            forbidden_detail="club_owner_required",
        )
    except (LookupError, PermissionError) as exc:
        raise _to_http_error(exc) from exc


@router.get("/{club_id}/lifecycle", response_model=ClubLifecycleView)
def get_club_lifecycle(
    club_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubLifecycleView:
    _require_club_operator(session, club_id, current_user)
    try:
        return ClubLifecycleService(session).get_lifecycle(club_id)
    except Exception as exc:
        raise _to_http_error(exc) from exc


@router.get("/{club_id}/readiness", response_model=ClubReadinessView)
def get_club_readiness(
    club_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubReadinessView:
    _require_club_operator(session, club_id, current_user)
    try:
        return ClubLifecycleService(session).evaluate_readiness(club_id)
    except Exception as exc:
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/advance-lifecycle", response_model=ClubLifecycleView)
def advance_club_lifecycle(
    club_id: str,
    payload: ClubLifecycleAdvanceRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubLifecycleView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubLifecycleService(session).advance_lifecycle(
            actor=current_user,
            club_id=club_id,
            target_state=payload.target_state,
            reason=payload.reason,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.get("/{club_id}/squad-registration", response_model=SquadRegistrationView | None)
def get_squad_registration(
    club_id: str,
    season_label: str = Query(default="launch", min_length=1, max_length=32),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadRegistrationView | None:
    _require_club_operator(session, club_id, current_user)
    try:
        return ClubLifecycleService(session).get_squad_registration(club_id, season_label=season_label)
    except Exception as exc:
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/squad-registration", response_model=SquadRegistrationView)
def upsert_squad_registration(
    club_id: str,
    payload: SquadRegistrationUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadRegistrationView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubLifecycleService(session).upsert_squad_registration(
            actor=current_user,
            club_id=club_id,
            payload=payload,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/squad-registration/submit", response_model=SquadRegistrationView)
def submit_squad_registration(
    club_id: str,
    season_label: str = Query(default="launch", min_length=1, max_length=32),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadRegistrationView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubLifecycleService(session).submit_squad_registration(
            actor=current_user,
            club_id=club_id,
            season_label=season_label,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/squad-registration/lock", response_model=SquadRegistrationView)
def lock_squad_registration(
    club_id: str,
    season_label: str = Query(default="launch", min_length=1, max_length=32),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SquadRegistrationView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubLifecycleService(session).lock_squad_registration(
            actor=current_user,
            club_id=club_id,
            season_label=season_label,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.get("/{club_id}/operating-dashboard", response_model=ClubOperatingDashboardView)
def get_club_operating_dashboard(
    club_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubOperatingDashboardView:
    _require_club_operator(session, club_id, current_user)
    try:
        return ClubLifecycleService(session).operating_dashboard(club_id)
    except Exception as exc:
        raise _to_http_error(exc) from exc


@router.get("/admin/club-lifecycle", response_model=list[ClubLifecycleView])
def list_admin_club_lifecycle(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ClubLifecycleView]:
    club_ids = [
        item[0]
        for item in session.query(ClubProfile.id).order_by(ClubProfile.updated_at.desc()).limit(limit).all()
    ]
    service = ClubLifecycleService(session)
    return [service.get_lifecycle(club_id) for club_id in club_ids]
