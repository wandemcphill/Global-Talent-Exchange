from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.ingestion.models import Player
from app.models.regen import AcademyCandidate, AcademyIntakeBatch, RegenOriginMetadata, RegenProfile
from app.models.scouting_intelligence import (
    AcademySupplySignal,
    HiddenPotentialEstimate,
    ManagerScoutingProfile,
    PlayerLifecycleProfile,
    ScoutMission,
    ScoutReport,
    ScoutingNetwork,
    ScoutingNetworkAssignment,
    TalentDiscoveryBadge,
)
from app.schemas.scouting_intelligence import (
    AcademySupplySignalView,
    CompletedScoutMissionView,
    HiddenPotentialEstimateView,
    ManagerScoutingProfileView,
    PlayerLifecycleProfileView,
    ScoutMissionView,
    ScoutReportView,
    ScoutingNetworkAssignmentView,
    ScoutingPlanningView,
    ScoutingNetworkView,
    TalentDiscoveryBadgeView,
)
from app.services.regen_market_service import RegenMarketService, RegenRecommendationRequest, RegenSearchFilters

_MISSION_DURATIONS = {
    "short_scan": 7,
    "standard_assignment": 21,
    "deep_talent_search": 42,
}
_PERSONA_FACTORS = {
    "balanced": {"youth_bias": 0.15, "market_bias": 0.15, "tactical_bias": 0.15, "star_bias": 0.15, "accuracy_boost_bps": 150},
    "youth_developer": {"youth_bias": 0.55, "market_bias": 0.10, "tactical_bias": 0.15, "star_bias": 0.05, "accuracy_boost_bps": 550},
    "market_analyst": {"youth_bias": 0.20, "market_bias": 0.55, "tactical_bias": 0.10, "star_bias": 0.05, "accuracy_boost_bps": 450},
    "star_recruiter": {"youth_bias": 0.05, "market_bias": 0.15, "tactical_bias": 0.05, "star_bias": 0.60, "accuracy_boost_bps": 300},
    "tactical_specialist": {"youth_bias": 0.10, "market_bias": 0.10, "tactical_bias": 0.60, "star_bias": 0.05, "accuracy_boost_bps": 500},
}
_QUALITY_SCOUT_RATINGS = {
    "standard": 55,
    "advanced": 72,
    "elite": 88,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_age(date_of_birth: date | None, *, today: date | None = None) -> int:
    if date_of_birth is None:
        return 18
    current = today or date.today()
    years = current.year - date_of_birth.year
    if (current.month, current.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(0, years)


def _months_between(start_on: date, end_on: date) -> int:
    months = (end_on.year - start_on.year) * 12 + (end_on.month - start_on.month)
    if end_on.day < start_on.day:
        months -= 1
    return max(0, months)


@dataclass(frozen=True, slots=True)
class ManagerProfileUpsert:
    club_id: str
    manager_code: str
    manager_name: str
    persona_code: str
    preferred_system: str | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ScoutingNetworkCreate:
    club_id: str
    network_name: str
    region_code: str
    region_name: str
    specialty_code: str
    quality_tier: str
    weekly_cost_coin: int
    manager_profile_id: str | None = None
    scout_identity: str | None = None
    report_cadence_days: int = 7
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ScoutingNetworkAssignmentCreate:
    network_id: str
    club_id: str
    assignment_name: str
    assignment_scope: str = "region"
    territory_code: str | None = None
    focus_position: str | None = None
    age_band_min: int | None = None
    age_band_max: int | None = None
    budget_profile: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ScoutMissionCreate:
    club_id: str
    network_id: str
    mission_name: str
    mission_type: str = "standard_assignment"
    target_position: str | None = None
    target_region: str | None = None
    target_age_min: int | None = None
    target_age_max: int | None = None
    budget_limit_coin: int | None = None
    affordability_tier: str | None = None
    talent_type: str = "balanced"
    include_academy: bool = True
    manager_profile_id: str | None = None
    system_profile: str | None = None
    mission_duration_days: int | None = None
    metadata: dict[str, object] | None = None


class ScoutingIntelligenceService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        market_service: RegenMarketService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.market_service = market_service or RegenMarketService(session, settings=self.settings)

    def upsert_manager_profile(self, payload: ManagerProfileUpsert) -> ManagerScoutingProfileView:
        persona = self._normalize_persona(payload.persona_code)
        factors = _PERSONA_FACTORS[persona]
        profile = self.session.scalar(
            select(ManagerScoutingProfile).where(
                ManagerScoutingProfile.club_id == payload.club_id,
                ManagerScoutingProfile.manager_code == payload.manager_code,
            )
        )
        if profile is None:
            profile = ManagerScoutingProfile(
                club_id=payload.club_id,
                manager_code=payload.manager_code,
                manager_name=payload.manager_name,
                persona_code=persona,
            )
            self.session.add(profile)
        profile.manager_name = payload.manager_name
        profile.persona_code = persona
        profile.preferred_system = payload.preferred_system
        profile.youth_bias = factors["youth_bias"]
        profile.market_bias = factors["market_bias"]
        profile.tactical_bias = factors["tactical_bias"]
        profile.star_bias = factors["star_bias"]
        profile.accuracy_boost_bps = factors["accuracy_boost_bps"]
        profile.metadata_json = dict(payload.metadata or {})
        self.session.flush()
        return self._to_manager_profile_view(profile)

    def create_network(self, payload: ScoutingNetworkCreate) -> ScoutingNetworkView:
        manager_profile_id = None
        if payload.manager_profile_id is not None:
            manager_profile_id = self._manager_profile_for_club(payload.manager_profile_id, payload.club_id).id
        network = ScoutingNetwork(
            club_id=payload.club_id,
            manager_profile_id=manager_profile_id,
            network_name=payload.network_name,
            region_code=payload.region_code,
            region_name=payload.region_name,
            specialty_code=payload.specialty_code,
            quality_tier=payload.quality_tier,
            scout_identity=payload.scout_identity,
            scout_rating=self._resolve_scout_rating(payload.quality_tier),
            weekly_cost_coin=max(payload.weekly_cost_coin, 0),
            report_cadence_days=max(payload.report_cadence_days, 1),
            metadata_json=dict(payload.metadata or {}),
        )
        self.session.add(network)
        self.session.flush()
        return self._to_network_view(network)

    def assign_network(self, payload: ScoutingNetworkAssignmentCreate) -> ScoutingNetworkAssignmentView:
        self._validate_age_band(payload.age_band_min, payload.age_band_max, error_code="assignment_age_band_invalid")
        network = self._network_for_club(payload.network_id, payload.club_id)
        assignment = ScoutingNetworkAssignment(
            network_id=payload.network_id,
            club_id=payload.club_id,
            assignment_name=payload.assignment_name,
            assignment_scope=payload.assignment_scope,
            territory_code=payload.territory_code or network.region_code,
            focus_position=payload.focus_position,
            age_band_min=payload.age_band_min,
            age_band_max=payload.age_band_max,
            budget_profile=payload.budget_profile,
            starts_on=payload.starts_on or date.today(),
            ends_on=payload.ends_on,
            metadata_json=dict(payload.metadata or {}),
        )
        self.session.add(assignment)
        self.session.flush()
        return self._to_assignment_view(assignment)

    def create_mission(self, payload: ScoutMissionCreate) -> ScoutMissionView:
        self._validate_age_band(payload.target_age_min, payload.target_age_max, error_code="mission_age_band_invalid")
        mission_type = self._normalize_mission_type(payload.mission_type)
        network = self._network_for_club(payload.network_id, payload.club_id)
        manager_profile_id = payload.manager_profile_id or network.manager_profile_id
        if manager_profile_id is not None:
            manager_profile_id = self._manager_profile_for_club(manager_profile_id, payload.club_id).id
        mission = ScoutMission(
            club_id=payload.club_id,
            network_id=payload.network_id,
            manager_profile_id=manager_profile_id,
            mission_name=payload.mission_name,
            mission_type=mission_type,
            target_position=payload.target_position,
            target_region=payload.target_region or network.region_code,
            target_age_min=payload.target_age_min,
            target_age_max=payload.target_age_max,
            budget_limit_coin=payload.budget_limit_coin,
            affordability_tier=payload.affordability_tier,
            mission_duration_days=payload.mission_duration_days or _MISSION_DURATIONS[mission_type],
            talent_type=payload.talent_type,
            include_academy=payload.include_academy,
            system_profile=payload.system_profile,
            metadata_json=dict(payload.metadata or {}),
        )
        self.session.add(mission)
        self.session.flush()
        return self._to_mission_view(mission)

    def list_manager_profiles(self, club_id: str) -> tuple[ManagerScoutingProfileView, ...]:
        profiles = self.session.scalars(
            select(ManagerScoutingProfile)
            .where(ManagerScoutingProfile.club_id == club_id)
            .order_by(ManagerScoutingProfile.manager_name.asc(), ManagerScoutingProfile.created_at.asc())
        ).all()
        return tuple(self._to_manager_profile_view(profile) for profile in profiles)

    def list_academy_supply_signals(
        self,
        club_id: str,
        *,
        refresh: bool = False,
    ) -> tuple[AcademySupplySignalView, ...]:
        signals = []
        if not refresh:
            signals = self.session.scalars(
                select(AcademySupplySignal)
                .where(AcademySupplySignal.club_id == club_id)
                .order_by(AcademySupplySignal.visibility_score.desc(), AcademySupplySignal.created_at.desc())
            ).all()
        if refresh or not signals:
            return self.refresh_academy_supply_signals(club_id)
        return tuple(self._to_academy_signal_view(signal) for signal in signals)

    def list_talent_discovery_badges(
        self,
        club_id: str,
        *,
        mission_id: str | None = None,
        limit: int | None = None,
    ) -> tuple[TalentDiscoveryBadgeView, ...]:
        badges = self.session.scalars(
            select(TalentDiscoveryBadge)
            .where(TalentDiscoveryBadge.club_id == club_id)
            .order_by(TalentDiscoveryBadge.awarded_at.desc(), TalentDiscoveryBadge.id.desc())
        ).all()
        if mission_id is not None:
            badges = [
                badge
                for badge in badges
                if str((badge.metadata_json or {}).get("mission_id")) == mission_id
            ]
        if limit is not None:
            badges = badges[: max(limit, 1)]
        return tuple(self._to_badge_view(badge) for badge in badges)

    def list_player_lifecycle_profiles(
        self,
        club_id: str,
        *,
        player_ids: tuple[str, ...] = (),
        sync_current_roster: bool = False,
        limit: int | None = None,
    ) -> tuple[PlayerLifecycleProfileView, ...]:
        resolved_player_ids: list[str] = []
        seen_player_ids: set[str] = set()

        def _track_player(player_id: str) -> None:
            if player_id and player_id not in seen_player_ids:
                seen_player_ids.add(player_id)
                resolved_player_ids.append(player_id)

        for player_id in player_ids:
            _track_player(player_id)
        if sync_current_roster:
            roster_statement = (
                select(Player.id)
                .where(Player.current_club_profile_id == club_id)
                .order_by(Player.full_name.asc(), Player.id.asc())
            )
            if limit is not None:
                roster_statement = roster_statement.limit(max(limit, 1))
            for player_id in self.session.scalars(roster_statement).all():
                _track_player(player_id)

        for player_id in resolved_player_ids:
            self.sync_player_lifecycle_profile(player_id)

        statement = select(PlayerLifecycleProfile)
        if resolved_player_ids:
            statement = statement.where(PlayerLifecycleProfile.player_id.in_(resolved_player_ids))
        else:
            statement = statement.where(PlayerLifecycleProfile.club_id == club_id)
        statement = statement.order_by(
            PlayerLifecycleProfile.market_desirability.desc(),
            PlayerLifecycleProfile.age_years.asc(),
            PlayerLifecycleProfile.updated_at.desc(),
        )
        if limit is not None:
            statement = statement.limit(max(limit, 1))
        profiles = self.session.scalars(statement).all()
        return tuple(self._to_lifecycle_profile_view(profile) for profile in profiles)

    def build_planning_dashboard(
        self,
        club_id: str,
        *,
        roster_limit: int = 12,
    ) -> ScoutingPlanningView:
        networks = self.session.scalars(
            select(ScoutingNetwork)
            .where(ScoutingNetwork.club_id == club_id)
            .order_by(ScoutingNetwork.active.desc(), ScoutingNetwork.created_at.desc())
        ).all()
        assignments = self.session.scalars(
            select(ScoutingNetworkAssignment)
            .where(ScoutingNetworkAssignment.club_id == club_id)
            .order_by(ScoutingNetworkAssignment.status.asc(), ScoutingNetworkAssignment.starts_on.desc())
        ).all()
        missions = self.session.scalars(
            select(ScoutMission)
            .where(ScoutMission.club_id == club_id)
            .order_by(ScoutMission.created_at.desc(), ScoutMission.id.desc())
            .limit(max(roster_limit, 10))
        ).all()
        return ScoutingPlanningView(
            club_id=club_id,
            refreshed_at=_utcnow(),
            manager_profiles=self.list_manager_profiles(club_id),
            networks=tuple(self._to_network_view(network) for network in networks),
            assignments=tuple(self._to_assignment_view(assignment) for assignment in assignments),
            missions=tuple(self._to_mission_view(mission) for mission in missions),
            academy_supply_signals=self.list_academy_supply_signals(club_id, refresh=True),
            lifecycle_profiles=self.list_player_lifecycle_profiles(
                club_id,
                sync_current_roster=True,
                limit=max(roster_limit, 1),
            ),
            badges=self.list_talent_discovery_badges(club_id, limit=max(roster_limit, 1)),
        )

    def get_completed_mission(
        self,
        mission_id: str,
        *,
        club_id: str | None = None,
    ) -> CompletedScoutMissionView:
        mission = self.session.get(ScoutMission, mission_id)
        if mission is None or (club_id is not None and mission.club_id != club_id):
            raise ValueError("mission_not_found")
        reports = self.session.scalars(
            select(ScoutReport)
            .where(ScoutReport.mission_id == mission_id)
            .order_by(ScoutReport.recommendation_rank.asc(), ScoutReport.created_at.asc())
        ).all()
        hidden_potential_estimates = self.session.scalars(
            select(HiddenPotentialEstimate)
            .where(HiddenPotentialEstimate.mission_id == mission_id)
            .order_by(HiddenPotentialEstimate.created_at.asc(), HiddenPotentialEstimate.id.asc())
        ).all()
        return CompletedScoutMissionView(
            mission=self._to_mission_view(mission),
            reports=tuple(self._to_report_view(report) for report in reports),
            hidden_potential_estimates=tuple(
                self._to_hidden_potential_view(estimate) for estimate in hidden_potential_estimates
            ),
            academy_supply_signals=self.list_academy_supply_signals(mission.club_id),
            awarded_badges=self.list_talent_discovery_badges(mission.club_id, mission_id=mission.id),
        )

    def refresh_academy_supply_signals(self, club_id: str) -> tuple[AcademySupplySignalView, ...]:
        batches = self.session.scalars(
            select(AcademyIntakeBatch)
            .where(AcademyIntakeBatch.club_id == club_id)
            .order_by(AcademyIntakeBatch.created_at.desc())
        ).all()
        results: list[AcademySupplySignalView] = []
        for batch in batches:
            candidates = self.session.scalars(
                select(AcademyCandidate)
                .where(AcademyCandidate.batch_id == batch.id)
                .order_by(AcademyCandidate.age.asc(), AcademyCandidate.display_name.asc())
            ).all()
            candidate_count = len(candidates)
            standout_count = sum(1 for candidate in candidates if int(candidate.potential_range_json.get("maximum", 0)) >= 84)
            average_high = round(
                (
                    sum(int(candidate.potential_range_json.get("maximum", 0)) for candidate in candidates) / candidate_count
                )
                if candidate_count
                else 0.0,
                2,
            )
            visibility_score = round(
                min(100.0, (candidate_count * 8.0) + (standout_count * 12.0) + (average_high * 0.45)),
                2,
            )
            signal = self.session.scalar(
                select(AcademySupplySignal).where(
                    AcademySupplySignal.club_id == club_id,
                    AcademySupplySignal.batch_id == batch.id,
                    AcademySupplySignal.signal_type == "academy_pipeline",
                )
            )
            summary = (
                f"Academy intake {batch.season_label} exposes {candidate_count} visible prospects "
                f"with {standout_count} standout upside profiles."
            )
            if signal is None:
                signal = AcademySupplySignal(
                    club_id=club_id,
                    batch_id=batch.id,
                    signal_type="academy_pipeline",
                    summary_text=summary,
                )
                self.session.add(signal)
            signal.candidate_count = candidate_count
            signal.standout_count = standout_count
            signal.average_potential_high = average_high
            signal.visibility_score = visibility_score
            signal.signal_status = "visible" if candidate_count else "quiet"
            signal.summary_text = summary
            signal.metadata_json = {
                "season_label": batch.season_label,
                "academy_quality_score": batch.academy_quality_score,
                "candidate_ids": [candidate.id for candidate in candidates],
            }
            self.session.flush()
            results.append(self._to_academy_signal_view(signal))
        return tuple(results)

    def sync_player_lifecycle_profile(
        self,
        player_id: str,
        *,
        reference_on: date | None = None,
    ) -> PlayerLifecycleProfileView:
        player = self.session.get(Player, player_id)
        if player is None:
            raise ValueError("player_not_found")
        current = reference_on or date.today()
        age_years = _compute_age(player.date_of_birth, today=current)
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        phase = self._career_phase_for_age(age_years)
        lifecycle_age_months = None
        if regen is not None:
            lifecycle_age_months = _months_between(regen.generated_at.date(), current)
        desirability = self._market_desirability(phase, regen=regen)
        profile = self.session.scalar(select(PlayerLifecycleProfile).where(PlayerLifecycleProfile.player_id == player_id))
        if profile is None:
            profile = PlayerLifecycleProfile(player_id=player_id)
            self.session.add(profile)
        profile.regen_profile_id = regen.id if regen is not None else None
        profile.club_id = player.current_club_profile_id
        profile.phase = phase
        profile.phase_source = "age_curve"
        profile.age_years = age_years
        profile.lifecycle_age_months = lifecycle_age_months
        profile.market_desirability = desirability
        profile.planning_horizon_months = self._planning_horizon_for_phase(phase)
        profile.development_confidence_bps = self._development_confidence_for_phase(phase)
        profile.metadata_json = {
            "breakout_max_age": self.settings.regen_generation.player_lifecycle_growth_max_age,
            "peak_max_age": self.settings.regen_generation.player_lifecycle_peak_max_age,
            "decline_max_age": self.settings.regen_generation.player_lifecycle_decline_max_age,
            "regen_generation_source": regen.generation_source if regen is not None else None,
        }
        self.session.flush()
        return self._to_lifecycle_profile_view(profile)

    def complete_mission(
        self,
        mission_id: str,
        *,
        limit: int = 5,
        reference_on: date | None = None,
    ) -> CompletedScoutMissionView:
        mission = self.session.get(ScoutMission, mission_id)
        if mission is None:
            raise ValueError("mission_not_found")
        existing_report_id = self.session.scalar(
            select(ScoutReport.id).where(ScoutReport.mission_id == mission.id).limit(1)
        )
        if mission.status == "completed" or existing_report_id is not None:
            return self.get_completed_mission(mission.id, club_id=mission.club_id)
        network = self.session.get(ScoutingNetwork, mission.network_id)
        if network is None:
            raise ValueError("network_not_found")
        if network.club_id != mission.club_id:
            raise ValueError("network_club_mismatch")
        manager = self.session.get(ManagerScoutingProfile, mission.manager_profile_id) if mission.manager_profile_id else None
        if manager is not None and manager.club_id != mission.club_id:
            raise ValueError("manager_profile_club_mismatch")
        mission.status = "in_progress"
        academy_signals = self.refresh_academy_supply_signals(mission.club_id) if mission.include_academy else ()
        candidates = self._mission_candidates(mission)
        ranked = self._rank_candidates(candidates, mission, manager)
        selected = ranked[: max(limit, 1)]
        reports: list[ScoutReportView] = []
        estimates: list[HiddenPotentialEstimateView] = []
        badges: list[TalentDiscoveryBadgeView] = []
        scout_rating = self._effective_scout_rating(network, manager)
        persona = manager.persona_code if manager is not None else "balanced"
        system_profile = mission.system_profile or (manager.preferred_system if manager is not None else None)
        for index, candidate in enumerate(selected, start=1):
            report_view = self.market_service.create_scout_report(
                candidate["regen"].id,
                club_id=mission.club_id,
                scout_identity=network.scout_identity or network.network_name,
                scout_rating=scout_rating,
                manager_style=persona,
                system_profile=system_profile,
                premium_service=mission.mission_type == "deep_talent_search",
            )
            lifecycle = self.sync_player_lifecycle_profile(
                candidate["regen"].player_id,
                reference_on=reference_on,
            )
            report = ScoutReport(
                mission_id=mission.id,
                network_id=network.id,
                club_id=mission.club_id,
                regen_profile_id=candidate["regen"].id,
                academy_candidate_id=candidate["academy_candidate"].id if candidate["academy_candidate"] is not None else None,
                player_id=candidate["regen"].player_id,
                recommendation_rank=index,
                lifecycle_phase=lifecycle.phase,
                confidence_bps=report_view.scout_confidence_bps,
                fit_score=report_view.role_fit_score,
                potential_signal_score=round(report_view.future_potential_estimate - report_view.current_ability_estimate, 2),
                value_signal_score=round(
                    self._value_signal_score(
                        report_view.value_hint_coin,
                        report_view.future_potential_estimate,
                        report_view.current_ability_estimate,
                    ),
                    4,
                ),
                hidden_gem_signal=report_view.hidden_gem_score >= 10,
                current_ability_estimate=report_view.current_ability_estimate,
                future_potential_estimate=report_view.future_potential_estimate,
                value_hint_coin=report_view.value_hint_coin,
                summary_text=report_view.summary_text,
                tags_json=list(report_view.tags),
                metadata_json={
                    **dict(report_view.metadata),
                    "mission_type": mission.mission_type,
                    "talent_type": mission.talent_type,
                    "lifecycle_phase": lifecycle.phase,
                },
            )
            self.session.add(report)
            self.session.flush()
            estimate = self._create_hidden_potential_estimate(
                mission=mission,
                network=network,
                manager=manager,
                report=report,
                lifecycle=lifecycle,
            )
            self.session.add(estimate)
            self.session.flush()
            reports.append(self._to_report_view(report))
            estimates.append(self._to_hidden_potential_view(estimate))
            badges.extend(self._award_discovery_badges(mission, candidate, report, lifecycle))
        mission.status = "completed"
        mission.completed_at = _utcnow()
        mission.metadata_json = {
            **dict(mission.metadata_json or {}),
            "report_count": len(reports),
            "academy_signal_count": len(academy_signals),
        }
        self.session.flush()
        return self.get_completed_mission(mission.id, club_id=mission.club_id)

    def _mission_candidates(self, mission: ScoutMission) -> list[dict[str, object]]:
        filters = RegenSearchFilters(
            position_needs=(mission.target_position,) if mission.target_position else (),
            age_min=mission.target_age_min,
            age_max=mission.target_age_max,
            wonderkid_only=mission.talent_type == "wonderkid",
        )
        search_results = self.market_service.search_regens(filters)
        academy_candidates = {
            candidate.regen_profile_id: candidate
            for candidate in self.session.scalars(
                select(AcademyCandidate).where(AcademyCandidate.club_id == mission.club_id)
            ).all()
        }
        candidates: list[dict[str, object]] = []
        for item in search_results:
            regen = self.session.get(RegenProfile, item.profile.id)
            if regen is None:
                continue
            if mission.target_region and not self._matches_region(regen, mission.target_region):
                continue
            if mission.budget_limit_coin is not None and item.latest_value is not None and item.latest_value.current_value_coin > mission.budget_limit_coin:
                continue
            academy_candidate = academy_candidates.get(regen.id) if mission.include_academy else None
            if academy_candidate is not None or mission.include_academy is False or regen.generated_for_club_id == mission.club_id:
                candidates.append(
                    {
                        "result": item,
                        "regen": regen,
                        "academy_candidate": academy_candidate,
                    }
                )
        if mission.include_academy:
            for academy_candidate in academy_candidates.values():
                if any(
                    candidate["academy_candidate"] is not None and candidate["academy_candidate"].id == academy_candidate.id
                    for candidate in candidates
                ):
                    continue
                regen = self.session.get(RegenProfile, academy_candidate.regen_profile_id)
                if regen is None:
                    continue
                if mission.target_position and academy_candidate.primary_position != mission.target_position:
                    continue
                if mission.target_region and not self._matches_region(regen, mission.target_region):
                    continue
                if mission.target_age_min is not None and academy_candidate.age < mission.target_age_min:
                    continue
                if mission.target_age_max is not None and academy_candidate.age > mission.target_age_max:
                    continue
                candidates.append(
                    {
                        "result": None,
                        "regen": regen,
                        "academy_candidate": academy_candidate,
                    }
                )
        return candidates

    def _rank_candidates(
        self,
        candidates: list[dict[str, object]],
        mission: ScoutMission,
        manager: ManagerScoutingProfile | None,
    ) -> list[dict[str, object]]:
        manager_style = manager.persona_code if manager is not None else "balanced"
        request = RegenRecommendationRequest(
            club_id=mission.club_id,
            manager_style=manager_style,
            position_needs=(mission.target_position,) if mission.target_position else (),
            system_profile=mission.system_profile or (manager.preferred_system if manager is not None else None),
            budget_coin=mission.budget_limit_coin,
            premium_service=mission.mission_type == "deep_talent_search",
            limit=max(len(candidates), 1),
        )
        recommended = {
            item.regen_id: item
            for item in self.market_service.recommend_regens(request)
        }
        ranked: list[tuple[float, dict[str, object]]] = []
        for candidate in candidates:
            regen = candidate["regen"]
            academy_candidate = candidate["academy_candidate"]
            recommendation = recommended.get(regen.regen_id)
            profile = self.sync_player_lifecycle_profile(regen.player_id)
            score = (recommendation.priority_score if recommendation is not None else 0.0) + profile.market_desirability
            if academy_candidate is not None:
                score += 18.0
            if mission.talent_type == "wonderkid" and int(regen.potential_range_json.get("maximum", 0)) >= 88:
                score += 22.0
            ranked.append((score, candidate))
        return [candidate for _, candidate in sorted(ranked, key=lambda item: item[0], reverse=True)]

    def _create_hidden_potential_estimate(
        self,
        *,
        mission: ScoutMission,
        network: ScoutingNetwork,
        manager: ManagerScoutingProfile | None,
        report: ScoutReport,
        lifecycle: PlayerLifecycleProfileView,
    ) -> HiddenPotentialEstimate:
        uncertainty_band = max(
            1,
            round((100 - network.scout_rating) / 15) + round((10_000 - report.confidence_bps) / 2_000),
        )
        current_low = max(1, report.current_ability_estimate - uncertainty_band)
        current_high = min(99, report.current_ability_estimate + uncertainty_band)
        potential_low = max(current_high, report.future_potential_estimate - (uncertainty_band * 2))
        potential_high = min(99, report.future_potential_estimate + (uncertainty_band * 2))
        persona = manager.persona_code if manager is not None else "balanced"
        return HiddenPotentialEstimate(
            club_id=mission.club_id,
            network_id=network.id,
            mission_id=mission.id,
            scout_report_id=report.id,
            regen_profile_id=report.regen_profile_id,
            academy_candidate_id=report.academy_candidate_id,
            current_ability_low=current_low,
            current_ability_high=current_high,
            future_potential_low=potential_low,
            future_potential_high=potential_high,
            scout_confidence_bps=report.confidence_bps,
            uncertainty_band=uncertainty_band,
            lifecycle_phase=lifecycle.phase,
            revealed_by_persona=persona,
            metadata_json={
                "mission_type": mission.mission_type,
                "talent_type": mission.talent_type,
                "manager_profile_id": manager.id if manager is not None else None,
            },
        )

    def _award_discovery_badges(
        self,
        mission: ScoutMission,
        candidate: dict[str, object],
        report: ScoutReport,
        lifecycle: PlayerLifecycleProfileView,
    ) -> list[TalentDiscoveryBadgeView]:
        regen = candidate["regen"]
        academy_candidate = candidate["academy_candidate"]
        player = self.session.get(Player, regen.player_id)
        age = _compute_age(player.date_of_birth if player is not None else None)
        potential_high = int(regen.potential_range_json.get("maximum", report.future_potential_estimate))
        current_high = int(regen.current_ability_range_json.get("maximum", report.current_ability_estimate))
        badge_definitions: list[tuple[str, str, str]] = []
        if age <= 19 and potential_high >= 90:
            badge_definitions.append(("golden_boy_finder", "Golden Boy Finder", "elite"))
        if age <= 20 and potential_high >= 88:
            badge_definitions.append(("wonderkid_finder", "Wonderkid Finder", "elite"))
        if academy_candidate is not None and potential_high >= 84:
            badge_definitions.append(("academy_visionary", "Academy Visionary", "breakout"))
        if potential_high - current_high >= 14:
            badge_definitions.append(("talent_discoverer", "Talent Discoverer", "emerging"))
        views: list[TalentDiscoveryBadgeView] = []
        for badge_code, badge_name, evidence_level in badge_definitions:
            badge = self.session.scalar(
                select(TalentDiscoveryBadge).where(
                    TalentDiscoveryBadge.club_id == mission.club_id,
                    TalentDiscoveryBadge.regen_profile_id == regen.id,
                    TalentDiscoveryBadge.badge_code == badge_code,
                )
            )
            if badge is None:
                badge = TalentDiscoveryBadge(
                    club_id=mission.club_id,
                    regen_profile_id=regen.id,
                    academy_candidate_id=academy_candidate.id if academy_candidate is not None else None,
                    badge_code=badge_code,
                    badge_name=badge_name,
                    evidence_level=evidence_level,
                    summary_text=f"{badge_name} awarded after {mission.mission_name} surfaced a {lifecycle.phase} profile with upside.",
                    metadata_json={
                        "mission_id": mission.id,
                        "report_id": report.id,
                        "potential_high": potential_high,
                        "current_high": current_high,
                    },
                )
                self.session.add(badge)
                self.session.flush()
            views.append(self._to_badge_view(badge))
        return views

    def _normalize_persona(self, persona_code: str) -> str:
        normalized = persona_code.strip().lower().replace(" ", "_")
        return normalized if normalized in _PERSONA_FACTORS else "balanced"

    def _normalize_mission_type(self, mission_type: str) -> str:
        normalized = mission_type.strip().lower().replace(" ", "_")
        return normalized if normalized in _MISSION_DURATIONS else "standard_assignment"

    def _resolve_scout_rating(self, quality_tier: str) -> int:
        return _QUALITY_SCOUT_RATINGS.get(quality_tier.strip().lower(), _QUALITY_SCOUT_RATINGS["standard"])

    def _effective_scout_rating(
        self,
        network: ScoutingNetwork,
        manager: ManagerScoutingProfile | None,
    ) -> int:
        bonus = round((manager.accuracy_boost_bps if manager is not None else 0) / 100)
        return min(95, max(35, network.scout_rating + bonus))

    def _career_phase_for_age(self, age_years: int) -> str:
        if age_years <= self.settings.regen_generation.player_lifecycle_growth_max_age:
            return "breakout_growth"
        if age_years <= self.settings.regen_generation.player_lifecycle_peak_max_age:
            return "peak"
        if age_years <= self.settings.regen_generation.player_lifecycle_decline_max_age:
            return "decline"
        return "late_career"

    def _market_desirability(self, phase: str, *, regen: RegenProfile | None) -> float:
        base_scores = {
            "breakout_growth": 82.0,
            "peak": 91.0,
            "decline": 64.0,
            "late_career": 42.0,
        }
        base = base_scores.get(phase, 55.0)
        if regen is None:
            return base
        upside = max(int(regen.potential_range_json.get("maximum", regen.current_gsi)) - regen.current_gsi, 0)
        return round(min(99.0, base + (upside * 0.8)), 2)

    def _planning_horizon_for_phase(self, phase: str) -> int:
        return {
            "breakout_growth": 36,
            "peak": 24,
            "decline": 14,
            "late_career": 8,
        }.get(phase, 12)

    def _development_confidence_for_phase(self, phase: str) -> int:
        return {
            "breakout_growth": 6800,
            "peak": 8200,
            "decline": 7200,
            "late_career": 6000,
        }.get(phase, 6500)

    def _matches_region(self, regen: RegenProfile, target_region: str) -> bool:
        target = target_region.strip().lower()
        if not target:
            return True
        origin = self.session.scalar(select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == regen.id))
        candidates = {
            str(regen.birth_country_code or "").lower(),
            str(regen.birth_region or "").lower(),
            str(regen.birth_city or "").lower(),
            str(origin.country_code if origin is not None else "").lower(),
            str(origin.region_name if origin is not None else "").lower(),
            str(origin.city_name if origin is not None else "").lower(),
        }
        return target in candidates

    def _value_signal_score(self, value_hint_coin: int | None, future_potential: int, current_ability: int) -> float:
        if value_hint_coin is None:
            return 0.0
        upside = max(future_potential - current_ability, 0)
        return ((upside * 55) + (future_potential * 8)) / max(value_hint_coin, 1)

    def _validate_age_band(
        self,
        minimum: int | None,
        maximum: int | None,
        *,
        error_code: str,
    ) -> None:
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(error_code)

    def _manager_profile_for_club(self, manager_profile_id: str, club_id: str) -> ManagerScoutingProfile:
        profile = self.session.get(ManagerScoutingProfile, manager_profile_id)
        if profile is None:
            raise ValueError("manager_profile_not_found")
        if profile.club_id != club_id:
            raise ValueError("manager_profile_club_mismatch")
        return profile

    def _network_for_club(self, network_id: str, club_id: str) -> ScoutingNetwork:
        network = self.session.get(ScoutingNetwork, network_id)
        if network is None:
            raise ValueError("network_not_found")
        if network.club_id != club_id:
            raise ValueError("network_club_mismatch")
        return network

    def _to_manager_profile_view(self, profile: ManagerScoutingProfile) -> ManagerScoutingProfileView:
        return ManagerScoutingProfileView(
            id=profile.id,
            club_id=profile.club_id,
            manager_code=profile.manager_code,
            manager_name=profile.manager_name,
            persona_code=profile.persona_code,
            preferred_system=profile.preferred_system,
            youth_bias=profile.youth_bias,
            market_bias=profile.market_bias,
            tactical_bias=profile.tactical_bias,
            star_bias=profile.star_bias,
            accuracy_boost_bps=profile.accuracy_boost_bps,
            metadata=profile.metadata_json,
        )

    def _to_network_view(self, network: ScoutingNetwork) -> ScoutingNetworkView:
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

    def _to_assignment_view(self, assignment: ScoutingNetworkAssignment) -> ScoutingNetworkAssignmentView:
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

    def _to_mission_view(self, mission: ScoutMission) -> ScoutMissionView:
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

    def _to_report_view(self, report: ScoutReport) -> ScoutReportView:
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

    def _to_hidden_potential_view(self, estimate: HiddenPotentialEstimate) -> HiddenPotentialEstimateView:
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

    def _to_academy_signal_view(self, signal: AcademySupplySignal) -> AcademySupplySignalView:
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

    def _to_lifecycle_profile_view(self, profile: PlayerLifecycleProfile) -> PlayerLifecycleProfileView:
        return PlayerLifecycleProfileView(
            id=profile.id,
            player_id=profile.player_id,
            regen_profile_id=profile.regen_profile_id,
            club_id=profile.club_id,
            phase=profile.phase,
            phase_source=profile.phase_source,
            age_years=profile.age_years,
            lifecycle_age_months=profile.lifecycle_age_months,
            market_desirability=profile.market_desirability,
            planning_horizon_months=profile.planning_horizon_months,
            development_confidence_bps=profile.development_confidence_bps,
            metadata=profile.metadata_json,
        )

    def _to_badge_view(self, badge: TalentDiscoveryBadge) -> TalentDiscoveryBadgeView:
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


__all__ = [
    "ManagerProfileUpsert",
    "ScoutMissionCreate",
    "ScoutingIntelligenceService",
    "ScoutingNetworkAssignmentCreate",
    "ScoutingNetworkCreate",
]
