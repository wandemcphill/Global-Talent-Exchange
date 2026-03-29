from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.national_team_engine.schemas import (
    NationalTeamAutoBuildRequest,
    NationalTeamAutoBuildResponse,
    NationalTeamCompetitionCreateRequest,
    NationalTeamCompetitionEntryResponse,
    NationalTeamCompetitionEntrySubmitRequest,
    NationalTeamCompetitionLifecycleResponse,
    NationalTeamCompetitionPresentationResponse,
    NationalTeamCompetitionResponse,
    NationalTeamCountryRankingResponse,
    NationalTeamEntryDetailResponse,
    NationalTeamEntryResponse,
    NationalTeamEntryUpsertRequest,
    NationalTeamManagerHistoryResponse,
    NationalTeamRentalCreateRequest,
    NationalTeamRentalPlayerCollectionResponse,
    NationalTeamRentalStatusResponse,
    NationalTeamSquadMemberResponse,
    NationalTeamSquadUpsertRequest,
    NationalTeamTournamentGiftRequest,
    NationalTeamTournamentGiftResponse,
    NationalTeamUserHistoryResponse,
    StadiumAdResponse,
    StadiumAdUpsertRequest,
    StoryEventResponse,
    TournamentThemeResponse,
    TournamentThemeUpsertRequest,
)
from app.national_team_engine.competition_lifecycle_service import (
    NationalCompetitionLifecycleError,
    NationalCompetitionLifecycleService,
)
from app.national_team_engine.service import NationalTeamEngineError, NationalTeamEngineService
from app.national_team_engine.tournament_service import NationalTeamTournamentError, NationalTeamTournamentService
from app.wallets.service import InsufficientBalanceError

router = APIRouter(prefix="/national-team-engine", tags=["national-team-engine"])
admin_router = APIRouter(prefix="/admin/national-team-engine", tags=["national-team-engine-admin"])


def _engine_service(session: Session = Depends(get_session)) -> NationalTeamEngineService:
    return NationalTeamEngineService(session)


def _tournament_service(session: Session = Depends(get_session)) -> NationalTeamTournamentService:
    return NationalTeamTournamentService(session)


def _lifecycle_service(request: Request, session: Session = Depends(get_session)) -> NationalCompetitionLifecycleService:
    return NationalCompetitionLifecycleService(
        session,
        event_publisher=getattr(request.app.state, "event_publisher", None),
    )


def _entry_detail(payload: dict) -> NationalTeamEntryDetailResponse:
    return NationalTeamEntryDetailResponse.model_validate(payload)


def _lifecycle_detail(payload: dict) -> NationalTeamCompetitionLifecycleResponse:
    body = dict(payload)
    body["competition"] = NationalTeamCompetitionResponse.model_validate(payload["competition"], from_attributes=True)
    return NationalTeamCompetitionLifecycleResponse.model_validate(body)


def _raise_engine_http(exc: NationalTeamEngineError) -> None:
    detail = str(exc)
    if "not found" in detail.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    if "locked" in detail.lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


def _raise_tournament_http(exc: NationalTeamTournamentError) -> None:
    if exc.reason in {"competition_not_found", "entry_not_found", "player_not_found", "ad_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.reason) from exc
    if exc.reason in {"entry_manager_required"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.reason) from exc
    if exc.reason in {
        "competition_entry_not_open",
        "competition_entry_closed",
        "competition_already_live",
        "competition_completed",
        "free_players_already_claimed",
        "free_distribution_unavailable",
        "squad_limit_reached",
        "rental_contract_exists",
        "player_not_eligible",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.reason) from exc


def _raise_lifecycle_http(exc: NationalCompetitionLifecycleError) -> None:
    if exc.reason in {"competition_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.reason) from exc
    if exc.reason in {"entry_locked"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason) from exc
    if exc.reason in {
        "competition_entry_not_open",
        "competition_entry_closed",
        "competition_completed",
        "country_not_eligible",
        "duplicate_player",
        "invalid_squad_age",
        "player_age_missing",
        "squad_missing",
        "squad_too_small",
        "squad_too_large",
        "lifecycle_completed",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.reason) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.reason) from exc


@router.get("/competitions", response_model=list[NationalTeamCompetitionResponse])
def list_competitions(service: NationalTeamEngineService = Depends(_engine_service)):
    return [NationalTeamCompetitionResponse.model_validate(item, from_attributes=True) for item in service.list_competitions()]


@router.get("/competitions/{competition_id}", response_model=NationalTeamCompetitionResponse)
def get_competition(competition_id: str, service: NationalTeamEngineService = Depends(_engine_service)):
    competition = service.get_competition(competition_id)
    if competition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="National team competition was not found.")
    return NationalTeamCompetitionResponse.model_validate(competition, from_attributes=True)


@router.get("/rankings", response_model=list[NationalTeamCountryRankingResponse])
def list_country_rankings(
    limit: int = Query(default=50, ge=1, le=200),
    service: NationalCompetitionLifecycleService = Depends(_lifecycle_service),
):
    return [NationalTeamCountryRankingResponse.model_validate(item) for item in service.list_country_rankings(limit=limit)]


@router.get("/competitions/{competition_id}/lifecycle", response_model=NationalTeamCompetitionLifecycleResponse)
def get_competition_lifecycle(
    competition_id: str,
    session: Session = Depends(get_session),
    service: NationalCompetitionLifecycleService = Depends(_lifecycle_service),
):
    try:
        payload = service.get_lifecycle_payload(competition_id=competition_id)
        session.commit()
    except NationalCompetitionLifecycleError as exc:
        session.rollback()
        _raise_lifecycle_http(exc)
    return _lifecycle_detail(payload)


@router.post("/competitions/{competition_id}/entries", response_model=NationalTeamCompetitionEntryResponse)
def submit_competition_entry(
    competition_id: str,
    payload: NationalTeamCompetitionEntrySubmitRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: NationalCompetitionLifecycleService = Depends(_lifecycle_service),
):
    try:
        body = service.submit_entry(competition_id=competition_id, actor=current_user, payload=payload)
        session.commit()
    except NationalCompetitionLifecycleError as exc:
        session.rollback()
        _raise_lifecycle_http(exc)
    return NationalTeamCompetitionEntryResponse.model_validate(body)


@router.get("/entries/{entry_id}", response_model=NationalTeamEntryDetailResponse)
def get_entry(entry_id: str, session: Session = Depends(get_session), service: NationalTeamTournamentService = Depends(_tournament_service)):
    try:
        payload = service.build_entry_detail_payload(entry_id)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return _entry_detail(payload)


@router.get("/me/history", response_model=NationalTeamUserHistoryResponse)
def get_my_history(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    history = NationalTeamEngineService(session).user_history(user=current_user)
    return NationalTeamUserHistoryResponse(
        managed_entries=[NationalTeamEntryResponse.model_validate(item, from_attributes=True) for item in history["managed_entries"]],
        squad_memberships=[NationalTeamSquadMemberResponse.model_validate(item, from_attributes=True) for item in history["squad_memberships"]],
    )


@router.get("/competitions/{competition_id}/rental-pool", response_model=NationalTeamRentalPlayerCollectionResponse)
def list_rental_pool(
    competition_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    country_code: str | None = Query(default=None),
    real_only: bool = Query(default=False),
    preseeded_only: bool = Query(default=False),
    source_bucket: list[str] | None = Query(default=None),
    position: list[str] | None = Query(default=None),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        payload = service.list_rental_players(
            competition_id=competition_id,
            limit=limit,
            offset=offset,
            country_code=country_code,
            real_only=real_only,
            preseeded_only=preseeded_only,
            source_buckets=tuple(source_bucket or ()),
            positions=tuple(position or ()),
        )
    except NationalTeamTournamentError as exc:
        _raise_tournament_http(exc)
    return NationalTeamRentalPlayerCollectionResponse.model_validate(payload)


@router.post("/competitions/{competition_id}/auto-build-squad", response_model=NationalTeamAutoBuildResponse)
def auto_build_squad(
    competition_id: str,
    payload: NationalTeamAutoBuildRequest,
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        body = service.auto_build_squad(
            competition_id=competition_id,
            country_code=payload.country_code,
            budget_coin=payload.budget_coin,
            tactic=payload.tactic,
            real_only=payload.real_only,
            preseeded_only=payload.preseeded_only,
            source_buckets=payload.source_buckets,
            positions=payload.positions,
            tradable_only=payload.tradable_only,
        )
    except NationalTeamTournamentError as exc:
        _raise_tournament_http(exc)
    return NationalTeamAutoBuildResponse.model_validate(body)


@router.post("/entries/{entry_id}/free-players/claim", response_model=NationalTeamEntryDetailResponse)
def claim_free_players(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        payload = service.claim_free_players(entry_id=entry_id, actor=current_user)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return _entry_detail(payload)


@router.post("/entries/{entry_id}/rentals", response_model=NationalTeamEntryDetailResponse)
def rent_player(
    entry_id: str,
    payload: NationalTeamRentalCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        body = service.rent_player(entry_id=entry_id, actor=current_user, player_id=payload.player_id, shirt_number=payload.shirt_number)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    except InsufficientBalanceError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _entry_detail(body)


@router.get("/entries/{entry_id}/rental-status", response_model=NationalTeamRentalStatusResponse)
def get_rental_status(entry_id: str, session: Session = Depends(get_session), service: NationalTeamTournamentService = Depends(_tournament_service)):
    try:
        payload = service.build_rental_status_payload(entry_id=entry_id)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return NationalTeamRentalStatusResponse.model_validate(payload)


@router.get("/competitions/{competition_id}/presentation", response_model=NationalTeamCompetitionPresentationResponse)
def get_competition_presentation(
    competition_id: str,
    session: Session = Depends(get_session),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        payload = service.build_competition_presentation_payload(competition_id=competition_id)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return NationalTeamCompetitionPresentationResponse.model_validate(payload)


@router.get("/competitions/{competition_id}/theme", response_model=TournamentThemeResponse | None)
def get_theme(competition_id: str, service: NationalTeamTournamentService = Depends(_tournament_service)):
    try:
        payload = service.get_theme(competition_id=competition_id)
    except NationalTeamTournamentError as exc:
        _raise_tournament_http(exc)
    return TournamentThemeResponse.model_validate(payload) if payload is not None else None


@router.get("/competitions/{competition_id}/ads/active", response_model=list[StadiumAdResponse])
def get_active_ads(competition_id: str, service: NationalTeamTournamentService = Depends(_tournament_service)):
    try:
        payload = service.list_active_ads(competition_id=competition_id)
    except NationalTeamTournamentError as exc:
        _raise_tournament_http(exc)
    return [StadiumAdResponse.model_validate(item) for item in payload]


@router.get("/competitions/{competition_id}/story-events", response_model=list[StoryEventResponse])
def list_story_events(
    competition_id: str,
    match_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        payload = service.list_story_events(competition_id=competition_id, match_id=match_id, limit=limit)
    except NationalTeamTournamentError as exc:
        _raise_tournament_http(exc)
    return [StoryEventResponse.model_validate(item) for item in payload]


@router.post("/competitions/{competition_id}/gifts", response_model=NationalTeamTournamentGiftResponse)
def send_tournament_gift(
    competition_id: str,
    payload: NationalTeamTournamentGiftRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        body = service.send_tournament_gift(competition_id=competition_id, actor=current_user, payload=payload)
        session.commit()
    except (NationalTeamTournamentError, InsufficientBalanceError) as exc:
        session.rollback()
        if isinstance(exc, NationalTeamTournamentError):
            _raise_tournament_http(exc)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return NationalTeamTournamentGiftResponse.model_validate(body)


@admin_router.post("/competitions", response_model=NationalTeamCompetitionResponse)
def create_competition(payload: NationalTeamCompetitionCreateRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    service = NationalTeamEngineService(session)
    try:
        competition = service.create_competition(payload=payload, actor=current_admin)
    except NationalTeamEngineError as exc:
        session.rollback()
        _raise_engine_http(exc)
    session.commit()
    session.refresh(competition)
    return NationalTeamCompetitionResponse.model_validate(competition, from_attributes=True)


@admin_router.post("/competitions/seed-defaults", response_model=list[NationalTeamCompetitionResponse])
def seed_default_competitions(
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        payload = service.seed_default_competitions(actor=current_admin)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return [NationalTeamCompetitionResponse.model_validate(item) for item in payload]


@admin_router.post("/competitions/{competition_id}/entries/lock", response_model=NationalTeamCompetitionLifecycleResponse)
def lock_competition_entries(
    competition_id: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
    service: NationalCompetitionLifecycleService = Depends(_lifecycle_service),
):
    try:
        payload = service.lock_entries(competition_id=competition_id)
        session.commit()
    except NationalCompetitionLifecycleError as exc:
        session.rollback()
        _raise_lifecycle_http(exc)
    return _lifecycle_detail(payload)


@admin_router.post("/competitions/{competition_id}/lifecycle/advance", response_model=NationalTeamCompetitionLifecycleResponse)
def advance_competition_lifecycle(
    competition_id: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
    service: NationalCompetitionLifecycleService = Depends(_lifecycle_service),
):
    try:
        payload = service.advance_lifecycle(competition_id=competition_id)
        session.commit()
    except NationalCompetitionLifecycleError as exc:
        session.rollback()
        _raise_lifecycle_http(exc)
    return _lifecycle_detail(payload)


@admin_router.post("/competitions/{competition_id}/entries", response_model=NationalTeamEntryResponse)
def upsert_entry(competition_id: str, payload: NationalTeamEntryUpsertRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    service = NationalTeamEngineService(session)
    try:
        entry = service.upsert_entry(competition_id=competition_id, payload=payload, actor=current_admin)
    except NationalTeamEngineError as exc:
        session.rollback()
        _raise_engine_http(exc)
    session.commit()
    session.refresh(entry)
    return NationalTeamEntryResponse.model_validate(entry, from_attributes=True)


@admin_router.post("/entries/{entry_id}/squad", response_model=NationalTeamEntryDetailResponse)
def upsert_squad(entry_id: str, payload: NationalTeamSquadUpsertRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
    service = NationalTeamEngineService(session)
    try:
        service.upsert_squad(entry_id=entry_id, members=payload.members, actor=current_admin)
        session.commit()
    except NationalTeamEngineError as exc:
        session.rollback()
        _raise_engine_http(exc)
    refreshed = NationalTeamTournamentService(session).build_entry_detail_payload(entry_id)
    return _entry_detail(refreshed)


@admin_router.put("/competitions/{competition_id}/theme", response_model=TournamentThemeResponse)
def upsert_theme(
    competition_id: str,
    payload: TournamentThemeUpsertRequest,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        body = service.upsert_theme(competition_id=competition_id, payload=payload, actor=current_admin)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return TournamentThemeResponse.model_validate(body)


@admin_router.get("/competitions/{competition_id}/ads", response_model=list[StadiumAdResponse])
def list_competition_ads(competition_id: str, service: NationalTeamTournamentService = Depends(_tournament_service), _admin: User = Depends(get_current_admin)):
    try:
        payload = service.list_ads(competition_id=competition_id)
    except NationalTeamTournamentError as exc:
        _raise_tournament_http(exc)
    return [StadiumAdResponse.model_validate(item) for item in payload]


@admin_router.post("/competitions/{competition_id}/ads", response_model=StadiumAdResponse, status_code=status.HTTP_201_CREATED)
def create_competition_ad(
    competition_id: str,
    payload: StadiumAdUpsertRequest,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        body = service.upsert_ad(competition_id=competition_id, payload=payload, actor=current_admin)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return StadiumAdResponse.model_validate(body)


@admin_router.put("/competitions/{competition_id}/ads/{ad_id}", response_model=StadiumAdResponse)
def update_competition_ad(
    competition_id: str,
    ad_id: str,
    payload: StadiumAdUpsertRequest,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        body = service.upsert_ad(competition_id=competition_id, payload=payload, actor=current_admin, ad_id=ad_id)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return StadiumAdResponse.model_validate(body)


@admin_router.post("/competitions/{competition_id}/story-events/generate", response_model=dict)
def generate_story_events(
    competition_id: str,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    try:
        payload = service.generate_story_events(competition_id=competition_id, actor=current_admin)
        session.commit()
    except NationalTeamTournamentError as exc:
        session.rollback()
        _raise_tournament_http(exc)
    return payload


@admin_router.post("/competitions/{competition_id}/rentals/cleanup", response_model=dict)
def cleanup_competition_rentals(
    competition_id: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    payload = service.cleanup_expired_rentals(competition_id=competition_id)
    session.commit()
    return payload


@admin_router.post("/competitions/{competition_id}/ads/rotate", response_model=dict)
def rotate_competition_ads(
    competition_id: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(get_current_admin),
    service: NationalTeamTournamentService = Depends(_tournament_service),
):
    payload = service.rotate_ads(competition_id=competition_id)
    session.commit()
    return payload
