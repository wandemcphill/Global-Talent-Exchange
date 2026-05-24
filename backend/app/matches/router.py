from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.match_event import MatchEventTeam
from app.models.user import User
from app.orchestrator.command_bus import OutboxCommandDispatcher
from app.orchestrator.orchestrator_service import OrchestratorService
from app.services.commentary_service import MatchCommentaryNotFoundError, MatchCommentaryService

from .schemas import (
    MatchAnalysisView,
    MatchCommandAcceptedView,
    MatchCommentaryView,
    MatchCompleteRequest,
    MatchReplayView,
    MatchStartRequest,
)
from .service import (
    AnalysisService,
    MatchCommandError,
    MatchCommandNotFoundError,
    MatchCommandService,
    MatchReplayNotFoundError,
    ReplayService,
)

router = APIRouter(prefix="/matches", tags=["matches"])


def get_replay_service(session: Session = Depends(get_session)) -> ReplayService:
    return ReplayService(session)


def get_analysis_service(session: Session = Depends(get_session)) -> AnalysisService:
    return AnalysisService(session)


def get_commentary_service(session: Session = Depends(get_session)) -> MatchCommentaryService:
    return MatchCommentaryService(session)


def get_orchestrator_service(
    request: Request,
    session: Session = Depends(get_session),
) -> OrchestratorService:
    settings = getattr(request.app.state, "settings", None)
    producer_name = (
        f"{settings.kafka_client_id}.matches"
        if settings is not None and getattr(settings, "kafka_client_id", None)
        else "gtex-api.matches"
    )
    return OrchestratorService(
        command_bus=OutboxCommandDispatcher(
            session=session,
            producer_name=producer_name,
        )
    )


def get_match_command_service(
    session: Session = Depends(get_session),
    orchestrator: OrchestratorService = Depends(get_orchestrator_service),
) -> MatchCommandService:
    return MatchCommandService(session=session, orchestrator=orchestrator)


@router.get("/{match_id}/replay", response_model=MatchReplayView)
def get_match_replay(match_id: str, service: ReplayService = Depends(get_replay_service)) -> MatchReplayView:
    try:
        return service.get_match_replay(match_id)
    except MatchReplayNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match replay not found.") from exc


@router.get("/{match_id}/analysis", response_model=MatchAnalysisView)
def get_match_analysis(
    match_id: str,
    team: MatchEventTeam = Query(default=MatchEventTeam.HOME),
    service: AnalysisService = Depends(get_analysis_service),
) -> MatchAnalysisView:
    try:
        return service.analyze_match(match_id, team)
    except MatchReplayNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match analysis not found.") from exc


@router.post("/start", response_model=MatchCommandAcceptedView, status_code=status.HTTP_202_ACCEPTED)
def start_match(
    payload: MatchStartRequest,
    _: User = Depends(get_current_admin),
    service: MatchCommandService = Depends(get_match_command_service),
) -> MatchCommandAcceptedView:
    try:
        return service.start_match(payload)
    except MatchCommandError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/complete", response_model=MatchCommandAcceptedView, status_code=status.HTTP_202_ACCEPTED)
def complete_match(
    payload: MatchCompleteRequest,
    _: User = Depends(get_current_admin),
    service: MatchCommandService = Depends(get_match_command_service),
) -> MatchCommandAcceptedView:
    try:
        return service.complete_match(payload)
    except MatchCommandNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MatchCommandError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{match_id}/commentary", response_model=MatchCommentaryView)
def get_match_commentary(
    match_id: str,
    tone: str = Query(default="neutral"),
    language: str = Query(default="en"),
    voice_enabled: bool = Query(default=False),
    session: Session = Depends(get_session),
    service: MatchCommentaryService = Depends(get_commentary_service),
) -> MatchCommentaryView:
    try:
        payload = service.get_match_commentary(
            match_id,
            tone=tone,
            language=language,
            voice_enabled=voice_enabled,
        )
    except MatchCommentaryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match commentary not found.") from exc
    session.commit()
    return payload
