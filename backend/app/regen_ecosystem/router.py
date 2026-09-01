from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User
from app.schemas.regen_ecosystem import (
    AcademyGenerationRequest,
    AcademyGenerationResultView,
    AcademyPromotionView,
    AgentCreateRequest,
    AgentView,
    AwardVoteRequest,
    AwardVoteView,
    CareerEventView,
    RegenAwardHubView,
    RegenFeedItemView,
    RegenHubPlayerView,
    RegenLineageChainView,
    ScoutCreateRequest,
    ScoutDiscoveryResultView,
    ScoutReportView,
    ScoutView,
    YouthAcademyUpsertRequest,
    YouthAcademyView,
)
from app.services.regen_ecosystem_service import (
    RegenEcosystemError,
    RegenEcosystemNotFoundError,
    RegenEcosystemService,
    RegenEcosystemValidationError,
)

router = APIRouter(tags=["regen-ecosystem"])


def _service(session: Session = Depends(get_session)) -> RegenEcosystemService:
    return RegenEcosystemService(session)


def _raise(exc: RegenEcosystemError) -> None:
    if isinstance(exc, RegenEcosystemNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RegenEcosystemValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/academy", response_model=YouthAcademyView, status_code=status.HTTP_201_CREATED)
def upsert_academy(
    payload: YouthAcademyUpsertRequest,
    service: RegenEcosystemService = Depends(_service),
    actor: User = Depends(get_current_user),
) -> YouthAcademyView:
    if payload.club_user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage your own club's academy."
        )
    try:
        academy = service.upsert_academy(
            club_user_id=payload.club_user_id,
            club_id=payload.club_id,
            level=payload.level,
            scouting_regions=payload.scouting_regions,
            capacity=payload.capacity,
            upgrade_cost=payload.upgrade_cost,
        )
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return service._to_academy_view(academy)


@router.post("/academy/generate", response_model=AcademyGenerationResultView)
def generate_academy_players(
    payload: AcademyGenerationRequest,
    service: RegenEcosystemService = Depends(_service),
    actor: User = Depends(get_current_user),
) -> AcademyGenerationResultView:
    if payload.club_user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage your own club's academy."
        )
    try:
        result = service.generate_academy_players(
            club_user_id=payload.club_user_id,
            club_id=payload.club_id,
            season_label=payload.season_label,
        )
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return result


@router.post("/academy/promote/{player_id}", response_model=AcademyPromotionView)
def promote_academy_player(
    player_id: str,
    service: RegenEcosystemService = Depends(_service),
    _actor: User = Depends(get_current_user),
) -> AcademyPromotionView:
    try:
        result = service.promote_academy_player(player_id)
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return result


@router.post("/scouts", response_model=ScoutView, status_code=status.HTTP_201_CREATED)
def create_scout(
    payload: ScoutCreateRequest,
    service: RegenEcosystemService = Depends(_service),
    actor: User = Depends(get_current_user),
) -> ScoutView:
    if payload.club_user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only manage your own club's scouts.")
    try:
        scout = service.create_scout(
            club_user_id=payload.club_user_id,
            club_id=payload.club_id,
            region=payload.region,
            skill_rating=payload.skill_rating,
            specialty=payload.specialty,
        )
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return service._to_scout_view(scout)


@router.post("/scouts/{scout_id}/discover", response_model=ScoutDiscoveryResultView)
def discover_regens(
    scout_id: str,
    limit: int = Query(default=5, ge=1, le=25),
    service: RegenEcosystemService = Depends(_service),
    _actor: User = Depends(get_current_user),
) -> ScoutDiscoveryResultView:
    try:
        result = service.discover_regens(scout_id, limit=limit)
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return result


@router.get("/scout/report/{player_id}", response_model=ScoutReportView)
def get_scout_report(
    player_id: str,
    scout_id: str | None = Query(default=None),
    service: RegenEcosystemService = Depends(_service),
) -> ScoutReportView:
    try:
        return service.get_scout_report(player_id, scout_id=scout_id)
    except RegenEcosystemError as exc:
        _raise(exc)


@router.post("/agents", response_model=AgentView, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreateRequest,
    service: RegenEcosystemService = Depends(_service),
    _actor: User = Depends(get_current_user),
) -> AgentView:
    try:
        agent = service.create_agent(
            name=payload.name,
            negotiation_skill=payload.negotiation_skill,
            player_ids=payload.player_ids,
        )
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return service._to_agent_view(agent)


@router.post("/players/{player_id}/career-events", response_model=CareerEventView)
def trigger_career_event(
    player_id: str,
    event_type: str | None = Query(default=None),
    service: RegenEcosystemService = Depends(_service),
    _actor: User = Depends(get_current_user),
) -> CareerEventView:
    try:
        event = service.trigger_career_event(player_id, event_type=event_type)
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return service._to_career_event_view(event)


@router.get("/regens/feed", response_model=list[RegenFeedItemView])
def list_regen_feed(
    limit: int = Query(default=20, ge=1, le=100),
    service: RegenEcosystemService = Depends(_service),
) -> list[RegenFeedItemView]:
    return list(service.list_feed(limit=limit))


@router.get("/regens/top", response_model=list[RegenHubPlayerView])
def list_top_regens(
    limit: int = Query(default=20, ge=1, le=100),
    service: RegenEcosystemService = Depends(_service),
) -> list[RegenHubPlayerView]:
    return list(service.list_top_regens(limit=limit))


@router.get("/regens/rising", response_model=list[RegenHubPlayerView])
def list_rising_regens(
    limit: int = Query(default=20, ge=1, le=100),
    service: RegenEcosystemService = Depends(_service),
) -> list[RegenHubPlayerView]:
    return list(service.list_rising_regens(limit=limit))


@router.get("/regens/awards", response_model=list[RegenAwardHubView])
def list_regen_awards(
    season_id: str | None = Query(default=None),
    service: RegenEcosystemService = Depends(_service),
) -> list[RegenAwardHubView]:
    return list(service.list_awards(season_id=season_id))


@router.post("/regens/awards/{award_id}/vote", response_model=AwardVoteView, status_code=status.HTTP_201_CREATED)
def cast_award_vote(
    award_id: str,
    payload: AwardVoteRequest,
    service: RegenEcosystemService = Depends(_service),
    actor: User = Depends(get_current_user),
) -> AwardVoteView:
    if payload.user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only cast a vote as yourself.")
    try:
        vote = service.cast_award_vote(
            award_id,
            user_id=payload.user_id,
            player_id=payload.player_id,
            season_id=payload.season_id,
        )
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return service._to_vote_view(vote)


@router.get("/regens/{regen_id}/lineage", response_model=RegenLineageChainView)
def get_regen_lineage(
    regen_id: str,
    service: RegenEcosystemService = Depends(_service),
) -> RegenLineageChainView:
    try:
        return service.get_lineage_chain(regen_id)
    except RegenEcosystemError as exc:
        _raise(exc)


@router.post("/regens/jobs/{job_name}")
def run_regen_job(
    job_name: str,
    _: User = Depends(get_current_admin),
    service: RegenEcosystemService = Depends(_service),
) -> dict[str, object]:
    # These jobs bulk-generate academy intakes, scouting discoveries and career
    # events across the whole player universe. Left open they are both an
    # unauthenticated write to the regen population and a cheap amplification
    # vector, so they are admin-only.
    try:
        if job_name == "academy-weekly":
            result = service.run_weekly_academy_generation()
        elif job_name == "scouting-discovery":
            result = service.run_scouting_discovery_jobs()
        elif job_name == "potential-updates":
            result = service.run_potential_update_jobs()
        elif job_name == "career-events":
            result = service.run_career_event_jobs()
        else:
            raise RegenEcosystemValidationError("unknown_regen_job")
    except RegenEcosystemError as exc:
        _raise(exc)
    service.session.commit()
    return {"job_name": job_name, "result": result}


__all__ = ["router"]
