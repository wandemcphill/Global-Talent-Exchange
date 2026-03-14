from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.user import User
from backend.app.player_import_engine.schemas import (
    PlayerCardSupplyJobCreateRequest,
    PlayerImportJobCreateRequest,
    PlayerImportJobView,
    PlayerImportItemView,
    YouthGenerationRequest,
    YouthGenerationResponse,
    YouthProspectView,
)
from backend.app.player_import_engine.service import PlayerImportError, PlayerImportService

router = APIRouter(prefix='/player-import', tags=['player-import'])
admin_router = APIRouter(prefix='/admin/player-import', tags=['admin-player-import'])


def _job_view(job, items) -> PlayerImportJobView:
    return PlayerImportJobView(
        id=job.id,
        created_by_user_id=job.created_by_user_id,
        source_type=job.source_type,
        source_label=job.source_label,
        status=job.status.value if hasattr(job.status, 'value') else str(job.status),
        total_items=job.total_items,
        valid_items=job.valid_items,
        imported_items=job.imported_items,
        failed_items=job.failed_items,
        notes=job.notes,
        metadata_json=job.metadata_json,
        items=[PlayerImportItemView(
            id=item.id,
            row_number=item.row_number,
            external_source_id=item.external_source_id,
            player_name=item.player_name,
            normalized_position=item.normalized_position,
            nationality_code=item.nationality_code,
            age=item.age,
            status=item.status.value if hasattr(item.status, 'value') else str(item.status),
            validation_errors_json=item.validation_errors_json,
            payload_json=item.payload_json,
            linked_player_id=item.linked_player_id,
        ) for item in items],
    )


def _prospect_view(item) -> YouthProspectView:
    return YouthProspectView(
        id=item.id,
        club_id=item.club_id,
        display_name=item.display_name,
        age=item.age,
        nationality_code=item.nationality_code,
        region_label=item.region_label,
        primary_position=item.primary_position,
        secondary_position=item.secondary_position,
        rating_band=item.rating_band.value if hasattr(item.rating_band, 'value') else str(item.rating_band),
        development_traits_json=item.development_traits_json,
        pathway_stage=item.pathway_stage.value if hasattr(item.pathway_stage, 'value') else str(item.pathway_stage),
        scouting_source=item.scouting_source,
        follow_priority=item.follow_priority,
    )


@admin_router.get('/jobs', response_model=list[PlayerImportJobView])
def list_import_jobs(_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> list[PlayerImportJobView]:
    service = PlayerImportService(session)
    views = []
    for job in service.list_jobs():
        _, items = service.get_job(job.id)
        views.append(_job_view(job, items))
    return views


@admin_router.post('/jobs', response_model=PlayerImportJobView, status_code=201)
def create_import_job(payload: PlayerImportJobCreateRequest, admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> PlayerImportJobView:
    service = PlayerImportService(session)
    try:
        job, items = service.create_job(actor=admin, source_type=payload.source_type, source_label=payload.source_label, rows=[item.model_dump() for item in payload.rows], commit=payload.commit)
        session.commit()
        return _job_view(job, items)
    except PlayerImportError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post('/card-supply', response_model=PlayerImportJobView, status_code=201)
def create_card_supply_job(payload: PlayerCardSupplyJobCreateRequest, admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> PlayerImportJobView:
    service = PlayerImportService(session)
    try:
        job, items = service.create_card_supply_job(actor=admin, source_label=payload.source_label, rows=[item.model_dump() for item in payload.rows], commit=payload.commit)
        session.commit()
        return _job_view(job, items)
    except PlayerImportError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post('/card-supply/csv', response_model=PlayerImportJobView, status_code=201)
def create_card_supply_job_from_csv(
    file: UploadFile = File(...),
    source_label: str = Query(default="card_supply_csv"),
    commit: bool = Query(default=True),
    admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PlayerImportJobView:
    service = PlayerImportService(session)
    try:
        raw_text = file.file.read().decode("utf-8-sig")
        reader = csv.DictReader(StringIO(raw_text))
        rows = [row for row in reader]
        job, items = service.create_card_supply_job(actor=admin, source_label=source_label, rows=rows, commit=commit)
        session.commit()
        return _job_view(job, items)
    except PlayerImportError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.get('/jobs/{job_id}', response_model=PlayerImportJobView)
def get_import_job(job_id: str, _admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> PlayerImportJobView:
    service = PlayerImportService(session)
    try:
        job, items = service.get_job(job_id)
        return _job_view(job, items)
    except PlayerImportError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.post('/youth/generate', response_model=YouthGenerationResponse)
def generate_youth_batch(payload: YouthGenerationRequest, admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> YouthGenerationResponse:
    service = PlayerImportService(session)
    try:
        job, items, prospects = service.generate_youth_batch(actor=admin, club_id=payload.club_id, count=payload.count, nationality_code=payload.nationality_code, region_label=payload.region_label)
        session.commit()
        return YouthGenerationResponse(job=_job_view(job, items), generated_prospects=[_prospect_view(item) for item in prospects], summary=f'Generated {len(prospects)} youth prospects.')
    except PlayerImportError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/youth-prospects/me', response_model=list[YouthProspectView])
def list_my_youth_prospects(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[YouthProspectView]:
    try:
        return [_prospect_view(item) for item in PlayerImportService(session).list_prospects_for_user(actor=user)]
    except PlayerImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/youth-prospects/{club_id}', response_model=list[YouthProspectView])
def list_club_youth_prospects(club_id: str, _user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[YouthProspectView]:
    return [_prospect_view(item) for item in PlayerImportService(session).list_prospects_for_club(club_id)]
