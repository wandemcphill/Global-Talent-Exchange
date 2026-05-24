from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin.capabilities import ADMIN_CAPABILITY_VALUES
from app.admin_godmode.service import (
    ALL_ADMIN_PERMISSIONS,
    AdminGodModeService,
    DEFAULT_ROLE_PERMISSIONS,
    GodModeError,
    GOD_MODE_ROLE_NAME,
    SCOPED_ADMIN_ROLE_NAME,
)
from app.auth.dependencies import get_current_super_admin, get_session
from app.auth.service import AuthService, AuthError, DuplicateUserError
from app.models.user import User, UserRole
from app.wallets.service import WalletService

router = APIRouter(prefix="/api/admin/access", tags=["admin-access"])


class AdminCreateRequest(BaseModel):
    email: str
    username: str
    password: str = Field(min_length=8)
    display_name: str | None = None
    role_name: str | None = Field(default=None, max_length=64)
    permissions: list[str] = Field(default_factory=list)


class AdminPermissionUpdateRequest(BaseModel):
    role_name: str | None = Field(default=None, max_length=64)
    permissions: list[str] = Field(default_factory=list)
    is_enabled: bool = True


class AdminAccountView(BaseModel):
    id: str
    email: str
    username: str
    display_name: str | None
    role: str
    admin_role_name: str
    permissions: list[str]
    assigned_permissions: list[str]
    is_active: bool


class AdminPermissionCatalogView(BaseModel):
    permissions: list[str]


@router.get("/permissions", response_model=AdminPermissionCatalogView)
def list_permission_catalog() -> AdminPermissionCatalogView:
    permission_set: set[str] = set(ALL_ADMIN_PERMISSIONS)
    permission_set.update(ADMIN_CAPABILITY_VALUES)
    for item in DEFAULT_ROLE_PERMISSIONS.values():
        permission_set.update(item)
    permission_set.update(
        {
            "manage_manager_catalog",
            "manage_manager_supply",
            "manage_competitions",
            "review_audit_log",
            "manage_admin_accounts",
            "review_withdrawals",
            "toggle_payment_rails",
            "manage_commissions",
        }
    )
    return AdminPermissionCatalogView(permissions=sorted(permission_set))


@router.get("", response_model=list[AdminAccountView])
def list_admins(
    request: Request, session: Session = Depends(get_session), _: User = Depends(get_current_super_admin)
) -> list[AdminAccountView]:
    service = _godmode_service(request)
    state = service._load_state(request.app)
    admins = session.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])).all()
    return [_admin_account_view(service, state, admin) for admin in admins]


@router.post("", response_model=AdminAccountView, status_code=status.HTTP_201_CREATED)
def create_admin(
    payload: AdminCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_super_admin),
) -> AdminAccountView:
    service = AuthService()
    godmode_service = _godmode_service(request)
    try:
        user = service.ensure_admin_user(
            session,
            email=payload.email,
            password=payload.password,
            username=payload.username,
            display_name=payload.display_name or payload.username,
            role=UserRole.ADMIN,
        )
        state = godmode_service.upsert_admin_assignment(
            request.app,
            session,
            admin=user,
            role_name=payload.role_name,
            permissions=payload.permissions,
            is_enabled=True,
        )
        session.commit()
        session.refresh(user)
        return _admin_account_view(godmode_service, state, user)
    except (DuplicateUserError, AuthError, GodModeError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{user_id}/permissions", response_model=AdminAccountView)
def update_admin_permissions(
    user_id: str,
    payload: AdminPermissionUpdateRequest,
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_super_admin),
) -> AdminAccountView:
    admin = session.get(User, user_id)
    if admin is None or admin.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found.")
    if admin.role == UserRole.SUPER_ADMIN and not payload.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Super admin accounts cannot be disabled from this screen."
        )
    godmode_service = _godmode_service(request)
    state = godmode_service.upsert_admin_assignment(
        request.app,
        session,
        admin=admin,
        role_name=payload.role_name,
        permissions=payload.permissions,
        is_enabled=payload.is_enabled,
    )
    admin.is_active = payload.is_enabled
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return _admin_account_view(godmode_service, state, admin)


def _godmode_service(request: Request) -> AdminGodModeService:
    return AdminGodModeService(
        wallet_service=WalletService(cache_backend=getattr(request.app.state, "cache_backend", None))
    )


def _admin_account_view(
    service: AdminGodModeService,
    state: dict[str, object],
    admin: User,
) -> AdminAccountView:
    profile = service.resolve_profile(admin, state)
    assignment = service.assignment_snapshot(admin, state)
    return AdminAccountView(
        id=admin.id,
        email=admin.email,
        username=admin.username,
        display_name=admin.display_name,
        role=admin.role.value,
        admin_role_name=str(
            assignment["role_name"]
            or (GOD_MODE_ROLE_NAME if admin.role == UserRole.SUPER_ADMIN else SCOPED_ADMIN_ROLE_NAME)
        ),
        permissions=list(profile.permissions),
        assigned_permissions=list(assignment["permissions"] or []),
        is_active=admin.is_active,
    )
