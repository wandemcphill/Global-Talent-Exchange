from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.media_engine.schemas import (
    MatchRevenueSnapshotView,
    MatchViewCreateRequest,
    MatchViewView,
    MediaAssetView,
    MediaDownloadRequest,
    MediaDownloadResponse,
    PremiumVideoPurchaseRequest,
    PremiumVideoPurchaseView,
    RevenueSnapshotCreateRequest,
)
from backend.app.media_engine.service import MediaEngineError, MediaEngineService
from backend.app.models.user import User
from backend.app.services.media_access_service import MediaAccessError, MediaAccessService
from backend.app.services.signing_service import SignedTokenService
from backend.app.services.storage_media_service import MediaStorageService
from backend.app.storage import LocalObjectStorage, StorageNotFound

router = APIRouter(prefix='/media-engine', tags=['media-engine'])
admin_router = APIRouter(prefix='/admin/media-engine', tags=['admin-media-engine'])


def _view(item) -> MatchViewView:
    return MatchViewView.model_validate(item, from_attributes=True)


def _purchase(item) -> PremiumVideoPurchaseView:
    return PremiumVideoPurchaseView.model_validate(item, from_attributes=True)


def _snapshot(item) -> MatchRevenueSnapshotView:
    return MatchRevenueSnapshotView.model_validate(item, from_attributes=True)


def _asset(item) -> MediaAssetView:
    return MediaAssetView(
        storage_key=item.storage_key,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        metadata=item.metadata,
        expires_at=item.expires_at,
    )


def _storage_service(request: Request) -> MediaStorageService:
    settings = request.app.state.settings
    storage = LocalObjectStorage(settings.media_storage.storage_root)
    return MediaStorageService(storage=storage, config=settings.media_storage)


def _access_service(request: Request, session: Session) -> MediaAccessService:
    settings = request.app.state.settings
    signer = SignedTokenService(settings.media_signing_secret, purpose="media_download")
    return MediaAccessService(
        session=session,
        settings=settings,
        storage_service=_storage_service(request),
        signer=signer,
        event_publisher=getattr(request.app.state, "event_publisher", None),
    )


def _media_service(session: Session, request: Request | None = None) -> MediaEngineService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return MediaEngineService(session, event_publisher=request.app.state.event_publisher)
    return MediaEngineService(session)


@router.post('/views', response_model=MatchViewView, status_code=201)
def create_view(payload: MatchViewCreateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MatchViewView:
    try:
        item = MediaEngineService(session).record_view(actor=user, match_key=payload.match_key, competition_key=payload.competition_key, watch_seconds=payload.watch_seconds, premium_unlocked=payload.premium_unlocked)
        session.commit()
        return _view(item)
    except MediaEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/purchases', response_model=PremiumVideoPurchaseView, status_code=201)
def purchase_video(payload: PremiumVideoPurchaseRequest, request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> PremiumVideoPurchaseView:
    try:
        item = _media_service(session, request).purchase_video(actor=user, match_key=payload.match_key, competition_key=payload.competition_key)
        session.commit()
        return _purchase(item)
    except MediaEngineError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/me/purchases', response_model=list[PremiumVideoPurchaseView])
def list_my_purchases(request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[PremiumVideoPurchaseView]:
    return [_purchase(item) for item in _media_service(session, request).list_purchases(actor=user)]


@router.get('/matches/{match_key}/snapshot', response_model=MatchRevenueSnapshotView)
def get_snapshot(match_key: str, _user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MatchRevenueSnapshotView:
    return _snapshot(MediaEngineService(session).build_snapshot(match_key=match_key))


@admin_router.post('/snapshots', response_model=MatchRevenueSnapshotView)
def create_snapshot(payload: RevenueSnapshotCreateRequest, _admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> MatchRevenueSnapshotView:
    item = MediaEngineService(session).build_snapshot(match_key=payload.match_key, competition_key=payload.competition_key, home_club_id=payload.home_club_id, away_club_id=payload.away_club_id)
    session.commit()
    return _snapshot(item)


@admin_router.post('/highlights', response_model=MediaAssetView, status_code=201)
async def upload_highlight(
    request: Request,
    file: UploadFile = File(...),
    match_key: str = Form(...),
    clip_label: str | None = Form(default=None),
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> MediaAssetView:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Highlight file is empty.")
    service = _storage_service(request)
    asset = service.store_temporary_highlight(
        match_key=match_key,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        clip_label=clip_label,
    )
    session.commit()
    return _asset(asset)


@admin_router.post('/highlights/{storage_key:path}/archive', response_model=MediaAssetView)
def archive_highlight(
    storage_key: str,
    request: Request,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> MediaAssetView:
    service = _storage_service(request)
    try:
        asset = service.archive_highlight(storage_key=storage_key)
    except StorageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return _asset(asset)


@admin_router.post('/exports', response_model=MediaAssetView, status_code=201)
async def upload_export_package(
    request: Request,
    file: UploadFile = File(...),
    match_key: str = Form(...),
    export_label: str | None = Form(default=None),
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
) -> MediaAssetView:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Export file is empty.")
    service = _storage_service(request)
    asset = service.store_export_package(
        match_key=match_key,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        export_label=export_label,
    )
    session.commit()
    return _asset(asset)


@router.post('/downloads', response_model=MediaDownloadResponse)
def request_download(
    payload: MediaDownloadRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MediaDownloadResponse:
    try:
        ticket = _access_service(request, session).issue_download(
            actor=user,
            storage_key=payload.storage_key,
            match_key=payload.match_key,
            download_kind=payload.download_kind,
            premium_required=payload.premium_required,
            watermark_label=payload.watermark_label,
            watermark_metadata=payload.watermark_metadata,
        )
    except (MediaAccessError, StorageNotFound) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return MediaDownloadResponse(
        storage_key=ticket.storage_key,
        download_url=ticket.download_url,
        expires_at=ticket.expires_at,
        content_type=ticket.content_type,
        filename=ticket.filename,
        metadata=ticket.metadata,
    )


@router.get('/downloads/{token}')
def download_signed_media(
    token: str,
    request: Request,
    session: Session = Depends(get_session),
):
    service = _access_service(request, session)
    try:
        resolved = service.resolve_download(token=token)
    except MediaAccessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage = service.storage_service.storage
    try:
        path = storage.open_file(key=resolved.storage_key)
    except StorageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return FileResponse(path, media_type=resolved.content_type, filename=resolved.filename)
