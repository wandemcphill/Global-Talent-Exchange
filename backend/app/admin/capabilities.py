from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import StrEnum
import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.auth.dependencies import get_current_admin
from app.models.user import User, UserRole
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)


class AdminCapability(StrEnum):
    MANAGE_ADMIN_ROLES = "manage_admin_roles"
    MANAGE_COMMISSIONS = "manage_commissions"
    MANAGE_PAYMENT_RAILS = "manage_payment_rails"
    MANAGE_WITHDRAWALS = "manage_withdrawals"
    MANAGE_TREASURY_WITHDRAWALS = "manage_treasury_withdrawals"
    MANAGE_LIQUIDITY_DESK = "manage_liquidity_desk"
    MANAGE_COMPETITIONS = "manage_competitions"
    VIEW_AUDIT_LOG = "view_audit_log"
    VIEW_INTEGRITY_CONTROLS = "view_integrity_controls"
    PAUSE_PAYMENTS = "pause_payments"
    MANAGE_MANAGER_CATALOG = "manage_manager_catalog"
    MANAGE_MANAGER_SUPPLY = "manage_manager_supply"
    MANAGE_REGEN_UNIVERSE = "manage_regen_universe"
    MANAGE_NATIONAL_REGENS = "manage_national_regens"
    MANAGE_REGEN_AWARDS = "manage_regen_awards"
    MANAGE_REGEN_GENERATION = "manage_regen_generation"


ADMIN_CAPABILITY_VALUES: tuple[str, ...] = tuple(item.value for item in AdminCapability)
_GENERIC_FORBIDDEN_DETAIL = "Admin capability could not be verified for this action."


@dataclass(frozen=True, slots=True)
class AdminAuditContext:
    actor_user_id: str
    actor_email: str | None
    actor_role: str
    capability: str
    method: str
    path: str
    route_name: str | None
    request_id: str | None = None

    def as_metadata(self) -> dict[str, Any]:
        return asdict(self)


def require_admin_capability(capability: AdminCapability) -> Callable[..., User]:
    def dependency(request: Request, actor: User = Depends(get_current_admin)) -> User:
        assert_admin_capability(request, actor, capability)
        request.state.admin_audit_context = build_admin_audit_context(request, actor, capability)
        return actor

    return dependency


def assert_admin_capability(request: Request, actor: User, capability: AdminCapability | str) -> None:
    # Imported locally to avoid an import cycle (admin_godmode.service ->
    # admin_godmode.router -> admin.capabilities) at module load time.
    from app.admin_godmode.service import PermissionDeniedError

    resolved_capability = capability.value if isinstance(capability, AdminCapability) else str(capability)
    if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required for this action.",
        )

    service = _admin_godmode_service(request)
    state: dict[str, Any] = {}
    if actor.role != UserRole.SUPER_ADMIN:
        try:
            state = service._load_state(request.app)
        except Exception as exc:
            logger.warning(
                "admin.capability.denied actor_user_id=%s capability=%s reason=state_unavailable",
                actor.id,
                resolved_capability,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_GENERIC_FORBIDDEN_DETAIL,
            ) from exc

    profile = service.resolve_profile(actor, state)
    try:
        service._assert_has_permission(profile, resolved_capability)
    except PermissionDeniedError as exc:
        logger.warning(
            "admin.capability.denied actor_user_id=%s role_name=%s capability=%s",
            actor.id,
            profile.role_name,
            resolved_capability,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    logger.info(
        "admin.capability.granted actor_user_id=%s role_name=%s capability=%s",
        actor.id,
        profile.role_name,
        resolved_capability,
    )


def build_admin_audit_context(
    request: Request,
    actor: User,
    capability: AdminCapability | str,
) -> AdminAuditContext:
    request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    route = request.scope.get("route")
    route_name = getattr(route, "name", None)
    actor_role = actor.role.value if hasattr(actor.role, "value") else str(actor.role)
    resolved_capability = capability.value if isinstance(capability, AdminCapability) else str(capability)
    return AdminAuditContext(
        actor_user_id=actor.id,
        actor_email=actor.email,
        actor_role=actor_role,
        capability=resolved_capability,
        method=request.method,
        path=request.url.path,
        route_name=route_name,
        request_id=request_id,
    )


def note_admin_read(request: Request, action_key: str, **metadata: Any) -> None:
    context = getattr(request.state, "admin_audit_context", None)
    context_metadata = context.as_metadata() if isinstance(context, AdminAuditContext) else {}
    logger.info(
        "admin.read action_key=%s context=%s metadata=%s",
        action_key,
        context_metadata,
        metadata,
    )


def _admin_godmode_service(request: Request) -> AdminGodModeService:
    from app.admin_godmode.service import AdminGodModeService

    publisher = getattr(request.app.state, "event_publisher", None)
    return AdminGodModeService(
        wallet_service=WalletService(
            event_publisher=publisher,
            cache_backend=getattr(request.app.state, "cache_backend", None),
        )
    )


__all__ = [
    "ADMIN_CAPABILITY_VALUES",
    "AdminAuditContext",
    "AdminCapability",
    "assert_admin_capability",
    "build_admin_audit_context",
    "note_admin_read",
    "require_admin_capability",
]
