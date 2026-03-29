from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.commentary.schemas import CommentarySelectionRequest, CommentarySelectionView, CommentatorProfileView
from app.commentary.service import CommentaryService, CommentaryServiceError
from app.models.user import User

router = APIRouter(tags=["commentary"])
legacy_router = APIRouter(prefix="/commentary", tags=["commentary"])
api_router = APIRouter(prefix="/api/commentary", tags=["commentary"])


def _service(session: Session) -> CommentaryService:
    service = CommentaryService(session)
    service.seed_defaults()
    if session.new or session.dirty:
        session.commit()
    return service


@legacy_router.get("/profiles", response_model=list[CommentatorProfileView])
@api_router.get("/profiles", response_model=list[CommentatorProfileView])
def list_commentary_profiles(session: Session = Depends(get_session)) -> list[CommentatorProfileView]:
    return _service(session).list_profiles()


@legacy_router.post("/select", response_model=CommentarySelectionView)
@api_router.post("/select", response_model=CommentarySelectionView)
def select_commentary_profile(
    payload: CommentarySelectionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CommentarySelectionView:
    service = _service(session)
    try:
        selection = service.save_selection(user=user, payload=payload)
        session.commit()
        return selection
    except CommentaryServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


router.include_router(legacy_router)
router.include_router(api_router)

__all__ = ["router"]
