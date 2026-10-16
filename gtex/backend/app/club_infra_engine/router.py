from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.club_infra_engine.schemas import ClubInfraActionResponse, ClubInfraDashboardResponse, FacilityUpgradeRequest, StadiumUpgradeRequest, SupportClubRequest
from app.club_infra_engine.service import ClubInfraError, ClubInfraService
from app.models.user import User

router = APIRouter(prefix='/club-infra', tags=['club-infra'])
admin_router = APIRouter(prefix='/admin/club-infra', tags=['admin-club-infra'])


def _dashboard_view(payload: dict[str, object]) -> ClubInfraDashboardResponse:
    stadium = payload['stadium']
    facilities = payload['facilities']
    token = payload['supporter_token']
    holding = payload.get('my_holding')
    return ClubInfraDashboardResponse(
        club_id=payload['club_id'],
        club_name=payload['club_name'],
        stadium={
            'id': stadium.id,
            'club_id': stadium.club_id,
            'name': stadium.name,
            'level': stadium.level,
            'capacity': stadium.capacity,
            'theme_key': stadium.theme_key,
            'gift_retention_bonus_bps': stadium.gift_retention_bonus_bps,
            'revenue_multiplier_bps': stadium.revenue_multiplier_bps,
            'prestige_bonus_bps': stadium.prestige_bonus_bps,
        },
        facilities={
            'id': facilities.id,
            'club_id': facilities.club_id,
            'training_level': facilities.training_level,
            'academy_level': facilities.academy_level,
            'medical_level': facilities.medical_level,
            'branding_level': facilities.branding_level,
            'upkeep_cost_fancoin': facilities.upkeep_cost_fancoin,
        },
        supporter_token={
            'id': token.id,
            'club_id': token.club_id,
            'token_name': token.token_name,
            'token_symbol': token.token_symbol,
            'circulating_supply': token.circulating_supply,
            'holder_count': token.holder_count,
            'influence_points': token.influence_points,
            'status': token.status.value if hasattr(token.status, 'value') else str(token.status),
            'description': token.description,
            'metadata_json': token.metadata_json,
        },
        my_holding=None if holding is None else {
            'id': holding.id,
            'club_id': holding.club_id,
            'user_id': holding.user_id,
            'token_balance': holding.token_balance,
            'influence_points': holding.influence_points,
            'is_founding_supporter': holding.is_founding_supporter,
            'metadata_json': holding.metadata_json,
        },
        projected_matchday_revenue_coin=payload['projected_matchday_revenue_coin'],
        projected_gift_retention_ratio=payload['projected_gift_retention_ratio'],
        prestige_index=payload['prestige_index'],
        insights=payload['insights'],
    )


@router.get('/my', response_model=ClubInfraDashboardResponse)
def get_my_club_infra(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> ClubInfraDashboardResponse:
    try:
        return _dashboard_view(ClubInfraService(session).my_dashboard(user))
    except ClubInfraError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/clubs/{club_id}', response_model=ClubInfraDashboardResponse)
def get_club_infra(club_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> ClubInfraDashboardResponse:
    try:
        return _dashboard_view(ClubInfraService(session).dashboard_for_club(club_id=club_id, viewer=user))
    except ClubInfraError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/my/stadium/upgrade', response_model=ClubInfraActionResponse)
def upgrade_my_stadium(payload: StadiumUpgradeRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> ClubInfraActionResponse:
    try:
        dashboard = ClubInfraService(session).upgrade_stadium(actor=user, target_level=payload.target_level)
        session.commit()
        return ClubInfraActionResponse(dashboard=_dashboard_view(dashboard), message='Stadium upgrade applied.')
    except ClubInfraError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/my/facilities/upgrade', response_model=ClubInfraActionResponse)
def upgrade_my_facility(payload: FacilityUpgradeRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> ClubInfraActionResponse:
    try:
        dashboard = ClubInfraService(session).upgrade_facility(actor=user, facility_key=payload.facility_key, increment=payload.increment)
        session.commit()
        return ClubInfraActionResponse(dashboard=_dashboard_view(dashboard), message='Facility upgrade applied.')
    except ClubInfraError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/clubs/{club_id}/support', response_model=ClubInfraActionResponse)
def support_club(club_id: str, payload: SupportClubRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> ClubInfraActionResponse:
    try:
        dashboard = ClubInfraService(session).support_club(actor=user, club_id=club_id, quantity=payload.quantity)
        session.commit()
        return ClubInfraActionResponse(dashboard=_dashboard_view(dashboard), message='Supporter share participation recorded.')
    except ClubInfraError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post('/seed')
def seed_club_infra(_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> dict[str, int]:
    count = ClubInfraService(session).bootstrap_existing_clubs()
    session.commit()
    return {'seeded_clubs': count}
