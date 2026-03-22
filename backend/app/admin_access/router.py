from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin_godmode.service import ADMIN_GODMODE_FILE, DEFAULT_ROLE_PERMISSIONS
from app.auth.dependencies import get_current_super_admin, get_session
from app.auth.service import AuthService, AuthError, DuplicateUserError
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/admin/access", tags=["admin-access"])


class AdminCreateRequest(BaseModel):
    email: str
    username: str
    password: str = Field(min_length=8)
    display_name: str | None = None
    permissions: list[str] = Field(default_factory=list)


class AdminPermissionUpdateRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list)
    is_enabled: bool = True


class AdminAccountView(BaseModel):
    id: str
    email: str
    username: str
    display_name: str | None
    role: str
    permissions: list[str]
    is_active: bool


class AdminPermissionCatalogView(BaseModel):
    permissions: list[str]


@router.get("/permissions", response_model=AdminPermissionCatalogView)
def list_permission_catalog() -> AdminPermissionCatalogView:
    permission_set: set[str] = set()
    for item in DEFAULT_ROLE_PERMISSIONS.values():
        permission_set.update(item)
    permission_set.update({
        "manage_manager_catalog",
        "manage_manager_supply",
        "manage_competitions",
        "review_audit_log",
        "manage_admin_accounts",
        "review_withdrawals",
        "toggle_payment_rails",
        "manage_commissions",
    })
    return AdminPermissionCatalogView(permissions=sorted(permission_set))


@router.get("", response_model=list[AdminAccountView])
def list_admins(request: Request, session: Session = Depends(get_session), _: User = Depends(get_current_super_admin)) -> list[AdminAccountView]:
    state = _load_state(request)
    assignments = {str(item.get("subject_key", "")).lower(): item for item in state["roles"].get("assignments", [])}
    admins = session.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])).all()
    items = []
    for admin in admins:
        assignment = assignments.get(admin.email.lower()) or assignments.get(admin.id.lower()) or assignments.get(admin.username.lower()) or {}
        items.append(AdminAccountView(id=admin.id, email=admin.email, username=admin.username, display_name=admin.display_name, role=admin.role.value, permissions=list(assignment.get("permissions") or []), is_active=admin.is_active))
    return items


@router.post("", response_model=AdminAccountView, status_code=status.HTTP_201_CREATED)
def create_admin(payload: AdminCreateRequest, request: Request, session: Session = Depends(get_session), _: User = Depends(get_current_super_admin)) -> AdminAccountView:
    service = AuthService()
    try:
        user = service.ensure_admin_user(session, email=payload.email, password=payload.password, username=payload.username, display_name=payload.display_name or payload.username, role=UserRole.ADMIN)
        state = _load_state(request)
        _upsert_assignment(state, user, payload.permissions, True)
        _save_state(request, state)
        session.commit()
        session.refresh(user)
        return AdminAccountView(id=user.id, email=user.email, username=user.username, display_name=user.display_name, role=user.role.value, permissions=payload.permissions, is_active=user.is_active)
    except (DuplicateUserError, AuthError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{user_id}/permissions", response_model=AdminAccountView)
def update_admin_permissions(user_id: str, payload: AdminPermissionUpdateRequest, request: Request, session: Session = Depends(get_session), _: User = Depends(get_current_super_admin)) -> AdminAccountView:
    admin = session.get(User, user_id)
    if admin is None or admin.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found.")
    if admin.role == UserRole.SUPER_ADMIN and not payload.is_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Super admin accounts cannot be disabled from this screen.")
    state = _load_state(request)
    _upsert_assignment(state, admin, payload.permissions, payload.is_enabled)
    admin.is_active = payload.is_enabled
    _save_state(request, state)
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return AdminAccountView(id=admin.id, email=admin.email, username=admin.username, display_name=admin.display_name, role=admin.role.value, permissions=payload.permissions, is_active=admin.is_active)


def _state_path(request: Request) -> Path:
    return request.app.state.settings.config_root / ADMIN_GODMODE_FILE


def _load_state(request: Request) -> dict[str, Any]:
    path = _state_path(request)
    if not path.exists():
        state = {"roles": {"default_admin_role": "god_mode", "available_roles": DEFAULT_ROLE_PERMISSIONS, "assignments": []}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(request: Request, state: dict[str, Any]) -> None:
    path = _state_path(request)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _upsert_assignment(state: dict[str, Any], admin: User, permissions: list[str], is_enabled: bool) -> None:
    assignments = state.setdefault("roles", {}).setdefault("assignments", [])
    assignments[:] = [item for item in assignments if str(item.get("subject_key", "")).lower() not in {admin.email.lower(), admin.id.lower(), admin.username.lower()}]
    assignments.append({"subject_key": admin.email.lower(), "role_name": "god_mode", "permissions": permissions, "is_enabled": is_enabled})
