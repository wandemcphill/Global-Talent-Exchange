from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.streamer_tournament_engine.schemas import (
    StreamerTournamentCreateRequest,
    StreamerTournamentInviteCreateRequest,
    StreamerTournamentListView,
    StreamerTournamentJoinRequest,
    StreamerTournamentPolicyUpsertRequest,
    StreamerTournamentPolicyView,
    StreamerTournamentPublishRequest,
    StreamerTournamentReviewRequest,
    StreamerTournamentRewardGrantView,
    StreamerTournamentRewardPlanReplaceRequest,
    StreamerTournamentRiskReviewRequest,
    StreamerTournamentRiskSignalView,
    StreamerTournamentSettleRequest,
    StreamerTournamentSettlementView,
    StreamerTournamentUpdateRequest,
    StreamerTournamentView,
)
from app.models.streamer_tournament import StreamerTournamentRiskStatus
from app.streamer_tournament_engine.service import (
    StreamerTournamentError,
    StreamerTournamentNotFoundError,
    StreamerTournamentPermissionError,
    StreamerTournamentService,
    StreamerTournamentValidationError,
)

router = APIRouter(prefix="/streamer-tournaments", tags=["streamer-tournaments"])
admin_router = APIRouter(prefix="/admin/streamer-tournaments", tags=["admin-streamer-tournaments"])


def _service(session: Session = Depends(get_session)) -> StreamerTournamentService:
    return StreamerTournamentService(session)


def _raise_http(exc: StreamerTournamentError) -> None:
    if isinstance(exc, StreamerTournamentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, StreamerTournamentPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.detail) from exc
    if isinstance(exc, StreamerTournamentValidationError):
        conflict_reasons = {
            "duplicate_invite",
            "duplicate_slug",
            "invite_limit_reached",
            "invite_required",
            "not_eligible",
            "registration_closed",
            "tournament_full",
        }
        status_code = status.HTTP_409_CONFLICT if exc.reason in conflict_reasons else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("", response_model=StreamerTournamentListView)
def list_public_tournaments(service: StreamerTournamentService = Depends(_service)) -> StreamerTournamentListView:
    return StreamerTournamentListView(tournaments=[StreamerTournamentView.model_validate(item) for item in service.list_tournaments()])


@router.get("/mine", response_model=StreamerTournamentListView)
def list_my_tournaments(
    current_user: User = Depends(get_current_user),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentListView:
    return StreamerTournamentListView(
        tournaments=[StreamerTournamentView.model_validate(item) for item in service.list_tournaments(actor=current_user, mine_only=True)]
    )


@router.post("", response_model=StreamerTournamentView, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: StreamerTournamentCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        tournament = service.create_tournament(actor=current_user, payload=payload)
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@router.get("/{tournament_id}", response_model=StreamerTournamentView)
def get_tournament(tournament_id: str, service: StreamerTournamentService = Depends(_service)) -> StreamerTournamentView:
    try:
        tournament = service.get_tournament(tournament_id)
    except StreamerTournamentError as exc:
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@router.patch("/{tournament_id}", response_model=StreamerTournamentView)
def update_tournament(
    tournament_id: str,
    payload: StreamerTournamentUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        tournament = service.update_tournament(actor=current_user, tournament_id=tournament_id, payload=payload)
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@router.put("/{tournament_id}/rewards", response_model=StreamerTournamentView)
def replace_reward_plan(
    tournament_id: str,
    payload: StreamerTournamentRewardPlanReplaceRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        tournament = service.replace_rewards(actor=current_user, tournament_id=tournament_id, rewards=payload.rewards)
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@router.post("/{tournament_id}/invites", response_model=StreamerTournamentView)
def create_invite(
    tournament_id: str,
    payload: StreamerTournamentInviteCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        service.create_invite(actor=current_user, tournament_id=tournament_id, payload=payload)
        tournament = service.get_tournament(tournament_id)
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@router.post("/{tournament_id}/join", response_model=StreamerTournamentView)
def join_tournament(
    tournament_id: str,
    payload: StreamerTournamentJoinRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        tournament = service.join_tournament(actor=current_user, tournament_id=tournament_id, payload=payload)
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@router.post("/{tournament_id}/publish", response_model=StreamerTournamentView)
def publish_tournament(
    tournament_id: str,
    payload: StreamerTournamentPublishRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        tournament = service.publish_tournament(
            actor=current_user,
            tournament_id=tournament_id,
            submission_notes=payload.submission_notes,
        )
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@admin_router.get("/policy", response_model=StreamerTournamentPolicyView)
def get_policy(service: StreamerTournamentService = Depends(_service), _: User = Depends(get_current_admin)) -> StreamerTournamentPolicyView:
    return StreamerTournamentPolicyView.model_validate(service.get_policy(), from_attributes=True)


@admin_router.put("/policy", response_model=StreamerTournamentPolicyView)
def update_policy(
    payload: StreamerTournamentPolicyUpsertRequest,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentPolicyView:
    policy = service.upsert_policy(actor=current_user, payload=payload)
    session.commit()
    return StreamerTournamentPolicyView.model_validate(policy, from_attributes=True)


@admin_router.post("/{tournament_id}/review", response_model=StreamerTournamentView)
def review_tournament(
    tournament_id: str,
    payload: StreamerTournamentReviewRequest,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentView:
    try:
        tournament = service.review_tournament(
            actor=current_user,
            tournament_id=tournament_id,
            approve=payload.approve,
            notes=payload.notes,
        )
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentView.model_validate(tournament)


@admin_router.get("/risk-signals", response_model=list[StreamerTournamentRiskSignalView])
def list_risk_signals(
    status_filter: StreamerTournamentRiskStatus | None = Query(default=StreamerTournamentRiskStatus.OPEN),
    service: StreamerTournamentService = Depends(_service),
    _: User = Depends(get_current_admin),
) -> list[StreamerTournamentRiskSignalView]:
    return [StreamerTournamentRiskSignalView.model_validate(item, from_attributes=True) for item in service.list_risk_signals(status_filter=status_filter)]


@admin_router.post("/risk-signals/{signal_id}/review", response_model=StreamerTournamentRiskSignalView)
def review_risk_signal(
    signal_id: str,
    payload: StreamerTournamentRiskReviewRequest,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentRiskSignalView:
    try:
        signal = service.review_risk_signal(
            actor=current_user,
            signal_id=signal_id,
            status_value=payload.action,
            notes=payload.notes,
        )
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentRiskSignalView.model_validate(signal, from_attributes=True)


@admin_router.post("/{tournament_id}/settle", response_model=StreamerTournamentSettlementView)
def settle_tournament(
    tournament_id: str,
    payload: StreamerTournamentSettleRequest,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: StreamerTournamentService = Depends(_service),
) -> StreamerTournamentSettlementView:
    try:
        result = service.settle_tournament(
            actor=current_user,
            tournament_id=tournament_id,
            placements=payload.placements,
            note=payload.note,
        )
        session.commit()
    except StreamerTournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return StreamerTournamentSettlementView(
        tournament=StreamerTournamentView.model_validate(result["tournament"]),
        grants=[StreamerTournamentRewardGrantView.model_validate(item) for item in result["grants"]],
    )

