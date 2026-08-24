from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.federations.schemas import (
    FederationCreateRequest,
    FederationDashboardView,
    FederationGovernanceView,
    FederationJobsRunView,
    FederationLeagueCreateRequest,
    FederationLeagueView,
    FederationMembershipCreateRequest,
    FederationMembershipView,
    FederationNarrativeView,
    NationalAssociationProfileView,
    NationalEligibilityReviewRequest,
    NationalEligibilityReviewView,
    FederationProposalCreateRequest,
    FederationProposalView,
    FederationRankingItemView,
    FederationRevenueDistributionRequest,
    RegionalTournamentView,
    FederationSanctionCreateRequest,
    FederationSanctionView,
    FederationTreasuryEntryView,
    FederationValidateActionRequest,
    FederationValidationResultView,
    FederationView,
    FederationVoteCreateRequest,
    FederationVoteView,
)
from app.federations.service import (
    FederationError,
    FederationNotFoundError,
    FederationService,
    FederationValidationError,
)
from app.models.user import User

router = APIRouter(prefix="/federations", tags=["federations"])
admin_router = APIRouter(prefix="/admin/federations", tags=["admin-federations"])


def _service(session: Session = Depends(get_session)) -> FederationService:
    return FederationService(session=session)


def _raise(exc: FederationError) -> Never:
    if isinstance(exc, FederationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, FederationValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("", response_model=list[FederationView])
def list_federations(service: FederationService = Depends(_service)) -> list[FederationView]:
    return [FederationView.model_validate(item, from_attributes=True) for item in service.list_federations()]


@router.post("", response_model=FederationView, status_code=status.HTTP_201_CREATED)
def create_federation(
    payload: FederationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(_service),
) -> FederationView:
    try:
        federation = service.create_federation(
            actor=current_user,
            name=payload.name,
            structure_json=payload.structure_json,
            rules_json=payload.rules_json,
            is_public=payload.is_public,
            default_reality_mode=payload.default_reality_mode,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(federation)
    return FederationView.model_validate(federation, from_attributes=True)


@router.get("/rankings", response_model=list[FederationRankingItemView])
def get_rankings(service: FederationService = Depends(_service)) -> list[FederationRankingItemView]:
    return [FederationRankingItemView.model_validate(item) for item in service.refresh_rankings()]


@router.get("/regional-tournaments", response_model=list[RegionalTournamentView])
def list_regional_tournaments(service: FederationService = Depends(_service)) -> list[RegionalTournamentView]:
    return [RegionalTournamentView.model_validate(item) for item in service.list_regional_tournaments()]


@router.get("/national-associations/{country_code}", response_model=NationalAssociationProfileView)
def get_national_association(
    country_code: str,
    service: FederationService = Depends(_service),
) -> NationalAssociationProfileView:
    try:
        payload = service.build_national_association_profile(country_code)
    except FederationError as exc:
        _raise(exc)
    return NationalAssociationProfileView.model_validate(payload)


@router.post("/national-associations/{country_code}/eligibility-review", response_model=NationalEligibilityReviewView)
def review_national_eligibility(
    country_code: str,
    payload: NationalEligibilityReviewRequest,
    _current_user: User = Depends(get_current_admin),
    service: FederationService = Depends(_service),
) -> NationalEligibilityReviewView:
    try:
        result = service.review_national_eligibility(
            country_code=country_code,
            player_id=payload.player_id,
            club_id=payload.club_id,
            competition_id=payload.competition_id,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    return NationalEligibilityReviewView.model_validate(result)


@router.get("/{federation_id}", response_model=FederationDashboardView)
def get_federation_dashboard(
    federation_id: str,
    service: FederationService = Depends(_service),
) -> FederationDashboardView:
    try:
        payload = service.build_dashboard(federation_id)
    except FederationError as exc:
        _raise(exc)
    return FederationDashboardView(
        leagues=[FederationLeagueView.model_validate(item, from_attributes=True) for item in payload["leagues"]],
        rules=payload["rules"],
        members=payload["members"],
        reputation=payload["reputation"],
    )


@router.get("/{federation_id}/governance", response_model=FederationGovernanceView)
def get_governance_view(
    federation_id: str,
    service: FederationService = Depends(_service),
) -> FederationGovernanceView:
    try:
        payload = service.build_governance_view(federation_id)
    except FederationError as exc:
        _raise(exc)
    return FederationGovernanceView(
        proposals=[FederationProposalView.model_validate(item, from_attributes=True) for item in payload["proposals"]],
        votes=[FederationVoteView.model_validate(item, from_attributes=True) for item in payload["votes"]],
        sanctions=[FederationSanctionView.model_validate(item, from_attributes=True) for item in payload["sanctions"]],
    )


@router.get("/{federation_id}/leagues", response_model=list[FederationLeagueView])
def list_leagues(federation_id: str, service: FederationService = Depends(_service)) -> list[FederationLeagueView]:
    try:
        leagues = service.list_leagues(federation_id)
    except FederationError as exc:
        _raise(exc)
    return [FederationLeagueView.model_validate(item, from_attributes=True) for item in leagues]


@router.post("/{federation_id}/leagues", response_model=FederationLeagueView, status_code=status.HTTP_201_CREATED)
def create_league(
    federation_id: str,
    payload: FederationLeagueCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(_service),
) -> FederationLeagueView:
    try:
        league = service.create_league(
            actor=current_user,
            federation_id=federation_id,
            name=payload.name,
            competition_type=payload.competition_type,
            format=payload.format,
            divisions_json=payload.divisions_json,
            promotion_relegation_rules_json=payload.promotion_relegation_rules_json,
            entry_requirements_json=payload.entry_requirements_json,
            governance_rules_override_json=payload.governance_rules_override_json,
            season_label=payload.season_label,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(league)
    return FederationLeagueView.model_validate(league, from_attributes=True)


@router.get("/{federation_id}/memberships", response_model=list[FederationMembershipView])
def list_memberships(
    federation_id: str, service: FederationService = Depends(_service)
) -> list[FederationMembershipView]:
    try:
        memberships = service.list_memberships(federation_id)
    except FederationError as exc:
        _raise(exc)
    return [FederationMembershipView.model_validate(item, from_attributes=True) for item in memberships]


@router.post(
    "/{federation_id}/memberships", response_model=FederationMembershipView, status_code=status.HTTP_201_CREATED
)
def create_membership(
    federation_id: str,
    payload: FederationMembershipCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(_service),
) -> FederationMembershipView:
    try:
        membership = service.create_membership(
            actor=current_user,
            federation_id=federation_id,
            club_id=payload.club_id,
            user_id=payload.user_id,
            role=payload.role,
            auto_activate=payload.auto_activate,
            entry_requirements_json=payload.entry_requirements_json,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(membership)
    return FederationMembershipView.model_validate(membership, from_attributes=True)


@router.post("/{federation_id}/proposals", response_model=FederationProposalView, status_code=status.HTTP_201_CREATED)
def create_proposal(
    federation_id: str,
    payload: FederationProposalCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(_service),
) -> FederationProposalView:
    try:
        proposal = service.create_proposal(
            actor=current_user,
            federation_id=federation_id,
            league_id=payload.league_id,
            proposal_type=payload.proposal_type,
            title=payload.title,
            summary=payload.summary,
            payload_json=payload.payload_json,
            voting_ends_at=payload.voting_ends_at,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(proposal)
    return FederationProposalView.model_validate(proposal, from_attributes=True)


@router.post("/proposals/{proposal_id}/votes", response_model=FederationVoteView)
def cast_vote(
    proposal_id: str,
    payload: FederationVoteCreateRequest,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(_service),
) -> FederationVoteView:
    try:
        _proposal, vote = service.cast_vote(
            actor=current_user,
            proposal_id=proposal_id,
            vote_type=payload.vote_type,
            comment=payload.comment,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(vote)
    return FederationVoteView.model_validate(vote, from_attributes=True)


@router.post("/{federation_id}/sanctions", response_model=FederationSanctionView, status_code=status.HTTP_201_CREATED)
def apply_sanction(
    federation_id: str,
    payload: FederationSanctionCreateRequest,
    current_user: User = Depends(get_current_admin),
    service: FederationService = Depends(_service),
) -> FederationSanctionView:
    try:
        sanction = service.apply_sanction(
            actor=current_user,
            federation_id=federation_id,
            league_id=payload.league_id,
            club_id=payload.club_id,
            player_id=payload.player_id,
            sanction_type=payload.sanction_type,
            reason=payload.reason,
            fine_amount=payload.fine_amount,
            points_deduction=payload.points_deduction,
            suspension_matches=payload.suspension_matches,
            ends_at=payload.ends_at,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(sanction)
    return FederationSanctionView.model_validate(sanction, from_attributes=True)


@router.post("/{federation_id}/validate-action", response_model=FederationValidationResultView)
def validate_action(
    federation_id: str,
    payload: FederationValidateActionRequest,
    service: FederationService = Depends(_service),
) -> FederationValidationResultView:
    try:
        result = service.validate_action(
            federation_id=federation_id,
            league_id=payload.league_id,
            action_type=payload.action_type,
            club_id=payload.club_id,
            player_id=payload.player_id,
            proposed_fee=payload.proposed_fee,
            proposed_wage=payload.proposed_wage,
            source_reference=payload.source_reference,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    return FederationValidationResultView.model_validate(result)


@router.post("/{federation_id}/treasury/distribute", response_model=FederationTreasuryEntryView)
def distribute_revenue(
    federation_id: str,
    payload: FederationRevenueDistributionRequest,
    current_user: User = Depends(get_current_admin),
    service: FederationService = Depends(_service),
) -> FederationTreasuryEntryView:
    del current_user
    try:
        entry = service.distribute_revenue(
            federation_id=federation_id,
            source_type=payload.source_type,
            source_reference=payload.source_reference,
            gross_amount=payload.gross_amount,
            federation_share_bps=payload.federation_share_bps,
            metadata_json=payload.metadata_json,
        )
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(entry)
    return FederationTreasuryEntryView.model_validate(entry, from_attributes=True)


@router.get("/{federation_id}/narratives", response_model=list[FederationNarrativeView])
def get_narratives(
    federation_id: str,
    service: FederationService = Depends(_service),
) -> list[FederationNarrativeView]:
    try:
        items = service.generate_narratives(federation_id)
    except FederationError as exc:
        _raise(exc)
    return [FederationNarrativeView.model_validate(item, from_attributes=True) for item in items]


@admin_router.post("/run-jobs", response_model=FederationJobsRunView)
def run_background_jobs(
    _: User = Depends(get_current_admin),
    service: FederationService = Depends(_service),
) -> FederationJobsRunView:
    try:
        result = service.run_background_jobs_once()
    except FederationError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    return FederationJobsRunView.model_validate(result)
