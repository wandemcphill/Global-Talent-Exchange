from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.ingestion.real_player_import_ops_schemas import (
    RealPlayerImportBatchDetailView,
    RealPlayerImportBatchIssueView,
    RealPlayerImportBatchResumeRequest,
    RealPlayerImportBatchRunRequest,
    RealPlayerImportBatchSummaryView,
    RealPlayerImportValuationStatusView,
)
from app.ingestion.real_player_import_ops_service import (
    RealPlayerImportOpsError,
    RealPlayerImportOpsService,
)
from app.ingestion.real_player_import_schemas import RealPlayerImportExecutionSummary, RealPlayerImportStatusRead, RealPlayerImportTriggerRequest
from app.ingestion.real_player_import_service import RealPlayerImportError, RealPlayerImportService
from app.ingestion.schemas import CursorRead, ProviderHealthSnapshot, SyncExecutionSummary, SyncRunRead, SyncStatusRead, SyncTriggerRequest
from app.ingestion.service import IngestionService
from app.models.user import User
from app.providers import ProviderConfigurationError

router = APIRouter(prefix="/internal/ingestion", tags=["ingestion"], dependencies=[Depends(get_current_admin)])


def get_ingestion_service(
    request: Request,
    session: Session = Depends(get_session),
) -> IngestionService:
    return IngestionService(
        session,
        cache_backend=request.app.state.cache_backend,
        settings=request.app.state.settings,
    )


def get_real_player_import_service(
    request: Request,
    session: Session = Depends(get_session),
) -> RealPlayerImportService:
    return RealPlayerImportService(
        session,
        settings=request.app.state.settings,
    )


def get_real_player_import_ops_service(request: Request) -> RealPlayerImportOpsService:
    return RealPlayerImportOpsService(
        session_factory=request.app.state.session_factory,
        database_url=str(request.app.state.db_engine.url),
        settings=request.app.state.settings,
    )


@router.post("/bootstrap-sync", response_model=SyncExecutionSummary, status_code=status.HTTP_202_ACCEPTED)
def trigger_bootstrap_sync(
    payload: SyncTriggerRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    _: User = Depends(get_current_admin),
) -> SyncExecutionSummary:
    try:
        cache_backend = request.app.state.cache_backend if request is not None else None
        summary = IngestionService(
            session,
            cache_backend=cache_backend,
            settings=request.app.state.settings if request is not None else None,
        ).bootstrap_sync(
            provider_name=payload.provider_name,
            competition_external_id=payload.competition_external_id,
            season_external_id=payload.season_external_id,
        )
        session.commit()
        return summary
    except (KeyError, ProviderConfigurationError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/incremental-sync", response_model=SyncExecutionSummary, status_code=status.HTTP_202_ACCEPTED)
def trigger_incremental_sync(
    payload: SyncTriggerRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    _: User = Depends(get_current_admin),
) -> SyncExecutionSummary:
    try:
        cache_backend = request.app.state.cache_backend if request is not None else None
        summary = IngestionService(
            session,
            cache_backend=cache_backend,
            settings=request.app.state.settings if request is not None else None,
        ).sync_incremental(
            provider_name=payload.provider_name,
            cursor_key=payload.cursor_key,
        )
        session.commit()
        return summary
    except (KeyError, ProviderConfigurationError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/competitions/{competition_external_id}/refresh", response_model=SyncExecutionSummary, status_code=status.HTTP_202_ACCEPTED)
def refresh_competition(
    competition_external_id: str,
    payload: SyncTriggerRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    _: User = Depends(get_current_admin),
) -> SyncExecutionSummary:
    cache_backend = request.app.state.cache_backend if request is not None else None
    summary = IngestionService(
        session,
        cache_backend=cache_backend,
        settings=request.app.state.settings if request is not None else None,
    ).refresh_competition(
        provider_name=payload.provider_name,
        competition_external_id=competition_external_id,
        season_external_id=payload.season_external_id,
    )
    session.commit()
    return summary


@router.post("/clubs/{club_external_id}/refresh", response_model=SyncExecutionSummary, status_code=status.HTTP_202_ACCEPTED)
def refresh_club(
    club_external_id: str,
    payload: SyncTriggerRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    _: User = Depends(get_current_admin),
) -> SyncExecutionSummary:
    cache_backend = request.app.state.cache_backend if request is not None else None
    summary = IngestionService(
        session,
        cache_backend=cache_backend,
        settings=request.app.state.settings if request is not None else None,
    ).refresh_club(
        provider_name=payload.provider_name,
        club_external_id=club_external_id,
        competition_external_id=payload.competition_external_id,
        season_external_id=payload.season_external_id,
    )
    session.commit()
    return summary


@router.post("/players/{player_external_id}/refresh", response_model=SyncExecutionSummary, status_code=status.HTTP_202_ACCEPTED)
def refresh_player(
    player_external_id: str,
    payload: SyncTriggerRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    _: User = Depends(get_current_admin),
) -> SyncExecutionSummary:
    cache_backend = request.app.state.cache_backend if request is not None else None
    summary = IngestionService(
        session,
        cache_backend=cache_backend,
        settings=request.app.state.settings if request is not None else None,
    ).refresh_player(
        provider_name=payload.provider_name,
        player_external_id=player_external_id,
        club_external_id=payload.club_external_id,
        competition_external_id=payload.competition_external_id,
        season_external_id=payload.season_external_id,
    )
    session.commit()
    return summary


@router.get("/status", response_model=SyncStatusRead)
def get_sync_status(
    provider_name: str = Query(default="mock"),
    service: IngestionService = Depends(get_ingestion_service),
    _: User = Depends(get_current_admin),
) -> SyncStatusRead:
    return service.get_sync_status(provider_name=provider_name)


@router.get("/runs", response_model=list[SyncRunRead])
def list_recent_sync_runs(
    provider_name: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: IngestionService = Depends(get_ingestion_service),
    _: User = Depends(get_current_admin),
) -> list[SyncRunRead]:
    return service.list_recent_sync_runs(provider_name=provider_name, limit=limit)


@router.get("/providers/{provider_name}/health", response_model=ProviderHealthSnapshot)
def inspect_provider_health(
    provider_name: str,
    service: IngestionService = Depends(get_ingestion_service),
    _: User = Depends(get_current_admin),
) -> ProviderHealthSnapshot:
    try:
        return service.inspect_provider_health(provider_name=provider_name)
    except (KeyError, ProviderConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/cursors/{provider_name}", response_model=CursorRead | None)
def inspect_last_cursor(
    provider_name: str,
    cursor_key: str = Query(default="default"),
    service: IngestionService = Depends(get_ingestion_service),
    _: User = Depends(get_current_admin),
) -> CursorRead | None:
    return service.get_last_cursor(provider_name=provider_name, cursor_key=cursor_key)


@router.post("/real-players/import", response_model=RealPlayerImportExecutionSummary, status_code=status.HTTP_202_ACCEPTED)
def trigger_real_player_import(
    payload: RealPlayerImportTriggerRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    _: User = Depends(get_current_admin),
) -> RealPlayerImportExecutionSummary:
    try:
        summary = RealPlayerImportService(
            session,
            settings=request.app.state.settings if request is not None else None,
        ).import_directory(
            provider_name=payload.provider_name,
            batch_size=payload.batch_size,
            max_pages=payload.max_pages,
            cursor_key=payload.cursor_key,
            restart=payload.restart,
        )
        session.commit()
        return summary
    except (KeyError, ProviderConfigurationError, RealPlayerImportError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/real-players/status", response_model=RealPlayerImportStatusRead)
def get_real_player_import_status(
    provider_name: str | None = Query(default=None),
    cursor_key: str | None = Query(default=None),
    service: RealPlayerImportService = Depends(get_real_player_import_service),
    _: User = Depends(get_current_admin),
) -> RealPlayerImportStatusRead:
    return service.get_status(provider_name=provider_name, cursor_key=cursor_key)


@router.get("/real-players/batches", response_model=list[RealPlayerImportBatchSummaryView])
def list_real_player_import_batches(
    limit: int = Query(default=20, ge=1, le=100),
    batch_status: str | None = Query(default=None),
    provider_name: str | None = Query(default=None),
    batch_key: str | None = Query(default=None),
    service: RealPlayerImportOpsService = Depends(get_real_player_import_ops_service),
    _: User = Depends(get_current_admin),
) -> list[RealPlayerImportBatchSummaryView]:
    return service.list_batches(
        limit=limit,
        batch_status=batch_status,
        provider_name=provider_name,
        batch_key=batch_key,
    )


@router.post("/real-players/batches", response_model=RealPlayerImportBatchDetailView, status_code=status.HTTP_202_ACCEPTED)
def run_real_player_import_batch(
    payload: RealPlayerImportBatchRunRequest,
    admin: User = Depends(get_current_admin),
    service: RealPlayerImportOpsService = Depends(get_real_player_import_ops_service),
) -> RealPlayerImportBatchDetailView:
    try:
        return service.run_batch(actor_user_id=admin.id, payload=payload)
    except RealPlayerImportOpsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/real-players/batches/{batch_id}/resume", response_model=RealPlayerImportBatchDetailView)
def resume_real_player_import_batch(
    batch_id: str,
    payload: RealPlayerImportBatchResumeRequest,
    admin: User = Depends(get_current_admin),
    service: RealPlayerImportOpsService = Depends(get_real_player_import_ops_service),
) -> RealPlayerImportBatchDetailView:
    try:
        return service.resume_batch(batch_id=batch_id, actor_user_id=admin.id, payload=payload)
    except RealPlayerImportOpsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/real-players/batches/{batch_id}", response_model=RealPlayerImportBatchDetailView)
def get_real_player_import_batch(
    batch_id: str,
    include_rows: bool = Query(default=False),
    service: RealPlayerImportOpsService = Depends(get_real_player_import_ops_service),
    _: User = Depends(get_current_admin),
) -> RealPlayerImportBatchDetailView:
    try:
        return service.get_batch(batch_id=batch_id, include_rows=include_rows)
    except RealPlayerImportOpsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/real-players/batches/{batch_id}/issues", response_model=list[RealPlayerImportBatchIssueView])
def list_real_player_import_batch_issues(
    batch_id: str,
    issue_type: str | None = Query(default=None),
    unresolved_only: bool = Query(default=True),
    service: RealPlayerImportOpsService = Depends(get_real_player_import_ops_service),
    _: User = Depends(get_current_admin),
) -> list[RealPlayerImportBatchIssueView]:
    try:
        return service.list_unresolved_issues(
            batch_id=batch_id,
            issue_type=issue_type,
            unresolved_only=unresolved_only,
        )
    except RealPlayerImportOpsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/real-players/batches/{batch_id}/valuation-status", response_model=RealPlayerImportValuationStatusView)
def get_real_player_import_batch_valuation_status(
    batch_id: str,
    service: RealPlayerImportOpsService = Depends(get_real_player_import_ops_service),
    _: User = Depends(get_current_admin),
) -> RealPlayerImportValuationStatusView:
    try:
        return service.get_valuation_status(batch_id=batch_id)
    except RealPlayerImportOpsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
