from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from random import Random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import ClubReputationProfile
from app.common.enums.injury_severity import InjurySeverity
from app.core.config import Settings, get_settings
from app.ingestion.models import (
    Competition,
    Country,
    Match,
    Player,
    PlayerMatchStat,
    PlayerSeasonStat,
    PlayerVerification,
)
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.notification_record import NotificationRecord
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHistory,
    PlayerCardHolding,
    PlayerCardOwnerHistory,
    PlayerCardTier,
)
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_personality import PlayerPersonality
from app.models.regen import (
    AcademyCandidate,
    AcademyIntakeBatch,
    RegenDiscoveryBadge,
    RegenGenerationEvent,
    RegenLegacyRecord,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenValueSnapshot,
    RegenVisualProfile,
)
from app.models.regen_ecosystem import (
    Agent,
    CareerEvent,
    RegenAttributeProfile,
    RegenAwardVote,
    RegenBloodlineLink,
    Scout,
    YouthAcademy,
)
from app.models.user import User
from app.regen_universe.models import (
    RegenAward as UniverseAward,
    RegenAwardWinner,
    RegenPerformanceRecord,
    RegenRankingSnapshot,
    RegenSeason,
)
from app.schemas.player_lifecycle import ContractCreateRequest, InjuryCreateRequest
from app.schemas.regen_ecosystem import (
    AcademyGeneratedPlayerView,
    AcademyGenerationResultView,
    AcademyPromotionView,
    AgentView,
    AwardVoteView,
    CareerEventView,
    RegenAwardHubView,
    RegenBloodlineNodeView,
    RegenFeedItemView,
    RegenHubPlayerView,
    RegenLineageChainView,
    ScoutDiscoveryResultView,
    ScoutReportView,
    ScoutView,
    YouthAcademyView,
)
from app.services.player_agency_service import PlayerAgencyService
from app.services.player_lifecycle_service import PlayerLifecycleService
from app.services.regen_market_service import RegenMarketService
from app.services.regen_portrait_service import RegenPortraitService
from app.services.regen_service import RegenClubContext, RegenGenerationEngine

_REGION_STRENGTH = {
    "lagos": 1.22,
    "enugu": 1.08,
    "kano": 1.04,
    "abuja": 1.10,
    "nigeria": 1.08,
    "ghana": 1.04,
    "morocco": 1.10,
    "brazil": 1.18,
    "spain": 1.16,
    "japan": 1.05,
}
_REGION_TALENT_DENSITY = {
    "lagos": 0.72,
    "enugu": 0.58,
    "kano": 0.55,
    "abuja": 0.60,
    "nigeria": 0.62,
    "ghana": 0.57,
    "morocco": 0.61,
    "brazil": 0.75,
    "spain": 0.71,
    "japan": 0.53,
}
_RARITY_MULTIPLIER = {
    "common": 1.0,
    "rare": 1.15,
    "elite": 1.35,
    "generational": 1.7,
}
_BADGE_LABELS = {
    "wonderkid": "Wonderkid",
    "late_bloomer": "Late Bloomer",
    "injury_prone": "Injury Prone",
    "big_game_player": "Big Game Player",
}
_AGENT_NAMES = (
    "Mina Okafor",
    "Jules Duarte",
    "Sefa Mensah",
    "Kenji Mori",
    "Luca Varela",
    "Youssef Bennani",
)
_INJURY_TYPES = {
    InjurySeverity.MINOR: "Muscle fatigue",
    InjurySeverity.MODERATE: "Hamstring strain",
    InjurySeverity.MAJOR: "Ligament damage",
    InjurySeverity.SEASON_ENDING: "ACL rupture",
}
_CLUB_PROGRESSION_REASONS = {
    "season_rollover",
    "academy_level_up",
    "scout_mission_complete",
    "youth_tournament_performance",
    "club_progression_milestone",
}


class RegenEcosystemError(ValueError):
    pass


class RegenEcosystemNotFoundError(RegenEcosystemError):
    pass


class RegenEcosystemValidationError(RegenEcosystemError):
    pass


def _season_label(reference_on: date | None = None) -> str:
    current = reference_on or date.today()
    start_year = current.year if current.month >= 7 else current.year - 1
    return f"{start_year}/{start_year + 1}"


def _age_on(date_of_birth: date | None, reference_on: date | None = None) -> int:
    if date_of_birth is None:
        return 18
    current = reference_on or date.today()
    years = current.year - date_of_birth.year
    if (current.month, current.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(0, years)


def _clamp_int(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, round(value)))


def _clamp_float(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _midpoint(value_range: dict[str, int] | None, fallback: int = 50) -> int:
    if not value_range:
        return fallback
    minimum = int(value_range.get("minimum", fallback))
    maximum = int(value_range.get("maximum", fallback))
    return round((minimum + maximum) / 2)


@dataclass(slots=True)
class RegenEcosystemService:
    session: Session
    settings: Settings | None = None
    generation_engine: RegenGenerationEngine = field(init=False)
    market_service: RegenMarketService = field(init=False)
    lifecycle_service: PlayerLifecycleService = field(init=False)
    agency_service: PlayerAgencyService = field(init=False)

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.generation_engine = RegenGenerationEngine(self.settings)
        self.market_service = RegenMarketService(self.session, settings=self.settings)
        self.lifecycle_service = PlayerLifecycleService(self.session, settings=self.settings)
        self.agency_service = PlayerAgencyService(self.session)

    def upsert_academy(
        self,
        *,
        club_user_id: str,
        club_id: str | None = None,
        level: int = 1,
        scouting_regions: tuple[str, ...] = (),
        capacity: int = 6,
        upgrade_cost: int = 100_000,
    ) -> YouthAcademy:
        club = self._resolve_club(club_user_id=club_user_id, club_id=club_id)
        academy = self.session.scalar(select(YouthAcademy).where(YouthAcademy.club_user_id == club_user_id))
        if academy is None:
            academy = YouthAcademy(club_user_id=club_user_id)
            self.session.add(academy)
        academy.club_id = club.id
        academy.level = max(1, min(10, level))
        academy.scouting_regions_json = list(scouting_regions)
        academy.capacity = max(1, capacity)
        academy.upgrade_cost = max(0, upgrade_cost)
        self.session.flush()
        return academy

    def create_scout(
        self,
        *,
        club_user_id: str,
        club_id: str | None,
        region: str,
        skill_rating: int,
        specialty: str,
    ) -> Scout:
        club = self._resolve_club(club_user_id=club_user_id, club_id=club_id)
        scout = Scout(
            club_user_id=club_user_id,
            club_id=club.id,
            region=region.strip(),
            skill_rating=max(0, min(100, skill_rating)),
            specialty=specialty.strip().lower() or "youth",
            metadata_json={"rules_only": True},
        )
        self.session.add(scout)
        self.session.flush()
        return scout

    def create_agent(
        self,
        *,
        name: str,
        negotiation_skill: int,
        player_ids: tuple[str, ...] = (),
    ) -> Agent:
        agent = Agent(
            name=name.strip(),
            negotiation_skill=max(0, min(100, negotiation_skill)),
            player_ids_json=list(dict.fromkeys(player_ids)),
            metadata_json={"lightweight": True},
        )
        self.session.add(agent)
        self.session.flush()
        return agent

    def generate_academy_players(
        self,
        *,
        club_user_id: str,
        club_id: str | None = None,
        season_label: str | None = None,
        reference_on: date | None = None,
    ) -> AcademyGenerationResultView:
        club = self._resolve_club(club_user_id=club_user_id, club_id=club_id)
        academy = self.session.scalar(select(YouthAcademy).where(YouthAcademy.club_user_id == club_user_id))
        if academy is None:
            academy = self.upsert_academy(club_user_id=club_user_id, club_id=club.id)
        elif academy.club_id != club.id:
            academy.club_id = club.id
            self.session.flush()
        open_slots = max(academy.capacity - self._occupied_academy_slots(club.id), 0)
        resolved_season = season_label or _season_label(reference_on)
        if open_slots <= 0:
            return AcademyGenerationResultView(
                academy=self._to_academy_view(academy),
                batch_id=None,
                season_label=resolved_season,
                generated_count=0,
                generated_players=(),
            )

        club_context = self._build_club_context(club, academy)
        generated = self.generation_engine.generate_academy_intake(
            club_id=club.id,
            season_label=resolved_season,
            club_context=club_context,
            intake_size=open_slots,
            rng=Random(self._stable_seed("academy", club.id, resolved_season, str(open_slots))),
        )
        batch = AcademyIntakeBatch(
            id=generated.batch.id,
            club_id=club.id,
            season_id=None,
            season_label=generated.batch.season_label,
            trigger_reason="academy_manual",
            idempotency_key=f"academy-manual:{club.id}:{generated.batch.season_label}",
            intake_size=generated.batch.intake_size,
            academy_quality_score=generated.batch.academy_quality_score,
            status="generated",
            metadata_json={
                "academy_level": academy.level,
                "scouting_regions": list(academy.scouting_regions_json),
                "rules_only": True,
                "source": "academy_pipeline",
                "reason": "academy_manual",
            },
            created_at=generated.batch.generated_at,
            updated_at=generated.batch.generated_at,
        )
        self.session.add(batch)
        self.session.flush()

        generated_players: list[AcademyGeneratedPlayerView] = []
        for generated_profile, generated_candidate in zip(generated.regens, generated.batch.candidates, strict=True):
            candidate, regen, player, attr = self._persist_generated_regen(
                club=club,
                academy=academy,
                batch=batch,
                generated_profile=generated_profile,
                generated_candidate=generated_candidate,
                reference_on=reference_on or batch.created_at.date(),
                generation_source="organic_newgen",
                source_scope="academy_pipeline",
                trigger_reason="academy_manual",
                is_tradable=True,
                audit_metadata={"source": "academy_pipeline", "reason": "academy_manual"},
            )
            generated_players.append(self._to_generated_player_view(candidate, regen, player, attr))

        self.session.flush()
        return AcademyGenerationResultView(
            academy=self._to_academy_view(academy),
            batch_id=batch.id,
            season_label=batch.season_label,
            generated_count=len(generated_players),
            generated_players=tuple(generated_players),
        )

    def generate_club_progression_intake(
        self,
        club_id: str,
        reason: str,
        season_id: str,
        idempotency_key: str | None = None,
        *,
        reference_on: date | None = None,
    ) -> AcademyGenerationResultView:
        normalized_reason = reason.strip().lower()
        if normalized_reason not in _CLUB_PROGRESSION_REASONS:
            raise RegenEcosystemValidationError("unsupported_club_progression_reason")
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise RegenEcosystemNotFoundError("club_not_found")
        season = self.session.get(RegenSeason, season_id)
        if season is None:
            raise RegenEcosystemNotFoundError("regen_season_not_found")
        academy = self._ensure_academy_for_club(club)
        existing_batch = self.session.scalar(
            select(AcademyIntakeBatch).where(
                AcademyIntakeBatch.club_id == club.id,
                AcademyIntakeBatch.season_id == season.id,
                AcademyIntakeBatch.trigger_reason == normalized_reason,
            )
        )
        if existing_batch is not None:
            return self._academy_generation_result_from_batch(academy=academy, batch=existing_batch)

        effective_level = self._effective_academy_level(club.id, academy=academy)
        intake_size = self._club_progression_intake_size(
            club_id=club.id,
            season_id=season.id,
            reason=normalized_reason,
            academy_level=effective_level,
        )
        effective_reference_on = reference_on or season.start_date
        resolved_season_label = self._regen_season_label(season)
        audit_metadata = {
            "academy_level": effective_level,
            "idempotency_key": (
                idempotency_key or f"club-progression:{club.id}:{season.id}:{normalized_reason}"
            ).strip(),
            "reason": normalized_reason,
            "rules_only": True,
            "season_id": season.id,
            "season_number": season.season_number,
            "source": "club_progression",
        }
        club_context = self._build_progression_club_context(club, academy, academy_level=effective_level)
        generated = self.generation_engine.generate_academy_intake(
            club_id=club.id,
            season_label=resolved_season_label,
            club_context=club_context,
            intake_size=intake_size,
            rng=Random(
                self._stable_seed(
                    "club-progression",
                    club.id,
                    season.id,
                    normalized_reason,
                    str(intake_size),
                )
            ),
        )
        batch = AcademyIntakeBatch(
            id=generated.batch.id,
            club_id=club.id,
            season_id=season.id,
            season_label=generated.batch.season_label,
            trigger_reason=normalized_reason,
            idempotency_key=str(audit_metadata["idempotency_key"]),
            intake_size=generated.batch.intake_size,
            academy_quality_score=generated.batch.academy_quality_score,
            status="generated",
            metadata_json={
                **audit_metadata,
                "academy_quality_score": generated.batch.academy_quality_score,
                "scouting_regions": list(academy.scouting_regions_json),
            },
            created_at=generated.batch.generated_at,
            updated_at=generated.batch.generated_at,
        )
        self.session.add(batch)
        self.session.flush()

        generated_players: list[AcademyGeneratedPlayerView] = []
        for generated_profile, generated_candidate in zip(generated.regens, generated.batch.candidates, strict=True):
            candidate, regen, player, attr = self._persist_generated_regen(
                club=club,
                academy=academy,
                batch=batch,
                generated_profile=generated_profile,
                generated_candidate=generated_candidate,
                reference_on=effective_reference_on,
                generation_source="club_progression_intake",
                source_scope="club_progression",
                trigger_reason=normalized_reason,
                is_tradable=False,
                audit_metadata=audit_metadata,
            )
            generated_players.append(self._to_generated_player_view(candidate, regen, player, attr))

        self.session.flush()
        return AcademyGenerationResultView(
            academy=self._to_academy_view(academy),
            batch_id=batch.id,
            season_label=batch.season_label,
            generated_count=len(generated_players),
            generated_players=tuple(generated_players),
        )

    def promote_academy_player(
        self, player_identifier: str, *, reference_on: date | None = None
    ) -> AcademyPromotionView:
        candidate, regen, player = self._resolve_candidate_player(player_identifier)
        effective_date = reference_on or date.today()
        if candidate.age < 16:
            raise RegenEcosystemValidationError("academy_player_too_young_to_promote")
        if candidate.status == "promoted":
            active_contract = self._latest_contract(player.id)
            return AcademyPromotionView(
                academy_candidate_id=candidate.id,
                player_id=player.id,
                regen_profile_id=regen.id,
                promoted=True,
                contract_id=active_contract.id if active_contract is not None else None,
                academy_slots_remaining=self._academy_capacity_remaining(candidate.club_id),
                status=candidate.status,
            )
        contract = self.lifecycle_service.create_contract(
            player.id,
            ContractCreateRequest(
                club_id=candidate.club_id,
                wage_amount=self._initial_salary_for_regen(regen),
                bonus_terms="Academy graduation contract.",
                release_clause_amount=Decimal(str(max(0, _midpoint(regen.potential_range_json) * 175))),
                starts_on=effective_date,
                ends_on=effective_date + timedelta(days=730),
                signed_on=effective_date,
            ),
            reference_on=effective_date,
        )
        candidate.status = "promoted"
        regen.status = "active"
        self._record_player_event(
            player_id=player.id,
            club_id=candidate.club_id,
            event_type="academy_promoted",
            event_status="recorded",
            occurred_on=effective_date,
            summary=f"{player.full_name} promoted from the youth academy.",
            details={"academy_candidate_id": candidate.id, "contract_id": contract.id},
        )
        self._promote_career_entry(player.id)
        self._notify(
            candidate.club_id,
            "ACADEMY_GRADUATE",
            f"{player.full_name} graduated from the academy.",
            resource_id=player.id,
        )
        self.sync_agent_contract_pressure(player.id, reference_on=effective_date)
        self.session.flush()
        return AcademyPromotionView(
            academy_candidate_id=candidate.id,
            player_id=player.id,
            regen_profile_id=regen.id,
            promoted=True,
            contract_id=contract.id,
            academy_slots_remaining=self._academy_capacity_remaining(candidate.club_id),
            status=candidate.status,
        )

    def discover_regens(self, scout_id: str, *, limit: int = 5) -> ScoutDiscoveryResultView:
        scout = self.session.get(Scout, scout_id)
        if scout is None:
            raise RegenEcosystemNotFoundError("scout_not_found")
        club = self._resolve_club(club_user_id=scout.club_user_id, club_id=scout.club_id)
        density = self._region_density(scout.region)
        probability = round((scout.skill_rating / 100.0) * density, 4)
        discovered: list[AcademyGeneratedPlayerView] = []
        candidates = self.session.execute(
            select(RegenProfile, Player)
            .join(Player, Player.id == RegenProfile.player_id)
            .where(RegenProfile.status.in_(("academy_candidate", "active")))
            .order_by(RegenProfile.generated_at.desc(), Player.full_name.asc())
        ).all()
        for regen, player in candidates:
            if len(discovered) >= max(limit, 1):
                break
            if not self._matches_region(regen, scout.region):
                continue
            if self._already_discovered(club.id, regen.id):
                continue
            attr = self._ensure_attribute_profile(regen)
            roll = self._stable_ratio("discover", scout.id, regen.id, scout.region)
            if roll > probability and attr.rarity_tier != "generational":
                continue
            self.session.add(
                RegenDiscoveryBadge(
                    regen_id=regen.id,
                    club_id=club.id,
                    badge_code="discovered",
                    badge_name="Discovered Talent",
                    metadata_json={"scout_id": scout.id, "skill_rating": scout.skill_rating},
                )
            )
            self._notify(
                club.id,
                "REGEN_DISCOVERED",
                f"{player.full_name} has been discovered by scouting.",
                resource_id=player.id,
            )
            academy_candidate = self.session.scalar(
                select(AcademyCandidate).where(AcademyCandidate.regen_profile_id == regen.id)
            )
            discovered.append(self._to_generated_player_view(academy_candidate, regen, player, attr))
        self.session.flush()
        return ScoutDiscoveryResultView(
            scout=self._to_scout_view(scout),
            discovery_probability=probability,
            discovered_players=tuple(discovered),
        )

    def get_scout_report(self, player_identifier: str, *, scout_id: str | None = None) -> ScoutReportView:
        regen = self._resolve_regen(player_identifier)
        player = self.session.get(Player, regen.player_id)
        if player is None:
            raise RegenEcosystemNotFoundError("regen_player_not_found")
        scout = self._resolve_report_scout(regen, scout_id=scout_id)
        attr = self._ensure_attribute_profile(regen)
        report = self.market_service.create_scout_report(
            regen.id,
            club_id=scout.club_id,
            scout_identity=scout.id,
            scout_rating=scout.skill_rating,
            manager_style="balanced",
            premium_service=scout.skill_rating >= 85,
        )
        accuracy = max(0, min(100, scout.skill_rating))
        hidden_stats = {
            key: self._estimate_hidden_value(
                actual=value,
                accuracy=accuracy,
                specialty=scout.specialty,
                stat_key=key,
                scout_id=scout.id,
                regen_id=regen.id,
            )
            for key, value in (attr.hidden_stats_json or {}).items()
        }
        return ScoutReportView(
            scout_id=scout.id,
            player_id=player.id,
            regen_profile_id=regen.id,
            accuracy=accuracy,
            visible_stats=dict(attr.visible_stats_json or {}),
            hidden_stats=hidden_stats,
            potential_range=dict(regen.potential_range_json or {}),
            personality_state=dict(attr.personality_state_json or {}),
            rarity_tier=attr.rarity_tier,
            badge_codes=tuple(attr.badge_codes_json or []),
            summary_text=report.summary_text,
            generated_at=report.created_at,
        )

    def update_dynamic_potentials(
        self, *, limit: int | None = None, reference_on: date | None = None
    ) -> dict[str, object]:
        regens = self.session.scalars(select(RegenProfile).order_by(RegenProfile.generated_at.asc())).all()
        if limit is not None:
            regens = regens[: max(limit, 1)]
        updated_player_ids: list[str] = []
        effective_date = reference_on or date.today()
        for regen in regens:
            player = self.session.get(Player, regen.player_id)
            if player is None:
                continue
            attr = self._ensure_attribute_profile(regen)
            current_range = dict(regen.potential_range_json or {})
            maximum = int(current_range.get("maximum", regen.current_gsi))
            minimum = int(current_range.get("minimum", regen.current_gsi))
            performance = self._recent_performance_signal(player.id)
            poor_development = performance["minutes"] < 360 or performance["average_rating"] < 6.2
            delta = 0
            if performance["high_performance"]:
                delta += 1 + round(int(attr.hidden_stats_json.get("growth_variance", 50)) / 45)
            if poor_development:
                delta -= 1 + round((100 - int(attr.personality_state_json.get("morale", 50))) / 70)
            delta += self._mentorship_boost(player, regen)
            if delta:
                updated_maximum = _clamp_int(maximum + delta, minimum=max(minimum, regen.current_gsi), maximum=99)
                if updated_maximum != maximum:
                    regen.potential_range_json = {"minimum": minimum, "maximum": updated_maximum}
                    attr.last_potential_update_at = datetime.combine(
                        effective_date, datetime.min.time(), tzinfo=timezone.utc
                    )
                    self._sync_rarity_and_badges(regen, player, attr)
                    updated_player_ids.append(player.id)
            self._evolve_personality(player.id, reference_on=effective_date)
        self.session.flush()
        return {"updated_count": len(updated_player_ids), "player_ids": updated_player_ids}

    def trigger_career_event(
        self,
        player_id: str,
        *,
        event_type: str | None = None,
        reference_on: date | None = None,
    ) -> CareerEvent:
        player = self.session.get(Player, player_id)
        if player is None:
            raise RegenEcosystemNotFoundError("player_not_found")
        regen = self._require_regen_by_player(player_id)
        attr = self._ensure_attribute_profile(regen)
        effective_date = reference_on or date.today()
        resolved_type = event_type or self._choose_career_event(regen, attr)
        if resolved_type == "injury":
            severity = self._injury_severity(attr)
            injury = self.lifecycle_service.create_injury_case(
                player.id,
                InjuryCreateRequest(
                    severity=severity,
                    injury_type=_INJURY_TYPES[severity],
                    occurred_on=effective_date,
                    club_id=player.current_club_profile_id,
                    notes="Triggered by the regen career events engine.",
                ),
                reference_on=effective_date,
            )
            injury_history = list(attr.injury_history_json or [])
            injury_history.append(
                {
                    "injury_id": injury.id,
                    "injury_type": injury.injury_type,
                    "severity": injury.severity,
                    "occurred_on": injury.occurred_on.isoformat(),
                }
            )
            attr.injury_history_json = injury_history
            self._sync_rarity_and_badges(regen, player, attr)
            impact = {
                "injury_id": injury.id,
                "severity": injury.severity,
                "recovery_days": injury.recovery_days,
                "temporary_stat_drop": max(2, round(attr.injury_risk / 8)),
            }
            summary = f"{player.full_name} suffered an injury setback."
            self._notify(player.current_club_profile_id, "INJURY_ALERT", summary, resource_id=player.id)
        elif resolved_type == "breakout":
            regen.potential_range_json = {
                "minimum": int((regen.potential_range_json or {}).get("minimum", regen.current_gsi)),
                "maximum": _clamp_int(
                    int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) + 3,
                    minimum=regen.current_gsi,
                    maximum=99,
                ),
            }
            state = dict(attr.personality_state_json or {})
            state["confidence"] = _clamp_int(float(state.get("confidence", 50)) + 8)
            state["morale"] = _clamp_int(float(state.get("morale", 50)) + 6)
            attr.personality_state_json = state
            self._sync_rarity_and_badges(regen, player, attr)
            impact = {"potential_delta": 3, "confidence_delta": 8, "morale_delta": 6}
            summary = f"{player.full_name} is breaking out into first-team relevance."
            self._notify(player.current_club_profile_id, "PLAYER_BREAKOUT", summary, resource_id=player.id)
        elif resolved_type == "scandal":
            state = dict(attr.personality_state_json or {})
            state["morale"] = _clamp_int(float(state.get("morale", 50)) - 10)
            state["confidence"] = _clamp_int(float(state.get("confidence", 50)) - 6)
            attr.personality_state_json = state
            impact = {"morale_delta": -10, "confidence_delta": -6}
            summary = f"{player.full_name} is dealing with off-pitch noise."
        elif resolved_type == "transfer_drama":
            impact = self.sync_agent_contract_pressure(player.id, reference_on=effective_date)
            summary = f"{player.full_name} is unsettled and pushing for clarity over the next step."
            self._notify(player.current_club_profile_id, "TRANSFER_REQUEST", summary, resource_id=player.id)
        elif resolved_type == "mentorship":
            mentor_boost = self._mentorship_boost(player, regen, force=True)
            state = dict(attr.personality_state_json or {})
            state["confidence"] = _clamp_int(float(state.get("confidence", 50)) + mentor_boost * 2)
            state["pressure_response"] = _clamp_int(float(state.get("pressure_response", 50)) + mentor_boost)
            attr.personality_state_json = state
            impact = {"growth_rate_boost": mentor_boost, "pressure_response_delta": mentor_boost}
            summary = f"{player.full_name} is benefiting from senior mentorship."
        else:
            raise RegenEcosystemValidationError("unsupported_career_event_type")

        event = CareerEvent(
            player_id=player.id,
            regen_profile_id=regen.id,
            type=resolved_type,
            occurred_on=effective_date,
            impact_json=impact,
            summary=summary,
            metadata_json={"rules_only": True},
        )
        self.session.add(event)
        self.session.flush()
        return event

    def sync_agent_contract_pressure(self, player_id: str, *, reference_on: date | None = None) -> dict[str, object]:
        player = self.session.get(Player, player_id)
        if player is None:
            raise RegenEcosystemNotFoundError("player_not_found")
        regen = self._require_regen_by_player(player_id)
        attr = self._ensure_attribute_profile(regen)
        agent = self._ensure_agent_for_player(player_id)
        effective_date = reference_on or date.today()
        state = self.agency_service.sync(player_id, reference_on=effective_date)[3]
        active_contract = self._latest_contract(player.id)
        expected_salary = self._agent_salary_expectation(regen, attr, agent)
        underused = self._recent_performance_signal(player.id)["minutes"] < 240
        low_morale = float(attr.personality_state_json.get("morale", 50)) < 45
        high_potential = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) >= 85
        transfer_request_triggered = False
        if active_contract is not None and active_contract.wage_amount < expected_salary:
            state.contract_stance = "requests_renegotiation"
        if low_morale and high_potential and underused:
            state.transfer_request_status = "transfer_request"
            state.transfer_appetite = max(state.transfer_appetite, 72.0)
            transfer_request_triggered = True
        self.session.flush()
        return {
            "agent_id": agent.id,
            "expected_salary": str(expected_salary),
            "transfer_request_triggered": transfer_request_triggered,
            "contract_stance": state.contract_stance,
        }

    def list_feed(self, *, limit: int = 20) -> tuple[RegenFeedItemView, ...]:
        items: list[RegenFeedItemView] = []
        generation_events = self.session.scalars(
            select(RegenGenerationEvent).order_by(RegenGenerationEvent.created_at.desc()).limit(max(limit, 1))
        ).all()
        for event in generation_events:
            regen = self.session.get(RegenProfile, event.regen_profile_id)
            player = self.session.get(Player, regen.player_id) if regen is not None else None
            items.append(
                RegenFeedItemView(
                    event_type="new_generation",
                    occurred_at=event.created_at,
                    player_id=player.id if player is not None else None,
                    regen_profile_id=regen.id if regen is not None else None,
                    display_name=player.full_name if player is not None else None,
                    headline=(
                        f"{player.full_name} entered the regen universe."
                        if player is not None
                        else "New regen generated."
                    ),
                    details={"generation_source": event.generation_source, "season_label": event.season_label},
                )
            )
        career_events = self.session.scalars(
            select(CareerEvent).order_by(CareerEvent.created_at.desc()).limit(max(limit, 1))
        ).all()
        for event in career_events:
            player = self.session.get(Player, event.player_id)
            items.append(
                RegenFeedItemView(
                    event_type=event.type,
                    occurred_at=event.created_at,
                    player_id=event.player_id,
                    regen_profile_id=event.regen_profile_id,
                    display_name=player.full_name if player is not None else None,
                    headline=event.summary or f"{player.full_name if player is not None else 'Player'} update",
                    details=dict(event.impact_json or {}),
                )
            )
        promotions = self.session.scalars(
            select(PlayerCareerEntry)
            .where(PlayerCareerEntry.squad_role == "academy_graduate")
            .order_by(PlayerCareerEntry.created_at.desc())
            .limit(max(limit, 1))
        ).all()
        for promotion in promotions:
            items.append(
                RegenFeedItemView(
                    event_type="academy_graduate",
                    occurred_at=promotion.created_at,
                    player_id=promotion.player_id,
                    regen_profile_id=self._regen_id_for_player(promotion.player_id),
                    display_name=self._player_name(promotion.player_id),
                    headline=f"{promotion.club_name} promoted an academy graduate.",
                    details={"season_label": promotion.season_label},
                )
            )
        return tuple(sorted(items, key=lambda item: item.occurred_at, reverse=True)[: max(limit, 1)])

    def list_top_regens(self, *, limit: int = 20) -> tuple[RegenHubPlayerView, ...]:
        latest_season = self._latest_or_active_season()
        if latest_season is not None:
            entries = self.session.scalars(
                select(RegenRankingSnapshot)
                .where(RegenRankingSnapshot.season_id == latest_season.id, RegenRankingSnapshot.category == "overall")
                .order_by(RegenRankingSnapshot.rank.asc())
                .limit(max(limit, 1))
            ).all()
            if entries:
                result: list[RegenHubPlayerView] = []
                for entry in entries:
                    regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == entry.player_id))
                    if regen is None:
                        continue
                    player = self.session.get(Player, entry.player_id)
                    if player is None:
                        continue
                    attr = self._ensure_attribute_profile(regen)
                    result.append(self._to_hub_player_view(regen, player, attr, score=entry.score, rank=entry.rank))
                return tuple(result)
        return self._fallback_ranked_regens(limit=limit, sort_key="market_value")

    def list_rising_regens(self, *, limit: int = 20) -> tuple[RegenHubPlayerView, ...]:
        latest_season = self._latest_or_active_season()
        if latest_season is not None:
            records = self.session.scalars(
                select(RegenPerformanceRecord)
                .where(RegenPerformanceRecord.season_id == latest_season.id)
                .order_by(RegenPerformanceRecord.improvement_score.desc(), RegenPerformanceRecord.overall_score.desc())
                .limit(max(limit, 1))
            ).all()
            if records:
                result: list[RegenHubPlayerView] = []
                for index, record in enumerate(records, start=1):
                    regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == record.player_id))
                    if regen is None:
                        continue
                    player = self.session.get(Player, record.player_id)
                    if player is None:
                        continue
                    attr = self._ensure_attribute_profile(regen)
                    result.append(
                        self._to_hub_player_view(regen, player, attr, score=record.improvement_score, rank=index)
                    )
                return tuple(result)
        return self._fallback_ranked_regens(limit=limit, sort_key="uniqueness")

    def list_awards(self, *, season_id: str | None = None) -> tuple[RegenAwardHubView, ...]:
        season = self._resolve_season(season_id)
        if season is None:
            return ()
        awards = self.session.scalars(
            select(UniverseAward).order_by(UniverseAward.sort_order.asc(), UniverseAward.name.asc())
        ).all()
        results: list[RegenAwardHubView] = []
        for award in awards:
            winners = self.session.scalars(
                select(RegenAwardWinner)
                .where(RegenAwardWinner.award_id == award.id, RegenAwardWinner.season_id == season.id)
                .order_by(
                    RegenAwardWinner.rank.is_(None), RegenAwardWinner.rank.asc(), RegenAwardWinner.player_name.asc()
                )
            ).all()
            vote_rows = self.session.execute(
                select(RegenAwardVote.player_id, func.count(RegenAwardVote.id))
                .where(RegenAwardVote.award_id == award.id, RegenAwardVote.season_id == season.id)
                .group_by(RegenAwardVote.player_id)
                .order_by(func.count(RegenAwardVote.id).desc())
            ).all()
            results.append(
                RegenAwardHubView(
                    award_id=award.id,
                    award_code=award.code,
                    award_name=award.name,
                    season_id=season.id,
                    season_number=season.season_number,
                    winners=[
                        {
                            "player_id": winner.player_id,
                            "player_name": winner.player_name,
                            "rank": winner.rank,
                            "ranking_score": winner.ranking_score,
                        }
                        for winner in winners
                    ],
                    vote_totals=[
                        {"player_id": player_id, "display_name": self._player_name(player_id), "votes": vote_count}
                        for player_id, vote_count in vote_rows
                    ],
                )
            )
        return tuple(results)

    def cast_award_vote(
        self, award_id: str, *, user_id: str, player_id: str, season_id: str | None = None
    ) -> RegenAwardVote:
        award = self.session.get(UniverseAward, award_id)
        if award is None:
            raise RegenEcosystemNotFoundError("award_not_found")
        if self.session.get(User, user_id) is None:
            raise RegenEcosystemNotFoundError("user_not_found")
        if self.session.get(Player, player_id) is None:
            raise RegenEcosystemNotFoundError("player_not_found")
        season = self._resolve_season(season_id)
        if season is None:
            raise RegenEcosystemValidationError("season_not_found_for_vote")
        existing = self.session.scalar(
            select(RegenAwardVote).where(
                RegenAwardVote.award_id == award.id,
                RegenAwardVote.player_id == player_id,
                RegenAwardVote.user_id == user_id,
                RegenAwardVote.season_id == season.id,
            )
        )
        if existing is not None:
            return existing
        vote = RegenAwardVote(
            user_id=user_id,
            player_id=player_id,
            award_id=award.id,
            season_id=season.id,
            metadata_json={"rules_only": True},
        )
        self.session.add(vote)
        self.session.flush()
        return vote

    def get_lineage_chain(self, regen_identifier: str) -> RegenLineageChainView:
        regen = self._resolve_regen(regen_identifier)
        chain: list[RegenBloodlineNodeView] = []
        current = regen
        visited: set[str] = set()
        while current is not None and current.id not in visited:
            visited.add(current.id)
            bloodline = self.session.scalar(
                select(RegenBloodlineLink).where(RegenBloodlineLink.regen_profile_id == current.id)
            )
            player = self.session.get(Player, current.player_id)
            legacy = (
                self.session.get(RegenLegacyRecord, bloodline.parent_legacy_id)
                if bloodline is not None and bloodline.parent_legacy_id
                else None
            )
            chain.append(
                RegenBloodlineNodeView(
                    regen_profile_id=current.id,
                    regen_id=current.regen_id,
                    display_name=player.full_name if player is not None else current.regen_id,
                    parent_legacy_id=legacy.id if legacy is not None else None,
                    legacy_score=legacy.legacy_score if legacy is not None else None,
                    legacy_tier=legacy.legacy_tier if legacy is not None else None,
                )
            )
            if legacy is None:
                break
            current = self.session.scalar(select(RegenProfile).where(RegenProfile.id == legacy.regen_id))
        return RegenLineageChainView(regen_profile_id=regen.id, chain=tuple(chain))

    def run_weekly_academy_generation(self, *, reference_on: date | None = None) -> dict[str, object]:
        academies = self.session.scalars(select(YouthAcademy).order_by(YouthAcademy.created_at.asc())).all()
        results = []
        for academy in academies:
            generated = self.generate_academy_players(
                club_user_id=academy.club_user_id,
                club_id=academy.club_id,
                season_label=_season_label(reference_on),
                reference_on=reference_on,
            )
            results.append({"academy_id": academy.id, "generated_count": generated.generated_count})
        return {"academies_processed": len(academies), "results": results}

    def run_scouting_discovery_jobs(self) -> dict[str, object]:
        scouts = self.session.scalars(
            select(Scout).where(Scout.active.is_(True)).order_by(Scout.created_at.asc())
        ).all()
        results = []
        for scout in scouts:
            discovered = self.discover_regens(scout.id, limit=3)
            results.append({"scout_id": scout.id, "discovered_count": len(discovered.discovered_players)})
        return {"scouts_processed": len(scouts), "results": results}

    def run_potential_update_jobs(self) -> dict[str, object]:
        return self.update_dynamic_potentials()

    def run_career_event_jobs(self, *, limit: int = 10, reference_on: date | None = None) -> dict[str, object]:
        regens = self.session.scalars(
            select(RegenProfile).order_by(RegenProfile.generated_at.asc()).limit(max(limit, 1))
        ).all()
        created: list[str] = []
        for regen in regens:
            attr = self._ensure_attribute_profile(regen)
            trigger_ratio = (
                0.18 + (attr.injury_risk / 500.0) + (int(attr.hidden_stats_json.get("clutch_factor", 50)) / 1000.0)
            )
            if self._stable_ratio("career-job", regen.id, str(reference_on or date.today())) > trigger_ratio:
                continue
            event = self.trigger_career_event(regen.player_id, reference_on=reference_on)
            created.append(event.id)
        return {"events_created": len(created), "event_ids": created}

    def _persist_generated_regen(
        self,
        *,
        club: ClubProfile,
        academy: YouthAcademy,
        batch: AcademyIntakeBatch,
        generated_profile,
        generated_candidate,
        reference_on: date,
        generation_source: str = "organic_newgen",
        source_scope: str = "academy_pipeline",
        trigger_reason: str = "academy_manual",
        is_tradable: bool = True,
        audit_metadata: dict[str, object] | None = None,
    ) -> tuple[AcademyCandidate, RegenProfile, Player, RegenAttributeProfile]:
        audit_payload = dict(audit_metadata or {})
        country = self._ensure_country(generated_profile.birth_country_code)
        player = Player(
            source_provider="gtex_regen",
            provider_external_id=f"regen:{generated_profile.regen_id}",
            country_id=country.id,
            current_club_profile_id=club.id,
            full_name=generated_profile.display_name,
            first_name=generated_profile.display_name.split(" ", 1)[0],
            last_name=(
                generated_profile.display_name.split(" ", 1)[1] if " " in generated_profile.display_name else None
            ),
            short_name=generated_profile.display_name,
            position=generated_profile.primary_position,
            normalized_position=self._normalized_position(generated_profile.primary_position),
            date_of_birth=reference_on - timedelta(days=generated_profile.age * 365),
            preferred_foot="right",
            market_value_eur=float(generated_profile.current_gsi) * 12_000.0,
            profile_completeness_score=0.96,
            is_tradable=is_tradable,
            is_real_player=False,
            canonical_display_name=generated_profile.display_name,
        )
        self.session.add(player)
        self.session.flush()
        self.session.add(
            PlayerVerification(
                player_id=player.id,
                status="verified",
                verification_source="regen_ecosystem",
                confidence_score=1.0,
                rights_confirmed=True,
                reviewer_notes="Rules-only academy regen generation.",
            )
        )
        tier = self._ensure_regen_card_tier()
        card = PlayerCard(
            player_id=player.id,
            tier_id=tier.id,
            edition_code="regen_unique",
            display_name=generated_profile.display_name,
            season_label=batch.season_label,
            card_variant="academy_regen",
            supply_total=1,
            supply_available=1,
            metadata_json={
                "origin_type": "academy_regen",
                "reason": trigger_reason,
                "regen_id": generated_profile.regen_id,
                "source": source_scope,
            },
        )
        self.session.add(card)
        self.session.flush()
        self.session.add(
            PlayerCardHistory(
                player_card_id=card.id,
                event_type=(
                    "club_progression_intake_created"
                    if source_scope == "club_progression"
                    else "academy_intake_created"
                ),
                description=(
                    "Club progression regen card created from a progression milestone."
                    if source_scope == "club_progression"
                    else "Academy regen card created from the weekly youth pipeline."
                ),
                delta_supply=1,
                delta_available=1,
                actor_user_id=club.owner_user_id,
                metadata_json={"academy_id": academy.id, **audit_payload},
            )
        )
        self.session.add(
            PlayerCardHolding(
                player_card_id=card.id,
                owner_user_id=club.owner_user_id,
                quantity_total=1,
                quantity_reserved=0,
                metadata_json={"origin": source_scope, "trigger_reason": trigger_reason},
            )
        )
        self.session.add(
            PlayerCardOwnerHistory(
                player_card_id=card.id,
                from_user_id=None,
                to_user_id=club.owner_user_id,
                quantity=1,
                event_type=(
                    "club_progression_intake_created"
                    if source_scope == "club_progression"
                    else "academy_intake_created"
                ),
                reference_id=generated_profile.regen_id,
                metadata_json={"club_id": club.id, **audit_payload},
            )
        )
        regen = RegenProfile(
            regen_id=generated_profile.regen_id,
            player_id=player.id,
            linked_unique_card_id=card.id,
            generated_for_club_id=club.id,
            birth_country_code=generated_profile.birth_country_code,
            birth_region=generated_profile.birth_region,
            birth_city=generated_profile.birth_city,
            primary_position=generated_profile.primary_position,
            secondary_positions_json=list(generated_profile.secondary_positions),
            generated_at=generated_profile.generated_at,
            current_gsi=generated_profile.current_gsi,
            current_ability_range_json={
                "minimum": generated_profile.current_ability_range.minimum,
                "maximum": generated_profile.current_ability_range.maximum,
            },
            potential_range_json={
                "minimum": generated_profile.potential_range.minimum,
                "maximum": generated_profile.potential_range.maximum,
            },
            scout_confidence=generated_profile.scout_confidence,
            generation_source=generation_source,
            is_special_lineage=generated_profile.is_special_lineage,
            status="academy_candidate",
            club_quality_score=generated_profile.club_quality_score,
            metadata_json={
                **dict(generated_profile.metadata or {}),
                "rules_only": True,
                "academy_level": academy.level,
                "academy_quality_multiplier": self._academy_quality_multiplier(academy, generated_profile.birth_region),
                "source": source_scope,
                "trigger_reason": trigger_reason,
                **audit_payload,
            },
        )
        self.session.add(regen)
        self.session.flush()
        regen_personality = RegenPersonalityProfile(
            regen_profile_id=regen.id,
            temperament=generated_profile.personality.temperament,
            leadership=generated_profile.personality.leadership,
            ambition=generated_profile.personality.ambition,
            loyalty=generated_profile.personality.loyalty,
            work_rate=generated_profile.personality.work_rate,
            flair=generated_profile.personality.flair,
            resilience=generated_profile.personality.resilience,
            personality_tags_json=list(generated_profile.personality.personality_tags),
        )
        self.session.add(regen_personality)
        origin = RegenOriginMetadata(
            regen_profile_id=regen.id,
            country_code=generated_profile.origin.country_code,
            region_name=generated_profile.origin.region_name,
            city_name=generated_profile.origin.city_name,
            hometown_club_affinity=club.club_name,
            ethnolinguistic_profile=generated_profile.origin.ethnolinguistic_profile,
            religion_naming_pattern=generated_profile.origin.religion_naming_pattern,
            urbanicity=generated_profile.origin.urbanicity,
            metadata_json={"scouting_regions": list(academy.scouting_regions_json), "source": source_scope},
        )
        self.session.add(origin)
        visual_profile = dict((generated_profile.metadata or {}).get("visual_profile") or {})
        regen_visual_profile = RegenVisualProfile(
            regen_profile_id=regen.id,
            portrait_seed=str(visual_profile.get("portrait_seed") or generated_profile.regen_id),
            skin_tone=str(visual_profile.get("skin_tone") or ""),
            hair_profile=str(visual_profile.get("hair_profile") or ""),
            accessory_profile_json=dict(visual_profile.get("accessory_profile") or {}),
            kit_style=str(visual_profile.get("kit_style") or ""),
            metadata_json={},
        )
        self.session.add(regen_visual_profile)
        RegenPortraitService(self.session).ensure_player_portrait(
            player,
            regen=regen,
            visual_profile=regen_visual_profile,
        )
        player_personality = self._ensure_player_personality(
            player=player, regen=regen, regen_personality=regen_personality, origin=origin
        )
        candidate = AcademyCandidate(
            id=generated_candidate.id,
            batch_id=batch.id,
            club_id=club.id,
            regen_profile_id=regen.id,
            display_name=generated_candidate.display_name,
            age=generated_candidate.age,
            nationality_code=generated_candidate.nationality_code,
            birth_region=generated_candidate.birth_region,
            birth_city=generated_candidate.birth_city,
            primary_position=generated_candidate.primary_position,
            secondary_position=generated_candidate.secondary_position,
            current_ability_range_json={
                "minimum": generated_candidate.current_ability_range.minimum,
                "maximum": generated_candidate.current_ability_range.maximum,
            },
            potential_range_json={
                "minimum": generated_candidate.potential_range.minimum,
                "maximum": generated_candidate.potential_range.maximum,
            },
            scout_confidence=generated_candidate.scout_confidence,
            status="academy_candidate",
            metadata_json={
                "decision_deadline_on": (
                    generated_candidate.decision_deadline_on.isoformat()
                    if generated_candidate.decision_deadline_on
                    else None
                ),
                "free_agency_status": generated_candidate.free_agency_status,
                "platform_capture_share_pct": generated_candidate.platform_capture_share_pct,
                "previous_club_capture_share_pct": generated_candidate.previous_club_capture_share_pct,
                "special_training_eligible": generated_candidate.special_training_eligible,
                "source": source_scope,
                "trigger_reason": trigger_reason,
                **audit_payload,
            },
            created_at=generated_candidate.generated_at,
            updated_at=generated_candidate.generated_at,
        )
        self.session.add(candidate)
        self.session.add(
            RegenGenerationEvent(
                regen_profile_id=regen.id,
                club_id=club.id,
                generation_source=generation_source,
                season_label=batch.season_label,
                event_status="generated",
                probability_score=self._region_density(
                    generated_profile.birth_region or generated_profile.birth_country_code
                ),
                quality_roll=self._academy_quality_multiplier(academy, generated_profile.birth_region),
                metadata_json={
                    "academy_batch_id": batch.id,
                    "reason": trigger_reason,
                    "source": source_scope,
                    **audit_payload,
                },
            )
        )
        self.session.add(
            PlayerCareerEntry(
                player_id=player.id,
                club_id=club.id,
                club_name=club.club_name,
                season_label=batch.season_label,
                squad_role="academy_pool",
                appearances=0,
                goals=0,
                assists=0,
                honours_json=[],
                notes=(
                    "Generated through the club progression intake pipeline."
                    if source_scope == "club_progression"
                    else "Generated through the academy player pipeline."
                ),
                start_on=reference_on,
                end_on=None,
            )
        )
        self._record_player_event(
            player_id=player.id,
            club_id=club.id,
            event_type=(
                "club_progression_intake_generated"
                if source_scope == "club_progression"
                else "academy_intake_generated"
            ),
            event_status="academy_pool",
            occurred_on=reference_on,
            summary=(
                f"{player.full_name} joined the club progression intake."
                if source_scope == "club_progression"
                else f"{player.full_name} joined the academy pool."
            ),
            details={"academy_batch_id": batch.id, "academy_candidate_id": candidate.id, **audit_payload},
        )
        if source_scope == "club_progression":
            self.session.add(
                CareerEvent(
                    player_id=player.id,
                    regen_profile_id=regen.id,
                    type="club_progression_intake",
                    occurred_on=reference_on,
                    impact_json={
                        "academy_level": audit_payload.get("academy_level", academy.level),
                        "reason": trigger_reason,
                    },
                    summary=f"{player.full_name} joined through club progression intake.",
                    metadata_json={"academy_batch_id": batch.id, "academy_candidate_id": candidate.id, **audit_payload},
                )
            )
        attr = self._ensure_attribute_profile(regen, player=player, personality=player_personality, refresh=True)
        self._notify(
            club.id,
            "REGEN_DISCOVERED",
            (
                f"{player.full_name} entered the club progression intake."
                if source_scope == "club_progression"
                else f"{player.full_name} entered the academy pool."
            ),
            resource_id=player.id,
        )
        return candidate, regen, player, attr

    def _ensure_player_personality(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        regen_personality: RegenPersonalityProfile,
        origin: RegenOriginMetadata,
    ) -> PlayerPersonality:
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        if personality is not None:
            return personality
        professionalism = regen_personality.work_rate
        greed = self._stable_int("greed", regen.id, minimum=30, maximum=85)
        adaptability = self._stable_int("adaptability", regen.id, minimum=35, maximum=90)
        competitiveness = _clamp_int((regen_personality.ambition * 0.55) + (regen.current_gsi * 0.45))
        ego = _clamp_int((regen_personality.flair * 0.60) + (regen_personality.ambition * 0.25))
        development_focus = _clamp_int((professionalism * 0.55) + (regen_personality.resilience * 0.30))
        hometown_affinity = 82 if origin.city_name else 50
        trophy_hunger = _clamp_int((regen_personality.ambition * 0.70) + (regen.current_gsi * 0.20))
        media_appetite = _clamp_int((regen_personality.flair * 0.70) + 12)
        if greed >= 78:
            target_band = "money-first"
        elif development_focus >= 68:
            target_band = "development-first"
        elif regen_personality.ambition >= 80:
            target_band = "prestige-first"
        elif regen_personality.loyalty >= 70:
            target_band = "stability-first"
        else:
            target_band = "minutes-first"
        personality = PlayerPersonality(
            player_id=player.id,
            regen_profile_id=regen.id,
            source_scope="regen",
            ambition=regen_personality.ambition,
            loyalty=regen_personality.loyalty,
            professionalism=professionalism,
            greed=greed,
            temperament=regen_personality.temperament,
            patience=regen_personality.resilience,
            adaptability=adaptability,
            competitiveness=competitiveness,
            ego=ego,
            development_focus=development_focus,
            hometown_affinity=hometown_affinity,
            trophy_hunger=trophy_hunger,
            media_appetite=media_appetite,
            default_career_target_band=target_band,
            metadata_json={"seeded_by": "regen_ecosystem"},
        )
        self.session.add(personality)
        self.session.flush()
        return personality

    def _ensure_attribute_profile(
        self,
        regen: RegenProfile,
        *,
        player: Player | None = None,
        personality: PlayerPersonality | None = None,
        refresh: bool = False,
    ) -> RegenAttributeProfile:
        player = player or self.session.get(Player, regen.player_id)
        if player is None:
            raise RegenEcosystemNotFoundError("regen_player_not_found")
        personality = personality or self.session.scalar(
            select(PlayerPersonality).where(PlayerPersonality.player_id == player.id)
        )
        if personality is None:
            regen_personality = self.session.scalar(
                select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen.id)
            )
            origin = self.session.scalar(
                select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == regen.id)
            )
            if regen_personality is None or origin is None:
                raise RegenEcosystemNotFoundError("regen_personality_or_origin_missing")
            personality = self._ensure_player_personality(
                player=player, regen=regen, regen_personality=regen_personality, origin=origin
            )
        attr = self.session.scalar(
            select(RegenAttributeProfile).where(RegenAttributeProfile.regen_profile_id == regen.id)
        )
        if attr is None:
            attr = RegenAttributeProfile(regen_profile_id=regen.id, player_id=player.id)
            self.session.add(attr)
        if refresh or not attr.visible_stats_json:
            attr.visible_stats_json = self._build_visible_stats(regen, personality)
            attr.hidden_stats_json = self._build_hidden_stats(regen)
            attr.personality_state_json = self._build_personality_state(regen, personality)
            attr.injury_risk = self._compute_injury_risk(attr.hidden_stats_json)
        self._sync_rarity_and_badges(regen, player, attr)
        self._record_value_snapshot(regen, player, attr)
        self.session.flush()
        return attr

    def _build_visible_stats(self, regen: RegenProfile, personality: PlayerPersonality) -> dict[str, int]:
        current_mid = _midpoint(regen.current_ability_range_json, regen.current_gsi)
        technical = _clamp_int(
            (current_mid * 0.68) + (personality.media_appetite * 0.08) + (personality.development_focus * 0.12)
        )
        physical = _clamp_int((current_mid * 0.64) + (personality.competitiveness * 0.15) + 6)
        mental = _clamp_int((current_mid * 0.60) + (personality.professionalism * 0.20) + (personality.patience * 0.10))
        tactical = _clamp_int((current_mid * 0.62) + (personality.adaptability * 0.18))
        return {"technical": technical, "physical": physical, "mental": mental, "tactical": tactical}

    def _build_hidden_stats(self, regen: RegenProfile) -> dict[str, int]:
        potential_gap = max(
            int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) - regen.current_gsi, 0
        )
        consistency = self._stable_int("consistency", regen.id, minimum=35, maximum=92)
        injury_proneness = self._stable_int("injury_proneness", regen.id, minimum=18, maximum=82)
        clutch_factor = self._stable_int("clutch_factor", regen.id, minimum=30, maximum=96)
        growth_variance = _clamp_int(
            self._stable_int("growth_variance", regen.id, minimum=25, maximum=88) + (potential_gap * 0.4)
        )
        return {
            "consistency": consistency,
            "injury_proneness": injury_proneness,
            "clutch_factor": clutch_factor,
            "growth_variance": growth_variance,
        }

    def _build_personality_state(
        self, regen: RegenProfile, personality: PlayerPersonality
    ) -> dict[str, int | float | str | bool]:
        return {
            "confidence": _clamp_int((personality.ambition * 0.35) + (regen.current_gsi * 0.45)),
            "morale": _clamp_int((personality.loyalty * 0.18) + (personality.professionalism * 0.32) + 24),
            "pressure_response": _clamp_int(
                (personality.temperament * 0.25) + (personality.patience * 0.35) + (personality.competitiveness * 0.20)
            ),
            "agent_pressure": 0,
            "mentor_boost": 0,
        }

    def _sync_rarity_and_badges(self, regen: RegenProfile, player: Player, attr: RegenAttributeProfile) -> None:
        age = _age_on(player.date_of_birth)
        potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        uniqueness = round(
            min(
                100.0,
                (
                    max(potential_max - 70, 0) * 1.1
                    + (10 if regen.is_special_lineage else 0)
                    + (float(attr.hidden_stats_json.get("clutch_factor", 50)) * 0.18)
                    + (float(attr.hidden_stats_json.get("growth_variance", 50)) * 0.16)
                    + (6 if len(regen.secondary_positions_json or []) >= 2 else 0)
                ),
            ),
            2,
        )
        if potential_max >= 94 and uniqueness >= 80:
            rarity = "generational"
        elif potential_max >= 88 and uniqueness >= 65:
            rarity = "elite"
        elif potential_max >= 80 or uniqueness >= 55:
            rarity = "rare"
        else:
            rarity = "common"
        badges: list[str] = []
        if age <= 21 and potential_max >= 86:
            badges.append("wonderkid")
        if age >= 19 and potential_max - regen.current_gsi >= 18:
            badges.append("late_bloomer")
        if len(attr.injury_history_json or []) >= 2 or int(attr.hidden_stats_json.get("injury_proneness", 0)) >= 72:
            badges.append("injury_prone")
        if int(attr.hidden_stats_json.get("clutch_factor", 0)) >= 76:
            badges.append("big_game_player")
        attr.rarity_tier = rarity
        attr.uniqueness_score = uniqueness
        attr.badge_codes_json = badges
        attr.market_value_coin = self._calculate_market_value(regen, player, attr)

    def _record_value_snapshot(self, regen: RegenProfile, player: Player, attr: RegenAttributeProfile) -> None:
        latest = self.session.scalar(
            select(RegenValueSnapshot)
            .where(RegenValueSnapshot.regen_id == regen.id)
            .order_by(RegenValueSnapshot.calculated_at.desc())
        )
        if latest is not None and latest.current_value_coin == attr.market_value_coin:
            return
        current_rating = max(regen.current_gsi, _midpoint(regen.current_ability_range_json, regen.current_gsi))
        potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        ability_component = current_rating * max(current_rating // 2, 1)
        potential_component = current_rating * potential_max
        rarity_component = round(attr.uniqueness_score * 12)
        self.session.add(
            RegenValueSnapshot(
                regen_id=regen.id,
                current_value_coin=attr.market_value_coin,
                ability_component=ability_component,
                potential_component=potential_component,
                reputation_component=round(rarity_component * 0.35),
                narrative_component=round(rarity_component * 0.20),
                demand_component=round(rarity_component * 0.10),
                guardrail_multiplier=self._age_factor(_age_on(player.date_of_birth)),
                metadata_json={"formula": "rating * potential_max * rarity_multiplier * age_factor"},
            )
        )

    def _calculate_market_value(self, regen: RegenProfile, player: Player, attr: RegenAttributeProfile) -> int:
        rating = max(regen.current_gsi, _midpoint(regen.current_ability_range_json, regen.current_gsi))
        potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        rarity_multiplier = _RARITY_MULTIPLIER.get(attr.rarity_tier, 1.0)
        age_factor = self._age_factor(_age_on(player.date_of_birth))
        return max(500, round(rating * potential_max * rarity_multiplier * age_factor))

    def _age_factor(self, age: int) -> float:
        if age <= 18:
            return 1.35
        if age <= 21:
            return 1.22
        if age <= 25:
            return 1.0
        if age <= 29:
            return 0.86
        return 0.72

    def _recent_performance_signal(self, player_id: str) -> dict[str, float | int | bool]:
        season_stats = self.session.scalars(
            select(PlayerSeasonStat).where(PlayerSeasonStat.player_id == player_id)
        ).all()
        match_stats = self.session.scalars(select(PlayerMatchStat).where(PlayerMatchStat.player_id == player_id)).all()
        appearances = sum(max(stat.appearances or 0, 0) for stat in season_stats)
        minutes = sum(max(stat.minutes or 0, 0) for stat in season_stats)
        average_rating_values = [stat.average_rating for stat in season_stats if stat.average_rating is not None]
        if not average_rating_values:
            average_rating_values = [stat.rating for stat in match_stats if stat.rating is not None]
        average_rating = (
            round(sum(average_rating_values) / len(average_rating_values), 2) if average_rating_values else 6.5
        )
        goals = sum(max(stat.goals or 0, 0) for stat in season_stats)
        assists = sum(max(stat.assists or 0, 0) for stat in season_stats)
        return {
            "appearances": appearances,
            "minutes": minutes,
            "average_rating": average_rating,
            "high_performance": average_rating >= 7.1 or goals + assists >= 10,
        }

    def _mentorship_boost(self, player: Player, regen: RegenProfile, *, force: bool = False) -> int:
        if player.current_club_profile_id is None:
            return 0
        peers = self.session.scalars(
            select(Player)
            .where(
                Player.current_club_profile_id == player.current_club_profile_id,
                Player.id != player.id,
                Player.normalized_position == player.normalized_position,
            )
            .order_by(Player.date_of_birth.asc())
        ).all()
        for peer in peers:
            if _age_on(peer.date_of_birth) < 28 and not force:
                continue
            total_appearances = int(
                self.session.scalar(
                    select(func.coalesce(func.sum(PlayerCareerEntry.appearances), 0)).where(
                        PlayerCareerEntry.player_id == peer.id
                    )
                )
                or 0
            )
            if total_appearances < 80 and not force:
                continue
            return 2 if force else 1
        return 0

    def _evolve_personality(self, player_id: str, *, reference_on: date | None = None) -> None:
        player = self.session.get(Player, player_id)
        regen = self._require_regen_by_player(player_id)
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player_id))
        if player is None or personality is None:
            return
        attr = self._ensure_attribute_profile(regen, player=player, personality=personality)
        effective_date = reference_on or date.today()
        match_rows = self.session.execute(
            select(PlayerMatchStat, Match, Competition)
            .join(Match, Match.id == PlayerMatchStat.match_id)
            .outerjoin(Competition, Competition.id == Match.competition_id)
            .where(PlayerMatchStat.player_id == player_id)
            .order_by(Match.kickoff_at.desc())
            .limit(12)
        ).all()
        wins = 0
        bench_count = 0
        big_matches = 0
        good_big_matches = 0
        for stat, match, competition in match_rows:
            if match.winner_club_id is not None and stat.club_id == match.winner_club_id:
                wins += 1
            if (stat.starts or 0) <= 0:
                bench_count += 1
            is_big = (
                bool(getattr(competition, "is_major", False))
                or (getattr(competition, "competition_strength", 0) or 0) >= 75
            )
            if is_big:
                big_matches += 1
                if (stat.rating or 0) >= 7.0:
                    good_big_matches += 1
        state = dict(attr.personality_state_json or {})
        confidence = float(state.get("confidence", 50))
        morale = float(state.get("morale", 50))
        pressure = float(state.get("pressure_response", 50))
        if wins >= 4:
            confidence += 6
        if bench_count >= 4:
            morale -= 7
        if big_matches >= 2:
            pressure += 5 if good_big_matches >= max(1, big_matches // 2) else -4
        state["confidence"] = _clamp_int(confidence)
        state["morale"] = _clamp_int(morale)
        state["pressure_response"] = _clamp_int(pressure)
        state["last_evolved_on"] = effective_date.isoformat()
        attr.personality_state_json = state
        personality.competitiveness = _clamp_int((personality.competitiveness * 0.85) + (state["confidence"] * 0.15))
        personality.patience = _clamp_int((personality.patience * 0.85) + (state["pressure_response"] * 0.15))
        self.sync_agent_contract_pressure(player_id, reference_on=effective_date)

    def _choose_career_event(self, regen: RegenProfile, attr: RegenAttributeProfile) -> str:
        injury_roll = self._stable_ratio("career-injury", regen.id, str(len(attr.injury_history_json or [])))
        breakout_roll = self._stable_ratio(
            "career-breakout", regen.id, str((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        )
        if injury_roll < min(0.55, attr.injury_risk / 100.0):
            return "injury"
        if breakout_roll < 0.35 and int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) >= 84:
            return "breakout"
        if self._stable_ratio("career-transfer", regen.id, regen.status) < 0.20:
            return "transfer_drama"
        if self._stable_ratio("career-mentor", regen.id, regen.primary_position) < 0.18:
            return "mentorship"
        return "scandal"

    def _injury_severity(self, attr: RegenAttributeProfile) -> InjurySeverity:
        risk = attr.injury_risk
        if risk >= 70:
            return InjurySeverity.SEASON_ENDING
        if risk >= 58:
            return InjurySeverity.MAJOR
        if risk >= 42:
            return InjurySeverity.MODERATE
        return InjurySeverity.MINOR

    def _compute_injury_risk(self, hidden_stats: dict[str, int]) -> float:
        proneness = float(hidden_stats.get("injury_proneness", 50))
        consistency = float(hidden_stats.get("consistency", 50))
        return round(_clamp_float((proneness * 0.72) + ((100.0 - consistency) * 0.18) + 6.0), 2)

    def _resolve_report_scout(self, regen: RegenProfile, *, scout_id: str | None) -> Scout:
        if scout_id is not None:
            scout = self.session.get(Scout, scout_id)
            if scout is None:
                raise RegenEcosystemNotFoundError("scout_not_found")
            return scout
        scout = self.session.scalar(
            select(Scout)
            .where(Scout.club_id == regen.generated_for_club_id, Scout.active.is_(True))
            .order_by(Scout.skill_rating.desc(), Scout.created_at.asc())
        )
        if scout is None:
            club = self.session.get(ClubProfile, regen.generated_for_club_id)
            if club is None:
                raise RegenEcosystemNotFoundError("club_not_found")
            scout = self.create_scout(
                club_user_id=club.owner_user_id,
                club_id=club.id,
                region=regen.birth_region or club.region_name or club.country_code or "domestic",
                skill_rating=55,
                specialty="youth",
            )
        return scout

    def _estimate_hidden_value(
        self,
        *,
        actual: int,
        accuracy: int,
        specialty: str,
        stat_key: str,
        scout_id: str,
        regen_id: str,
    ) -> int | None:
        specialty_bonus = 0
        if specialty == "physical" and stat_key == "injury_proneness":
            specialty_bonus = 12
        if specialty == "technical" and stat_key in {"consistency", "clutch_factor"}:
            specialty_bonus = 8
        effective_accuracy = min(100, accuracy + specialty_bonus)
        if self._stable_ratio("reveal", scout_id, regen_id, stat_key) > effective_accuracy / 100.0:
            return None
        noise = max(1, round((100 - effective_accuracy) / 10))
        delta = self._stable_int("reveal-noise", scout_id, regen_id, stat_key, minimum=-noise, maximum=noise)
        return _clamp_int(actual + delta)

    def _fallback_ranked_regens(self, *, limit: int, sort_key: str) -> tuple[RegenHubPlayerView, ...]:
        regens = self.session.scalars(select(RegenProfile).order_by(RegenProfile.generated_at.desc())).all()
        ranked: list[tuple[float, RegenHubPlayerView]] = []
        for regen in regens:
            player = self.session.get(Player, regen.player_id)
            if player is None:
                continue
            attr = self._ensure_attribute_profile(regen, player=player)
            score = float(attr.market_value_coin if sort_key == "market_value" else attr.uniqueness_score)
            ranked.append((score, self._to_hub_player_view(regen, player, attr, score=score, rank=None)))
        result = [item for _score, item in sorted(ranked, key=lambda value: value[0], reverse=True)[: max(limit, 1)]]
        for index, item in enumerate(result, start=1):
            item.rank = index
        return tuple(result)

    def _academy_generation_result_from_batch(
        self,
        *,
        academy: YouthAcademy,
        batch: AcademyIntakeBatch,
    ) -> AcademyGenerationResultView:
        generated_players: list[AcademyGeneratedPlayerView] = []
        rows = self.session.execute(
            select(AcademyCandidate, RegenProfile, Player)
            .join(RegenProfile, RegenProfile.id == AcademyCandidate.regen_profile_id)
            .join(Player, Player.id == RegenProfile.player_id)
            .where(AcademyCandidate.batch_id == batch.id)
            .order_by(AcademyCandidate.created_at.asc(), AcademyCandidate.id.asc())
        ).all()
        for candidate, regen, player in rows:
            attr = self._ensure_attribute_profile(regen, player=player)
            generated_players.append(self._to_generated_player_view(candidate, regen, player, attr))
        return AcademyGenerationResultView(
            academy=self._to_academy_view(academy),
            batch_id=batch.id,
            season_label=batch.season_label,
            generated_count=len(generated_players),
            generated_players=tuple(generated_players),
        )

    def _ensure_academy_for_club(self, club: ClubProfile) -> YouthAcademy:
        academy = self.session.scalar(select(YouthAcademy).where(YouthAcademy.club_id == club.id))
        if academy is None:
            academy = self.upsert_academy(club_user_id=club.owner_user_id, club_id=club.id)
        elif academy.club_id != club.id:
            academy.club_id = club.id
            self.session.flush()
        return academy

    def _club_progression_intake_size(
        self,
        *,
        club_id: str,
        season_id: str,
        reason: str,
        academy_level: int,
    ) -> int:
        minimum, maximum = self._club_progression_intake_bounds(academy_level)
        return self._stable_int(
            "club-progression-intake-size",
            club_id,
            season_id,
            reason,
            str(academy_level),
            minimum=minimum,
            maximum=maximum,
        )

    def _club_progression_intake_bounds(self, academy_level: int) -> tuple[int, int]:
        normalized_level = max(academy_level, 1)
        if normalized_level <= 1:
            return (1, 2)
        if normalized_level == 2:
            return (2, 3)
        if normalized_level == 3:
            return (3, 5)
        return (5, 8)

    def _regen_season_label(self, season: RegenSeason) -> str:
        metadata_label = str((season.metadata_json or {}).get("season_label") or "").strip()
        if metadata_label:
            return metadata_label
        return f"{season.start_date.year}/{season.end_date.year}"

    def _build_progression_club_context(
        self,
        club: ClubProfile,
        academy: YouthAcademy,
        *,
        academy_level: int,
    ) -> RegenClubContext:
        base_context = self._build_club_context(club, academy)
        return replace(
            base_context,
            youth_coaching=max(base_context.youth_coaching, float(academy_level * 12)),
            training_level=max(base_context.training_level, float(academy_level * 11)),
            academy_level=max(base_context.academy_level, float(academy_level * 14)),
            academy_investment=max(base_context.academy_investment, float(academy_level * 14)),
            manager_youth_development=max(
                base_context.manager_youth_development, float(min(95, (academy_level * 16) + 14))
            ),
        )

    def _to_generated_player_view(
        self,
        candidate: AcademyCandidate | None,
        regen: RegenProfile,
        player: Player,
        attr: RegenAttributeProfile,
    ) -> AcademyGeneratedPlayerView:
        return AcademyGeneratedPlayerView(
            academy_candidate_id=candidate.id if candidate is not None else regen.id,
            player_id=player.id,
            regen_profile_id=regen.id,
            regen_id=regen.regen_id,
            display_name=player.full_name,
            age=_age_on(player.date_of_birth),
            primary_position=regen.primary_position,
            potential_min=int((regen.potential_range_json or {}).get("minimum", regen.current_gsi)),
            potential_max=int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)),
            rarity_tier=attr.rarity_tier,
            badge_codes=tuple(attr.badge_codes_json or []),
            market_value_coin=attr.market_value_coin,
        )

    def _to_hub_player_view(
        self,
        regen: RegenProfile,
        player: Player,
        attr: RegenAttributeProfile,
        *,
        score: float,
        rank: int | None,
    ) -> RegenHubPlayerView:
        return RegenHubPlayerView(
            player_id=player.id,
            regen_profile_id=regen.id,
            regen_id=regen.regen_id,
            display_name=player.full_name,
            age=_age_on(player.date_of_birth),
            primary_position=regen.primary_position,
            current_rating=max(regen.current_gsi, _midpoint(regen.current_ability_range_json, regen.current_gsi)),
            potential_max=int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)),
            rarity_tier=attr.rarity_tier,
            uniqueness_score=attr.uniqueness_score,
            market_value_coin=attr.market_value_coin,
            badge_codes=tuple(attr.badge_codes_json or []),
            score=round(score, 2),
            rank=rank,
        )

    def _to_scout_view(self, scout: Scout) -> ScoutView:
        return ScoutView(
            id=scout.id,
            club_user_id=scout.club_user_id,
            club_id=scout.club_id,
            region=scout.region,
            skill_rating=scout.skill_rating,
            specialty=scout.specialty,
            active=scout.active,
            created_at=scout.created_at,
            updated_at=scout.updated_at,
        )

    def _to_academy_view(self, academy: YouthAcademy) -> YouthAcademyView:
        return YouthAcademyView(
            id=academy.id,
            club_user_id=academy.club_user_id,
            club_id=academy.club_id,
            level=academy.level,
            scouting_regions=tuple(academy.scouting_regions_json or []),
            capacity=academy.capacity,
            upgrade_cost=academy.upgrade_cost,
            created_at=academy.created_at,
            updated_at=academy.updated_at,
        )

    def _to_agent_view(self, agent: Agent) -> AgentView:
        return AgentView(
            id=agent.id,
            name=agent.name,
            negotiation_skill=agent.negotiation_skill,
            player_ids=tuple(agent.player_ids_json or []),
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )

    def _to_vote_view(self, vote: RegenAwardVote) -> AwardVoteView:
        return AwardVoteView(
            id=vote.id,
            user_id=vote.user_id,
            player_id=vote.player_id,
            award_id=vote.award_id,
            season_id=vote.season_id,
            voted_at=vote.voted_at,
        )

    def _to_career_event_view(self, event: CareerEvent) -> CareerEventView:
        return CareerEventView(
            id=event.id,
            player_id=event.player_id,
            regen_profile_id=event.regen_profile_id,
            type=event.type,
            occurred_on=event.occurred_on,
            impact=dict(event.impact_json or {}),
            summary=event.summary,
            created_at=event.created_at,
        )

    def _resolve_club(self, *, club_user_id: str, club_id: str | None = None) -> ClubProfile:
        if club_id is not None:
            club = self.session.get(ClubProfile, club_id)
            if club is not None and club.owner_user_id == club_user_id:
                return club
        club = self.session.scalar(
            select(ClubProfile).where(ClubProfile.owner_user_id == club_user_id).order_by(ClubProfile.created_at.asc())
        )
        if club is None:
            raise RegenEcosystemNotFoundError("club_not_found")
        return club

    def _resolve_candidate_player(self, player_identifier: str) -> tuple[AcademyCandidate, RegenProfile, Player]:
        candidate = self.session.get(AcademyCandidate, player_identifier)
        regen = None
        if candidate is None:
            regen = self._resolve_regen(player_identifier)
            candidate = self.session.scalar(
                select(AcademyCandidate).where(AcademyCandidate.regen_profile_id == regen.id)
            )
            if candidate is None:
                raise RegenEcosystemNotFoundError("academy_candidate_not_found")
        else:
            regen = self.session.get(RegenProfile, candidate.regen_profile_id)
        if regen is None:
            raise RegenEcosystemNotFoundError("regen_not_found")
        player = self.session.get(Player, regen.player_id)
        if player is None:
            raise RegenEcosystemNotFoundError("player_not_found")
        return candidate, regen, player

    def _resolve_regen(self, identifier: str) -> RegenProfile:
        regen = self.session.get(RegenProfile, identifier)
        if regen is not None:
            return regen
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.regen_id == identifier))
        if regen is not None:
            return regen
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == identifier))
        if regen is not None:
            return regen
        raise RegenEcosystemNotFoundError("regen_not_found")

    def _require_regen_by_player(self, player_id: str) -> RegenProfile:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        if regen is None:
            raise RegenEcosystemNotFoundError("regen_not_found")
        return regen

    def _occupied_academy_slots(self, club_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count(AcademyCandidate.id)).where(
                    AcademyCandidate.club_id == club_id,
                    AcademyCandidate.status.not_in(("promoted", "released", "free_agent")),
                )
            )
            or 0
        )

    def _academy_capacity_remaining(self, club_id: str) -> int:
        academy = self.session.scalar(select(YouthAcademy).where(YouthAcademy.club_id == club_id))
        if academy is None:
            return 0
        return max(academy.capacity - self._occupied_academy_slots(club_id), 0)

    def _build_club_context(self, club: ClubProfile, academy: YouthAcademy) -> RegenClubContext:
        facility = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club.id))
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club.id))
        effective_level = self._effective_academy_level(club.id, academy=academy, facility=facility)
        academy_score = effective_level * 10
        return RegenClubContext(
            country_code=club.country_code or self.settings.regen_generation.default_country_code,
            region_name=club.region_name,
            city_name=club.city_name,
            youth_coaching=float(effective_level * 10),
            training_level=float(
                max(facility.training_level if facility is not None else effective_level, effective_level) * 10
            ),
            academy_level=float(academy_score),
            academy_investment=float(academy_score),
            first_team_gsi=58.0,
            club_reputation=float(reputation.current_score if reputation is not None else 50.0),
            competition_quality=float(reputation.current_score if reputation is not None else 45.0),
            manager_youth_development=float(min(95, academy_score + 10)),
            urbanicity="urban" if club.city_name else None,
        )

    def _effective_academy_level(
        self,
        club_id: str,
        *,
        academy: YouthAcademy,
        facility: ClubFacility | None = None,
    ) -> int:
        resolved_facility = facility or self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club_id))
        facility_level = resolved_facility.academy_level if resolved_facility is not None else academy.level
        return max(1, academy.level, facility_level)

    def _academy_quality_multiplier(self, academy: YouthAcademy, region_name: str | None) -> float:
        base_random = 0.82 + (self._stable_ratio("academy-quality", academy.id, region_name or "default") * 0.36)
        region_strength = self._region_strength(region_name)
        return round(base_random * academy.level * region_strength / 10.0, 4)

    def _region_strength(self, region_name: str | None) -> float:
        if not region_name:
            return 1.0
        return _REGION_STRENGTH.get(region_name.strip().lower(), 1.0)

    def _region_density(self, region_name: str | None) -> float:
        if not region_name:
            return 0.5
        return _REGION_TALENT_DENSITY.get(region_name.strip().lower(), 0.5)

    def _matches_region(self, regen: RegenProfile, region_query: str) -> bool:
        tokens = {
            (regen.birth_region or "").strip().lower(),
            (regen.birth_city or "").strip().lower(),
            (regen.birth_country_code or "").strip().lower(),
        }
        return region_query.strip().lower() in tokens

    def _already_discovered(self, club_id: str, regen_id: str) -> bool:
        return (
            self.session.scalar(
                select(RegenDiscoveryBadge.id).where(
                    RegenDiscoveryBadge.club_id == club_id,
                    RegenDiscoveryBadge.regen_id == regen_id,
                    RegenDiscoveryBadge.badge_code == "discovered",
                )
            )
            is not None
        )

    def _ensure_country(self, country_code: str) -> Country:
        code = country_code.upper()
        country = self.session.scalar(select(Country).where(Country.alpha2_code == code))
        if country is not None:
            return country
        country = Country(
            source_provider="regen_ecosystem",
            provider_external_id=f"country:{code}",
            name=code,
            alpha2_code=code,
            alpha3_code=code,
            fifa_code=code,
            confederation_code=None,
            market_region="regen",
            is_enabled_for_universe=True,
        )
        self.session.add(country)
        self.session.flush()
        return country

    def _ensure_regen_card_tier(self) -> PlayerCardTier:
        tier = self.session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == "regen_unique"))
        if tier is not None:
            return tier
        tier = PlayerCardTier(
            code="regen_unique",
            name="Regen Unique",
            rarity_rank=99,
            max_supply=1,
            supply_multiplier=Decimal("1.0000"),
            base_mint_price_credits=Decimal("0.0000"),
            color_hex="#C88C2D",
            is_active=True,
            metadata_json={"origin_type": "regen"},
        )
        self.session.add(tier)
        self.session.flush()
        return tier

    def _record_player_event(
        self,
        *,
        player_id: str,
        club_id: str | None,
        event_type: str,
        event_status: str,
        occurred_on: date,
        summary: str,
        details: dict[str, object],
    ) -> None:
        self.session.add(
            PlayerLifecycleEvent(
                player_id=player_id,
                club_id=club_id,
                event_type=event_type,
                event_status=event_status,
                occurred_on=occurred_on,
                effective_from=occurred_on,
                summary=summary,
                details_json=details,
            )
        )

    def _promote_career_entry(self, player_id: str) -> None:
        entry = self.session.scalar(
            select(PlayerCareerEntry)
            .where(PlayerCareerEntry.player_id == player_id)
            .order_by(PlayerCareerEntry.created_at.desc())
        )
        if entry is not None:
            entry.squad_role = "academy_graduate"

    def _notify(self, club_id: str | None, topic: str, message: str, *, resource_id: str | None = None) -> None:
        if not club_id:
            return
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            return
        self.session.add(
            NotificationRecord(
                user_id=club.owner_user_id,
                topic=topic,
                template_key=topic,
                resource_type="player" if resource_id is not None else None,
                resource_id=resource_id,
                message=message[:255],
                metadata_json={"club_id": club_id},
            )
        )

    def _latest_contract(self, player_id: str) -> PlayerContract | None:
        return self.session.scalar(
            select(PlayerContract)
            .where(PlayerContract.player_id == player_id)
            .order_by(PlayerContract.ends_on.desc(), PlayerContract.created_at.desc())
        )

    def _initial_salary_for_regen(self, regen: RegenProfile) -> Decimal:
        potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        salary = max(250, round((regen.current_gsi * 6.5) + (potential_max * 2.1)))
        return Decimal(str(salary))

    def _agent_salary_expectation(self, regen: RegenProfile, attr: RegenAttributeProfile, agent: Agent) -> Decimal:
        potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        demand = max(
            300, round((potential_max * 9.5) + (agent.negotiation_skill * 4.2) + (attr.market_value_coin / 180))
        )
        return Decimal(str(demand))

    def _ensure_agent_for_player(self, player_id: str) -> Agent:
        agents = self.session.scalars(select(Agent).order_by(Agent.created_at.asc())).all()
        for agent in agents:
            if player_id in set(agent.player_ids_json or []):
                return agent
        name = _AGENT_NAMES[self._stable_seed("agent-name", player_id) % len(_AGENT_NAMES)]
        negotiation_skill = self._stable_int("agent-skill", player_id, minimum=48, maximum=92)
        agent = Agent(
            name=name,
            negotiation_skill=negotiation_skill,
            player_ids_json=[player_id],
            metadata_json={"auto_created": True},
        )
        self.session.add(agent)
        self.session.flush()
        return agent

    def _latest_or_active_season(self) -> RegenSeason | None:
        season = self.session.scalar(
            select(RegenSeason).where(RegenSeason.is_active.is_(True)).order_by(RegenSeason.season_number.desc())
        )
        if season is not None:
            return season
        return self.session.scalar(select(RegenSeason).order_by(RegenSeason.season_number.desc()))

    def _resolve_season(self, season_id: str | None) -> RegenSeason | None:
        if season_id is not None:
            return self.session.get(RegenSeason, season_id)
        return self._latest_or_active_season()

    def _regen_id_for_player(self, player_id: str) -> str | None:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        return regen.id if regen is not None else None

    def _player_name(self, player_id: str) -> str | None:
        player = self.session.get(Player, player_id)
        return player.full_name if player is not None else None

    def _normalized_position(self, position: str) -> str:
        if position == "GK":
            return "goalkeeper"
        if position in {"CB", "RB", "LB"}:
            return "defender"
        if position in {"DM", "CM", "AM"}:
            return "midfielder"
        return "forward"

    def _stable_seed(self, *parts: str) -> int:
        digest = sha256(":".join(parts).encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _stable_ratio(self, *parts: str) -> float:
        return (self._stable_seed(*parts) % 10_000) / 10_000.0

    def _stable_int(self, *parts: str, minimum: int, maximum: int) -> int:
        if maximum <= minimum:
            return minimum
        span = maximum - minimum + 1
        return minimum + (self._stable_seed(*parts) % span)


__all__ = [
    "RegenEcosystemError",
    "RegenEcosystemNotFoundError",
    "RegenEcosystemService",
    "RegenEcosystemValidationError",
]
