from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.user import User
from backend.app.policies.schemas import (
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
    UserComplianceStatus,
)
from backend.app.policies.service import PolicyService

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


def _map_summary(document) -> PolicyDocumentSummary:
    latest_version = next((version for version in document.versions if version.is_published), None)
    return PolicyDocumentSummary(
        id=document.id,
        document_key=document.document_key,
        title=document.title,
        is_mandatory=document.is_mandatory,
        active=document.active,
        latest_version=_map_version(latest_version) if latest_version else None,
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
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PolicyDocumentDetail:
    service = PolicyService(session)
    version = service.upsert_document_version(payload=payload)
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
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CountryFeaturePolicyAdminSummary:
    service = PolicyService(session)
    policy = service.upsert_country_policy(payload=payload)
    session.commit()
    session.refresh(policy)
    return CountryFeaturePolicyAdminSummary.model_validate(policy, from_attributes=True)
