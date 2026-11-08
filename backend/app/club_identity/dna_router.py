from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.access_control.dependencies import require_bound_organization_access
from app.auth.dependencies import get_current_user
from app.club_identity.dna_schemas import (
    ClubDNAPolicyPatch,
    ClubDNAPolicyView,
    ClubGovernanceExceptionCreateRequest,
    ClubGovernanceExceptionView,
)
from app.db import get_session
from app.models.access_control import OrganizationRole
from app.models.club_profile import ClubProfile
from app.models.user import User, UserRole
from app.services.club_governance_policy import ClubGovernancePolicyService
from app.club_identity.ai_studio_service import ClubIdentityStudioService
from dataclasses import asdict

router = APIRouter(prefix="/api/clubs", tags=["club-dna-governance"])


class StudioRecommendationRequest(BaseModel):
    club_name: str
    country_code: str | None = "FRA"
    city_name: str | None = "Lyon"
    preferred_style: str = "traditional"
    recruitment_focus: str = "youth"
    preferred_age_bracket: str = "U23"
    nationality_focus: str = "preferred"


class StudioConversationalEditRequest(BaseModel):
    current_kit: dict[str, Any]
    current_crest: dict[str, Any]
    instruction: str


@router.post("/studio/recommend")
def recommend_club_identity(payload: StudioRecommendationRequest) -> dict[str, Any]:
    service = ClubIdentityStudioService()
    bundle = service.generate_recommendation_bundle(
        club_name=payload.club_name,
        country_code=payload.country_code,
        city_name=payload.city_name,
        preferred_style=payload.preferred_style,
        recruitment_focus=payload.recruitment_focus,
        preferred_age_bracket=payload.preferred_age_bracket,
        nationality_focus=payload.nationality_focus,
    )
    return asdict(bundle)


@router.post("/studio/edit")
def edit_club_identity_conversational(payload: StudioConversationalEditRequest) -> dict[str, Any]:
    service = ClubIdentityStudioService()
    return service.apply_conversational_edit(
        current_kit=payload.current_kit,
        current_crest=payload.current_crest,
        instruction=payload.instruction,
    )


require_club_write_access = require_bound_organization_access(
    OrganizationRole.CLUB, forbidden_detail="club_access_required"
)


def _require_club_owner(club_id: str, *, session: Session, current_user: User) -> ClubProfile:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found.")
    if club.owner_user_id != current_user.id and current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this club.")
    return club


class PolicyEvaluationPreflightRequest(BaseModel):
    player_id: str | None = None
    player_name: str | None = None
    nationality: str | None = None
    age: int | None = None
    dual_nationalities: list[str] | None = None


class PolicyEvaluationPreflightResponse(BaseModel):
    is_eligible: bool
    policy_violated: str | None = None
    violation_reason: str | None = None
    exception_permitted: bool = False
    has_approved_exception: bool = False
    exception_id: str | None = None


@router.get("/{club_id}/dna", response_model=ClubDNAPolicyView)
def get_club_dna(
    club_id: str,
    session: Session = Depends(get_session),
) -> ClubDNAPolicyView:
    policy = ClubGovernancePolicyService(session).get_or_create_policy(club_id)
    return ClubDNAPolicyView(
        club_id=policy.club_id,
        primary_philosophy=policy.primary_philosophy,
        secondary_philosophies=policy.secondary_philosophies or [],
        nationality_mode=policy.nationality_mode,
        target_nationalities=policy.target_nationalities or [],
        allow_dual_nationality=policy.allow_dual_nationality,
        age_mode=policy.age_mode,
        preferred_max_age=policy.preferred_max_age,
        allow_age_exceptions=policy.allow_age_exceptions,
        transfer_strategy=policy.transfer_strategy,
        financial_philosophy=policy.financial_philosophy,
        club_vision_narrative=policy.club_vision_narrative,
        metadata=dict(policy.metadata_json or {}),
    )


@router.patch("/{club_id}/dna", response_model=ClubDNAPolicyView)
def patch_club_dna(
    club_id: str,
    payload: ClubDNAPolicyPatch,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _: User = Depends(require_club_write_access),
) -> ClubDNAPolicyView:
    _require_club_owner(club_id, session=session, current_user=current_user)
    service = ClubGovernancePolicyService(session)
    updates = payload.model_dump(exclude_unset=True)
    try:
        policy = service.update_policy(club_id, updates)
        session.commit()
        session.refresh(policy)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

    return ClubDNAPolicyView(
        club_id=policy.club_id,
        primary_philosophy=policy.primary_philosophy,
        secondary_philosophies=policy.secondary_philosophies or [],
        nationality_mode=policy.nationality_mode,
        target_nationalities=policy.target_nationalities or [],
        allow_dual_nationality=policy.allow_dual_nationality,
        age_mode=policy.age_mode,
        preferred_max_age=policy.preferred_max_age,
        allow_age_exceptions=policy.allow_age_exceptions,
        transfer_strategy=policy.transfer_strategy,
        financial_philosophy=policy.financial_philosophy,
        club_vision_narrative=policy.club_vision_narrative,
        metadata=dict(policy.metadata_json or {}),
    )


@router.post("/{club_id}/governance/evaluate", response_model=PolicyEvaluationPreflightResponse)
def evaluate_recruitment_preflight(
    club_id: str,
    payload: PolicyEvaluationPreflightRequest,
    session: Session = Depends(get_session),
) -> PolicyEvaluationPreflightResponse:
    service = ClubGovernancePolicyService(session)
    result = service.evaluate_player_recruitment_eligibility(
        club_id,
        player_id=payload.player_id,
        player_name=payload.player_name,
        nationality=payload.nationality,
        age=payload.age,
        dual_nationalities=payload.dual_nationalities,
    )
    return PolicyEvaluationPreflightResponse(
        is_eligible=result.is_eligible,
        policy_violated=result.policy_violated,
        violation_reason=result.violation_reason,
        exception_permitted=result.exception_permitted,
        has_approved_exception=result.has_approved_exception,
        exception_id=result.exception_id,
    )


@router.get("/{club_id}/governance/exceptions", response_model=list[ClubGovernanceExceptionView])
def list_governance_exceptions(
    club_id: str,
    session: Session = Depends(get_session),
) -> list[ClubGovernanceExceptionView]:
    service = ClubGovernancePolicyService(session)
    exceptions = service.list_exceptions(club_id)
    return [
        ClubGovernanceExceptionView(
            id=item.id,
            club_id=item.club_id,
            policy_type=item.policy_type,
            player_id=item.player_id,
            player_name=item.player_name,
            player_nationality=item.player_nationality,
            player_age=item.player_age,
            reason=item.reason,
            approved_by_user_id=item.approved_by_user_id,
            status=item.status,
            approved_at=item.approved_at,
            metadata=dict(item.metadata_json or {}),
        )
        for item in exceptions
    ]


@router.post(
    "/{club_id}/governance/exceptions", response_model=ClubGovernanceExceptionView, status_code=status.HTTP_201_CREATED
)
def approve_governance_exception(
    club_id: str,
    payload: ClubGovernanceExceptionCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _: User = Depends(require_club_write_access),
) -> ClubGovernanceExceptionView:
    _require_club_owner(club_id, session=session, current_user=current_user)
    service = ClubGovernancePolicyService(session)
    try:
        exception = service.approve_exception(
            club_id,
            player_id=payload.player_id,
            player_name=payload.player_name,
            policy_type=payload.policy_type,
            reason=payload.reason,
            user_id=current_user.id,
            player_nationality=payload.player_nationality,
            player_age=payload.player_age,
        )
        session.commit()
        session.refresh(exception)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

    return ClubGovernanceExceptionView(
        id=exception.id,
        club_id=exception.club_id,
        policy_type=exception.policy_type,
        player_id=exception.player_id,
        player_name=exception.player_name,
        player_nationality=exception.player_nationality,
        player_age=exception.player_age,
        reason=exception.reason,
        approved_by_user_id=exception.approved_by_user_id,
        status=exception.status,
        approved_at=exception.approved_at,
        metadata=dict(exception.metadata_json or {}),
    )


@router.get("/{club_id}/dna/squad-alignment")
def get_club_dna_squad_alignment(
    club_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return ClubGovernancePolicyService(session).generate_squad_dna_recommendations(club_id)
