from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.hosted_competition_engine.schemas import (
    CompetitionTemplateView,
    HostedCompetitionCreateRequest,
    HostedCompetitionCreateResponse,
    HostedCompetitionDetailResponse,
    HostedCompetitionFinanceView,
    HostedCompetitionFinalizeRequest,
    HostedCompetitionFinalizeResponse,
    HostedCompetitionJoinResponse,
    HostedCompetitionLaunchResponse,
    HostedCompetitionListResponse,
    HostedCompetitionParticipantView,
    HostedCompetitionSettlementView,
    HostedCompetitionStandingView,
    HostedCompetitionView,
)
from backend.app.hosted_competition_engine.service import HostedCompetitionError, HostedCompetitionService
from backend.app.models.hosted_competition import CompetitionTemplate
from backend.app.models.user import User

router = APIRouter(prefix='/hosted-competitions', tags=['hosted-competitions'])
admin_router = APIRouter(prefix='/admin/hosted-competitions', tags=['admin-hosted-competitions'])


def _template_view(item) -> CompetitionTemplateView:
    return CompetitionTemplateView.model_validate(item, from_attributes=True)


def _competition_view(item) -> HostedCompetitionView:
    data = HostedCompetitionView.model_validate(item, from_attributes=True).model_dump()
    status = data.get('status')
    if hasattr(status, 'value'):
        data['status'] = status.value
    return HostedCompetitionView.model_validate(data)


def _participant_view(item) -> HostedCompetitionParticipantView:
    return HostedCompetitionParticipantView.model_validate(item, from_attributes=True)


def _standing_view(item) -> HostedCompetitionStandingView:
    return HostedCompetitionStandingView.model_validate(item, from_attributes=True)


def _settlement_view(item) -> HostedCompetitionSettlementView:
    data = HostedCompetitionSettlementView.model_validate(item, from_attributes=True).model_dump()
    status = data.get('status')
    if hasattr(status, 'value'):
        data['status'] = status.value
    return HostedCompetitionSettlementView.model_validate(data)


@router.get('/templates', response_model=list[CompetitionTemplateView])
def list_templates(session: Session = Depends(get_session)) -> list[CompetitionTemplateView]:
    service = HostedCompetitionService(session)
    return [_template_view(item) for item in service.list_templates()]


@router.get('', response_model=HostedCompetitionListResponse)
def list_public_competitions(session: Session = Depends(get_session)) -> HostedCompetitionListResponse:
    service = HostedCompetitionService(session)
    return HostedCompetitionListResponse(competitions=[_competition_view(item) for item in service.list_public_competitions()])


@router.get('/mine', response_model=HostedCompetitionListResponse)
def list_my_competitions(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> HostedCompetitionListResponse:
    service = HostedCompetitionService(session)
    return HostedCompetitionListResponse(competitions=[_competition_view(item) for item in service.list_for_host(user=user)])


@router.post('', response_model=HostedCompetitionCreateResponse)
def create_competition(payload: HostedCompetitionCreateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> HostedCompetitionCreateResponse:
    service = HostedCompetitionService(session)
    try:
        competition, template, host_participation_created = service.create_competition(host=user, payload=payload)
        session.commit()
        session.refresh(competition)
    except HostedCompetitionError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HostedCompetitionCreateResponse(
        competition=_competition_view(competition),
        template=_template_view(template),
        host_participation_created=host_participation_created,
        dashboard_summary=f"{competition.title} opened with reward pool {competition.reward_pool_fancoin} FanCoin.",
    )


@router.get('/{competition_id}', response_model=HostedCompetitionDetailResponse)
def get_competition_detail(competition_id: str, session: Session = Depends(get_session)) -> HostedCompetitionDetailResponse:
    service = HostedCompetitionService(session)
    competition = service.get_competition(competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail='Hosted competition was not found.')
    template = session.get(CompetitionTemplate, competition.template_id)
    participants = service.participants_for_competition(competition.id)
    return HostedCompetitionDetailResponse(
        competition=_competition_view(competition),
        template=_template_view(template),
        participants=[_participant_view(item) for item in participants],
        current_participants=len(participants),
        join_open=competition.status in {'open', 'draft'} and len(participants) < competition.max_participants,
    )


@router.post('/{competition_id}/join', response_model=HostedCompetitionJoinResponse)
def join_competition(competition_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> HostedCompetitionJoinResponse:
    service = HostedCompetitionService(session)
    try:
        competition, participant = service.join_competition(user=user, competition_id=competition_id)
        session.commit()
        session.refresh(participant)
        current_participants = len(service.participants_for_competition(competition.id))
    except HostedCompetitionError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HostedCompetitionJoinResponse(
        competition=_competition_view(competition),
        participant=_participant_view(participant),
        current_participants=current_participants,
        dashboard_summary=f"Joined {competition.title}. Participants: {current_participants}/{competition.max_participants}.",
    )


@router.get('/{competition_id}/standings', response_model=list[HostedCompetitionStandingView])
def list_standings(competition_id: str, session: Session = Depends(get_session)) -> list[HostedCompetitionStandingView]:
    service = HostedCompetitionService(session)
    if service.get_competition(competition_id) is None:
        raise HTTPException(status_code=404, detail='Hosted competition was not found.')
    return [_standing_view(item) for item in service.standings_for_competition(competition_id)]


@router.get('/{competition_id}/finance', response_model=HostedCompetitionFinanceView)
def get_finance(competition_id: str, session: Session = Depends(get_session)) -> HostedCompetitionFinanceView:
    service = HostedCompetitionService(session)
    try:
        return HostedCompetitionFinanceView.model_validate(service.finance_snapshot(competition_id))
    except HostedCompetitionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{competition_id}/launch', response_model=HostedCompetitionLaunchResponse)
def launch_competition(competition_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> HostedCompetitionLaunchResponse:
    service = HostedCompetitionService(session)
    competition = service.get_competition(competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail='Hosted competition was not found.')
    if competition.host_user_id != user.id:
        raise HTTPException(status_code=403, detail='Only the host can launch this competition.')
    try:
        competition = service.launch_competition(actor=user, competition_id=competition_id)
        session.commit()
    except HostedCompetitionError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    standings = service.standings_for_competition(competition_id)
    return HostedCompetitionLaunchResponse(
        competition=_competition_view(competition),
        standings=[_standing_view(item) for item in standings],
        dashboard_summary=f'{competition.title} is now live with {len(standings)} seeded participants.',
    )


@admin_router.post('/seed', response_model=list[CompetitionTemplateView])
def seed_templates(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> list[CompetitionTemplateView]:
    service = HostedCompetitionService(session)
    service.seed_defaults()
    session.commit()
    return [_template_view(item) for item in service.list_templates()]


@admin_router.post('/{competition_id}/finalize', response_model=HostedCompetitionFinalizeResponse)
def finalize_competition(competition_id: str, payload: HostedCompetitionFinalizeRequest, admin_user: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> HostedCompetitionFinalizeResponse:
    service = HostedCompetitionService(session)
    try:
        competition, standings, settlements = service.finalize_competition(
            actor=admin_user,
            competition_id=competition_id,
            placements=[item.model_dump() for item in payload.placements],
            note=payload.note,
        )
        session.commit()
    except HostedCompetitionError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finance = HostedCompetitionFinanceView.model_validate(service.finance_snapshot(competition_id))
    return HostedCompetitionFinalizeResponse(
        competition=_competition_view(competition),
        standings=[_standing_view(item) for item in standings],
        settlements=[_settlement_view(item) for item in settlements],
        finance=finance,
        dashboard_summary=f'{competition.title} has been settled with {len(settlements)} ledger-backed settlement record(s).',
    )
