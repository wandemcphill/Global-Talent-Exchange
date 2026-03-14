from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.media_engine.schemas import MatchRevenueSnapshotView, MatchViewCreateRequest, MatchViewView, PremiumVideoPurchaseRequest, PremiumVideoPurchaseView, RevenueSnapshotCreateRequest
from backend.app.media_engine.service import MediaEngineError, MediaEngineService
from backend.app.models.user import User

router = APIRouter(prefix='/media-engine', tags=['media-engine'])
admin_router = APIRouter(prefix='/admin/media-engine', tags=['admin-media-engine'])


def _view(item) -> MatchViewView:
    return MatchViewView.model_validate(item, from_attributes=True)


def _purchase(item) -> PremiumVideoPurchaseView:
    return PremiumVideoPurchaseView.model_validate(item, from_attributes=True)


def _snapshot(item) -> MatchRevenueSnapshotView:
    return MatchRevenueSnapshotView.model_validate(item, from_attributes=True)


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
def purchase_video(payload: PremiumVideoPurchaseRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> PremiumVideoPurchaseView:
    item = MediaEngineService(session).purchase_video(actor=user, match_key=payload.match_key, competition_key=payload.competition_key)
    session.commit()
    return _purchase(item)


@router.get('/me/purchases', response_model=list[PremiumVideoPurchaseView])
def list_my_purchases(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[PremiumVideoPurchaseView]:
    return [_purchase(item) for item in MediaEngineService(session).list_purchases(actor=user)]


@router.get('/matches/{match_key}/snapshot', response_model=MatchRevenueSnapshotView)
def get_snapshot(match_key: str, _user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MatchRevenueSnapshotView:
    return _snapshot(MediaEngineService(session).build_snapshot(match_key=match_key))


@admin_router.post('/snapshots', response_model=MatchRevenueSnapshotView)
def create_snapshot(payload: RevenueSnapshotCreateRequest, _admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> MatchRevenueSnapshotView:
    item = MediaEngineService(session).build_snapshot(match_key=payload.match_key, competition_key=payload.competition_key, home_club_id=payload.home_club_id, away_club_id=payload.away_club_id)
    session.commit()
    return _snapshot(item)
