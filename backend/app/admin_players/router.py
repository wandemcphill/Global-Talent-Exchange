from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.admin.capabilities import AdminCapability, note_admin_read, require_admin_capability
from app.auth.dependencies import get_session
from app.models.user import User

from .schemas import PlayerAdminEditRequest, PlayerAdminEditResult, PlayerAdminView
from .service import AdminPlayerError, AdminPlayerService, PlayerNotFoundError

router = APIRouter(prefix="/api/admin/players", tags=["admin-players"])


def get_service() -> AdminPlayerService:
    return AdminPlayerService()


@router.get("", response_model=list[PlayerAdminView])
def search_players(
    request: Request,
    search: str | None = None,
    tier: str | None = None,
    source: str | None = None,
    limit: int = 24,
    session: Session = Depends(get_session),
    actor: User = Depends(require_admin_capability(AdminCapability.MANAGE_PLAYERS)),
    service: AdminPlayerService = Depends(get_service),
) -> list[PlayerAdminView]:
    note_admin_read(request, "admin.players.search", search=search, tier=tier, source=source)
    return service.list_players(session, search=search, tier=tier, source=source, limit=limit)


@router.get("/{player_id}", response_model=PlayerAdminView)
def read_player(
    player_id: str,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(require_admin_capability(AdminCapability.MANAGE_PLAYERS)),
    service: AdminPlayerService = Depends(get_service),
) -> PlayerAdminView:
    note_admin_read(request, "admin.players.read", player_id=player_id)
    try:
        return service.get_player(session, player_id)
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{player_id}", response_model=PlayerAdminEditResult)
def edit_player(
    player_id: str,
    payload: PlayerAdminEditRequest,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(require_admin_capability(AdminCapability.MANAGE_PLAYERS)),
    service: AdminPlayerService = Depends(get_service),
) -> PlayerAdminEditResult:
    try:
        result = service.edit_player(session, player_id, payload)
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AdminPlayerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return result


__all__ = ["router"]
