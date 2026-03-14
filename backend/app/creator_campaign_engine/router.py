from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.creator_campaign_engine.schemas import (
    CampaignSnapshotRequest,
    CreatorCampaignCreateRequest,
    CreatorCampaignMetricSnapshotView,
    CreatorCampaignMetricsView,
    CreatorCampaignUpdateRequest,
    CreatorCampaignView,
)
from backend.app.creator_campaign_engine.service import CreatorCampaignEngineError, CreatorCampaignEngineService
from backend.app.models.user import User

router = APIRouter(prefix="/creator-campaigns", tags=["creator-campaigns"])
admin_router = APIRouter(prefix="/admin/creator-campaigns", tags=["admin-creator-campaigns"])


def get_service(session: Session = Depends(get_session)) -> CreatorCampaignEngineService:
    return CreatorCampaignEngineService(session)


def _raise(exc: CreatorCampaignEngineError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=list[CreatorCampaignView])
def list_my_campaigns(current_user: User = Depends(get_current_user), service: CreatorCampaignEngineService = Depends(get_service)) -> list[CreatorCampaignView]:
    try:
        items = service.list_my_campaigns(actor=current_user)
    except CreatorCampaignEngineError as exc:
        _raise(exc)
    return [CreatorCampaignView.model_validate(item) for item in items]


@router.post("", response_model=CreatorCampaignView, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CreatorCampaignCreateRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> CreatorCampaignView:
    service = CreatorCampaignEngineService(session)
    try:
        item = service.create_campaign(actor=current_user, payload=payload)
    except CreatorCampaignEngineError as exc:
        _raise(exc)
    session.commit()
    session.refresh(item)
    return CreatorCampaignView.model_validate(item)


@router.patch("/{campaign_id}", response_model=CreatorCampaignView)
def update_campaign(campaign_id: str, payload: CreatorCampaignUpdateRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> CreatorCampaignView:
    service = CreatorCampaignEngineService(session)
    try:
        item = service.update_campaign(actor=current_user, campaign_id=campaign_id, payload=payload)
    except CreatorCampaignEngineError as exc:
        _raise(exc)
    session.commit()
    session.refresh(item)
    return CreatorCampaignView.model_validate(item)


@router.get("/{campaign_id}/metrics", response_model=CreatorCampaignMetricsView)
def get_campaign_metrics(campaign_id: str, current_user: User = Depends(get_current_user), service: CreatorCampaignEngineService = Depends(get_service)) -> CreatorCampaignMetricsView:
    try:
        return CreatorCampaignMetricsView.model_validate(service.campaign_metrics_view(actor=current_user, campaign_id=campaign_id))
    except CreatorCampaignEngineError as exc:
        _raise(exc)


@router.get("/{campaign_id}/snapshots", response_model=list[CreatorCampaignMetricSnapshotView])
def list_snapshots(campaign_id: str, current_user: User = Depends(get_current_user), service: CreatorCampaignEngineService = Depends(get_service)) -> list[CreatorCampaignMetricSnapshotView]:
    try:
        items = service.list_snapshots(actor=current_user, campaign_id=campaign_id)
    except CreatorCampaignEngineError as exc:
        _raise(exc)
    return [CreatorCampaignMetricSnapshotView.model_validate(item) for item in items]


@router.post("/{campaign_id}/snapshot", response_model=CreatorCampaignMetricSnapshotView)
def snapshot_campaign(campaign_id: str, payload: CampaignSnapshotRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> CreatorCampaignMetricSnapshotView:
    service = CreatorCampaignEngineService(session)
    try:
        item = service.snapshot_campaign(actor=current_user, campaign_id=campaign_id, snapshot_date=payload.snapshot_date)
    except CreatorCampaignEngineError as exc:
        _raise(exc)
    session.commit()
    session.refresh(item)
    return CreatorCampaignMetricSnapshotView.model_validate(item)


@admin_router.get("/{campaign_id}/metrics", response_model=CreatorCampaignMetricsView)
def admin_get_campaign_metrics(campaign_id: str, _: User = Depends(get_current_admin), service: CreatorCampaignEngineService = Depends(get_service)) -> CreatorCampaignMetricsView:
    try:
        return CreatorCampaignMetricsView.model_validate(service.campaign_metrics_admin_view(campaign_id=campaign_id))
    except CreatorCampaignEngineError as exc:
        _raise(exc)
