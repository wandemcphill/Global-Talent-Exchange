from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.governance_engine.schemas import (
    GovernanceClubPanelResponse,
    GovernanceOverviewResponse,
    GovernanceProposalCreateRequest,
    GovernanceProposalDetailResponse,
    GovernanceProposalListResponse,
    GovernanceProposalStatusRequest,
    GovernanceProposalView,
    GovernanceVoteRequest,
    GovernanceVoteResponse,
    GovernanceVoteView,
)
from app.governance_engine.service import GovernanceEngineError, GovernanceEngineService
from app.models.user import User

router = APIRouter(prefix="/governance", tags=["governance"])
admin_router = APIRouter(prefix="/admin/governance", tags=["admin-governance"])


def _proposal_view(item) -> GovernanceProposalView:
    return GovernanceProposalView.model_validate(item, from_attributes=True)


def _vote_view(item) -> GovernanceVoteView:
    return GovernanceVoteView.model_validate(item, from_attributes=True)


@router.get("/proposals", response_model=GovernanceProposalListResponse)
def list_proposals(club_id: str | None = None, session: Session = Depends(get_session)) -> GovernanceProposalListResponse:
    service = GovernanceEngineService(session)
    return GovernanceProposalListResponse(proposals=[_proposal_view(item) for item in service.list_proposals(club_id=club_id)])


@router.get("/me/overview", response_model=GovernanceOverviewResponse)
def my_governance_overview(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> GovernanceOverviewResponse:
    data = GovernanceEngineService(session).overview_for_user(user=user)
    return GovernanceOverviewResponse(**data)


@router.get("/clubs/{club_id}/panel", response_model=GovernanceClubPanelResponse)
def get_club_governance_panel(
    club_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GovernanceClubPanelResponse:
    service = GovernanceEngineService(session)
    try:
        payload = service.build_club_panel(club_id=club_id, user=user)
    except GovernanceEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GovernanceClubPanelResponse(**payload)


@router.post("/proposals", response_model=GovernanceProposalView)
def create_proposal(payload: GovernanceProposalCreateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> GovernanceProposalView:
    service = GovernanceEngineService(session)
    try:
        proposal = service.create_proposal(
            proposer=user,
            club_id=payload.club_id,
            scope=payload.scope,
            title=payload.title,
            summary=payload.summary,
            category=payload.category,
            minimum_tokens_required=payload.minimum_tokens_required,
            quorum_token_weight=payload.quorum_token_weight,
            voting_ends_at_iso=payload.voting_ends_at_iso,
            metadata_json=payload.metadata_json,
        )
        session.commit()
        session.refresh(proposal)
        return _proposal_view(proposal)
    except GovernanceEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/proposals/{proposal_id}", response_model=GovernanceProposalDetailResponse)
def get_proposal(proposal_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> GovernanceProposalDetailResponse:
    service = GovernanceEngineService(session)
    try:
        proposal = service.get_proposal(proposal_id)
        eligible, reason, _ = service.eligibility_for(proposal=proposal, user=user)
    except GovernanceEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    votes = service.list_votes(proposal_id)
    my_vote = service.my_vote(proposal_id=proposal_id, user_id=user.id)
    return GovernanceProposalDetailResponse(
        proposal=_proposal_view(proposal),
        votes=[_vote_view(item) for item in votes],
        my_vote=_vote_view(my_vote) if my_vote else None,
        user_eligible=eligible,
        eligibility_reason=reason,
    )


@router.post("/proposals/{proposal_id}/vote", response_model=GovernanceVoteResponse)
def cast_vote(proposal_id: str, payload: GovernanceVoteRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> GovernanceVoteResponse:
    service = GovernanceEngineService(session)
    try:
        proposal, vote = service.cast_vote(proposal_id=proposal_id, voter=user, choice=payload.choice, comment=payload.comment)
        session.commit()
        session.refresh(proposal)
        session.refresh(vote)
        return GovernanceVoteResponse(
            proposal=_proposal_view(proposal),
            vote=_vote_view(vote),
            summary=f"Vote recorded with weight {vote.influence_weight}.",
        )
    except GovernanceEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post("/proposals/{proposal_id}/status", response_model=GovernanceProposalView)
def close_or_update_proposal(proposal_id: str, payload: GovernanceProposalStatusRequest, _: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> GovernanceProposalView:
    service = GovernanceEngineService(session)
    try:
        proposal = service.close_proposal(proposal_id=proposal_id, status=payload.status, result_summary=payload.result_summary)
        session.commit()
        session.refresh(proposal)
        return _proposal_view(proposal)
    except GovernanceEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
