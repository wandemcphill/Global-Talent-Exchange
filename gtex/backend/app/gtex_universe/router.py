from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_current_user, get_session
from app.gtex.runtime import ensure_gtex_runtime
from app.gtex_universe.schemas import (
    CareerCreateRequest,
    CareerPlayerView,
    CareerRetireRequest,
    CareerTrainRequest,
    CareerTransferRequest,
    CeremonyTicketPurchaseRequest,
    CeremonyVoteRequest,
    FanExperienceTicketView,
    FanTribeJoinRequest,
    FanTribeView,
    FanProfileUpdateRequest,
    FanProfileView,
    FanTicketPurchaseRequest,
    FanReactionCreateRequest,
    FanReactionSignalView,
    LegacyBoardView,
    MatchChatMessageCreateRequest,
    MatchChatPostResponseView,
    FullExperienceSimulationRequest,
    FullExperienceSimulationView,
    MatchFanExperienceView,
    MatchSocialWarfareView,
    RegenHypeBoardView,
    RealWorldEventView,
    SyncUpdateRequest,
    SyncUpdateResponse,
)
from app.gtex_universe.service import (
    UniverseConflictError,
    UniverseError,
    UniverseNotFoundError,
    UniverseValidationError,
)
from app.models.user import User

router = APIRouter(tags=["gtex-universe"])


def get_runtime(request: Request):
    return ensure_gtex_runtime(request.app)


def raise_universe_http_exception(exc: UniverseError) -> Never:
    if isinstance(exc, UniverseNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, UniverseConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, UniverseValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/career/create", response_model=CareerPlayerView, status_code=status.HTTP_201_CREATED)
def create_career_player(
    payload: CareerCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> CareerPlayerView:
    try:
        career_player = runtime.universe.create_career_player(session, user=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return CareerPlayerView.model_validate(career_player)


@router.get("/career/{user_id}", response_model=CareerPlayerView)
def get_career_player(
    user_id: str,
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> CareerPlayerView:
    try:
        career_player = runtime.universe.get_career_player(session, user_id=user_id)
    except UniverseError as exc:
        raise_universe_http_exception(exc)
    return CareerPlayerView.model_validate(career_player)


@router.post("/career/train", response_model=CareerPlayerView)
def train_career_player(
    payload: CareerTrainRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> CareerPlayerView:
    try:
        career_player = runtime.universe.train_career_player(session, user=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return CareerPlayerView.model_validate(career_player)


@router.post("/career/transfer", response_model=CareerPlayerView)
def transfer_career_player(
    payload: CareerTransferRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> CareerPlayerView:
    try:
        career_player = runtime.universe.transfer_career_player(session, user=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return CareerPlayerView.model_validate(career_player)


@router.post("/career/retire", response_model=CareerPlayerView)
def retire_career_player(
    payload: CareerRetireRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> CareerPlayerView:
    try:
        career_player = runtime.universe.retire_career_player(session, user=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return CareerPlayerView.model_validate(career_player)


@router.get("/fans/profile", response_model=FanProfileView)
def get_fan_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FanProfileView:
    try:
        payload = runtime.universe.get_fan_profile(session, actor=current_user)
    except UniverseError as exc:
        raise_universe_http_exception(exc)
    return FanProfileView.model_validate(payload)


@router.put("/fans/profile", response_model=FanProfileView)
def update_fan_profile(
    payload: FanProfileUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FanProfileView:
    try:
        updated = runtime.universe.update_fan_profile(session, actor=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return FanProfileView.model_validate(updated)


@router.post("/fans/tribe/join", response_model=FanTribeView)
def join_fan_tribe(
    payload: FanTribeJoinRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FanTribeView:
    try:
        tribe = runtime.universe.join_fan_tribe(
            session,
            actor=current_user,
            match_id=payload.match_id,
            club_id=payload.club_id,
        )
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return FanTribeView.model_validate(tribe)


@router.get("/matches/{match_id}/fan-experience", response_model=MatchFanExperienceView)
def get_match_fan_experience(
    match_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    runtime=Depends(get_runtime),
) -> MatchFanExperienceView:
    try:
        payload = runtime.universe.get_match_fan_experience(session, match_id=match_id, current_user=current_user)
    except UniverseError as exc:
        raise_universe_http_exception(exc)
    return MatchFanExperienceView.model_validate(payload)


@router.get("/matches/{match_id}/social-warfare", response_model=MatchSocialWarfareView)
def get_match_social_warfare(
    match_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    runtime=Depends(get_runtime),
) -> MatchSocialWarfareView:
    try:
        payload = runtime.universe.get_match_social_warfare(session, match_id=match_id, current_user=current_user)
    except UniverseError as exc:
        raise_universe_http_exception(exc)
    return MatchSocialWarfareView.model_validate(payload)


@router.post("/matches/{match_id}/tickets", response_model=FanExperienceTicketView, status_code=status.HTTP_201_CREATED)
def purchase_match_ticket(
    match_id: str,
    payload: FanTicketPurchaseRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FanExperienceTicketView:
    try:
        ticket = runtime.universe.purchase_match_ticket(session, actor=current_user, match_id=match_id, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return FanExperienceTicketView.model_validate(ticket)


@router.post("/matches/{match_id}/reactions", response_model=FanReactionSignalView, status_code=status.HTTP_201_CREATED)
def create_match_reaction(
    match_id: str,
    payload: FanReactionCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FanReactionSignalView:
    try:
        reaction = runtime.universe.create_match_reaction(session, actor=current_user, match_id=match_id, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return FanReactionSignalView.model_validate(reaction)


@router.post("/matches/{match_id}/chat/messages", response_model=MatchChatPostResponseView, status_code=status.HTTP_201_CREATED)
def post_match_chat_message(
    match_id: str,
    payload: MatchChatMessageCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> MatchChatPostResponseView:
    try:
        response = runtime.universe.post_match_chat_message(
            session,
            actor=current_user,
            match_id=match_id,
            message=payload.message,
            emoji=payload.emoji,
            intensity=payload.intensity,
        )
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return MatchChatPostResponseView.model_validate(response)


@router.get("/real-world/events", response_model=list[RealWorldEventView])
def list_real_world_events(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> list[RealWorldEventView]:
    events = runtime.universe.list_real_world_events(session, limit=limit)
    return [RealWorldEventView.model_validate(item) for item in events]


@router.post("/sync/update", response_model=SyncUpdateResponse)
def sync_update(
    payload: SyncUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> SyncUpdateResponse:
    try:
        response = runtime.universe.sync_update(session, actor=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return SyncUpdateResponse.model_validate(response)


@router.post("/awards/ceremony/tickets", response_model=FanExperienceTicketView, status_code=status.HTTP_201_CREATED)
def purchase_ceremony_ticket(
    payload: CeremonyTicketPurchaseRequest,
    season_id: str = Query(..., min_length=1),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FanExperienceTicketView:
    try:
        ticket = runtime.universe.purchase_ceremony_ticket(session, actor=current_user, season_id=season_id, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return FanExperienceTicketView.model_validate(ticket)


@router.post("/awards/ceremony/vote")
def cast_ceremony_vote(
    payload: CeremonyVoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> dict[str, object]:
    try:
        vote = runtime.universe.cast_ceremony_vote(session, actor=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return vote


@router.get("/legacy/board", response_model=LegacyBoardView)
def get_legacy_board(
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> LegacyBoardView:
    try:
        payload = runtime.universe.get_legacy_board(session, limit=limit)
    except UniverseError as exc:
        raise_universe_http_exception(exc)
    return LegacyBoardView.model_validate(payload)


@router.get("/regen-hype", response_model=RegenHypeBoardView)
def get_regen_hype(
    season_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> RegenHypeBoardView:
    try:
        payload = runtime.universe.get_regen_hype(session, season_id=season_id)
    except UniverseError as exc:
        raise_universe_http_exception(exc)
    return RegenHypeBoardView.model_validate(payload)


@router.post("/experience/full-simulation", response_model=FullExperienceSimulationView)
def run_full_experience_simulation(
    payload: FullExperienceSimulationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    runtime=Depends(get_runtime),
) -> FullExperienceSimulationView:
    try:
        response = runtime.universe.simulate_full_experience(session, actor=current_user, payload=payload)
        session.commit()
    except UniverseError as exc:
        session.rollback()
        raise_universe_http_exception(exc)
    return FullExperienceSimulationView.model_validate(response)
