from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.discovery_engine.schemas import DiscoveryHomeView, DiscoveryItemView, FeaturedRailUpsertRequest, FeaturedRailView, SavedSearchCreate, SavedSearchView
from backend.app.discovery_engine.service import DiscoveryEngineError, DiscoveryEngineService
from backend.app.models.user import User

router = APIRouter(prefix="/discovery", tags=["discovery"])
admin_router = APIRouter(prefix="/admin/discovery", tags=["admin-discovery"])


def get_service(session: Session = Depends(get_session)) -> DiscoveryEngineService:
    return DiscoveryEngineService(session)


def _raise(exc: DiscoveryEngineError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/home", response_model=DiscoveryHomeView)
def get_home(current_user: User = Depends(get_current_user), service: DiscoveryEngineService = Depends(get_service)) -> DiscoveryHomeView:
    data = service.home(actor=current_user)
    return DiscoveryHomeView(
        featured_rails=[FeaturedRailView.model_validate(item) for item in data["featured_rails"]],
        featured_items=[DiscoveryItemView.model_validate(item) for item in data["featured_items"]],
        recommended_items=[DiscoveryItemView.model_validate(item) for item in data["recommended_items"]],
        live_now_items=[DiscoveryItemView.model_validate(item) for item in data["live_now_items"]],
        saved_searches=[SavedSearchView.model_validate(item) for item in data["saved_searches"]],
    )


@router.get("/search", response_model=list[DiscoveryItemView])
def search_discovery(
    q: str = Query(min_length=2),
    entity_scope: str = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: DiscoveryEngineService = Depends(get_service),
) -> list[DiscoveryItemView]:
    return [DiscoveryItemView.model_validate(item) for item in service.search(actor=current_user, query=q, entity_scope=entity_scope, limit=limit)]


@router.get("/saved-searches", response_model=list[SavedSearchView])
def list_saved_searches(current_user: User = Depends(get_current_user), service: DiscoveryEngineService = Depends(get_service)) -> list[SavedSearchView]:
    return [SavedSearchView.model_validate(item) for item in service.list_saved_searches(actor=current_user)]


@router.post("/saved-searches", response_model=SavedSearchView, status_code=status.HTTP_201_CREATED)
def create_saved_search(payload: SavedSearchCreate, current_user: User = Depends(get_current_user), service: DiscoveryEngineService = Depends(get_service)) -> SavedSearchView:
    try:
        item = service.save_search(actor=current_user, **payload.model_dump())
    except DiscoveryEngineError as exc:
        _raise(exc)
    return SavedSearchView.model_validate(item)


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(search_id: str, current_user: User = Depends(get_current_user), service: DiscoveryEngineService = Depends(get_service)) -> None:
    try:
        service.delete_saved_search(actor=current_user, search_id=search_id)
    except DiscoveryEngineError as exc:
        _raise(exc)


@admin_router.get("/featured-rails", response_model=list[FeaturedRailView])
def list_featured_rails(_: User = Depends(get_current_admin), service: DiscoveryEngineService = Depends(get_service)) -> list[FeaturedRailView]:
    return [FeaturedRailView.model_validate(item) for item in service.list_featured_rails(active_only=False)]


@admin_router.post("/featured-rails", response_model=FeaturedRailView)
def upsert_featured_rail(payload: FeaturedRailUpsertRequest, actor: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> FeaturedRailView:
    service = DiscoveryEngineService(session)
    item = service.upsert_featured_rail(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return FeaturedRailView.model_validate(item)
