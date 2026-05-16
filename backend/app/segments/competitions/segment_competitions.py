from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.admin_godmode.service import AdminGodModeService, PermissionDeniedError
from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user
from app.competitions.creator_league_router import router as creator_league_router
from app.common.enums.competition_format import CompetitionFormat
from app.models.user import User, UserRole
from app.models.competition import Competition
from app.schemas.competition_lifecycle import (
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
from app.schemas.competition_requests import (
    CompetitionCreateRequest,
    CompetitionHostType,
    CompetitionInviteCreateRequest,
    CompetitionJoinActionRequest,
    CompetitionJoinRequest,
    CompetitionLeaveRequest,
    CompetitionPublishRequest,
    RandomCompetitionRequest,
    CompetitionUpdateRequest,
)
from app.schemas.competition_responses import (
    ClubCompetitionLeaderboardResponse,
    CompetitionFinancialSummaryView,
    CompetitionParticipantsResponse,
    CompetitionPotView,
    CompetitionProgressionView,
    CompetitionInviteView,
    CompetitionInvitesResponse,
    CompetitionListResponse,
    CompetitionRewardsResponse,
    CompetitionSummaryView,
    RandomCompetitionQuoteView,
)
from app.services.competition_orchestrator import (
    CompetitionActionError,
    CompetitionOrchestrator,
    get_competition_orchestrator,
)
from app.services.competition_reminder_service import CompetitionReminderService
from app.wallets.service import WalletService

router = APIRouter(prefix="/api/competitions", tags=["competitions"])
admin_router = APIRouter(prefix="/api/admin/competitions", tags=["admin-competitions"])
router.include_router(creator_league_router)


def _require_manage_competitions_permission(request: Request, actor: User) -> None:
    if actor.role == UserRole.SUPER_ADMIN:
        return
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required for this action.",
        )
    service = AdminGodModeService(
        wallet_service=WalletService(cache_backend=getattr(request.app.state, "cache_backend", None))
    )
    try:
        state = service._load_state(request.app)
        profile = service.resolve_profile(actor, state)
        service._assert_has_permission(profile, "manage_competitions")
    except PermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


def _is_admin_managed_platform_competition(source_type: str | None) -> bool:
    if source_type is None:
        return False
    normalized = source_type.strip().lower()
    return normalized in {
        "gtex",
        "platform",
        "gtex_platform",
        "gtex_competition",
    }


def _require_manage_competitions_or_creator(
    request: Request,
    actor: User,
    competition: Competition,
) -> None:
    # Allow the actual host/creator to publish and launch their own hosted
    # competitions. Keep only true platform-curated competitions admin-gated.
    #
    # Important: this is intentionally scoped to the auth layer in this router.
    # Do not change the broader gtex_hosted finance/economy classification here.
    if competition.host_user_id == actor.id and not _is_admin_managed_platform_competition(competition.source_type):
        return
    _require_manage_competitions_permission(request, actor)


def _display_name_for(actor: User) -> str:
    return actor.display_name or actor.username or actor.email or actor.id


def _user_competition_payload(payload: CompetitionCreateRequest, actor: User) -> CompetitionCreateRequest:
    return payload.model_copy(
        update={
            "creator_id": actor.id,
            "creator_name": payload.creator_name or _display_name_for(actor),
            "host_type": CompetitionHostType.USER_HOSTED,
            "source_type": CompetitionHostType.USER_HOSTED.value,
            "type": CompetitionHostType.USER_HOSTED.value,
            "currency": "credit",
        }
    )


def _legacy_user_competition_payload(
    payload: CompetitionCreateRequest,
    actor: User | None,
) -> CompetitionCreateRequest:
    creator_id = actor.id if actor is not None else payload.creator_id
    if creator_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials or creator_id are required.",
        )
    creator_name = payload.creator_name
    if not creator_name:
        creator_name = _display_name_for(actor) if actor is not None else creator_id
    return payload.model_copy(
        update={
            "creator_id": creator_id,
            "creator_name": creator_name,
            "host_type": CompetitionHostType.USER_HOSTED,
            "source_type": CompetitionHostType.USER_HOSTED.value,
            "type": CompetitionHostType.USER_HOSTED.value,
            "currency": "credit",
        }
    )


def _admin_competition_payload(payload: CompetitionCreateRequest, actor: User) -> CompetitionCreateRequest:
    host_type = payload.host_type or CompetitionHostType.GTEX_HOSTED
    if host_type is CompetitionHostType.GTEX_HOSTED:
        return payload.model_copy(
            update={
                "creator_id": actor.id,
                "creator_name": payload.creator_name or "GTEX",
                "host_type": CompetitionHostType.GTEX_HOSTED,
                "source_type": CompetitionHostType.GTEX_HOSTED.value,
                "type": CompetitionHostType.GTEX_HOSTED.value,
                "currency": "coin",
            }
        )
    return payload.model_copy(
        update={
            "creator_id": payload.creator_id or actor.id,
            "creator_name": payload.creator_name or _display_name_for(actor),
            "host_type": CompetitionHostType.USER_HOSTED,
            "source_type": CompetitionHostType.USER_HOSTED.value,
            "type": CompetitionHostType.USER_HOSTED.value,
            "currency": "credit",
        }
    )


@router.post(
    "", response_model=CompetitionSummaryView, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED
)
def create_competition(
    payload: CompetitionCreateRequest,
    actor: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    resolved = _user_competition_payload(payload, actor)
    return _handle_competition_errors(lambda: orchestrator.create(resolved))


@router.post(
    "/create",
    response_model=CompetitionSummaryView,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_competition_alias(
    payload: CompetitionCreateRequest,
    actor: User | None = Depends(get_optional_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    resolved = _legacy_user_competition_payload(payload, actor)
    return _handle_competition_errors(lambda: orchestrator.create(resolved))


@admin_router.post(
    "", response_model=CompetitionSummaryView, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED
)
def admin_create_competition(
    payload: CompetitionCreateRequest,
    request: Request,
    actor: User = Depends(get_current_admin),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    _require_manage_competitions_permission(request, actor)
    resolved = _admin_competition_payload(payload, actor)
    return _handle_competition_errors(lambda: orchestrator.create(resolved))


@admin_router.post("/reminders/dispatch")
def admin_dispatch_competition_reminders(
    request: Request,
    actor: User = Depends(get_current_admin),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> dict[str, int]:
    _require_manage_competitions_permission(request, actor)
    created = CompetitionReminderService(orchestrator.session).dispatch_due_reminders()
    return {"created": created}


@router.patch("/{competition_id}", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def update_competition(
    competition_id: str,
    payload: CompetitionUpdateRequest,
    _: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.update(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/publish", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def publish_competition(
    competition_id: str,
    payload: CompetitionPublishRequest,
    request: Request,
    actor: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    competition = orchestrator.session.get(Competition, competition_id)
    if competition is None:
        raise _not_found(competition_id)
    _require_manage_competitions_or_creator(request, actor, competition)
    result = _handle_competition_errors(
        lambda: orchestrator.publish(competition_id, open_for_join=payload.open_for_join)
    )
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get(
    "/players/{subject_id}/progression", response_model=CompetitionProgressionView, response_model_exclude_none=True
)
def get_competition_progression(
    subject_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionProgressionView:
    result = orchestrator.progression(subject_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Competition progression for {subject_id} was not found",
        )
    return result


@router.get("/leaderboard/clubs", response_model=ClubCompetitionLeaderboardResponse)
def get_club_competition_leaderboard(
    limit: int = Query(default=50, ge=1, le=200),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> ClubCompetitionLeaderboardResponse:
    return orchestrator.club_leaderboard(limit=limit)


@router.post("/random/quote", response_model=RandomCompetitionQuoteView, response_model_exclude_none=True)
def quote_random_competition(
    payload: RandomCompetitionRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> RandomCompetitionQuoteView:
    result = orchestrator.random_quote(mode=payload.mode, club_id=payload.club_id, user_id=current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No eligible random competition was found.")
    return result


@router.post("/random/join", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def join_random_competition(
    payload: RandomCompetitionRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    quote = orchestrator.random_quote(mode=payload.mode, club_id=payload.club_id, user_id=current_user.id)
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No eligible random competition was found.")
    join_payload = CompetitionJoinRequest(user_id=current_user.id, club_id=payload.club_id)
    return _join_competition_response(
        quote.competition_id,
        join_payload,
        current_user=current_user,
        orchestrator=orchestrator,
    )


@router.get("/{competition_id}", response_model=CompetitionSummaryView, response_model_exclude_none=True)
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


@router.get("", response_model=CompetitionListResponse, response_model_exclude_none=True)
def list_competitions(
    public_only: bool = Query(default=False),
    format: CompetitionFormat | None = Query(default=None),
    fee_filter: Literal["free", "paid"] | None = Query(default=None),
    sort: Literal["trending", "new", "prize_pool", "fill_rate"] = Query(default="trending"),
    creator_id: str | None = Query(default=None),
    beginner_friendly: bool | None = Query(default=None),
    reward_filter: str | None = Query(default=None),
    ranked: bool | None = Query(default=None),
    host_type: str | None = Query(default=None),
    availability: str | None = Query(default=None),
    starts: str | None = Query(default=None),
    start_from: datetime | None = Query(default=None),
    start_to: datetime | None = Query(default=None),
    min_entry_fee: float | None = Query(default=None, ge=0),
    max_entry_fee: float | None = Query(default=None, ge=0),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionListResponse:
    return orchestrator.list(
        public_only=public_only,
        format=format,
        fee_filter=fee_filter,
        sort=sort,
        creator_id=creator_id,
        beginner_friendly=beginner_friendly,
        reward_filter=reward_filter,
        ranked=ranked,
        host_type=host_type,
        availability=availability,
        starts=starts,
        start_from=start_from,
        start_to=start_to,
        min_entry_fee=min_entry_fee,
        max_entry_fee=max_entry_fee,
    )


@router.post("/{competition_id}/join", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def join_competition(
    competition_id: str,
    payload: CompetitionJoinRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    return _join_competition_response(
        competition_id,
        payload,
        current_user=current_user,
        orchestrator=orchestrator,
    )


@router.post("/join", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def join_competition_alias(
    payload: CompetitionJoinActionRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    return _join_competition_response(
        payload.competition_id,
        payload,
        current_user=current_user,
        orchestrator=orchestrator,
    )


def _join_competition_response(
    competition_id: str,
    payload: CompetitionJoinRequest,
    *,
    current_user: User,
    orchestrator: CompetitionOrchestrator,
) -> CompetitionSummaryView:
    if payload.user_id is not None and payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user does not match competition join payload.",
        )
    resolved_user_id = current_user.id
    resolved_user_name = payload.user_name or current_user.display_name or current_user.username
    result = _handle_competition_errors(
        lambda: orchestrator.join(
            competition_id,
            user_id=resolved_user_id,
            user_name=resolved_user_name,
            club_id=payload.club_id,
            club_name=payload.club_name,
            invite_code=payload.invite_code,
            passcode=payload.passcode,
        )
    )
    if result is None:
        raise _not_found(competition_id)
    if not result.join_eligibility.eligible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=result.join_eligibility.reason or "join_not_allowed"
        )
    return result


@router.post("/{competition_id}/leave", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def leave_competition(
    competition_id: str,
    payload: CompetitionLeaveRequest,
    _: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.leave(competition_id, user_id=payload.user_id))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/invites", response_model=CompetitionInviteView, status_code=status.HTTP_201_CREATED)
def create_competition_invite(
    competition_id: str,
    payload: CompetitionInviteCreateRequest,
    _: User = Depends(get_current_user),
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


@router.post(
    "/{competition_id}/invites/accept", response_model=CompetitionSummaryView, response_model_exclude_none=True
)
def accept_competition_invite(
    competition_id: str,
    payload: CompetitionInviteAcceptRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    if payload.user_id is not None and payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user does not match competition invite payload.",
        )
    result = _handle_competition_errors(
        lambda: orchestrator.accept_invite(competition_id, payload, actor_user_id=current_user.id)
    )
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/summary", response_model=CompetitionSummaryView, response_model_exclude_none=True)
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


@router.get(
    "/{competition_id}/financials", response_model=CompetitionFinancialSummaryView, response_model_exclude_none=True
)
def get_competition_financials(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionFinancialSummaryView:
    result = orchestrator.financials(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/participants", response_model=CompetitionParticipantsResponse)
def get_competition_participants(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionParticipantsResponse:
    result = orchestrator.participants(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/pot", response_model=CompetitionPotView)
def get_competition_pot(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionPotView:
    result = orchestrator.pot(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/cancel", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def cancel_competition(
    competition_id: str,
    request: Request,
    actor: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    competition = orchestrator.session.get(Competition, competition_id)
    if competition is None:
        raise _not_found(competition_id)
    _require_manage_competitions_or_creator(request, actor, competition)
    result = orchestrator.cancel(competition_id, actor_user_id=actor.id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/settle-payouts", response_model=CompetitionRewardsResponse)
def settle_competition_payouts(
    competition_id: str,
    request: Request,
    actor: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionRewardsResponse:
    competition = orchestrator.session.get(Competition, competition_id)
    if competition is None:
        raise _not_found(competition_id)
    _require_manage_competitions_or_creator(request, actor, competition)
    result = orchestrator.settle_payouts(competition_id)
    if result is None:
        raise _not_found(competition_id)
    return result


@router.get("/{competition_id}/rewards", response_model=CompetitionRewardsResponse, response_model_exclude_none=True)
def get_competition_rewards(
    competition_id: str,
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionRewardsResponse:
    result = orchestrator.rewards(competition_id)
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


@router.post("/{competition_id}/seed", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def seed_competition(
    competition_id: str,
    payload: CompetitionSeedRequest,
    _: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.seed_competition(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/launch", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def launch_competition(
    competition_id: str,
    request: Request,
    actor: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    competition = orchestrator.session.get(Competition, competition_id)
    if competition is None:
        raise _not_found(competition_id)
    _require_manage_competitions_or_creator(request, actor, competition)
    result = _handle_competition_errors(lambda: orchestrator.launch_competition(competition_id))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/advance", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def advance_competition(
    competition_id: str,
    payload: CompetitionAdvanceRequest,
    _: User = Depends(get_current_user),
    orchestrator: CompetitionOrchestrator = Depends(get_competition_orchestrator),
) -> CompetitionSummaryView:
    result = _handle_competition_errors(lambda: orchestrator.advance_competition(competition_id, payload))
    if result is None:
        raise _not_found(competition_id)
    return result


@router.post("/{competition_id}/finalize", response_model=CompetitionSummaryView, response_model_exclude_none=True)
def finalize_competition(
    competition_id: str,
    payload: CompetitionFinalizeRequest,
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
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


@router.post(
    "/{competition_id}/matches/{match_id}/events",
    response_model=CompetitionMatchEventView,
    status_code=status.HTTP_201_CREATED,
)
def record_match_event(
    competition_id: str,
    match_id: str,
    payload: CompetitionMatchEventRequest,
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
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
