from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.schemas.competition_lifecycle import (
    CompetitionAdvanceRequest,
    CompetitionFinalizeRequest,
    CompetitionInviteAcceptRequest,
    CompetitionMatchEventRequest,
    CompetitionMatchEventView,
    CompetitionMatchResultRequest,
    CompetitionMatchView,
    CompetitionRoundView,
    CompetitionScheduleJobRequest,
    CompetitionScheduleJobView,
    CompetitionSchedulePreviewRequest,
    CompetitionSchedulePreviewResponse,
    CompetitionSeedRequest,
    CompetitionStandingView,
)
from backend.app.schemas.competition_requests import (
    CompetitionCreateRequest,
    CompetitionInviteCreateRequest,
    CompetitionJoinRequest,
    CompetitionLeaveRequest,
    CompetitionPublishRequest,
    CompetitionUpdateRequest,
)
from backend.app.schemas.competition_responses import (
    CompetitionFinancialSummaryView,
    CompetitionInviteView,
    CompetitionInvitesResponse,
    CompetitionListResponse,
    CompetitionSummaryView,
)
from backend.app.services.competition_orchestrator import (
    CompetitionActionError,
    CompetitionOrchestrator,
    get_competition_orchestrator,
)

router = APIRouter(prefix="/api/competitions", tags=["competitions"])


@router.post("", response_model=CompetitionSummaryView, status_code=status.HTTP_201_CREATED)
def create_competition(
    payload: CompetitionCreateRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    return _handle_competition_errors(lambda: orchestrator.create(payload))


@router.patch("/{competition_id}", response_model=CompetitionSummaryView)
def update_competition(
    competition_id: str,
    payload: CompetitionUpdateRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.update(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/publish", response_model=CompetitionSummaryView)
def publish_competition(
    competition_id: str,
    payload: CompetitionPublishRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = orchestrator.publish(competition_id, open_for_join=payload.open_for_join)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}", response_model=CompetitionSummaryView)
def get_competition(
    competition_id: str,
    viewer_id: str | None = Query(default=None),
    invite_code: str | None = Query(default=None),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = orchestrator.get(competition_id, user_id=viewer_id, invite_code=invite_code)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("", response_model=CompetitionListResponse)
def list_competitions(
    public_only: bool = Query(default=False),
    format: CompetitionFormat | None = Query(default=None),
    fee_filter: Literal["free", "paid"] | None = Query(default=None),
    sort: Literal["trending", "new", "prize_pool", "fill_rate"] = Query(default="trending"),
    creator_id: str | None = Query(default=None),
    beginner_friendly: bool | None = Query(default=None),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionListResponse:
    return orchestrator.list(
        public_only=public_only,
        format=format,
        fee_filter=fee_filter,
        sort=sort,
        creator_id=creator_id,
        beginner_friendly=beginner_friendly,
    )


@router.post("/{competition_id}/join", response_model=CompetitionSummaryView)
def join_competition(
    competition_id: str,
    payload: CompetitionJoinRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = orchestrator.join(
        competition_id,
        user_id=payload.user_id,
        user_name=payload.user_name,
        invite_code=payload.invite_code,
    )
    if result is None:
        raise _not_found(competition_id)
    if not result.join_eligibility.eligible:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.join_eligibility.reason or "join_not_allowed")
    return result


@router.post("/{competition_id}/leave", response_model=CompetitionSummaryView)
def leave_competition(
    competition_id: str,
    payload: CompetitionLeaveRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = orchestrator.leave(competition_id, user_id=payload.user_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/invites", response_model=CompetitionInviteView, status_code=status.HTTP_201_CREATED)
def create_competition_invite(
    competition_id: str,
    payload: CompetitionInviteCreateRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionInviteView:
    result = _handle_competition_errors(
        lambda: orchestrator.create_invite(
            competition_id,
            issued_by=payload.issued_by,
            max_uses=payload.max_uses,
            expires_at=payload.expires_at,
            note=payload.note,
        )
    )
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/invites", response_model=CompetitionInvitesResponse)
def list_competition_invites(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionInvitesResponse:
    result = orchestrator.list_invites(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/invites/accept", response_model=CompetitionSummaryView)
def accept_competition_invite(
    competition_id: str,
    payload: CompetitionInviteAcceptRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.accept_invite(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/summary", response_model=CompetitionSummaryView)
def get_competition_summary(
    competition_id: str,
    viewer_id: str | None = Query(default=None),
    invite_code: str | None = Query(default=None),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = orchestrator.summary(competition_id, user_id=viewer_id, invite_code=invite_code)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/financials", response_model=CompetitionFinancialSummaryView)
def get_competition_financials(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionFinancialSummaryView:
    result = orchestrator.financials(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/rounds", response_model=tuple[CompetitionRoundView, ...])
def get_competition_rounds(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> tuple[CompetitionRoundView, ...]:
    result = orchestrator.rounds(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/fixtures", response_model=tuple[CompetitionMatchView, ...])
def get_competition_fixtures(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> tuple[CompetitionMatchView, ...]:
    result = orchestrator.fixtures(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/standings", response_model=tuple[CompetitionStandingView, ...])
def get_competition_standings(
    competition_id: str,
    group_key: str | None = Query(default=None),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> tuple[CompetitionStandingView, ...]:
    result = orchestrator.standings(competition_id, group_key=group_key)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/seed", response_model=CompetitionSummaryView)
def seed_competition(
    competition_id: str,
    payload: CompetitionSeedRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.seed_competition(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/launch", response_model=CompetitionSummaryView)
def launch_competition(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.launch_competition(competition_id))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/advance", response_model=CompetitionSummaryView)
def advance_competition(
    competition_id: str,
    payload: CompetitionAdvanceRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.advance_competition(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/finalize", response_model=CompetitionSummaryView)
def finalize_competition(
    competition_id: str,
    payload: CompetitionFinalizeRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.finalize_competition(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/schedule/preview", response_model=CompetitionSchedulePreviewResponse)
def preview_competition_schedule(
    competition_id: str,
    payload: CompetitionSchedulePreviewRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSchedulePreviewResponse:
    result = _handle_competition_errors(lambda: orchestrator.schedule_preview(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/schedule/jobs", response_model=CompetitionScheduleJobView)
def create_competition_schedule_job(
    competition_id: str,
    payload: CompetitionScheduleJobRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionScheduleJobView:
    result = _handle_competition_errors(lambda: orchestrator.create_schedule_job(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/schedule/jobs", response_model=CompetitionScheduleJobView)
def get_latest_schedule_job(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionScheduleJobView:
    result = orchestrator.schedule_job_status(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/schedule/jobs/{job_id}", response_model=CompetitionScheduleJobView)
def get_schedule_job_status(
    competition_id: str,
    job_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionScheduleJobView:
    result = orchestrator.schedule_job_status(competition_id, job_id=job_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/matches/{match_id}/events", response_model=CompetitionMatchEventView, status_code=status.HTTP_201_CREATED)
def record_match_event(
    competition_id: str,
    match_id: str,
    payload: CompetitionMatchEventRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionMatchEventView:
    result = _handle_competition_errors(lambda: orchestrator.record_match_event(competition_id, match_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/matches/{match_id}/events", response_model=tuple[CompetitionMatchEventView, ...])
def list_match_events(
    competition_id: str,
    match_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> tuple[CompetitionMatchEventView, ...]:
    result = orchestrator.list_match_events(competition_id, match_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/matches/{match_id}/result", response_model=CompetitionMatchView)
def complete_match(
    competition_id: str,
    match_id: str,
    payload: CompetitionMatchResultRequest,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionMatchView:
    result = _handle_competition_errors(lambda: orchestrator.complete_match(competition_id, match_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


def _handle_competition_errors(func):
    try:
        return func()
    except CompetitionActionError as exc:
        status_code = status.HTTP_403_FORBIDDEN if exc.reason == "invite_forbidden" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=exc.reason) from exc


def _not_found(competition_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Competition {competition_id} was not found",
    )


__all__ = ["router"]
