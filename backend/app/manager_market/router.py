from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.user import User
from backend.app.wallets.service import InsufficientBalanceError, WalletService

from .schemas import (
    AssignManagerRequest,
    CompetitionAdminUpdateRequest,
    CompetitionAdminView,
    CompetitionOrchestrationView,
    CompetitionRuntimeView,
    ManagerAuditEventView,
    ManagerCatalogPage,
    ManagerComparisonView,
    ManagerFilterMetadataView,
    ManagerHistoryEntryView,
    ManagerListingView,
    ManagerRecommendationView,
    ManagerSupplyUpdateRequest,
    ManagerTradeResultView,
    RecruitManagerRequest,
    SwapTradeRequest,
    TeamManagersView,
    TradeListingRequest,
)
from .service import CapacityError, ManagerMarketError, ManagerMarketService

router = APIRouter(tags=["managers"])
public_router = APIRouter(prefix="/api/managers", tags=["managers"])
admin_router = APIRouter(prefix="/api/admin/managers", tags=["admin-managers"])


def get_service() -> ManagerMarketService:
    return ManagerMarketService(wallet_service=WalletService())


@public_router.get("/filters", response_model=ManagerFilterMetadataView)
def get_filters(request: Request, session: Session = Depends(get_session), service: ManagerMarketService = Depends(get_service)) -> ManagerFilterMetadataView:
    return service.filter_metadata(request.app, session)


@public_router.get("/catalog", response_model=ManagerCatalogPage)
def list_catalog(
    request: Request,
    search: str | None = None,
    tactic: str | None = Query(default=None),
    trait: str | None = Query(default=None),
    mentality: str | None = Query(default=None),
    rarity: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=1000),
    service: ManagerMarketService = Depends(get_service),
    session: Session = Depends(get_session),
) -> ManagerCatalogPage:
    return service.list_catalog(request.app, session, search=search, tactic=tactic, trait=trait, mentality=mentality, rarity=rarity, limit=limit)


@public_router.get("/team", response_model=TeamManagersView)
def get_team(request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> TeamManagersView:
    return service.get_team(request.app, session, current_user)


@public_router.post("/recruit", response_model=TeamManagersView)
def recruit_manager(payload: RecruitManagerRequest, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> TeamManagersView:
    try:
        result = service.recruit_manager(request.app, session, current_user, payload.manager_id, payload.slot)
        session.commit()
        return result
    except CapacityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.post("/assign", response_model=TeamManagersView)
def assign_manager(payload: AssignManagerRequest, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> TeamManagersView:
    try:
        result = service.assign_manager(request.app, session, current_user, payload.asset_id, payload.slot)
        session.commit()
        return result
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.post("/{asset_id}/release", response_model=TeamManagersView)
def release_manager(asset_id: str, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> TeamManagersView:
    try:
        result = service.release_manager(request.app, session, current_user, asset_id)
        session.commit()
        return result
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.get("/trade-listings", response_model=list[ManagerListingView])
def list_listings(request: Request, session: Session = Depends(get_session), service: ManagerMarketService = Depends(get_service)) -> list[ManagerListingView]:
    return service.list_trade_listings(request.app, session)


@public_router.get("/my-trade-listings", response_model=list[ManagerListingView])
def list_my_listings(request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> list[ManagerListingView]:
    return service.list_trade_listings(request.app, session, seller_user_id=current_user.id)


@public_router.post("/trade-listings/{listing_id}/cancel", response_model=TeamManagersView)
def cancel_listing(listing_id: str, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> TeamManagersView:
    try:
        result = service.cancel_listing(request.app, session, current_user, listing_id)
        session.commit()
        return result
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.get("/competition-runtime/{code}", response_model=CompetitionRuntimeView)
def get_competition_runtime(code: str, request: Request, participants: int = Query(default=2, ge=0), region: str = Query(default="africa"), session: Session = Depends(get_session), service: ManagerMarketService = Depends(get_service)) -> CompetitionRuntimeView:
    return service.preview_competition_runtime(request.app, session, code=code, participants=participants, region=region)


@public_router.post("/trade-listings", response_model=ManagerListingView, status_code=status.HTTP_201_CREATED)
def create_listing(payload: TradeListingRequest, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> ManagerListingView:
    try:
        result = service.create_listing(request.app, session, current_user, payload.asset_id, payload.asking_price_credits)
        session.commit()
        return result
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.post("/trade-listings/{listing_id}/buy", response_model=ManagerTradeResultView)
def buy_listing(listing_id: str, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> ManagerTradeResultView:
    try:
        result = service.buy_listing(request.app, session, current_user, listing_id)
        session.commit()
        return result
    except (ManagerMarketError, InsufficientBalanceError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.post("/swap", response_model=ManagerTradeResultView)
def swap_trade(payload: SwapTradeRequest, request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> ManagerTradeResultView:
    try:
        result = service.swap_trade(request.app, session, current_user, payload.proposer_asset_id, payload.requested_asset_id, payload.cash_adjustment_credits)
        session.commit()
        return result
    except (ManagerMarketError, InsufficientBalanceError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@public_router.get("/recommendation", response_model=ManagerRecommendationView)
def get_recommendation(request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> ManagerRecommendationView:
    return service.recommend(request.app, session, current_user)


@public_router.get("/compare", response_model=ManagerComparisonView)
def compare_managers(request: Request, left_manager_id: str = Query(...), right_manager_id: str = Query(...), session: Session = Depends(get_session), service: ManagerMarketService = Depends(get_service)) -> ManagerComparisonView:
    return service.compare_managers(request.app, session, left_manager_id, right_manager_id)


@public_router.get("/history", response_model=list[ManagerHistoryEntryView])
def get_trade_history(request: Request, manager_id: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_session), current_user: User = Depends(get_current_user), service: ManagerMarketService = Depends(get_service)) -> list[ManagerHistoryEntryView]:
    return service.trade_history(request.app, session, current_user, manager_id=manager_id, limit=limit)


@admin_router.get("/audit-log", response_model=list[ManagerAuditEventView])
def list_audit_log(request: Request, limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_session), _: User = Depends(get_current_admin), service: ManagerMarketService = Depends(get_service)) -> list[ManagerAuditEventView]:
    return service.list_audit_log(request.app, session, limit=limit)


@admin_router.get("/competitions", response_model=list[CompetitionAdminView])
def list_competitions(request: Request, session: Session = Depends(get_session), _: User = Depends(get_current_admin), service: ManagerMarketService = Depends(get_service)) -> list[CompetitionAdminView]:
    return service.list_competitions(request.app, session)


@admin_router.patch("/competitions/{code}", response_model=CompetitionAdminView)
def update_competition(code: str, payload: CompetitionAdminUpdateRequest, request: Request, session: Session = Depends(get_session), actor: User = Depends(get_current_admin), service: ManagerMarketService = Depends(get_service)) -> CompetitionAdminView:
    try:
        result = service.update_competition(request.app, session, actor, code, payload)
        session.commit()
        return result
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@admin_router.get("/competitions/{code}/orchestrate", response_model=CompetitionOrchestrationView)
def orchestrate_competition(code: str, request: Request, participants: int = Query(default=4, ge=0), region: str = Query(default="africa"), session: Session = Depends(get_session), _: User = Depends(get_current_admin), service: ManagerMarketService = Depends(get_service)) -> CompetitionOrchestrationView:
    return service.orchestrate_competition(request.app, session, code, participants, region)


@admin_router.put("/catalog/{manager_id}/supply")
def update_supply(manager_id: str, payload: ManagerSupplyUpdateRequest, request: Request, session: Session = Depends(get_session), actor: User = Depends(get_current_admin), service: ManagerMarketService = Depends(get_service)):
    try:
        result = service.update_manager_supply(request.app, session, actor, manager_id, payload)
        session.commit()
        return result
    except ManagerMarketError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


router.include_router(public_router)
router.include_router(admin_router)
