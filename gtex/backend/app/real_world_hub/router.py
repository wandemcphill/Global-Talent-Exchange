from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.models.user import User
from app.models.real_world_hub import RealityMode
from app.real_world_hub.schemas import (
    HybridPlayerView,
    RealDataProviderUpsertRequest,
    RealDataProviderView,
    RealDataSyncJobView,
    RealityModeSettingRequest,
    RealityModeSettingView,
    RealPlayerView,
    RealWorldSyncRequest,
    StatsNormalizationRequest,
    StatsNormalizationView,
)
from app.real_world_hub.service import (
    RealWorldHubError,
    RealWorldHubNotFoundError,
    RealWorldHubService,
    RealWorldHubValidationError,
)

router = APIRouter(prefix="/real-world", tags=["real-world"])
admin_router = APIRouter(prefix="/admin/real-world", tags=["admin-real-world"])


def _service(session: Session = Depends(get_session)) -> RealWorldHubService:
    return RealWorldHubService(session=session)


def _raise(exc: RealWorldHubError) -> Never:
    if isinstance(exc, RealWorldHubNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RealWorldHubValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/providers", response_model=list[RealDataProviderView])
def list_providers(service: RealWorldHubService = Depends(_service)) -> list[RealDataProviderView]:
    return [RealDataProviderView.model_validate(item, from_attributes=True) for item in service.list_providers()]


@admin_router.post("/providers", response_model=RealDataProviderView)
def upsert_provider(
    payload: RealDataProviderUpsertRequest,
    _: User = Depends(get_current_admin),
    service: RealWorldHubService = Depends(_service),
) -> RealDataProviderView:
    try:
        provider = service.upsert_provider(
            name=payload.name,
            api_endpoint=payload.api_endpoint,
            refresh_interval=payload.refresh_interval,
            normalization_profile_version=payload.normalization_profile_version,
            is_active=payload.is_active,
            metadata_json=payload.metadata_json,
        )
    except RealWorldHubError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    return RealDataProviderView.model_validate(provider, from_attributes=True)


@admin_router.post("/providers/{provider_id}/sync", response_model=RealDataSyncJobView)
def sync_provider(
    provider_id: str,
    payload: RealWorldSyncRequest | None = None,
    _: User = Depends(get_current_admin),
    service: RealWorldHubService = Depends(_service),
) -> RealDataSyncJobView:
    try:
        job = service.sync_provider(provider_id=provider_id, payload=payload)
    except RealWorldHubError as exc:
        service.session.rollback()
        _raise(exc)
    service.session.commit()
    service.session.refresh(job)
    return RealDataSyncJobView.model_validate(job, from_attributes=True)


@router.get("/players", response_model=list[RealPlayerView])
def list_real_players(
    provider_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: RealWorldHubService = Depends(_service),
) -> list[RealPlayerView]:
    return [
        RealPlayerView.model_validate(item, from_attributes=True)
        for item in service.list_real_players(provider_id=provider_id, limit=limit)
    ]


@router.get("/players/{real_player_id}", response_model=RealPlayerView)
def get_real_player(real_player_id: str, service: RealWorldHubService = Depends(_service)) -> RealPlayerView:
    try:
        player = service.get_real_player(real_player_id)
    except RealWorldHubError as exc:
        _raise(exc)
    return RealPlayerView.model_validate(player, from_attributes=True)


@router.post("/normalize", response_model=StatsNormalizationView)
def normalize_player(
    payload: StatsNormalizationRequest,
    service: RealWorldHubService = Depends(_service),
) -> StatsNormalizationView:
    try:
        result = service.normalize_player_seed(payload.player)
    except RealWorldHubError as exc:
        _raise(exc)
    normalized = result["normalized"]
    return StatsNormalizationView(
        source_name=normalized.source_name,
        source_player_key=normalized.source_player_key,
        normalization_profile_version=normalized.normalization_profile_version,
        real_world_rating=result["real_world_rating"],
        normalized_rating=result["normalized_rating"],
        attributes_json=result["attributes_json"],
        injury_status=normalized.injury_status,
        soft_injury_impact=result["soft_injury_impact"],
    )


@router.get("/hybrid-players", response_model=list[HybridPlayerView])
def list_hybrid_players(
    limit: int = Query(default=50, ge=1, le=200),
    mode: RealityMode | None = Query(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    service: RealWorldHubService = Depends(_service),
) -> list[HybridPlayerView]:
    payload = service.list_hybrid_players(
        user_id=current_user.id if current_user is not None else None,
        mode=mode,
        limit=limit,
    )
    return [HybridPlayerView.model_validate(item) for item in payload]


@router.get("/settings/me", response_model=RealityModeSettingView)
def get_my_settings(
    current_user: User = Depends(get_current_user),
    service: RealWorldHubService = Depends(_service),
) -> RealityModeSettingView:
    settings = service.get_or_create_settings(user_id=current_user.id)
    service.session.commit()
    return RealityModeSettingView.model_validate(settings, from_attributes=True)


@router.post("/settings/me", response_model=RealityModeSettingView)
def update_my_settings(
    payload: RealityModeSettingRequest,
    current_user: User = Depends(get_current_user),
    service: RealWorldHubService = Depends(_service),
) -> RealityModeSettingView:
    settings = service.upsert_settings(
        user_id=current_user.id,
        mode=payload.mode,
        enable_real_world_events=payload.enable_real_world_events,
        enable_soft_injuries=payload.enable_soft_injuries,
        enable_transfer_mirror=payload.enable_transfer_mirror,
        metadata_json=payload.metadata_json,
    )
    service.session.commit()
    return RealityModeSettingView.model_validate(settings, from_attributes=True)
