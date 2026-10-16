from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.access_control.schemas import (
    AccessAuditLogView,
    OrganizationCreateRequest,
    OrganizationCreateResponse,
    OrganizationInviteAcceptRequest,
    OrganizationInviteRequest,
    OrganizationInviteView,
    OrganizationMembershipView,
    OrganizationSummaryView,
)
from app.access_control.service import AccessControlError, AccessControlService, InviteExpiredError, InviteMismatchError, UserAccessContext, user_has_bound_organization_access
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.access_control import Organization, OrganizationInvite, OrganizationType
from app.models.user import User

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def _membership_view(context) -> OrganizationMembershipView:
    return OrganizationMembershipView(
        id=context.membership_id,
        organization_id=context.organization_id,
        organization_name=context.organization_name,
        organization_type=context.organization_type,
        role=context.role,
        is_primary=context.is_primary,
        permissions=list(context.permissions),
    )


def _organization_view(organization: Organization) -> OrganizationSummaryView:
    return OrganizationSummaryView(
        id=organization.id,
        name=organization.name,
        organization_type=organization.organization_type,
        club_profile_id=organization.club_profile_id,
    )


def _invite_view(invite: OrganizationInvite, organization: Organization) -> OrganizationInviteView:
    return OrganizationInviteView(
        id=invite.id,
        organization_id=organization.id,
        organization_name=organization.name,
        organization_type=organization.organization_type,
        email=invite.email,
        role=invite.role,
        invite_code=invite.invite_code,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
    )


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, InviteExpiredError):
        return HTTPException(status_code=status.HTTP_410_GONE, detail=str(error))
    if isinstance(error, InviteMismatchError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, AccessControlError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/me", response_model=list[OrganizationMembershipView])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[OrganizationMembershipView]:
    context: UserAccessContext = AccessControlService(session).bind_user_access_context(current_user)
    return [_membership_view(item) for item in context.memberships]


@router.post("", response_model=OrganizationCreateResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrganizationCreateResponse:
    if payload.organization_type != OrganizationType.AGENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="club_organizations_are_created_from_club_creation",
        )
    service = AccessControlService(session)
    try:
        organization, membership = service.create_agency_organization(name=payload.name, creator=current_user)
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    context = service.bind_user_access_context(current_user)
    membership_view = next(
        (_membership_view(item) for item in context.memberships if item.membership_id == membership.id),
        OrganizationMembershipView(
            id=membership.id,
            organization_id=organization.id,
            organization_name=organization.name,
            organization_type=organization.organization_type,
            role=membership.role,
            is_primary=membership.is_primary,
            permissions=list(service.permissions_for_role(membership.role)),
        ),
    )
    return OrganizationCreateResponse(
        organization=_organization_view(organization),
        membership=membership_view,
    )


@router.post("/{organization_id}/invite", response_model=OrganizationInviteView, status_code=status.HTTP_201_CREATED)
def invite_user_to_organization(
    organization_id: str,
    payload: OrganizationInviteRequest,
    admin_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> OrganizationInviteView:
    service = AccessControlService(session)
    try:
        invite = service.invite_user_to_organization(
            organization_id=organization_id,
            email=payload.email,
            role=payload.role,
            invited_by=admin_user,
        )
        organization = session.get(Organization, organization_id)
        assert organization is not None
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return _invite_view(invite, organization)


@router.post("/invites/accept", response_model=OrganizationMembershipView)
def accept_organization_invite(
    payload: OrganizationInviteAcceptRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrganizationMembershipView:
    service = AccessControlService(session)
    try:
        _invite, membership, organization = service.accept_invite(
            invite_code=payload.invite_code,
            user=current_user,
        )
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error

    context = service.bind_user_access_context(current_user)
    for item in context.memberships:
        if item.membership_id == membership.id:
            return _membership_view(item)
    return OrganizationMembershipView(
        id=membership.id,
        organization_id=organization.id,
        organization_name=organization.name,
        organization_type=organization.organization_type,
        role=membership.role,
        is_primary=membership.is_primary,
        permissions=list(service.permissions_for_role(membership.role)),
    )


@router.get("/{organization_id}/audit-log", response_model=list[AccessAuditLogView])
def list_organization_audit_log(
    organization_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[AccessAuditLogView]:
    if not user_has_bound_organization_access(current_user, organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="organization_access_required")
    return [
        AccessAuditLogView.model_validate(item)
        for item in AccessControlService(session).list_audit_logs(organization_id=organization_id, limit=limit)
    ]


__all__ = ["router"]
