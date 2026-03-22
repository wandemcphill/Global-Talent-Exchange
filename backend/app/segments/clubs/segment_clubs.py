from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_session
from app.models.club_profile import ClubProfile
from app.models.scouting_intelligence import (
    AcademySupplySignal,
    HiddenPotentialEstimate,
    ScoutMission,
    ScoutReport,
    ScoutingNetwork,
    ScoutingNetworkAssignment,
    TalentDiscoveryBadge,
)
from app.schemas.club_branding_core import ClubCosmeticPurchaseCore
from app.schemas.club_requests import (
    BrandingUpsertRequest,
    CatalogPurchaseRequest,
    ClubCreateRequest,
    ClubUpdateRequest,
    JerseyCreateRequest,
    JerseyUpdateRequest,
)
from app.schemas.club_responses import (
    ClubBrandingView,
    ClubCatalogView,
    ClubJerseysView,
    ClubProfileView,
    ClubPurchasesView,
    ClubShowcaseView,
    ClubTrophiesView,
)
from app.schemas.scouting_intelligence import (
    AcademySupplySignalView,
    CompletedScoutMissionView,
    HiddenPotentialEstimateView,
    ManagerScoutingProfileUpsertRequest,
    ManagerScoutingProfileView,
    PlayerLifecycleProfileView,
    ScoutMissionCreateRequest,
    ScoutMissionView,
    ScoutReportView,
    ScoutingNetworkAssignmentCreateRequest,
    ScoutingNetworkAssignmentView,
    ScoutingNetworkCreateRequest,
    ScoutingPlanningView,
    ScoutingNetworkView,
    TalentDiscoveryBadgeView,
)
from app.services.club_branding_service import ClubBrandingService
from app.services.club_cosmetic_catalog_service import ClubCosmeticCatalogService
from app.services.club_jersey_service import ClubJerseyService
from app.services.club_purchase_service import ClubPurchaseService
from app.services.club_showcase_service import ClubShowcaseService
from app.services.club_trophy_service import ClubTrophyService
from app.services.scouting_intelligence_service import (
    ManagerProfileUpsert,
    ScoutMissionCreate,
    ScoutingIntelligenceService,
    ScoutingNetworkAssignmentCreate,
    ScoutingNetworkCreate,
)

router = APIRouter(prefix="/api/clubs", tags=["clubs"])


def _user_id(current_user) -> str:
    user_id = getattr(current_user, "id", None)
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_context_missing")
    return user_id


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, ValueError):
        detail = str(error)
        if detail == "club_slug_taken":
            status_code = status.HTTP_409_CONFLICT
        elif detail.endswith("_not_found"):
            status_code = status.HTTP_404_NOT_FOUND
        elif detail.endswith("_club_mismatch"):
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        return HTTPException(status_code=status_code, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _require_owned_club(session: Session, club_id: str, current_user) -> ClubProfile:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club_not_found")
    if club.owner_user_id != _user_id(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="club_owner_required")
    return club


def _get_scouting_service(session: Session) -> ScoutingIntelligenceService:
    return ScoutingIntelligenceService(session)


def _to_network_view(network: ScoutingNetwork) -> ScoutingNetworkView:
    return ScoutingNetworkView(
        id=network.id,
        club_id=network.club_id,
        manager_profile_id=network.manager_profile_id,
        network_name=network.network_name,
        region_code=network.region_code,
        region_name=network.region_name,
        specialty_code=network.specialty_code,
        quality_tier=network.quality_tier,
        scout_identity=network.scout_identity,
        scout_rating=network.scout_rating,
        weekly_cost_coin=network.weekly_cost_coin,
        report_cadence_days=network.report_cadence_days,
        active=network.active,
        metadata=network.metadata_json,
    )


def _to_assignment_view(assignment: ScoutingNetworkAssignment) -> ScoutingNetworkAssignmentView:
    return ScoutingNetworkAssignmentView(
        id=assignment.id,
        network_id=assignment.network_id,
        club_id=assignment.club_id,
        assignment_name=assignment.assignment_name,
        assignment_scope=assignment.assignment_scope,
        territory_code=assignment.territory_code,
        focus_position=assignment.focus_position,
        age_band_min=assignment.age_band_min,
        age_band_max=assignment.age_band_max,
        budget_profile=assignment.budget_profile,
        starts_on=assignment.starts_on,
        ends_on=assignment.ends_on,
        status=assignment.status,
        metadata=assignment.metadata_json,
    )


def _to_mission_view(mission: ScoutMission) -> ScoutMissionView:
    return ScoutMissionView(
        id=mission.id,
        club_id=mission.club_id,
        network_id=mission.network_id,
        manager_profile_id=mission.manager_profile_id,
        mission_name=mission.mission_name,
        mission_type=mission.mission_type,
        status=mission.status,
        target_position=mission.target_position,
        target_region=mission.target_region,
        target_age_min=mission.target_age_min,
        target_age_max=mission.target_age_max,
        budget_limit_coin=mission.budget_limit_coin,
        affordability_tier=mission.affordability_tier,
        mission_duration_days=mission.mission_duration_days,
        talent_type=mission.talent_type,
        include_academy=mission.include_academy,
        system_profile=mission.system_profile,
        completed_at=mission.completed_at,
        metadata=mission.metadata_json,
    )


def _to_report_view(report: ScoutReport) -> ScoutReportView:
    return ScoutReportView(
        id=report.id,
        mission_id=report.mission_id,
        network_id=report.network_id,
        club_id=report.club_id,
        regen_profile_id=report.regen_profile_id,
        academy_candidate_id=report.academy_candidate_id,
        player_id=report.player_id,
        recommendation_rank=report.recommendation_rank,
        lifecycle_phase=report.lifecycle_phase,
        confidence_bps=report.confidence_bps,
        fit_score=report.fit_score,
        potential_signal_score=report.potential_signal_score,
        value_signal_score=report.value_signal_score,
        hidden_gem_signal=report.hidden_gem_signal,
        current_ability_estimate=report.current_ability_estimate,
        future_potential_estimate=report.future_potential_estimate,
        value_hint_coin=report.value_hint_coin,
        summary_text=report.summary_text,
        tags=tuple(report.tags_json),
        metadata=report.metadata_json,
        created_at=report.created_at,
    )


def _to_hidden_potential_view(estimate: HiddenPotentialEstimate) -> HiddenPotentialEstimateView:
    return HiddenPotentialEstimateView(
        id=estimate.id,
        club_id=estimate.club_id,
        network_id=estimate.network_id,
        mission_id=estimate.mission_id,
        scout_report_id=estimate.scout_report_id,
        regen_profile_id=estimate.regen_profile_id,
        academy_candidate_id=estimate.academy_candidate_id,
        current_ability_low=estimate.current_ability_low,
        current_ability_high=estimate.current_ability_high,
        future_potential_low=estimate.future_potential_low,
        future_potential_high=estimate.future_potential_high,
        scout_confidence_bps=estimate.scout_confidence_bps,
        uncertainty_band=estimate.uncertainty_band,
        lifecycle_phase=estimate.lifecycle_phase,
        revealed_by_persona=estimate.revealed_by_persona,
        metadata=estimate.metadata_json,
        created_at=estimate.created_at,
    )


def _to_academy_signal_view(signal: AcademySupplySignal) -> AcademySupplySignalView:
    return AcademySupplySignalView(
        id=signal.id,
        club_id=signal.club_id,
        batch_id=signal.batch_id,
        signal_type=signal.signal_type,
        candidate_count=signal.candidate_count,
        standout_count=signal.standout_count,
        average_potential_high=signal.average_potential_high,
        visibility_score=signal.visibility_score,
        signal_status=signal.signal_status,
        summary_text=signal.summary_text,
        metadata=signal.metadata_json,
    )


def _to_badge_view(badge: TalentDiscoveryBadge) -> TalentDiscoveryBadgeView:
    return TalentDiscoveryBadgeView(
        id=badge.id,
        club_id=badge.club_id,
        regen_profile_id=badge.regen_profile_id,
        academy_candidate_id=badge.academy_candidate_id,
        badge_code=badge.badge_code,
        badge_name=badge.badge_name,
        evidence_level=badge.evidence_level,
        summary_text=badge.summary_text,
        awarded_at=badge.awarded_at,
        metadata=badge.metadata_json,
    )


@router.post("", response_model=ClubProfileView, status_code=status.HTTP_201_CREATED)
def create_club(
    payload: ClubCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubProfileView:
    try:
        club = ClubBrandingService(session).create_club_profile(owner_user_id=_user_id(current_user), payload=payload)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubProfileView(profile=ClubBrandingService(session).get_club_profile(club.id))


@router.get("/catalog", response_model=ClubCatalogView)
def get_catalog(session: Session = Depends(get_session)) -> ClubCatalogView:
    return ClubCatalogView(items=ClubCosmeticCatalogService(session).list_items())


@router.post("/catalog/purchase", response_model=ClubCosmeticPurchaseCore, status_code=status.HTTP_201_CREATED)
def purchase_catalog_item(
    payload: CatalogPurchaseRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubCosmeticPurchaseCore:
    try:
        purchase = ClubPurchaseService(session).purchase_catalog_item(
            buyer_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubCosmeticPurchaseCore.model_validate(purchase)


@router.patch("/{club_id}", response_model=ClubProfileView)
def update_club(
    club_id: str,
    payload: ClubUpdateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubProfileView:
    try:
        club = ClubBrandingService(session).update_club_profile(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubProfileView(profile=ClubBrandingService(session).get_club_profile(club.id))


@router.get("/{club_id}", response_model=ClubProfileView)
def get_club(club_id: str, session: Session = Depends(get_session)) -> ClubProfileView:
    try:
        profile = ClubBrandingService(session).get_club_profile(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubProfileView(profile=profile)


@router.get("/{club_id}/showcase", response_model=ClubShowcaseView)
def get_club_showcase(club_id: str, session: Session = Depends(get_session)) -> ClubShowcaseView:
    try:
        return ClubShowcaseService(session).get_showcase(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error


@router.get("/{club_id}/trophies", response_model=ClubTrophiesView)
def get_club_trophies(club_id: str, session: Session = Depends(get_session)) -> ClubTrophiesView:
    try:
        cabinet, trophies = ClubTrophyService(session).get_trophy_cabinet(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubTrophiesView(cabinet=cabinet, trophies=trophies)


@router.get("/{club_id}/scouting-intelligence/networks", response_model=tuple[ScoutingNetworkView, ...])
def list_scouting_intelligence_networks(
    club_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[ScoutingNetworkView, ...]:
    _require_owned_club(session, club_id, current_user)
    networks = session.scalars(
        select(ScoutingNetwork)
        .where(ScoutingNetwork.club_id == club_id)
        .order_by(ScoutingNetwork.active.desc(), ScoutingNetwork.created_at.desc())
    ).all()
    return tuple(_to_network_view(network) for network in networks)


@router.get("/{club_id}/scouting-intelligence/manager-profiles", response_model=tuple[ManagerScoutingProfileView, ...])
def list_scouting_intelligence_manager_profiles(
    club_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[ManagerScoutingProfileView, ...]:
    _require_owned_club(session, club_id, current_user)
    return _get_scouting_service(session).list_manager_profiles(club_id)


@router.post(
    "/{club_id}/scouting-intelligence/manager-profiles",
    response_model=ManagerScoutingProfileView,
    status_code=status.HTTP_201_CREATED,
)
def upsert_scouting_intelligence_manager_profile(
    club_id: str,
    payload: ManagerScoutingProfileUpsertRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ManagerScoutingProfileView:
    _require_owned_club(session, club_id, current_user)
    try:
        profile = _get_scouting_service(session).upsert_manager_profile(
            ManagerProfileUpsert(
                club_id=club_id,
                manager_code=payload.manager_code,
                manager_name=payload.manager_name,
                persona_code=payload.persona_code,
                preferred_system=payload.preferred_system,
                metadata=payload.metadata,
            )
        )
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return profile


@router.post(
    "/{club_id}/scouting-intelligence/networks",
    response_model=ScoutingNetworkView,
    status_code=status.HTTP_201_CREATED,
)
def create_scouting_intelligence_network(
    club_id: str,
    payload: ScoutingNetworkCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ScoutingNetworkView:
    _require_owned_club(session, club_id, current_user)
    try:
        network = _get_scouting_service(session).create_network(
            ScoutingNetworkCreate(
                club_id=club_id,
                manager_profile_id=payload.manager_profile_id,
                network_name=payload.network_name,
                region_code=payload.region_code,
                region_name=payload.region_name,
                specialty_code=payload.specialty_code,
                quality_tier=payload.quality_tier,
                weekly_cost_coin=payload.weekly_cost_coin,
                scout_identity=payload.scout_identity,
                report_cadence_days=payload.report_cadence_days,
                metadata=payload.metadata,
            )
        )
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return network


@router.get("/{club_id}/scouting-intelligence/assignments", response_model=tuple[ScoutingNetworkAssignmentView, ...])
def list_scouting_intelligence_assignments(
    club_id: str,
    network_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[ScoutingNetworkAssignmentView, ...]:
    _require_owned_club(session, club_id, current_user)
    statement = (
        select(ScoutingNetworkAssignment)
        .where(ScoutingNetworkAssignment.club_id == club_id)
        .order_by(ScoutingNetworkAssignment.starts_on.desc(), ScoutingNetworkAssignment.created_at.desc())
    )
    if network_id:
        statement = statement.where(ScoutingNetworkAssignment.network_id == network_id)
    assignments = session.scalars(statement).all()
    return tuple(_to_assignment_view(assignment) for assignment in assignments)


@router.post(
    "/{club_id}/scouting-intelligence/assignments",
    response_model=ScoutingNetworkAssignmentView,
    status_code=status.HTTP_201_CREATED,
)
def create_scouting_intelligence_assignment(
    club_id: str,
    payload: ScoutingNetworkAssignmentCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ScoutingNetworkAssignmentView:
    _require_owned_club(session, club_id, current_user)
    try:
        assignment = _get_scouting_service(session).assign_network(
            ScoutingNetworkAssignmentCreate(
                network_id=payload.network_id,
                club_id=club_id,
                assignment_name=payload.assignment_name,
                assignment_scope=payload.assignment_scope,
                territory_code=payload.territory_code,
                focus_position=payload.focus_position,
                age_band_min=payload.age_band_min,
                age_band_max=payload.age_band_max,
                budget_profile=payload.budget_profile,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                metadata=payload.metadata,
            )
        )
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return assignment


@router.get("/{club_id}/scouting-intelligence/missions", response_model=tuple[ScoutMissionView, ...])
def list_scouting_intelligence_missions(
    club_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[ScoutMissionView, ...]:
    _require_owned_club(session, club_id, current_user)
    statement = (
        select(ScoutMission)
        .where(ScoutMission.club_id == club_id)
        .order_by(ScoutMission.created_at.desc(), ScoutMission.id.desc())
    )
    if status_filter:
        statement = statement.where(ScoutMission.status == status_filter)
    missions = session.scalars(statement).all()
    return tuple(_to_mission_view(mission) for mission in missions)


@router.post(
    "/{club_id}/scouting-intelligence/missions",
    response_model=ScoutMissionView,
    status_code=status.HTTP_201_CREATED,
)
def create_scouting_intelligence_mission(
    club_id: str,
    payload: ScoutMissionCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ScoutMissionView:
    _require_owned_club(session, club_id, current_user)
    try:
        mission = _get_scouting_service(session).create_mission(
            ScoutMissionCreate(
                club_id=club_id,
                network_id=payload.network_id,
                manager_profile_id=payload.manager_profile_id,
                mission_name=payload.mission_name,
                mission_type=payload.mission_type,
                target_position=payload.target_position,
                target_region=payload.target_region,
                target_age_min=payload.target_age_min,
                target_age_max=payload.target_age_max,
                budget_limit_coin=payload.budget_limit_coin,
                affordability_tier=payload.affordability_tier,
                talent_type=payload.talent_type,
                include_academy=payload.include_academy,
                system_profile=payload.system_profile,
                mission_duration_days=payload.mission_duration_days,
                metadata=payload.metadata,
            )
        )
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return mission


@router.post("/{club_id}/scouting-intelligence/missions/{mission_id}/complete", response_model=CompletedScoutMissionView)
def complete_scouting_intelligence_mission(
    club_id: str,
    mission_id: str,
    limit: int = Query(default=5, ge=1, le=25),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> CompletedScoutMissionView:
    _require_owned_club(session, club_id, current_user)
    try:
        completed = _get_scouting_service(session).complete_mission(mission_id, limit=limit)
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return completed


@router.get("/{club_id}/scouting-intelligence/academy-supply-signals", response_model=tuple[AcademySupplySignalView, ...])
def list_scouting_intelligence_academy_supply_signals(
    club_id: str,
    refresh: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[AcademySupplySignalView, ...]:
    _require_owned_club(session, club_id, current_user)
    try:
        signals = _get_scouting_service(session).list_academy_supply_signals(club_id, refresh=refresh)
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return signals


@router.get("/{club_id}/scouting-intelligence/badges", response_model=tuple[TalentDiscoveryBadgeView, ...])
def list_scouting_intelligence_badges(
    club_id: str,
    mission_id: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[TalentDiscoveryBadgeView, ...]:
    _require_owned_club(session, club_id, current_user)
    return _get_scouting_service(session).list_talent_discovery_badges(club_id, mission_id=mission_id, limit=limit)


@router.get("/{club_id}/scouting-intelligence/lifecycle", response_model=tuple[PlayerLifecycleProfileView, ...])
def list_scouting_intelligence_lifecycle_profiles(
    club_id: str,
    player_id: list[str] | None = Query(default=None),
    sync_current_roster: bool = Query(default=False),
    limit: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> tuple[PlayerLifecycleProfileView, ...]:
    _require_owned_club(session, club_id, current_user)
    try:
        profiles = _get_scouting_service(session).list_player_lifecycle_profiles(
            club_id,
            player_ids=tuple(player_id or ()),
            sync_current_roster=sync_current_roster,
            limit=limit,
        )
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return profiles


@router.get("/{club_id}/scouting-intelligence/planning", response_model=ScoutingPlanningView)
def get_scouting_intelligence_planning(
    club_id: str,
    roster_limit: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ScoutingPlanningView:
    _require_owned_club(session, club_id, current_user)
    try:
        planning = _get_scouting_service(session).build_planning_dashboard(club_id, roster_limit=roster_limit)
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return planning


@router.get("/{club_id}/scouting-intelligence/missions/{mission_id}", response_model=CompletedScoutMissionView)
def get_scouting_intelligence_mission(
    club_id: str,
    mission_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> CompletedScoutMissionView:
    _require_owned_club(session, club_id, current_user)
    try:
        mission = _get_scouting_service(session).get_completed_mission(mission_id, club_id=club_id)
        session.commit()
    except Exception as error:  # noqa: BLE001
        session.rollback()
        raise _to_http_error(error) from error
    return mission


@router.post("/{club_id}/branding", response_model=ClubBrandingView, status_code=status.HTTP_201_CREATED)
@router.patch("/{club_id}/branding", response_model=ClubBrandingView)
def upsert_branding(
    club_id: str,
    payload: BrandingUpsertRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubBrandingView:
    try:
        profile, theme, assets = ClubBrandingService(session).upsert_branding(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubBrandingView(profile=profile, theme=theme, assets=assets)


@router.get("/{club_id}/branding", response_model=ClubBrandingView)
def get_branding(club_id: str, session: Session = Depends(get_session)) -> ClubBrandingView:
    try:
        profile, theme, assets = ClubBrandingService(session).get_branding(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubBrandingView(profile=profile, theme=theme, assets=assets)


@router.post("/{club_id}/jerseys", response_model=ClubJerseysView, status_code=status.HTTP_201_CREATED)
def create_jersey(
    club_id: str,
    payload: JerseyCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubJerseysView:
    try:
        ClubJerseyService(session).create_jersey(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubJerseysView(jerseys=ClubJerseyService(session).list_jerseys(club_id))


@router.patch("/{club_id}/jerseys/{jersey_id}", response_model=ClubJerseysView)
def update_jersey(
    club_id: str,
    jersey_id: str,
    payload: JerseyUpdateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubJerseysView:
    try:
        ClubJerseyService(session).update_jersey(
            club_id=club_id,
            jersey_id=jersey_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubJerseysView(jerseys=ClubJerseyService(session).list_jerseys(club_id))


@router.get("/{club_id}/jerseys", response_model=ClubJerseysView)
def list_jerseys(club_id: str, session: Session = Depends(get_session)) -> ClubJerseysView:
    try:
        jerseys = ClubJerseyService(session).list_jerseys(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubJerseysView(jerseys=jerseys)


@router.get("/{club_id}/purchases", response_model=ClubPurchasesView)
def list_purchases(
    club_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubPurchasesView:
    try:
        purchases = ClubPurchaseService(session).list_purchases(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubPurchasesView(purchases=purchases)
