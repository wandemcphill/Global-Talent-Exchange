from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin
from backend.app.db import get_session
from backend.app.schemas.club_admin import AdminClubDetailView, BrandingModerationResultView, ModerateBrandingRequest
from backend.app.schemas.club_analytics import ClubAnalyticsView, ClubSummaryView
from backend.app.services.club_admin_service import ClubAdminService
from backend.app.services.club_analytics_service import ClubAnalyticsService

router = APIRouter(prefix="/api/admin/clubs", tags=["admin-clubs"])


def _admin_id(current_admin) -> str:
    user_id = getattr(current_admin, "id", None)
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_context_missing")
    return user_id


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/summary", response_model=ClubSummaryView)
def get_summary(session: Session = Depends(get_session), _=Depends(get_current_admin)) -> ClubSummaryView:
    return ClubAnalyticsService(session).get_summary()


@router.get("/analytics", response_model=ClubAnalyticsView)
def get_analytics(session: Session = Depends(get_session), _=Depends(get_current_admin)) -> ClubAnalyticsView:
    return ClubAnalyticsService(session).get_analytics()


@router.get("/{club_id}", response_model=AdminClubDetailView)
def get_admin_detail(
    club_id: str,
    session: Session = Depends(get_session),
    _=Depends(get_current_admin),
) -> AdminClubDetailView:
    try:
        return ClubAdminService(session).get_admin_detail(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error


@router.post("/{club_id}/moderate-branding", response_model=BrandingModerationResultView)
def moderate_branding(
    club_id: str,
    payload: ModerateBrandingRequest,
    session: Session = Depends(get_session),
    current_admin=Depends(get_current_admin),
) -> BrandingModerationResultView:
    try:
        return ClubAdminService(session).moderate_branding(
            club_id=club_id,
            reviewer_user_id=_admin_id(current_admin),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
