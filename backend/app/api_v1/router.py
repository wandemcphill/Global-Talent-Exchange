from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, decode_access_token
from app.core.container import ApplicationContext
from app.models.user import User

from .schemas import (
    ApiEnvelope,
    ApiError,
    BroadcastPayRequest,
    ClubOfferRequest,
    ClubSaleRequest,
    FederationCreateRequest,
    FederationVoteRequest,
    MarketBidRequest,
    StoryGenerateRequest,
    TournamentRentRequest,
    TournamentSquadSubmitRequest,
)
from .service import (
    GlobalApiV1Error,
    GlobalApiV1NotFoundError,
    GlobalApiV1Service,
    GlobalApiV1ValidationError,
)

router = APIRouter(prefix="/api/v1", tags=["api-v1"])


def install_exception_handlers(app, _context: ApplicationContext) -> None:
    if getattr(app.state, "api_v1_exception_handlers_installed", False):
        return
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.state.api_v1_exception_handlers_installed = True


async def _handle_http_exception(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/api/v1"):
        return await http_exception_handler(request, exc)
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed."
    details = None if isinstance(detail, str) else detail
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ApiEnvelope[dict[str, Any]](
                success=False,
                data=None,
                error=ApiError(
                    code=_error_code_for_status(exc.status_code),
                    message=message,
                    details=details,
                ),
            )
        ),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/v1"):
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            ApiEnvelope[dict[str, Any]](
                success=False,
                data=None,
                error=ApiError(
                    code="validation_error",
                    message="Request validation failed.",
                    details=exc.errors(),
                ),
            )
        ),
    )


def get_service(request: Request) -> GlobalApiV1Service:
    return GlobalApiV1Service(request.app)


def ok(data: dict[str, Any]) -> ApiEnvelope[dict[str, Any]]:
    return ApiEnvelope[dict[str, Any]](success=True, data=data, error=None)


def _raise_global_api_http_error(exc: GlobalApiV1Error) -> None:
    if isinstance(exc, GlobalApiV1NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, GlobalApiV1ValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _error_code_for_status(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
    }
    return mapping.get(status_code, f"http_{status_code}")


@router.get("/home/dashboard", response_model=ApiEnvelope[dict[str, Any]])
def get_dashboard(
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.build_dashboard(current_user))


@router.get("/matches/{match_id}", response_model=ApiEnvelope[dict[str, Any]])
def get_match_state(
    match_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_match_state(match_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/market/listings", response_model=ApiEnvelope[dict[str, Any]])
def get_market_listings(
    page: int = Query(default=1, ge=1),
    rating_min: int | None = Query(default=None, ge=0),
    position: str | None = Query(default=None),
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.list_market_listings(page=page, rating_min=rating_min, position=position))


@router.post("/market/bid", response_model=ApiEnvelope[dict[str, Any]], status_code=status.HTTP_201_CREATED)
def place_market_bid(
    payload: MarketBidRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.place_bid(current_user, listing_id=payload.listing_id, amount=payload.amount)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.get("/regens", response_model=ApiEnvelope[dict[str, Any]])
def get_regens(
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.list_regens())


@router.get("/competitions", response_model=ApiEnvelope[dict[str, Any]])
def get_competitions(
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.list_competitions())


@router.get("/history/records", response_model=ApiEnvelope[dict[str, Any]])
def get_history_records(
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.list_history_records())


@router.get("/federations", response_model=ApiEnvelope[dict[str, Any]])
def get_federations(
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.list_federations())


@router.get("/players/{player_id}", response_model=ApiEnvelope[dict[str, Any]])
def get_player(
    player_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_player(player_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/clubs/{club_id}", response_model=ApiEnvelope[dict[str, Any]])
def get_club(
    club_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_club(club_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/clubs/{club_id}/squad", response_model=ApiEnvelope[dict[str, Any]])
def get_club_squad(
    club_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_club_squad(club_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/clubs/{club_id}/finances", response_model=ApiEnvelope[dict[str, Any]])
def get_club_finances(
    club_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_club_finances(club_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/clubs/{club_id}/fans", response_model=ApiEnvelope[dict[str, Any]])
def get_club_fans(
    club_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_club_fans(club_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/tournaments/{tournament_id}", response_model=ApiEnvelope[dict[str, Any]])
def get_tournament(
    tournament_id: str,
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_tournament(tournament_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.post("/tournaments/{tournament_id}/join", response_model=ApiEnvelope[dict[str, Any]])
def join_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.join_tournament(current_user, tournament_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.post("/tournaments/{tournament_id}/rent", response_model=ApiEnvelope[dict[str, Any]])
def rent_tournament_player(
    tournament_id: str,
    payload: TournamentRentRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.rent_player(current_user, tournament_id=tournament_id, player_id=payload.player_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.post("/tournaments/{tournament_id}/squad", response_model=ApiEnvelope[dict[str, Any]])
def submit_tournament_squad(
    tournament_id: str,
    payload: TournamentSquadSubmitRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.submit_squad(current_user, tournament_id=tournament_id, player_ids=payload.player_ids)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.get("/broadcast/{match_id}", response_model=ApiEnvelope[dict[str, Any]])
def get_broadcast(
    match_id: str,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.get_broadcast(current_user, match_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.post("/broadcast/pay", response_model=ApiEnvelope[dict[str, Any]])
def pay_to_watch(
    payload: BroadcastPayRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.pay_to_watch(current_user, match_id=payload.match_id, amount=payload.amount)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.post("/clubs/list", response_model=ApiEnvelope[dict[str, Any]], status_code=status.HTTP_201_CREATED)
def list_club_for_sale(
    payload: ClubSaleRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.list_club_for_sale(
            current_user,
            club_id=payload.club_id,
            asking_price=payload.asking_price,
            note=payload.note,
        )
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.get("/clubs/marketplace", response_model=ApiEnvelope[dict[str, Any]])
def get_club_marketplace(
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.get_club_marketplace())


@router.post("/clubs/offer", response_model=ApiEnvelope[dict[str, Any]], status_code=status.HTTP_201_CREATED)
def make_club_offer(
    payload: ClubOfferRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.make_club_offer(current_user, listing_id=payload.listing_id, amount=payload.amount)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.get("/users/{user_id}", response_model=ApiEnvelope[dict[str, Any]])
def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.get_user_profile(current_user, user_id))


@router.post("/users/{user_id}/follow", response_model=ApiEnvelope[dict[str, Any]])
def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.follow_user(current_user, user_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/feed", response_model=ApiEnvelope[dict[str, Any]])
def get_feed(
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.get_feed(current_user))


@router.get("/tasks", response_model=ApiEnvelope[dict[str, Any]])
def get_tasks(
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.list_tasks(current_user))


@router.post("/tasks/{task_id}/claim", response_model=ApiEnvelope[dict[str, Any]])
def claim_task_reward(
    task_id: str,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.claim_task(current_user, task_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.get("/stories", response_model=ApiEnvelope[dict[str, Any]])
def get_stories(
    _current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.get_stories())


@router.post("/stories/generate", response_model=ApiEnvelope[dict[str, Any]], status_code=status.HTTP_201_CREATED)
def trigger_story_generation(
    payload: StoryGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(
        service.generate_story(
            current_user,
            title=payload.title,
            story_type=payload.story_type,
            subject_id=payload.subject_id,
        )
    )


@router.post("/federations", response_model=ApiEnvelope[dict[str, Any]], status_code=status.HTTP_201_CREATED)
def create_federation(
    payload: FederationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    return ok(service.create_federation(current_user, name=payload.name, region=payload.region))


@router.post("/federations/{federation_id}/join", response_model=ApiEnvelope[dict[str, Any]])
def join_federation(
    federation_id: str,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        payload = service.join_federation(current_user, federation_id)
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(payload)


@router.post("/federations/vote", response_model=ApiEnvelope[dict[str, Any]])
def vote_on_federation(
    payload: FederationVoteRequest,
    current_user: User = Depends(get_current_user),
    service: GlobalApiV1Service = Depends(get_service),
) -> ApiEnvelope[dict[str, Any]]:
    try:
        result = service.vote_federation(
            current_user,
            federation_id=payload.federation_id,
            proposal_id=payload.proposal_id,
            vote=payload.vote,
        )
    except GlobalApiV1Error as exc:
        _raise_global_api_http_error(exc)
    return ok(result)


@router.websocket("/ws/match/{match_id}")
async def stream_match_commentary(websocket: WebSocket, match_id: str) -> None:
    user = _resolve_websocket_user(websocket)
    if user is None:
        await websocket.close(code=4401)
        return
    service = GlobalApiV1Service(websocket.scope["app"])
    try:
        payload = service.build_match_commentary_event(match_id)
    except GlobalApiV1Error:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    await websocket.send_json(payload)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


@router.websocket("/ws/market/{listing_id}")
async def stream_market_bids(websocket: WebSocket, listing_id: str) -> None:
    user = _resolve_websocket_user(websocket)
    if user is None:
        await websocket.close(code=4401)
        return
    service = GlobalApiV1Service(websocket.scope["app"])
    try:
        payload = service.get_market_bid_event(listing_id)
    except GlobalApiV1Error:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    await websocket.send_json(payload)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


@router.websocket("/ws/notifications")
async def stream_notifications(websocket: WebSocket) -> None:
    user = _resolve_websocket_user(websocket)
    if user is None:
        await websocket.close(code=4401)
        return
    service = GlobalApiV1Service(websocket.scope["app"])
    await websocket.accept()
    await websocket.send_json(service.get_notification_event(user.id))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


def _resolve_websocket_user(websocket: WebSocket) -> User | None:
    token = websocket.query_params.get("token")
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", maxsplit=1)[1].strip()
    if token is None or not token.strip():
        return None
    try:
        payload = decode_access_token(token.strip())
    except TokenError:
        return None
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return None
    session_factory = getattr(websocket.scope["app"].state, "session_factory", None)
    if session_factory is None:
        return None
    with session_factory() as session:
        user = session.get(User, subject)
        if user is None or not user.is_active:
            return None
        return user


__all__ = ["install_exception_handlers", "router"]
