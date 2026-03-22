from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.moderation.schemas import (
    ModerationAssignmentRequest,
    ModerationReportCreateRequest,
    ModerationReportView,
    ModerationResolveRequest,
    ModerationSummaryView,
)
from app.moderation.service import ModerationError, ModerationService
from app.models.moderation_report import ModerationReport
from app.models.user import User

router = APIRouter(prefix="/moderation", tags=["moderation"])
admin_router = APIRouter(prefix="/admin/moderation", tags=["admin-moderation"])


def _map_report(item: ModerationReport) -> ModerationReportView:
    return ModerationReportView(
        id=item.id,
        reporter_user_id=item.reporter_user_id,
        subject_user_id=item.subject_user_id,
        target_type=item.target_type,
        target_id=item.target_id,
        reason_code=item.reason_code,
        description=item.description,
        evidence_url=item.evidence_url,
        status=item.status.value,
        priority=item.priority.value,
        assigned_admin_user_id=item.assigned_admin_user_id,
        resolution_action=item.resolution_action.value,
        resolution_note=item.resolution_note,
        resolved_by_user_id=item.resolved_by_user_id,
        report_count_for_target=item.report_count_for_target,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/reports", response_model=ModerationReportView, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ModerationReportCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ModerationReportView:
    service = ModerationService(session)
    try:
        report = service.create_report(
            reporter=current_user,
            target_type=payload.target_type,
            target_id=payload.target_id,
            subject_user_id=payload.subject_user_id,
            reason_code=payload.reason_code,
            description=payload.description,
            evidence_url=payload.evidence_url,
        )
    except ModerationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(report)
    return _map_report(report)


@router.get("/me/reports", response_model=list[ModerationReportView])
def list_my_reports(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[ModerationReportView]:
    service = ModerationService(session)
    return [_map_report(item) for item in service.list_reports_for_user(user=current_user)]


@admin_router.get("/reports", response_model=list[ModerationReportView])
def list_reports(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[ModerationReportView]:
    service = ModerationService(session)
    try:
        items = service.list_reports(status=status, priority=priority, target_type=target_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [_map_report(item) for item in items]


@admin_router.get("/reports/summary", response_model=ModerationSummaryView)
def get_summary(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> ModerationSummaryView:
    service = ModerationService(session)
    data = service.summary()
    return ModerationSummaryView(
        open_count=data["open_count"],
        in_review_count=data["in_review_count"],
        actioned_count=data["actioned_count"],
        dismissed_count=data["dismissed_count"],
        critical_count=data["critical_count"],
        high_priority_count=data["high_priority_count"],
        recent_reports=[_map_report(item) for item in data["recent_reports"]],
    )


@admin_router.post("/reports/{report_id}/assign", response_model=ModerationReportView)
def assign_report(
    report_id: str,
    payload: ModerationAssignmentRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ModerationReportView:
    service = ModerationService(session)
    try:
        report = service.assign_report(
            report_id=report_id,
            admin_user_id=payload.admin_user_id or current_admin.id,
            priority=payload.priority,
        )
    except (ModerationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(report)
    return _map_report(report)


@admin_router.post("/reports/{report_id}/resolve", response_model=ModerationReportView)
def resolve_report(
    report_id: str,
    payload: ModerationResolveRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ModerationReportView:
    service = ModerationService(session)
    try:
        report = service.resolve_report(
            report_id=report_id,
            admin_user_id=current_admin.id,
            resolution_action=payload.resolution_action,
            resolution_note=payload.resolution_note,
            dismiss=payload.dismiss,
        )
    except (ModerationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(report)
    return _map_report(report)
