from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.dispute_engine.schemas import (
    DisputeAssignRequest,
    DisputeCreateRequest,
    DisputeDetailResponse,
    DisputeListResponse,
    DisputeMessageCreateRequest,
    DisputeMessageView,
    DisputeStatusRequest,
    DisputeView,
)
from app.dispute_engine.service import DisputeEngineError, DisputeEngineService
from app.models.user import User

router = APIRouter(prefix="/disputes", tags=["disputes"])
admin_router = APIRouter(prefix="/admin/disputes", tags=["admin-disputes"])


def _dispute_view(item) -> DisputeView:
    return DisputeView.model_validate(item, from_attributes=True)


def _message_view(item) -> DisputeMessageView:
    return DisputeMessageView.model_validate(item, from_attributes=True)


@router.post("", response_model=DisputeDetailResponse)
def create_dispute(payload: DisputeCreateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> DisputeDetailResponse:
    service = DisputeEngineService(session)
    try:
        dispute = service.create_dispute(
            user=user,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            reference=payload.reference,
            subject=payload.subject,
            message=payload.message,
            metadata_json=payload.metadata_json,
        )
        session.commit()
        return DisputeDetailResponse(dispute=_dispute_view(dispute), messages=[_message_view(item) for item in service.get_messages(dispute.id)])
    except DisputeEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/me", response_model=DisputeListResponse)
def my_disputes(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> DisputeListResponse:
    service = DisputeEngineService(session)
    disputes = service.list_for_user(user_id=user.id)
    return DisputeListResponse(disputes=[_dispute_view(item) for item in disputes], total_open=service.open_count())


@router.get("/{dispute_id}", response_model=DisputeDetailResponse)
def get_dispute(dispute_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> DisputeDetailResponse:
    service = DisputeEngineService(session)
    try:
        dispute = service.get_dispute(dispute_id)
    except DisputeEngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if dispute.user_id != user.id and user.role.value not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="You cannot view this dispute.")
    return DisputeDetailResponse(dispute=_dispute_view(dispute), messages=[_message_view(item) for item in service.get_messages(dispute.id)])


@router.post("/{dispute_id}/messages", response_model=DisputeDetailResponse)
def add_message(dispute_id: str, payload: DisputeMessageCreateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> DisputeDetailResponse:
    service = DisputeEngineService(session)
    try:
        dispute = service.get_dispute(dispute_id)
        if dispute.user_id != user.id and user.role.value not in {"admin", "super_admin"}:
            raise HTTPException(status_code=403, detail="You cannot message this dispute.")
        sender_role = "admin" if user.role.value in {"admin", "super_admin"} else "user"
        service.add_message(dispute=dispute, sender=user, sender_role=sender_role, message=payload.message, attachment_id=payload.attachment_id)
        session.commit()
        return DisputeDetailResponse(dispute=_dispute_view(dispute), messages=[_message_view(item) for item in service.get_messages(dispute.id)])
    except DisputeEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.get("", response_model=DisputeListResponse)
def list_disputes(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> DisputeListResponse:
    service = DisputeEngineService(session)
    disputes = service.list_for_admin()
    return DisputeListResponse(disputes=[_dispute_view(item) for item in disputes], total_open=service.open_count())


@admin_router.post("/{dispute_id}/assign", response_model=DisputeView)
def assign_dispute(dispute_id: str, payload: DisputeAssignRequest, _: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> DisputeView:
    service = DisputeEngineService(session)
    try:
        dispute = service.assign(dispute_id=dispute_id, admin_user_id=payload.admin_user_id)
        session.commit()
        return _dispute_view(dispute)
    except DisputeEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post("/{dispute_id}/status", response_model=DisputeView)
def update_dispute_status(dispute_id: str, payload: DisputeStatusRequest, admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> DisputeView:
    service = DisputeEngineService(session)
    try:
        dispute = service.update_status(dispute_id=dispute_id, status=payload.status, note=payload.note, actor=admin)
        session.commit()
        return _dispute_view(dispute)
    except DisputeEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
