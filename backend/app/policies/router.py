from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.base import utcnow
from app.models.user import User
from app.policies.schemas import (
    AdminRegionOverrideRequest,
    CountryFeaturePolicyAdminSummary,
    CountryFeaturePolicyResponse,
    CountryFeaturePolicyUpsertRequest,
    PolicyAcceptanceRequest,
    PolicyAcceptanceResponse,
    PolicyAcceptanceSummary,
    PolicyDocumentDetail,
    PolicyDocumentSummary,
    PolicyDocumentVersionSummary,
    PolicyDocumentVersionUpsertRequest,
    PolicyRequirementSummary,
    UserRegionProfileView,
    UserRegionUpdateRequest,
    UserComplianceStatus,
)
from app.policies.service import PolicyService
from app.risk_ops_engine.service import RiskOpsService

router = APIRouter(prefix="/policies", tags=["policies"])
admin_router = APIRouter(prefix="/admin/policies", tags=["admin-policies"])


def _map_version(version) -> PolicyDocumentVersionSummary:
    return PolicyDocumentVersionSummary(
        id=version.id,
        version_label=version.version_label,
        effective_at=version.effective_at,
        published_at=version.published_at,
        changelog=version.changelog,
    )


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _map_summary(document) -> PolicyDocumentSummary:
    now = utcnow()
    latest_version = next(
        (
            version
            for version in document.versions
            if version.is_published and (_coerce_utc(version.effective_at) or now) <= now
        ),
        None,
    )
    return PolicyDocumentSummary(
        id=document.id,
        document_key=document.document_key,
        title=document.title,
        is_mandatory=document.is_mandatory,
        active=document.active,
        latest_version=_map_version(latest_version) if latest_version else None,
    )


def _map_region_profile(profile, *, override_metadata: dict | None = None) -> UserRegionProfileView:
    now = utcnow()
    locked_until = _coerce_utc(profile.locked_until)
    locked = bool(profile.permanent_locked or (locked_until and now < locked_until))
    next_change_eligible_at = None if profile.permanent_locked else locked_until
    return UserRegionProfileView(
        region_code=profile.region_code,
        current_region=profile.region_code,
        selected_at=profile.selected_at,
        last_changed_at=profile.last_changed_at,
        locked_until=locked_until,
        change_count=profile.change_count,
        permanent_locked=profile.permanent_locked,
        next_change_eligible_at=next_change_eligible_at,
        permanent_change_used=bool(profile.permanent_locked or (profile.change_count or 0) >= 1),
        locked=locked,
        override_metadata=override_metadata,
    )


@router.get("/documents", response_model=list[PolicyDocumentSummary])
def list_policy_documents(
    mandatory_only: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> list[PolicyDocumentSummary]:
    service = PolicyService(session)
    return [_map_summary(document) for document in service.list_documents(mandatory_only=mandatory_only)]


@router.get("/documents/{document_key}", response_model=PolicyDocumentDetail)
def get_policy_document(
    document_key: str,
    version_label: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> PolicyDocumentDetail:
    service = PolicyService(session)
    try:
        version = service.get_document(document_key, version_label=version_label)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    document = version.document
    return PolicyDocumentDetail(
        id=document.id,
        document_key=document.document_key,
        title=document.title,
        is_mandatory=document.is_mandatory,
        active=document.active,
        latest_version=_map_version(version),
        body_markdown=version.body_markdown,
    )


@router.post("/acceptances", response_model=PolicyAcceptanceResponse)
def accept_policy_document(
    payload: PolicyAcceptanceRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PolicyAcceptanceResponse:
    service = PolicyService(session)
    try:
        acceptance = service.accept_document(
            user_id=current_user.id,
            document_key=payload.document_key,
            version_label=payload.version_label,
            ip_address=payload.ip_address,
            device_id=payload.device_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    version = acceptance.document_version or service.get_document(payload.document_key, version_label=payload.version_label)
    return PolicyAcceptanceResponse(
        acceptance_id=acceptance.id,
        document_key=version.document.document_key,
        version_label=version.version_label,
        accepted_at=acceptance.accepted_at,
    )


@router.get("/me/acceptances", response_model=list[PolicyAcceptanceSummary])
def list_my_policy_acceptances(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[PolicyAcceptanceSummary]:
    service = PolicyService(session)
    records = service.list_acceptances(user_id=current_user.id)
    return [
        PolicyAcceptanceSummary(
            document_key=record.document_version.document.document_key,
            title=record.document_version.document.title,
            version_label=record.document_version.version_label,
            accepted_at=record.accepted_at,
        )
        for record in records
    ]


@router.get("/country/{country_code}", response_model=CountryFeaturePolicyResponse)
def get_country_feature_policy(country_code: str, session: Session = Depends(get_session)) -> CountryFeaturePolicyResponse:
    service = PolicyService(session)
    try:
        policy = service.get_country_policy(country_code)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CountryFeaturePolicyResponse.model_validate(policy, from_attributes=True)

@router.get("/me/requirements", response_model=list[PolicyRequirementSummary])
def list_my_policy_requirements(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[PolicyRequirementSummary]:
    service = PolicyService(session)
    missing = service.list_missing_acceptances(user_id=current_user.id)
    return [
        PolicyRequirementSummary(
            document_key=version.document.document_key,
            title=version.document.title,
            version_label=version.version_label,
            is_mandatory=version.document.is_mandatory,
            effective_at=version.effective_at,
        )
        for version in missing
    ]


@router.get("/me/region", response_model=UserRegionProfileView)
def get_my_region(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserRegionProfileView:
    service = PolicyService(session)
    profile = service.ensure_user_region_profile(
        user=current_user,
        region_code=service.resolve_country_code_for_user(user=current_user),
    )
    return _map_region_profile(profile)


@router.post("/me/region", response_model=UserRegionProfileView)
def update_my_region(
    payload: UserRegionUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserRegionProfileView:
    service = PolicyService(session)
    try:
        profile = service.change_user_region(user=current_user, region_code=payload.region_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return _map_region_profile(profile)


@router.get("/me/compliance", response_model=UserComplianceStatus)
def get_my_compliance_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserComplianceStatus:
    service = PolicyService(session)
    country_policy = service.get_country_policy_for_user(user=current_user)
    missing = service.list_missing_acceptances(user_id=current_user.id)
    return UserComplianceStatus(
        country_code=country_policy.country_code,
        country_policy_bucket=country_policy.bucket_type,
        deposits_enabled=country_policy.deposits_enabled,
        market_trading_enabled=country_policy.market_trading_enabled,
        platform_reward_withdrawals_enabled=country_policy.platform_reward_withdrawals_enabled,
        required_policy_acceptances_missing=len(missing),
        missing_policy_acceptances=[
            PolicyRequirementSummary(
                document_key=version.document.document_key,
                title=version.document.title,
                version_label=version.version_label,
                is_mandatory=version.document.is_mandatory,
                effective_at=version.effective_at,
            )
            for version in missing
        ],
        can_deposit=country_policy.deposits_enabled and not missing,
        can_withdraw_platform_rewards=country_policy.platform_reward_withdrawals_enabled and not missing,
        can_trade_market=country_policy.market_trading_enabled and not missing,
    )



@admin_router.post("/documents", response_model=PolicyDocumentDetail)
def admin_upsert_policy_document(
    payload: PolicyDocumentVersionUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PolicyDocumentDetail:
    service = PolicyService(session)
    version = service.upsert_document_version(payload=payload)
    RiskOpsService(session).log_audit(
        actor_user_id=actor.id,
        action_key="policy.document.version.upserted",
        resource_type="policy_document",
        resource_id=version.document.id if version.document else None,
        detail=f"Policy document {payload.document_key} {payload.version_label} upserted.",
        metadata_json={
            "document_key": payload.document_key,
            "version_label": payload.version_label,
            "is_published": bool(payload.is_published),
        },
    )
    session.commit()
    document = version.document
    return PolicyDocumentDetail(
        id=document.id,
        document_key=document.document_key,
        title=document.title,
        is_mandatory=document.is_mandatory,
        active=document.active,
        latest_version=_map_version(version),
        body_markdown=version.body_markdown,
    )


@admin_router.get("/country-policies", response_model=list[CountryFeaturePolicyAdminSummary])
def admin_list_country_policies(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[CountryFeaturePolicyAdminSummary]:
    service = PolicyService(session)
    return [CountryFeaturePolicyAdminSummary.model_validate(item, from_attributes=True) for item in service.list_country_policies()]


@admin_router.post("/country-policies", response_model=CountryFeaturePolicyAdminSummary)
def admin_upsert_country_policy(
    payload: CountryFeaturePolicyUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CountryFeaturePolicyAdminSummary:
    service = PolicyService(session)
    policy = service.upsert_country_policy(payload=payload)
    RiskOpsService(session).log_audit(
        actor_user_id=actor.id,
        action_key="policy.country.upserted",
        resource_type="country_policy",
        resource_id=policy.id,
        detail=f"Country policy {policy.country_code}:{policy.bucket_type} upserted.",
        metadata_json={
            "country_code": policy.country_code,
            "bucket_type": policy.bucket_type,
        },
    )
    session.commit()
    session.refresh(policy)
    return CountryFeaturePolicyAdminSummary.model_validate(policy, from_attributes=True)


@admin_router.post("/documents/versions", response_model=PolicyDocumentDetail)
def admin_upsert_policy_document_version(
    payload: PolicyDocumentVersionUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PolicyDocumentDetail:
    service = PolicyService(session)
    version = service.upsert_document_version(payload=payload)
    RiskOpsService(session).log_audit(
        actor_user_id=actor.id,
        action_key="policy.document.version.upserted",
        resource_type="policy_document",
        resource_id=version.document.id if version.document else None,
        detail=f"Policy document {payload.document_key} {payload.version_label} upserted.",
        metadata_json={
            "document_key": payload.document_key,
            "version_label": payload.version_label,
            "is_published": bool(payload.is_published),
        },
    )
    session.commit()
    version = service.get_document(payload.document_key, version_label=payload.version_label, include_unpublished=True)
    document = version.document
    return PolicyDocumentDetail(
        id=document.id,
        document_key=document.document_key,
        title=document.title,
        is_mandatory=document.is_mandatory,
        active=document.active,
        latest_version=_map_version(version),
        body_markdown=version.body_markdown,
    )


@admin_router.post("/regions/override", response_model=UserRegionProfileView)
def admin_override_region(
    payload: AdminRegionOverrideRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> UserRegionProfileView:
    service = PolicyService(session)
    profile = service.override_user_region(
        user_id=payload.user_id,
        region_code=payload.region_code,
        actor_user_id=actor.id,
        reason=payload.reason,
    )
    session.commit()
    return _map_region_profile(
        profile,
        override_metadata={"actor_user_id": actor.id, "reason": payload.reason, "overridden_at": utcnow().isoformat()},
    )
