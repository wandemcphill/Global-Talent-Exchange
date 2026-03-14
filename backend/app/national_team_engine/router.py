from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.user import User
from backend.app.national_team_engine.schemas import (
    NationalTeamCompetitionCreateRequest,
    NationalTeamCompetitionResponse,
    NationalTeamEntryDetailResponse,
    NationalTeamEntryResponse,
    NationalTeamEntryUpsertRequest,
    NationalTeamSquadMemberResponse,
    NationalTeamSquadUpsertRequest,
    NationalTeamUserHistoryResponse,
    NationalTeamManagerHistoryResponse,
)
from backend.app.national_team_engine.service import NationalTeamEngineError, NationalTeamEngineService

router = APIRouter(prefix="/national-team-engine", tags=["national-team-engine"])
admin_router = APIRouter(prefix="/admin/national-team-engine", tags=["national-team-engine-admin"])


@router.get("/competitions", response_model=list[NationalTeamCompetitionResponse])
def list_competitions(session: Session = Depends(get_session)):
    return [NationalTeamCompetitionResponse.model_validate(item, from_attributes=True) for item in NationalTeamEngineService(session).list_competitions()]


@router.get("/entries/{entry_id}", response_model=NationalTeamEntryDetailResponse)
def get_entry(entry_id: str, session: Session = Depends(get_session)):
    entry = NationalTeamEngineService(session).get_entry_detail(entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="National team entry was not found.")
    return NationalTeamEntryDetailResponse(
        **NationalTeamEntryResponse.model_validate(entry, from_attributes=True).model_dump(),
        squad_members=[NationalTeamSquadMemberResponse.model_validate(item, from_attributes=True) for item in entry.squad_members],
        manager_history=[NationalTeamManagerHistoryResponse.model_validate(item, from_attributes=True) for item in entry.manager_history],
    )


@router.get("/me/history", response_model=NationalTeamUserHistoryResponse)
def get_my_history(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    history = NationalTeamEngineService(session).user_history(user=current_user)
    return NationalTeamUserHistoryResponse(
        managed_entries=[NationalTeamEntryResponse.model_validate(item, from_attributes=True) for item in history["managed_entries"]],
        squad_memberships=[NationalTeamSquadMemberResponse.model_validate(item, from_attributes=True) for item in history["squad_memberships"]],
    )


@admin_router.post("/competitions", response_model=NationalTeamCompetitionResponse)
def create_competition(payload: NationalTeamCompetitionCreateRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    service = NationalTeamEngineService(session)
    try:
        competition = service.create_competition(payload=payload, actor=current_admin)
    except NationalTeamEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(competition)
    return NationalTeamCompetitionResponse.model_validate(competition, from_attributes=True)


@admin_router.post("/competitions/{competition_id}/entries", response_model=NationalTeamEntryResponse)
def upsert_entry(competition_id: str, payload: NationalTeamEntryUpsertRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    service = NationalTeamEngineService(session)
    try:
        entry = service.upsert_entry(competition_id=competition_id, payload=payload, actor=current_admin)
    except NationalTeamEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(entry)
    return NationalTeamEntryResponse.model_validate(entry, from_attributes=True)


@admin_router.post("/entries/{entry_id}/squad", response_model=NationalTeamEntryDetailResponse)
def upsert_squad(entry_id: str, payload: NationalTeamSquadUpsertRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    service = NationalTeamEngineService(session)
    try:
        entry = service.upsert_squad(entry_id=entry_id, members=payload.members, actor=current_admin)
    except NationalTeamEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(entry)
    entry = service.get_entry_detail(entry_id)
    assert entry is not None
    return NationalTeamEntryDetailResponse(
        **NationalTeamEntryResponse.model_validate(entry, from_attributes=True).model_dump(),
        squad_members=[NationalTeamSquadMemberResponse.model_validate(item, from_attributes=True) for item in entry.squad_members],
        manager_history=[NationalTeamManagerHistoryResponse.model_validate(item, from_attributes=True) for item in entry.manager_history],
    )
