from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.regen_universe.expansion_service import (
    RegenUniverseExpansionError,
    RegenUniverseExpansionNotFoundError,
    RegenUniverseExpansionService,
    RegenUniverseExpansionValidationError,
)
from app.regen_universe.service import RegenUniverseError, RegenUniverseService
from app.schemas.regen_universe import (
    RegenAwardResultView,
    RegenBloodlinesView,
    RegenHallOfFameView,
    RegenRisingStarsView,
    RegenRankingLeaderboardView,
    RegenSeasonCloseRequest,
    RegenSeasonCreateRequest,
    RegenSeasonView,
    RegenScoutingFeedView,
    RegenUniverseCloseResultView,
    RegenUniversePlayerLookupView,
    RegenUniversePlayerShowcaseView,
)
from app.schemas.regen_universe_expansion import (
    NationalRegenPreseedRequest,
    NationalRegenSeedView,
    RegenEvolutionResultView,
    RegenGenerationTrackingView,
    RegenUniverseJobRunView,
    YouthTournamentCreateRequest,
    YouthTournamentView,
)


router = APIRouter(prefix="/regen-universe", tags=["regen-universe"])
admin_router = APIRouter(prefix="/admin/regen-universe", tags=["regen-universe-admin"])


def raise_regen_universe_expansion_http_exception(exc: RegenUniverseExpansionError) -> None:
    if isinstance(exc, RegenUniverseExpansionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RegenUniverseExpansionValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def _job_payload(job) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "name": job.name,
        "status": job.status,
        "queued_at": job.queued_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error,
        "result": job.result,
    }


@router.get("/seasons", response_model=list[RegenSeasonView])
def list_regen_seasons(
    active_only: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> list[RegenSeasonView]:
    service = RegenUniverseService(session)
    return [
        RegenSeasonView.model_validate(service._season_payload(item))
        for item in service.list_seasons(active_only=active_only)
    ]


@router.get("/awards", response_model=list[RegenAwardResultView])
def list_regen_awards(
    season_id: str | None = Query(default=None),
    award_code: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[RegenAwardResultView]:
    return [
        RegenAwardResultView.model_validate(item)
        for item in RegenUniverseService(session).list_awards(season_id=season_id, award_code=award_code)
    ]


@router.get("/rankings", response_model=RegenRankingLeaderboardView)
def list_regen_rankings(
    season_id: str | None = Query(default=None),
    category: str = Query(default="overall"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> RegenRankingLeaderboardView:
    return RegenRankingLeaderboardView.model_validate(
        RegenUniverseService(session).list_rankings(season_id=season_id, category=category, limit=limit)
    )


@router.get("/hall-of-fame", response_model=RegenHallOfFameView)
def list_regen_hall_of_fame(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> RegenHallOfFameView:
    return RegenHallOfFameView.model_validate(RegenUniverseService(session).list_hall_of_fame(limit=limit))


@router.get("/players/{player_id}", response_model=RegenUniversePlayerShowcaseView)
def get_regen_player_showcase(
    player_id: str,
    session: Session = Depends(get_session),
) -> RegenUniversePlayerShowcaseView:
    payload = RegenUniverseService(session).get_player_showcase(player_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="regen_universe_player_not_found")
    return RegenUniversePlayerShowcaseView.model_validate(payload)


@router.get("/player/{player_id}", response_model=RegenUniversePlayerLookupView)
def get_regen_player(
    player_id: str,
    session: Session = Depends(get_session),
) -> RegenUniversePlayerLookupView:
    payload = RegenUniverseService(session).get_player_lookup(player_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="regen_universe_player_not_found")
    return RegenUniversePlayerLookupView.model_validate(payload)


@router.get("/rising-stars", response_model=RegenRisingStarsView)
def list_regen_rising_stars(
    limit: int = Query(default=20, ge=1, le=100),
    age_max: int = Query(default=21, ge=16, le=30),
    session: Session = Depends(get_session),
) -> RegenRisingStarsView:
    return RegenRisingStarsView.model_validate(
        RegenUniverseService(session).list_rising_stars(limit=limit, age_max=age_max)
    )


@router.get("/bloodlines", response_model=RegenBloodlinesView)
def list_regen_bloodlines(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> RegenBloodlinesView:
    return RegenBloodlinesView.model_validate(RegenUniverseService(session).list_bloodlines(limit=limit))


@router.get("/scouting-feed", response_model=RegenScoutingFeedView)
def list_regen_scouting_feed(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> RegenScoutingFeedView:
    return RegenScoutingFeedView.model_validate(RegenUniverseService(session).list_scouting_feed(limit=limit))


@router.get("/youth-tournaments", response_model=list[YouthTournamentView])
def list_youth_tournaments(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> list[YouthTournamentView]:
    return [
        YouthTournamentView.model_validate(item)
        for item in RegenUniverseExpansionService(session).list_youth_tournaments(status=status_filter, limit=limit)
    ]


@router.get("/youth-tournaments/{tournament_id}", response_model=YouthTournamentView)
def get_youth_tournament(
    tournament_id: str,
    session: Session = Depends(get_session),
) -> YouthTournamentView:
    try:
        payload = RegenUniverseExpansionService(session).get_youth_tournament(tournament_id)
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    return YouthTournamentView.model_validate(payload)


@router.get("/national-regens", response_model=list[NationalRegenSeedView])
def list_national_regens(
    country_code: str | None = Query(default=None),
    seed_type: str | None = Query(default=None),
    preseed_batch: str | None = Query(default=None),
    age_min: int | None = Query(default=None, ge=0, le=99),
    age_max: int | None = Query(default=None, ge=0, le=99),
    limit: int = Query(default=100, ge=1, le=250),
    session: Session = Depends(get_session),
) -> list[NationalRegenSeedView]:
    return [
        NationalRegenSeedView.model_validate(item)
        for item in RegenUniverseExpansionService(session).list_preseeded_national_regens(
            country_code=country_code,
            seed_type=seed_type,
            preseed_batch=preseed_batch,
            age_min=age_min,
            age_max=age_max,
            limit=limit,
        )
    ]


@router.get("/tracking", response_model=RegenGenerationTrackingView)
def get_regen_tracking(
    session: Session = Depends(get_session),
) -> RegenGenerationTrackingView:
    return RegenGenerationTrackingView.model_validate(
        RegenUniverseExpansionService(session).build_regen_tracking()
    )


@admin_router.post("/seasons", response_model=RegenSeasonView)
def create_regen_season(
    payload: RegenSeasonCreateRequest,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenSeasonView:
    service = RegenUniverseService(session)
    try:
        season = service.create_season(
            season_number=payload.season_number,
            start_date=payload.start_date,
            end_date=payload.end_date,
            source_ingestion_season_ids=payload.source_ingestion_season_ids,
            is_active=payload.is_active,
        )
    except RegenUniverseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return RegenSeasonView.model_validate(service._season_payload(season))


@admin_router.post("/seasons/{season_id}/close", response_model=RegenUniverseCloseResultView)
def close_regen_season(
    season_id: str,
    payload: RegenSeasonCloseRequest,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenUniverseCloseResultView:
    service = RegenUniverseService(session)
    try:
        result = service.close_season(
            season_id=season_id,
            close_date=payload.close_date,
            start_next_season=payload.start_next_season,
        )
    except RegenUniverseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return RegenUniverseCloseResultView.model_validate(result)


@admin_router.post("/youth-tournaments", response_model=YouthTournamentView, status_code=status.HTTP_201_CREATED)
def create_youth_tournament(
    payload: YouthTournamentCreateRequest,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> YouthTournamentView:
    service = RegenUniverseExpansionService(session)
    try:
        tournament = service.create_youth_tournament(
            name=payload.name,
            age_limit=payload.age_limit,
            rewards=payload.rewards,
            start_date=payload.start_date,
            end_date=payload.end_date,
            participant_club_ids=payload.participant_club_ids,
            participant_limit=payload.participant_limit,
            simulate_immediately=payload.simulate_immediately,
        )
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    session.commit()
    return YouthTournamentView.model_validate(service.get_youth_tournament(tournament.id))


@admin_router.post("/national-regens/preseed", response_model=list[NationalRegenSeedView], status_code=status.HTTP_201_CREATED)
def preseed_national_regens(
    payload: NationalRegenPreseedRequest,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[NationalRegenSeedView]:
    service = RegenUniverseExpansionService(session)
    try:
        items = service.seed_preseeded_national_regens(
            country_codes=payload.country_codes,
            seeds_per_country=payload.seeds_per_country,
            age_min=payload.age_min,
            age_max=payload.age_max,
            include_legendary_regens=payload.include_legendary_regens,
            preseed_batch=payload.preseed_batch,
        )
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    session.commit()
    return [NationalRegenSeedView.model_validate(item) for item in items]


@admin_router.post("/seasons/{season_id}/evolution", response_model=RegenEvolutionResultView)
def apply_regen_evolution(
    season_id: str,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenEvolutionResultView:
    service = RegenUniverseExpansionService(session)
    try:
        payload = service.apply_evolution_cycle(season_id=season_id)
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    session.commit()
    return RegenEvolutionResultView.model_validate(payload)


@admin_router.post("/jobs/story-regeneration", response_model=RegenUniverseJobRunView)
def run_story_regeneration_job(
    request: Request,
    player_id: str | None = Query(default=None),
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenUniverseJobRunView:
    service = RegenUniverseExpansionService(session)
    job = request.app.state.job_backend.run(
        "regen_universe.story_regeneration",
        lambda: service.regenerate_stories(player_id=player_id),
    )
    session.commit()
    return RegenUniverseJobRunView.model_validate(_job_payload(job))


@admin_router.post("/jobs/rivalry-detection", response_model=RegenUniverseJobRunView)
def run_rivalry_detection_job(
    request: Request,
    player_id: str | None = Query(default=None),
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenUniverseJobRunView:
    service = RegenUniverseExpansionService(session)
    job = request.app.state.job_backend.run(
        "regen_universe.rivalry_detection",
        lambda: service.detect_rivalries(player_id=player_id),
    )
    session.commit()
    return RegenUniverseJobRunView.model_validate(_job_payload(job))


@admin_router.post("/jobs/dna-evolution", response_model=RegenUniverseJobRunView)
def run_dna_evolution_job(
    request: Request,
    player_id: str | None = Query(default=None),
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenUniverseJobRunView:
    service = RegenUniverseExpansionService(session)
    job = request.app.state.job_backend.run(
        "regen_universe.dna_evolution",
        lambda: service.evolve_dna_profiles(player_id=player_id),
    )
    session.commit()
    return RegenUniverseJobRunView.model_validate(_job_payload(job))


@admin_router.post("/jobs/tournament-scheduling", response_model=RegenUniverseJobRunView)
def run_tournament_scheduling_job(
    request: Request,
    days_ahead: int = Query(default=21, ge=1, le=90),
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenUniverseJobRunView:
    service = RegenUniverseExpansionService(session)
    job = request.app.state.job_backend.run(
        "regen_universe.tournament_scheduling",
        lambda: service.schedule_youth_tournaments(days_ahead=days_ahead),
    )
    session.commit()
    return RegenUniverseJobRunView.model_validate(_job_payload(job))
