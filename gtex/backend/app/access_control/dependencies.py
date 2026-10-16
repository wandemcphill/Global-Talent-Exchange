from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService, user_has_bound_organization_access
from app.auth.dependencies import get_current_user, get_session
from app.models.access_control import OrganizationRole
from app.models.club_profile import ClubProfile
from app.models.user import User


def require_bound_organization_access(
    *allowed_roles: OrganizationRole,
    forbidden_detail: str = "organization_access_required",
) -> Callable[[str, User], User]:
    allowed_role_set = set(allowed_roles)

    def dependency(
        club_id: str,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not user_has_bound_organization_access(
            current_user,
            club_id,
            allowed_roles=allowed_role_set,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=forbidden_detail)
        return current_user

    return dependency


def require_club_access(
    *allowed_roles: OrganizationRole,
    forbidden_detail: str = "club_access_required",
) -> Callable[[str, User, Session], ClubProfile]:
    allowed_role_set = set(allowed_roles)

    def dependency(
        club_id: str,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> ClubProfile:
        try:
            return AccessControlService(session).require_club_access(
                user=current_user,
                club_id=club_id,
                allowed_roles=allowed_role_set,
                forbidden_detail=forbidden_detail,
            )
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return dependency


__all__ = ["require_bound_organization_access", "require_club_access"]
