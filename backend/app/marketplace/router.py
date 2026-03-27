from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.marketplace.schemas import (
    AgentMarketplaceListingUpsert,
    AgentMarketplaceListingView,
    AgentMarketplaceMineView,
    AgentMarketplacePlayerListView,
    AgentMarketplacePlayerView,
    ConversationDetailView,
    ConversationMessageCreateRequest,
    ConversationStartRequest,
    ConversationStatusUpdateRequest,
    ConversationSummaryView,
)
from app.marketplace.service import (
    AgentMarketplaceService,
    MarketplaceConflictError,
    MarketplaceError,
    MarketplaceNotFoundError,
    MarketplacePermissionError,
    MarketplaceValidationError,
)
from app.models.user import User

marketplace_router = APIRouter(prefix="/marketplace", tags=["marketplace"])
conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_marketplace_service(session: Session = Depends(get_session)) -> AgentMarketplaceService:
    return AgentMarketplaceService(session=session)


def raise_marketplace_http_exception(exc: MarketplaceError) -> Never:
    if isinstance(exc, MarketplaceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, MarketplacePermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, MarketplaceConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, MarketplaceValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@marketplace_router.get("/players", response_model=AgentMarketplacePlayerListView)
def list_marketplace_players(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0, deprecated=True),
    search: str | None = Query(default=None),
    position: str | None = Query(default=None),
    country: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    availability: str | None = Query(default=None),
    sort: str = Query(default="recent"),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> AgentMarketplacePlayerListView:
    try:
        result = service.list_players(
            limit=limit,
            cursor=cursor,
            offset=offset,
            search=search,
            position=position,
            country=country,
            nationality=nationality,
            min_age=min_age,
            max_age=max_age,
            availability=availability,
            sort=sort,
        )
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return AgentMarketplacePlayerListView.model_validate(result)


@marketplace_router.get("/players/{player_id}", response_model=AgentMarketplacePlayerView)
def get_marketplace_player(
    player_id: str,
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> AgentMarketplacePlayerView:
    try:
        result = service.get_player(player_id)
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return AgentMarketplacePlayerView.model_validate(result)


@marketplace_router.get("/my-players", response_model=AgentMarketplaceMineView)
def list_my_marketplace_players(
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> AgentMarketplaceMineView:
    try:
        listings = service.list_agent_players(current_user.id)
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return AgentMarketplaceMineView.model_validate({"listings": listings})


@marketplace_router.put("/players/{player_id}", response_model=AgentMarketplaceListingView)
def upsert_marketplace_player(
    player_id: str,
    payload: AgentMarketplaceListingUpsert,
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> AgentMarketplaceListingView:
    try:
        result = service.upsert_listing(
            actor=current_user,
            player_id=player_id,
            is_available=payload.is_available,
            asking_type=payload.asking_type,
            note=payload.note,
        )
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return AgentMarketplaceListingView.model_validate(result)


@conversations_router.post("/start", response_model=ConversationDetailView, status_code=status.HTTP_201_CREATED)
def start_conversation(
    payload: ConversationStartRequest,
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> ConversationDetailView:
    try:
        result = service.start_conversation(
            actor=current_user,
            player_id=payload.player_id,
            message=payload.message,
            actor_role=payload.actor_role,
        )
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return ConversationDetailView.model_validate(result)


@conversations_router.get("", response_model=list[ConversationSummaryView])
def list_conversations(
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> list[ConversationSummaryView]:
    try:
        result = service.list_conversations(actor=current_user)
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return [ConversationSummaryView.model_validate(item) for item in result]


@conversations_router.get("/{conversation_id}/messages", response_model=ConversationDetailView)
def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> ConversationDetailView:
    try:
        result = service.get_conversation_detail(conversation_id=conversation_id, actor=current_user)
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return ConversationDetailView.model_validate(result)


@conversations_router.post("/{conversation_id}/message", response_model=ConversationDetailView)
def send_conversation_message(
    conversation_id: str,
    payload: ConversationMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> ConversationDetailView:
    try:
        result = service.send_message(
            conversation_id=conversation_id,
            actor=current_user,
            message=payload.message,
        )
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return ConversationDetailView.model_validate(result)


@conversations_router.post("/{conversation_id}/status", response_model=ConversationDetailView)
def update_conversation_status(
    conversation_id: str,
    payload: ConversationStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: AgentMarketplaceService = Depends(get_marketplace_service),
) -> ConversationDetailView:
    try:
        result = service.update_conversation_status(
            conversation_id=conversation_id,
            actor=current_user,
            status=payload.status,
        )
    except MarketplaceError as exc:
        raise_marketplace_http_exception(exc)
    return ConversationDetailView.model_validate(result)


api_router = APIRouter(prefix="/api")
api_router.include_router(marketplace_router)
api_router.include_router(conversations_router)

combined_router = APIRouter()
combined_router.include_router(marketplace_router)
combined_router.include_router(conversations_router)
combined_router.include_router(api_router)

router = combined_router

__all__ = ["router"]
