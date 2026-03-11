from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.ingestion.schemas import CursorRead, ProviderHealthSnapshot, SyncExecutionSummary, SyncRunRead, SyncStatusRead, SyncTriggerRequest
from backend.app.ingestion.service import IngestionService
from backend.app.models.user import User
from backend.app.providers import ProviderConfigurationError

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
