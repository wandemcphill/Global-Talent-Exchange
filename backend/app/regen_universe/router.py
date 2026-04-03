from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.core.cache_namespaces import REGEN_UNIVERSE_CACHE_NAMESPACE
from app.core.pagination import build_pagination_meta, paginate_sequence, resolve_pagination
from app.core.response_cache import get_response_cache
from app.core.task_queue import NullTaskQueueBackend, get_task_queue_backend
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.user import User
from app.models.youth_tournament import YouthTournament
from app.regen_universe.expansion_service import (
    RegenUniverseExpansionError,
    RegenUniverseExpansionNotFoundError,
    RegenUniverseExpansionService,
    RegenUniverseExpansionValidationError,
)
from app.regen_universe.models import RegenHallOfFame, RegenRankingSnapshot
from app.regen_universe.service import RegenUniverseError, RegenUniverseService
from app.schemas.regen_universe import (
    RegenAwardResultView,
    RegenAwardResultPageView,
    RegenBloodlinesView,
    RegenHallOfFameView,
    RegenRisingStarsView,
    RegenRankingLeaderboardView,
    RegenSeasonCloseRequest,
    RegenSeasonCreateRequest,
    RegenSeasonPageView,
    RegenSeasonView,
    RegenScoutingFeedView,
    RegenUniverseCloseResultView,
    RegenUniversePlayerLookupView,
    RegenUniversePlayerShowcaseView,
)
from app.schemas.regen_universe_expansion import (
    NationalRegenPreseedRequest,
    NationalRegenSeedPageView,
    NationalRegenSeedView,
    RegenEvolutionResultView,
    RegenGenerationTrackingView,
    RegenUniverseJobRunView,
    YouthTournamentCreateRequest,
    YouthTournamentPageView,
    YouthTournamentView,
)
from app.workers.jobs import (
    regen_dna_evolution_job,
    regen_rivalry_detection_job,
    regen_story_regeneration_job,
    regen_tournament_scheduling_job,
)

router = APIRouter(prefix="/regen-universe", tags=["regen-universe"])
admin_router = APIRouter(prefix="/admin/regen-universe", tags=["regen-universe-admin"])

ModelT = TypeVar("ModelT")


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


def _invalidate_regen_universe_cache(request: Request | None) -> None:
    if request is None:
        return
    get_response_cache(request.app).invalidate(REGEN_UNIVERSE_CACHE_NAMESPACE)


def _cached_response(
    request: Request,
    *,
    model_type: type[ModelT],
    builder: Callable[[], ModelT | dict[str, object]],
    scope_key: str | None = None,
) -> ModelT:
    settings = request.app.state.settings
    if settings.api_cache_enabled:
        cached_payload = get_response_cache(request.app).get_json(
            namespace=REGEN_UNIVERSE_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
            scope_key=scope_key,
        )
        if cached_payload is not None:
            return model_type.model_validate(cached_payload)
    payload = builder()
    response = payload if isinstance(payload, model_type) else model_type.model_validate(payload)
    if settings.api_cache_enabled:
        get_response_cache(request.app).set_json(
            namespace=REGEN_UNIVERSE_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
            scope_key=scope_key,
            payload=response.model_dump(mode="json"),
            ttl_seconds=settings.regen_universe_cache_ttl_seconds,
        )
    return response


def _enqueue_regen_job(
    request: Request,
    *,
    actor: User,
    task_name: str,
    callable_,
    kwargs: dict[str, object],
) -> RegenUniverseJobRunView:
    task_queue = get_task_queue_backend(request.app)
    if isinstance(task_queue, NullTaskQueueBackend):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Regen universe worker queue is unavailable.",
        )
    try:
        execution = task_queue.enqueue(
            name=task_name,
            callable_=callable_,
            kwargs=kwargs,
            timeout_seconds=300,
            retry_intervals_seconds=(10, 30, 60),
            owner_user_id=actor.id,
            meta=kwargs,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Regen universe worker queue is unavailable.",
        ) from exc
    return RegenUniverseJobRunView(
        job_id=execution.job_id,
        name=execution.name,
        status=execution.status,
        queued_at=execution.queued_at,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error=execution.error,
        result=execution.result,
    )


@router.get("/seasons", response_model=RegenSeasonPageView)
def list_regen_seasons(
    request: Request,
    active_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> RegenSeasonPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenSeasonPageView:
        service = RegenUniverseService(session)
        items = [
            RegenSeasonView.model_validate(service._season_payload(item))
            for item in service.list_seasons(active_only=active_only)
        ]
        page_items, pagination = paginate_sequence(items, params=params)
        return RegenSeasonPageView(items=page_items, pagination=pagination)

    return _cached_response(request, model_type=RegenSeasonPageView, builder=build)


@router.get("/awards", response_model=RegenAwardResultPageView)
def list_regen_awards(
    request: Request,
    season_id: str | None = Query(default=None),
    award_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> RegenAwardResultPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenAwardResultPageView:
        items = [
            RegenAwardResultView.model_validate(item)
            for item in RegenUniverseService(session).list_awards(season_id=season_id, award_code=award_code)
        ]
        page_items, pagination = paginate_sequence(items, params=params)
        return RegenAwardResultPageView(items=page_items, pagination=pagination)

    return _cached_response(request, model_type=RegenAwardResultPageView, builder=build)


@router.get("/rankings", response_model=RegenRankingLeaderboardView)
def list_regen_rankings(
    request: Request,
    season_id: str | None = Query(default=None),
    category: str = Query(default="overall"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> RegenRankingLeaderboardView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenRankingLeaderboardView:
        service = RegenUniverseService(session)
        payload = service.list_rankings(
            season_id=season_id,
            category=category,
            limit=params.per_page,
            offset=params.offset,
        )
        season_payload = payload.get("season")
        total = 0
        if isinstance(season_payload, dict) and season_payload.get("id"):
            total = int(
                session.scalar(
                    select(func.count())
                    .select_from(RegenRankingSnapshot)
                    .where(
                        RegenRankingSnapshot.season_id == season_payload["id"],
                        RegenRankingSnapshot.category == category,
                    )
                )
                or 0
            )
        payload["pagination"] = build_pagination_meta(params=params, total=total).model_dump(mode="json")
        return RegenRankingLeaderboardView.model_validate(payload)

    return _cached_response(request, model_type=RegenRankingLeaderboardView, builder=build)


@router.get("/hall-of-fame", response_model=RegenHallOfFameView)
def list_regen_hall_of_fame(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> RegenHallOfFameView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenHallOfFameView:
        payload = RegenUniverseService(session).list_hall_of_fame(limit=params.per_page, offset=params.offset)
        total = int(session.scalar(select(func.count()).select_from(RegenHallOfFame)) or 0)
        payload["pagination"] = build_pagination_meta(params=params, total=total).model_dump(mode="json")
        return RegenHallOfFameView.model_validate(payload)

    return _cached_response(request, model_type=RegenHallOfFameView, builder=build)


@router.get("/players/{player_id}", response_model=RegenUniversePlayerShowcaseView)
def get_regen_player_showcase(
    request: Request,
    player_id: str,
    session: Session = Depends(get_session),
) -> RegenUniversePlayerShowcaseView:
    def build() -> RegenUniversePlayerShowcaseView:
        payload = RegenUniverseService(session).get_player_showcase(player_id)
        if payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="regen_universe_player_not_found")
        return RegenUniversePlayerShowcaseView.model_validate(payload)

    return _cached_response(
        request,
        model_type=RegenUniversePlayerShowcaseView,
        builder=build,
        scope_key=player_id,
    )


@router.get("/player/{player_id}", response_model=RegenUniversePlayerLookupView)
def get_regen_player(
    request: Request,
    player_id: str,
    session: Session = Depends(get_session),
) -> RegenUniversePlayerLookupView:
    def build() -> RegenUniversePlayerLookupView:
        payload = RegenUniverseService(session).get_player_lookup(player_id)
        if payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="regen_universe_player_not_found")
        return RegenUniversePlayerLookupView.model_validate(payload)

    return _cached_response(
        request,
        model_type=RegenUniversePlayerLookupView,
        builder=build,
        scope_key=player_id,
    )


@router.get("/rising-stars", response_model=RegenRisingStarsView)
def list_regen_rising_stars(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    age_max: int = Query(default=21, ge=16, le=30),
    session: Session = Depends(get_session),
) -> RegenRisingStarsView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenRisingStarsView:
        payload = RegenUniverseService(session).list_rising_stars(
            limit=params.per_page,
            offset=params.offset,
            age_max=age_max,
        )
        total = int(payload.pop("total", 0))
        payload["pagination"] = build_pagination_meta(params=params, total=total).model_dump(mode="json")
        return RegenRisingStarsView.model_validate(payload)

    return _cached_response(request, model_type=RegenRisingStarsView, builder=build)


@router.get("/bloodlines", response_model=RegenBloodlinesView)
def list_regen_bloodlines(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> RegenBloodlinesView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenBloodlinesView:
        payload = RegenUniverseService(session).list_bloodlines(limit=params.per_page, offset=params.offset)
        total = int(payload.pop("total", 0))
        payload["pagination"] = build_pagination_meta(params=params, total=total).model_dump(mode="json")
        return RegenBloodlinesView.model_validate(payload)

    return _cached_response(request, model_type=RegenBloodlinesView, builder=build)


@router.get("/scouting-feed", response_model=RegenScoutingFeedView)
def list_regen_scouting_feed(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> RegenScoutingFeedView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> RegenScoutingFeedView:
        payload = RegenUniverseService(session).list_scouting_feed(limit=params.per_page, offset=params.offset)
        total = int(payload.pop("total", 0))
        payload["pagination"] = build_pagination_meta(params=params, total=total).model_dump(mode="json")
        return RegenScoutingFeedView.model_validate(payload)

    return _cached_response(request, model_type=RegenScoutingFeedView, builder=build)


@router.get("/youth-tournaments", response_model=YouthTournamentPageView)
def list_youth_tournaments(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> YouthTournamentPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> YouthTournamentPageView:
        service = RegenUniverseExpansionService(session)
        total_stmt = select(func.count()).select_from(YouthTournament)
        if status_filter:
            total_stmt = total_stmt.where(YouthTournament.status == status_filter)
        total = int(session.scalar(total_stmt) or 0)
        items = [
            YouthTournamentView.model_validate(item)
            for item in service.list_youth_tournaments(
                status=status_filter,
                limit=params.per_page,
                offset=params.offset,
            )
        ]
        return YouthTournamentPageView(
            items=items,
            pagination=build_pagination_meta(params=params, total=total),
        )

    return _cached_response(request, model_type=YouthTournamentPageView, builder=build)


@router.get("/youth-tournaments/{tournament_id}", response_model=YouthTournamentView)
def get_youth_tournament(
    request: Request,
    tournament_id: str,
    session: Session = Depends(get_session),
) -> YouthTournamentView:
    def build() -> YouthTournamentView:
        try:
            payload = RegenUniverseExpansionService(session).get_youth_tournament(tournament_id)
        except RegenUniverseExpansionError as exc:
            raise_regen_universe_expansion_http_exception(exc)
        return YouthTournamentView.model_validate(payload)

    return _cached_response(
        request,
        model_type=YouthTournamentView,
        builder=build,
        scope_key=tournament_id,
    )


@router.get("/national-regens", response_model=NationalRegenSeedPageView)
def list_national_regens(
    request: Request,
    country_code: str | None = Query(default=None),
    seed_type: str | None = Query(default=None),
    preseed_batch: str | None = Query(default=None),
    age_min: int | None = Query(default=None, ge=0, le=99),
    age_max: int | None = Query(default=None, ge=0, le=99),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=100, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
) -> NationalRegenSeedPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)

    def build() -> NationalRegenSeedPageView:
        service = RegenUniverseExpansionService(session)
        total_stmt = select(NationalRegenSeed).order_by(NationalRegenSeed.id.asc())
        if country_code:
            total_stmt = total_stmt.where(NationalRegenSeed.country_code == country_code.strip().upper())
        if seed_type:
            total_stmt = total_stmt.where(NationalRegenSeed.seed_type == seed_type.strip().lower())
        if preseed_batch:
            total_stmt = total_stmt.where(NationalRegenSeed.preseed_batch == preseed_batch.strip())
        seeds = list(session.scalars(total_stmt).all())
        if age_min is not None or age_max is not None:
            filtered: list[NationalRegenSeed] = []
            for seed in seeds:
                age = service._legacy_national_seed_age(seed)
                if age is None:
                    continue
                if age_min is not None and age < age_min:
                    continue
                if age_max is not None and age > age_max:
                    continue
                filtered.append(seed)
            seeds = filtered
        total = len(seeds)
        items = [
            NationalRegenSeedView.model_validate(item)
            for item in service.list_preseeded_national_regens(
                country_code=country_code,
                seed_type=seed_type,
                preseed_batch=preseed_batch,
                age_min=age_min,
                age_max=age_max,
                limit=params.per_page,
                offset=params.offset,
            )
        ]
        return NationalRegenSeedPageView(
            items=items,
            pagination=build_pagination_meta(params=params, total=total),
        )

    return _cached_response(request, model_type=NationalRegenSeedPageView, builder=build)


@router.get("/tracking", response_model=RegenGenerationTrackingView)
def get_regen_tracking(
    request: Request,
    session: Session = Depends(get_session),
) -> RegenGenerationTrackingView:
    return _cached_response(
        request,
        model_type=RegenGenerationTrackingView,
        builder=lambda: RegenGenerationTrackingView.model_validate(
            RegenUniverseExpansionService(session).build_regen_tracking()
        ),
    )


@admin_router.post("/seasons", response_model=RegenSeasonView)
def create_regen_season(
    payload: RegenSeasonCreateRequest,
    request: Request,
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
    _invalidate_regen_universe_cache(request)
    return RegenSeasonView.model_validate(service._season_payload(season))


@admin_router.post("/seasons/{season_id}/close", response_model=RegenUniverseCloseResultView)
def close_regen_season(
    season_id: str,
    payload: RegenSeasonCloseRequest,
    request: Request,
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
    _invalidate_regen_universe_cache(request)
    return RegenUniverseCloseResultView.model_validate(result)


@admin_router.post("/youth-tournaments", response_model=YouthTournamentView, status_code=status.HTTP_201_CREATED)
def create_youth_tournament(
    payload: YouthTournamentCreateRequest,
    request: Request,
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
    _invalidate_regen_universe_cache(request)
    return YouthTournamentView.model_validate(service.get_youth_tournament(tournament.id))


@admin_router.post(
    "/national-regens/preseed", response_model=NationalRegenSeedPageView, status_code=status.HTTP_201_CREATED
)
def preseed_national_regens(
    payload: NationalRegenPreseedRequest,
    request: Request,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> NationalRegenSeedPageView:
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
    _invalidate_regen_universe_cache(request)
    rendered = [NationalRegenSeedView.model_validate(item) for item in items]
    params = resolve_pagination(page=1, per_page=len(rendered) or 1)
    return NationalRegenSeedPageView(
        items=rendered,
        pagination=build_pagination_meta(params=params, total=len(rendered)),
    )


@admin_router.post("/seasons/{season_id}/evolution", response_model=RegenEvolutionResultView)
def apply_regen_evolution(
    season_id: str,
    request: Request,
    _actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RegenEvolutionResultView:
    service = RegenUniverseExpansionService(session)
    try:
        payload = service.apply_evolution_cycle(season_id=season_id)
    except RegenUniverseExpansionError as exc:
        raise_regen_universe_expansion_http_exception(exc)
    session.commit()
    _invalidate_regen_universe_cache(request)
    return RegenEvolutionResultView.model_validate(payload)


@admin_router.post(
    "/jobs/story-regeneration",
    response_model=RegenUniverseJobRunView,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_story_regeneration_job(
    request: Request,
    player_id: str | None = Query(default=None),
    actor: User = Depends(get_current_admin),
) -> RegenUniverseJobRunView:
    return _enqueue_regen_job(
        request,
        actor=actor,
        task_name="regen_universe.story_regeneration",
        callable_=regen_story_regeneration_job,
        kwargs={"player_id": player_id},
    )


@admin_router.post(
    "/jobs/rivalry-detection",
    response_model=RegenUniverseJobRunView,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_rivalry_detection_job(
    request: Request,
    player_id: str | None = Query(default=None),
    actor: User = Depends(get_current_admin),
) -> RegenUniverseJobRunView:
    return _enqueue_regen_job(
        request,
        actor=actor,
        task_name="regen_universe.rivalry_detection",
        callable_=regen_rivalry_detection_job,
        kwargs={"player_id": player_id},
    )


@admin_router.post(
    "/jobs/dna-evolution",
    response_model=RegenUniverseJobRunView,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_dna_evolution_job(
    request: Request,
    player_id: str | None = Query(default=None),
    actor: User = Depends(get_current_admin),
) -> RegenUniverseJobRunView:
    return _enqueue_regen_job(
        request,
        actor=actor,
        task_name="regen_universe.dna_evolution",
        callable_=regen_dna_evolution_job,
        kwargs={"player_id": player_id},
    )


@admin_router.post(
    "/jobs/tournament-scheduling",
    response_model=RegenUniverseJobRunView,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_tournament_scheduling_job(
    request: Request,
    days_ahead: int = Query(default=21, ge=1, le=90),
    actor: User = Depends(get_current_admin),
) -> RegenUniverseJobRunView:
    return _enqueue_regen_job(
        request,
        actor=actor,
        task_name="regen_universe.tournament_scheduling",
        callable_=regen_tournament_scheduling_job,
        kwargs={"days_ahead": days_ahead},
    )
