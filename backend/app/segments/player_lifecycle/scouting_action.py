from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.regen_ecosystem import Scout
from app.models.user import User
from app.schemas.regen_ecosystem import ScoutReportView
from app.services.regen_ecosystem_service import (
    RegenEcosystemError,
    RegenEcosystemNotFoundError,
    RegenEcosystemService,
    RegenEcosystemValidationError,
)

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> RegenEcosystemService:
    return RegenEcosystemService(session)


def _raise(exc: RegenEcosystemError) -> None:
    if isinstance(exc, RegenEcosystemNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RegenEcosystemValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/scout/report/{player_id}", response_model=ScoutReportView)
def scout_player(
    player_id: str,
    current_user: User = Depends(get_current_user),
    service: RegenEcosystemService = Depends(_service),
) -> ScoutReportView:
    scout = service.session.scalar(
        select(Scout)
        .where(
            Scout.club_user_id == current_user.id,
            Scout.active.is_(True),
        )
        .order_by(Scout.created_at.asc(), Scout.id.asc())
    )
    if scout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active scout is assigned to the authenticated club user",
        )

    try:
        result = service.get_scout_report(player_id, scout_id=scout.id)
    except RegenEcosystemError as exc:
        _raise(exc)

    service.session.commit()
    return result


__all__ = ["router"]
