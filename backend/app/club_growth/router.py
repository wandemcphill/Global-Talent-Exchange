from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_current_user, get_session
from app.models.access_control import OrganizationRole
from app.models.club_profile import ClubProfile
from app.models.user import User

from .schemas import (
    AcademyContractOfferRequest,
    AcademyContractOfferView,
    AcademyContractResponseRequest,
    AcademyGenerateProspectsRequest,
    AcademyProfileView,
    AcademyProspectView,
    ClubGrowthDashboardView,
    StaffContractView,
    StaffOfferRequest,
)
from .service import ClubGrowthError, ClubGrowthService

router = APIRouter(prefix="/clubs", tags=["club-growth"])


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, ClubGrowthError):
        detail = str(error)
        status_code = status.HTTP_409_CONFLICT
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


@router.get("/{club_id}/growth", response_model=ClubGrowthDashboardView)
def get_club_growth_dashboard(
    club_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubGrowthDashboardView:
    _require_club_operator(session, club_id, current_user)
    try:
        return ClubGrowthService(session).get_dashboard(club_id=club_id)
    except Exception as exc:
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/growth/staff/{staff_id}/offer", response_model=StaffContractView)
def offer_staff_contract(
    club_id: str,
    staff_id: str,
    payload: StaffOfferRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StaffContractView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).offer_staff_contract(
            actor=current_user,
            club_id=club_id,
            staff_id=staff_id,
            payload=payload,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/growth/staff-contracts/{contract_id}/accept", response_model=StaffContractView)
def accept_staff_contract(
    club_id: str,
    contract_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StaffContractView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).accept_staff_contract(
            actor=current_user,
            club_id=club_id,
            contract_id=contract_id,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/growth/staff-contracts/{contract_id}/terminate", response_model=StaffContractView)
def terminate_staff_contract(
    club_id: str,
    contract_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StaffContractView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).terminate_staff_contract(
            actor=current_user,
            club_id=club_id,
            contract_id=contract_id,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/growth/academy/upgrade", response_model=AcademyProfileView)
def upgrade_academy(
    club_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AcademyProfileView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).upgrade_academy(actor=current_user, club_id=club_id)
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/growth/academy/generate-prospects", response_model=list[AcademyProspectView])
def generate_academy_prospects(
    club_id: str,
    payload: AcademyGenerateProspectsRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AcademyProspectView]:
    _require_club_operator(session, club_id, current_user)
    try:
        views = ClubGrowthService(session).generate_prospects(
            actor=current_user,
            club_id=club_id,
            payload=payload,
        )
        session.commit()
        return views
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post(
    "/{club_id}/growth/academy/prospects/{prospect_id}/offer-contract",
    response_model=AcademyContractOfferView,
)
def offer_academy_prospect_contract(
    club_id: str,
    prospect_id: str,
    payload: AcademyContractOfferRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AcademyContractOfferView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).offer_prospect_contract(
            actor=current_user,
            club_id=club_id,
            prospect_id=prospect_id,
            payload=payload,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post(
    "/{club_id}/growth/academy/contracts/{offer_id}/respond",
    response_model=AcademyContractOfferView,
)
def respond_to_academy_contract(
    club_id: str,
    offer_id: str,
    payload: AcademyContractResponseRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AcademyContractOfferView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).respond_to_prospect_contract(
            actor=current_user,
            club_id=club_id,
            offer_id=offer_id,
            payload=payload,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc


@router.post("/{club_id}/growth/academy/prospects/{prospect_id}/promote", response_model=AcademyProspectView)
def promote_academy_prospect(
    club_id: str,
    prospect_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AcademyProspectView:
    _require_club_operator(session, club_id, current_user)
    try:
        view = ClubGrowthService(session).promote_prospect(
            actor=current_user,
            club_id=club_id,
            prospect_id=prospect_id,
        )
        session.commit()
        return view
    except Exception as exc:
        session.rollback()
        raise _to_http_error(exc) from exc
