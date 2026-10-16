from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.admin.capabilities import AdminCapability, require_admin_capability
from app.auth.dependencies import get_session
from app.models.user import User
from app.operations_readiness.schemas import OperationsReadinessNotificationDispatch, OperationsReadinessSnapshot
from app.operations_readiness.service import OperationsReadinessService

router = APIRouter(tags=["operations-readiness"])


@router.get("/admin/operations-readiness", response_model=OperationsReadinessSnapshot)
def get_operations_readiness(
    _: User = Depends(require_admin_capability(AdminCapability.VIEW_AUDIT_LOG)),
    session: Session = Depends(get_session),
) -> OperationsReadinessSnapshot:
    return OperationsReadinessService(session).snapshot()


@router.post(
    "/admin/operations-readiness/notify-blockers",
    response_model=OperationsReadinessNotificationDispatch,
)
def notify_operations_readiness_blockers(
    actor: User = Depends(require_admin_capability(AdminCapability.VIEW_AUDIT_LOG)),
    session: Session = Depends(get_session),
) -> OperationsReadinessNotificationDispatch:
    dispatch = OperationsReadinessService(session).notify_blockers(actor=actor)
    session.commit()
    return dispatch
