from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User

from .schemas import GlobalSearchResultView, GlobalSearchSuggestionView
from .service import GlobalSearchService

router = APIRouter(tags=["global-search"])


@router.get("/search", response_model=list[GlobalSearchResultView])
def global_search(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[GlobalSearchResultView]:
    return GlobalSearchService(session).search(actor=current_user, query=q, limit=limit, admin=False)


@router.get("/search/suggest", response_model=list[GlobalSearchSuggestionView])
def global_search_suggest(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[GlobalSearchSuggestionView]:
    return GlobalSearchService(session).suggest(actor=current_user, query=q, limit=limit)


@router.get("/admin/search", response_model=list[GlobalSearchResultView])
def admin_global_search(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=30, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[GlobalSearchResultView]:
    return GlobalSearchService(session).search(actor=current_admin, query=q, limit=limit, admin=True)
