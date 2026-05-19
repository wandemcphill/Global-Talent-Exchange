from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_control import (
    AccessAuditLog,
    Organization,
    OrganizationInvite,
    OrganizationMembership,
    OrganizationRole,
    OrganizationType,
    PlayerOwnership,
)
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.user import PublicAccountType, User, UserRole

ACCESS_CONTEXT_ATTR = "_access_control_context"
ACCESS_ROLE_MAP_ATTR = "_access_control_roles_by_org"
ACCESS_EFFECTIVE_ROLE_ATTR = "_access_control_effective_role"
ACCESS_ACTIVE_ORG_ATTR = "_access_control_active_organization_id"

INVITE_TTL_DAYS = 7

ROLE_PERMISSION_MATRIX: dict[OrganizationRole, tuple[str, ...]] = {
    OrganizationRole.ADMIN: (
        "players.view",
        "players.shortlist",
        "pipeline.manage",
        "contact.manage",
        "users.manage",
        "audit.view",
    ),
    OrganizationRole.SCOUT: (
        "players.view",
        "players.shortlist",
        "pipeline.manage",
        "contact.manage",
    ),
    OrganizationRole.CLUB: (
        "players.view",
        "pipeline.manage",
        "contact.manage",
    ),
    OrganizationRole.AGENT: (
        "players.view",
        "contact.manage",
        "players.manage_own",
    ),
}

MEMBERSHIP_TO_USER_ROLE: dict[OrganizationRole, UserRole] = {
    OrganizationRole.ADMIN: UserRole.ADMIN,
    OrganizationRole.SCOUT: UserRole.SCOUT,
    OrganizationRole.CLUB: UserRole.CLUB,
    OrganizationRole.AGENT: UserRole.AGENT,
}


class AccessControlError(ValueError):
    pass


class InviteExpiredError(AccessControlError):
    pass


class InviteMismatchError(AccessControlError):
    pass


@dataclass(frozen=True, slots=True)
class MembershipAccessContext:
    membership_id: str
    organization_id: str
    organization_name: str
    organization_type: OrganizationType
    role: OrganizationRole
    is_primary: bool
    permissions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UserAccessContext:
    effective_role: UserRole
    active_organization_id: str | None
    active_organization_name: str | None
    active_organization_type: OrganizationType | None
    permissions: tuple[str, ...]
    memberships: tuple[MembershipAccessContext, ...]


def bound_effective_role(user: object) -> UserRole | None:
    effective_role = getattr(user, ACCESS_EFFECTIVE_ROLE_ATTR, None)
    if isinstance(effective_role, UserRole):
        return effective_role
    raw_role = getattr(user, "role", None)
    if isinstance(raw_role, UserRole):
        return raw_role
    if isinstance(raw_role, str):
        try:
            return UserRole(raw_role)
        except ValueError:
            return None
    return None


def bound_organization_role(user: object, organization_id: str) -> OrganizationRole | None:
    raw_mapping = getattr(user, ACCESS_ROLE_MAP_ATTR, None)
    if isinstance(raw_mapping, dict):
        raw_role = raw_mapping.get(organization_id)
        if isinstance(raw_role, OrganizationRole):
            return raw_role
        if isinstance(raw_role, str):
            try:
                return OrganizationRole(raw_role)
            except ValueError:
                return None
    context = getattr(user, ACCESS_CONTEXT_ATTR, None)
    memberships = getattr(context, "memberships", ())
    for membership in memberships:
        if getattr(membership, "organization_id", None) != organization_id:
            continue
        role = getattr(membership, "role", None)
        if isinstance(role, OrganizationRole):
            return role
        if isinstance(role, str):
            try:
                return OrganizationRole(role)
            except ValueError:
                return None
    return None


def user_has_bound_organization_access(
    user: object,
    organization_id: str,
    *,
    allowed_roles: set[OrganizationRole] | None = None,
) -> bool:
    effective_role = bound_effective_role(user)
    if effective_role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        return True
    org_role = bound_organization_role(user, organization_id)
    if org_role is None:
        return False
    if allowed_roles is None:
        return True
    return org_role in allowed_roles


class AccessControlService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def permissions_for_role(self, role: OrganizationRole) -> tuple[str, ...]:
        return ROLE_PERMISSION_MATRIX.get(role, tuple())

    def list_memberships_for_user(self, user_id: str) -> tuple[MembershipAccessContext, ...]:
        rows = self.session.execute(
            select(OrganizationMembership, Organization)
            .join(Organization, Organization.id == OrganizationMembership.organization_id)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(OrganizationMembership.is_primary.desc(), OrganizationMembership.created_at.asc())
        ).all()
        return tuple(
            MembershipAccessContext(
                membership_id=membership.id,
                organization_id=organization.id,
                organization_name=organization.name,
                organization_type=organization.organization_type,
                role=membership.role,
                is_primary=membership.is_primary,
                permissions=self.permissions_for_role(membership.role),
            )
            for membership, organization in rows
        )

    def resolve_effective_role(
        self,
        user: User,
        memberships: tuple[MembershipAccessContext, ...] | None = None,
    ) -> UserRole:
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return user.role
        resolved_memberships = memberships if memberships is not None else self.list_memberships_for_user(user.id)
        primary_membership = self._primary_membership(resolved_memberships)
        if primary_membership is not None:
            return MEMBERSHIP_TO_USER_ROLE[primary_membership.role]
        return user.role

    def build_user_access_context(self, user: User) -> UserAccessContext:
        memberships = self._memberships_allowed_for_account(user, self.list_memberships_for_user(user.id))
        primary_membership = self._primary_membership(memberships)
        effective_role = self.resolve_effective_role(user, memberships)
        permissions: tuple[str, ...] = tuple()
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            permissions = tuple(self._dedupe_permissions(*(item.permissions for item in memberships)))
        elif primary_membership is not None:
            permissions = primary_membership.permissions
        return UserAccessContext(
            effective_role=effective_role,
            active_organization_id=primary_membership.organization_id if primary_membership is not None else None,
            active_organization_name=primary_membership.organization_name if primary_membership is not None else None,
            active_organization_type=primary_membership.organization_type if primary_membership is not None else None,
            permissions=permissions,
            memberships=memberships,
        )

    def bind_user_access_context(self, user: User) -> UserAccessContext:
        context = self.build_user_access_context(user)
        setattr(user, ACCESS_CONTEXT_ATTR, context)
        setattr(user, ACCESS_EFFECTIVE_ROLE_ATTR, context.effective_role)
        setattr(user, ACCESS_ACTIVE_ORG_ATTR, context.active_organization_id)
        setattr(
            user,
            ACCESS_ROLE_MAP_ATTR,
            {membership.organization_id: membership.role.value for membership in context.memberships},
        )
        return context

    def create_agency_organization(self, *, name: str, creator: User) -> tuple[Organization, OrganizationMembership]:
        organization = Organization(
            name=name.strip(),
            organization_type=OrganizationType.AGENCY,
            metadata_json={},
        )
        self.session.add(organization)
        self.session.flush()
        membership = OrganizationMembership(
            user_id=creator.id,
            organization_id=organization.id,
            role=OrganizationRole.AGENT,
            is_primary=not self._user_has_primary_membership(creator.id),
        )
        self.session.add(membership)
        self.session.flush()
        self.log_action(
            actor_user_id=creator.id,
            organization_id=organization.id,
            action="organization.created",
            metadata_json={"organization_type": organization.organization_type.value},
        )
        return organization, membership

    def ensure_club_organization(self, club: ClubProfile, *, owner_user_id: str | None = None) -> Organization:
        organization = self.session.get(Organization, club.id)
        if organization is None:
            organization = self.session.scalar(
                select(Organization).where(Organization.club_profile_id == club.id)
            )
        created = False
        if organization is None:
            organization = Organization(
                id=club.id,
                name=club.club_name,
                organization_type=OrganizationType.CLUB,
                club_profile_id=club.id,
                metadata_json={"slug": club.slug},
            )
            self.session.add(organization)
            self.session.flush()
            created = True

        resolved_owner_user_id = owner_user_id or club.owner_user_id
        if resolved_owner_user_id:
            self._ensure_membership(
                user_id=resolved_owner_user_id,
                organization_id=organization.id,
                role=OrganizationRole.CLUB,
                invited_by_user_id=None,
            )

        if created:
            self.log_action(
                actor_user_id=resolved_owner_user_id,
                organization_id=organization.id,
                action="organization.bootstrapped_from_club",
                metadata_json={"club_profile_id": club.id},
            )
        return organization

    def require_club_access(
        self,
        *,
        user: User,
        club_id: str,
        allowed_roles: set[OrganizationRole],
        forbidden_detail: str = "club_access_required",
    ) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError("club_not_found")

        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return club

        if self._public_account_type(user) != PublicAccountType.USER:
            raise PermissionError(forbidden_detail)

        membership = self._membership_for_user(user.id, club_id)
        if membership is None and club.owner_user_id == user.id:
            self.ensure_club_organization(club, owner_user_id=user.id)
            membership = self._membership_for_user(user.id, club_id)

        if membership is None or membership.role not in allowed_roles:
            raise PermissionError(forbidden_detail)
        return club

    def _memberships_allowed_for_account(
        self,
        user: User,
        memberships: tuple[MembershipAccessContext, ...],
    ) -> tuple[MembershipAccessContext, ...]:
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return memberships
        if self._public_account_type(user) == PublicAccountType.USER:
            return memberships
        return tuple(
            membership
            for membership in memberships
            if not self._is_club_membership(membership)
        )

    @staticmethod
    def _public_account_type(user: User) -> PublicAccountType:
        raw_account_type = getattr(user, "account_type", PublicAccountType.USER)
        if isinstance(raw_account_type, PublicAccountType):
            return raw_account_type
        candidate = str(raw_account_type).strip().lower()
        for account_type in PublicAccountType:
            if candidate in {account_type.value, account_type.name.lower()}:
                return account_type
        try:
            return PublicAccountType(candidate)
        except ValueError:
            return PublicAccountType.USER

    @staticmethod
    def _is_club_membership(membership: MembershipAccessContext) -> bool:
        organization_type = membership.organization_type
        if isinstance(organization_type, OrganizationType):
            return organization_type == OrganizationType.CLUB
        return str(organization_type).strip().lower() == OrganizationType.CLUB.value

    def invite_user_to_organization(
        self,
        *,
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: User,
    ) -> OrganizationInvite:
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise LookupError("organization_not_found")
        invite = OrganizationInvite(
            organization_id=organization.id,
            email=email.strip().lower(),
            role=role,
            invite_code=secrets.token_urlsafe(24),
            invited_by_user_id=invited_by.id,
            expires_at=utcnow() + timedelta(days=INVITE_TTL_DAYS),
            metadata_json={},
        )
        self.session.add(invite)
        self.session.flush()
        self.log_action(
            actor_user_id=invited_by.id,
            organization_id=organization.id,
            action="organization.invite_issued",
            target_user_id=None,
            metadata_json={"email": invite.email, "role": invite.role.value},
        )
        return invite

    def accept_invite(self, *, invite_code: str, user: User) -> tuple[OrganizationInvite, OrganizationMembership, Organization]:
        invite = self.session.scalar(
            select(OrganizationInvite).where(OrganizationInvite.invite_code == invite_code)
        )
        if invite is None:
            raise LookupError("organization_invite_not_found")
        now = utcnow()
        if invite.accepted_at is not None:
            raise AccessControlError("organization_invite_already_used")
        if self._as_utc(invite.expires_at) < now:
            raise InviteExpiredError("organization_invite_expired")
        if invite.email.strip().lower() != user.email.strip().lower():
            raise InviteMismatchError("organization_invite_email_mismatch")

        organization = self.session.get(Organization, invite.organization_id)
        if organization is None:
            raise LookupError("organization_not_found")

        membership = self._ensure_membership(
            user_id=user.id,
            organization_id=organization.id,
            role=invite.role,
            invited_by_user_id=invite.invited_by_user_id,
        )
        invite.accepted_by_user_id = user.id
        invite.accepted_at = now
        self.session.flush()
        self.log_action(
            actor_user_id=user.id,
            organization_id=organization.id,
            action="organization.invite_accepted",
            metadata_json={"role": membership.role.value},
        )
        return invite, membership, organization

    def list_audit_logs(self, *, organization_id: str, limit: int = 100) -> list[AccessAuditLog]:
        return self.session.scalars(
            select(AccessAuditLog)
            .where(AccessAuditLog.organization_id == organization_id)
            .order_by(AccessAuditLog.created_at.desc())
            .limit(limit)
        ).all()

    def assign_player_to_agent(
        self,
        *,
        player_id: str,
        agent_user_id: str,
        actor_user_id: str | None,
        organization_id: str | None = None,
    ) -> PlayerOwnership:
        ownership = self.session.scalar(select(PlayerOwnership).where(PlayerOwnership.player_id == player_id))
        if ownership is None:
            ownership = PlayerOwnership(
                player_id=player_id,
                agent_user_id=agent_user_id,
                organization_id=organization_id,
                assigned_by_user_id=actor_user_id,
                metadata_json={},
            )
            self.session.add(ownership)
        else:
            ownership.agent_user_id = agent_user_id
            ownership.organization_id = organization_id
            ownership.assigned_by_user_id = actor_user_id
        self.session.flush()
        self.log_action(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            player_id=player_id,
            target_user_id=agent_user_id,
            action="player.agent_assigned",
            metadata_json={},
        )
        return ownership

    def log_action(
        self,
        *,
        action: str,
        actor_user_id: str | None,
        organization_id: str | None = None,
        player_id: str | None = None,
        target_user_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> AccessAuditLog:
        event = AccessAuditLog(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            target_user_id=target_user_id,
            player_id=player_id,
            action=action,
            metadata_json=metadata_json or {},
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _ensure_membership(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: OrganizationRole,
        invited_by_user_id: str | None,
    ) -> OrganizationMembership:
        membership = self._membership_for_user(user_id, organization_id)
        if membership is None:
            membership = OrganizationMembership(
                user_id=user_id,
                organization_id=organization_id,
                role=role,
                is_primary=not self._user_has_primary_membership(user_id),
                invited_by_user_id=invited_by_user_id,
            )
            self.session.add(membership)
            self.session.flush()
            return membership
        membership.role = role
        if membership.invited_by_user_id is None:
            membership.invited_by_user_id = invited_by_user_id
        self.session.flush()
        return membership

    def _membership_for_user(self, user_id: str, organization_id: str) -> OrganizationMembership | None:
        return self.session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )

    def _user_has_primary_membership(self, user_id: str) -> bool:
        return self.session.scalar(
            select(OrganizationMembership.id).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_primary.is_(True),
            )
        ) is not None

    @staticmethod
    def _primary_membership(
        memberships: tuple[MembershipAccessContext, ...],
    ) -> MembershipAccessContext | None:
        for membership in memberships:
            if membership.is_primary:
                return membership
        return memberships[0] if memberships else None

    @staticmethod
    def _dedupe_permissions(*permission_sets: tuple[str, ...]) -> tuple[str, ...]:
        seen: list[str] = []
        for permission_set in permission_sets:
            for permission in permission_set:
                if permission not in seen:
                    seen.append(permission)
        return tuple(seen)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


__all__ = [
    "ACCESS_ACTIVE_ORG_ATTR",
    "ACCESS_CONTEXT_ATTR",
    "ACCESS_EFFECTIVE_ROLE_ATTR",
    "ACCESS_ROLE_MAP_ATTR",
    "AccessControlError",
    "AccessControlService",
    "InviteExpiredError",
    "InviteMismatchError",
    "MembershipAccessContext",
    "ROLE_PERMISSION_MATRIX",
    "UserAccessContext",
    "bound_effective_role",
    "bound_organization_role",
    "user_has_bound_organization_access",
]
