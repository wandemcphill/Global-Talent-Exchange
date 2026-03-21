from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import ClubReputationProfile
from app.ingestion.models import Competition, Player, PlayerSeasonStat
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.player_agency_state import PlayerAgencyState
from app.models.player_contract import PlayerContract
from app.models.player_personality import PlayerPersonality
from app.models.regen import RegenOriginMetadata, RegenProfile

DECIMAL_QUANTUM = Decimal("0.0001")


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def quantize_amount(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class AgencyReason:
    code: str
    text: str
    weight: float


@dataclass(frozen=True, slots=True)
class AgencyDecisionOutcome:
    decision_code: str
    decision_score: float
    confidence_band: str
    primary_reasons: tuple[AgencyReason, ...] = ()
    secondary_reasons: tuple[AgencyReason, ...] = ()
    persuading_factors: tuple[str, ...] = ()
    component_scores: dict[str, float] = field(default_factory=dict)
    next_review_at: datetime | None = None
    cooldown_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class AgencyClubContext:
    club_id: str | None
    club_name: str | None
    club_stature: float
    reputation_score: float
    league_quality: float
    competition_level: float
    project_attractiveness: float
    development_score: float
    expected_minutes_score: float
    squad_congestion: float
    bench_risk: float
    trophy_score: float
    geography_score: float
    continental_football: bool


@dataclass(frozen=True, slots=True)
class AgencyPlayerContext:
    player: Player
    regen: RegenProfile
    personality: PlayerPersonality
    state: PlayerAgencyState
    current_contract: PlayerContract | None
    current_club: AgencyClubContext
    current_wage_amount: Decimal
    salary_expectation_amount: Decimal
    playing_time_ratio: float
    current_minutes_score: float
    same_position_depth: int
    career_stage: str
    career_target_band: str
    preferred_role_band: str
    age_years: int | None
    lifecycle_months: int
    days_remaining: int | None
    reference_on: date


@dataclass(frozen=True, slots=True)
class ContractEvaluationInput:
    offering_club_id: str | None
    offered_wage_amount: Decimal
    contract_years: int
    role_promised: str | None
    release_clause_amount: Decimal | None
    bonus_amount: Decimal | None
    club_stature: float | None = None
    league_quality: float | None = None
    pathway_to_minutes: float | None = None
    development_opportunity: float | None = None
    squad_congestion: float | None = None
    project_attractiveness: float | None = None
    competition_level: float | None = None
    continental_football: bool | None = None
    is_renewal: bool = False
    requested_on: date | None = None


@dataclass(frozen=True, slots=True)
class TransferEvaluationInput:
    destination_club_id: str
    offered_wage_amount: Decimal
    contract_years: int
    expected_role: str | None
    expected_minutes: float | None = None
    club_stature: float | None = None
    league_quality: float | None = None
    competition_level: float | None = None
    squad_congestion: float | None = None
    development_fit: float | None = None
    geography_score: float | None = None
    continental_football: bool | None = None
    transfer_denied_recently: bool | None = None
    requested_on: date | None = None


@dataclass(slots=True)
class PlayerAgencyContextService:
    session: Session

    def build_player_context(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        personality: PlayerPersonality,
        state: PlayerAgencyState,
        reference_on: date,
    ) -> AgencyPlayerContext:
        current_contract = self.get_current_contract(player.id, reference_on=reference_on)
        current_club_id = current_contract.club_id if current_contract is not None else player.current_club_profile_id
        playing_time_ratio = self.current_playing_time_ratio(player)
        current_club = self.build_club_context(
            player=player,
            regen=regen,
            club_id=current_club_id,
            reference_on=reference_on,
            expected_minutes=playing_time_ratio * 100.0,
            role_label=state.preferred_role_band,
        )
        lifecycle_months = self.lifecycle_months(regen, reference_on=reference_on)
        age_years = self.resolve_age_years(player, regen=regen, reference_on=reference_on)
        current_wage = current_contract.wage_amount if current_contract is not None else Decimal("0.0000")
        salary_expectation = quantize_amount(
            max(
                state.salary_expectation_amount,
                Decimal(max(150, round((regen.current_gsi * 6.0) + (personality.ambition * 3.1) + (personality.greed * 2.6)))),
                current_wage,
            )
        )
        days_remaining = None
        if current_contract is not None:
            days_remaining = max(0, (current_contract.ends_on - reference_on).days)
        career_stage = self.infer_career_stage(
            player=player,
            regen=regen,
            personality=personality,
            reference_on=reference_on,
        )
        return AgencyPlayerContext(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            current_contract=current_contract,
            current_club=current_club,
            current_wage_amount=current_wage,
            salary_expectation_amount=salary_expectation,
            playing_time_ratio=playing_time_ratio,
            current_minutes_score=clamp(playing_time_ratio * 100.0),
            same_position_depth=self.position_depth(current_club_id, player.normalized_position),
            career_stage=career_stage,
            career_target_band=self.infer_career_target_band(
                player=player,
                regen=regen,
                personality=personality,
                state=state,
                reference_on=reference_on,
            ),
            preferred_role_band=self.infer_preferred_role_band(personality=personality, career_stage=career_stage),
            age_years=age_years,
            lifecycle_months=lifecycle_months,
            days_remaining=days_remaining,
            reference_on=reference_on,
        )

    def build_club_context(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        club_id: str | None,
        reference_on: date,
        club_stature: float | None = None,
        league_quality: float | None = None,
        competition_level: float | None = None,
        expected_minutes: float | None = None,
        development_fit: float | None = None,
        squad_congestion: float | None = None,
        project_attractiveness: float | None = None,
        geography_score: float | None = None,
        continental_football: bool | None = None,
        role_label: str | None = None,
    ) -> AgencyClubContext:
        del reference_on
        if club_id is None:
            empty_score = clamp(expected_minutes or 0.0)
            return AgencyClubContext(
                club_id=None,
                club_name=None,
                club_stature=0.0,
                reputation_score=0.0,
                league_quality=0.0,
                competition_level=0.0,
                project_attractiveness=0.0,
                development_score=0.0,
                expected_minutes_score=empty_score,
                squad_congestion=100.0,
                bench_risk=100.0,
                trophy_score=0.0,
                geography_score=0.0,
                continental_football=False,
            )

        profile = self.session.get(ClubProfile, club_id)
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        facility = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club_id))
        origin = self.session.scalar(select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == regen.id))

        reputation_score = float(club_stature if club_stature is not None else (reputation.current_score if reputation is not None else 45))
        trophy_score = clamp(
            (
                ((reputation.total_league_titles if reputation is not None else 0) * 8)
                + ((reputation.total_continental_titles if reputation is not None else 0) * 12)
                + ((reputation.total_world_super_cup_titles if reputation is not None else 0) * 18)
            ),
        )
        development_score = (
            clamp(development_fit)
            if development_fit is not None
            else clamp((((facility.training_level if facility is not None else 1) + (facility.academy_level if facility is not None else 1)) / 2) * 20.0)
        )
        resolved_league_quality = clamp(league_quality if league_quality is not None else self._league_quality_for_player(player, reputation_score))
        resolved_competition_level = clamp(competition_level if competition_level is not None else resolved_league_quality)
        resolved_geography_score = clamp(geography_score) if geography_score is not None else self._geography_score(profile=profile, origin=origin)
        depth = self.position_depth(club_id, player.normalized_position)
        resolved_congestion = clamp(squad_congestion if squad_congestion is not None else max(10.0, depth * 22.0))
        resolved_minutes = clamp(
            expected_minutes
            if expected_minutes is not None
            else (92.0 - (resolved_congestion * 0.55) + (development_score * 0.08) - (reputation_score * 0.08) + self._role_minutes_adjustment(role_label))
        )
        resolved_project = clamp(
            project_attractiveness
            if project_attractiveness is not None
            else ((reputation_score * 0.36) + (development_score * 0.28) + (resolved_competition_level * 0.16) + (trophy_score * 0.12) + (8.0 if continental_football else 0.0))
        )
        resolved_stature = clamp(club_stature if club_stature is not None else ((reputation_score * 0.74) + (trophy_score * 0.26)))
        resolved_continental = bool(
            continental_football
            if continental_football is not None
            else (reputation.total_continental_qualifications if reputation is not None else 0) > 0
        )
        bench_risk = clamp((resolved_congestion * 0.58) + (resolved_stature * 0.22) - (resolved_minutes * 0.45))
        return AgencyClubContext(
            club_id=club_id,
            club_name=profile.club_name if profile is not None else None,
            club_stature=resolved_stature,
            reputation_score=reputation_score,
            league_quality=resolved_league_quality,
            competition_level=resolved_competition_level,
            project_attractiveness=resolved_project,
            development_score=development_score,
            expected_minutes_score=resolved_minutes,
            squad_congestion=resolved_congestion,
            bench_risk=bench_risk,
            trophy_score=trophy_score,
            geography_score=resolved_geography_score,
            continental_football=resolved_continental,
        )

    def get_current_contract(self, player_id: str, *, reference_on: date) -> PlayerContract | None:
        statement = (
            select(PlayerContract)
            .where(PlayerContract.player_id == player_id)
            .order_by(PlayerContract.starts_on.desc(), PlayerContract.created_at.desc())
        )
        contracts = list(self.session.scalars(statement))
        for contract in contracts:
            if contract.starts_on <= reference_on <= contract.ends_on and contract.status in {"active", "expiring"}:
                return contract
        for contract in contracts:
            if contract.starts_on <= reference_on <= contract.ends_on:
                return contract
        return None

    def current_playing_time_ratio(self, player: Player) -> float:
        latest = self._latest_season_stat(player)
        if latest is None:
            return 0.65
        appearances = latest.appearances or 0
        starts = latest.starts or 0
        if appearances <= 0:
            return 0.2
        return clamp(starts / appearances, 0.0, 1.0)

    def lifecycle_months(self, regen: RegenProfile, *, reference_on: date) -> int:
        months = (reference_on.year - regen.generated_at.year) * 12 + (reference_on.month - regen.generated_at.month)
        if reference_on.day < regen.generated_at.day:
            months -= 1
        return max(0, months)

    def resolve_age_years(self, player: Player, *, regen: RegenProfile, reference_on: date) -> int | None:
        if player.date_of_birth is not None:
            years = reference_on.year - player.date_of_birth.year
            if (reference_on.month, reference_on.day) < (player.date_of_birth.month, player.date_of_birth.day):
                years -= 1
            return max(0, years)
        return 17 + (self.lifecycle_months(regen, reference_on=reference_on) // 12)

    def infer_career_stage(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        personality: PlayerPersonality,
        reference_on: date,
    ) -> str:
        del personality
        age_years = self.resolve_age_years(player, regen=regen, reference_on=reference_on)
        potential_gap = max(0, int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) - regen.current_gsi)
        lifecycle_months = self.lifecycle_months(regen, reference_on=reference_on)
        if age_years is not None:
            if age_years <= 19 and potential_gap >= 12:
                return "wonderkid"
            if age_years <= 21:
                return "prospect"
            if age_years <= 23:
                return "breakout"
            if age_years <= 27:
                return "established"
            if age_years <= 31:
                return "prime"
            return "veteran"
        if lifecycle_months <= 6 and potential_gap >= 12:
            return "wonderkid"
        if lifecycle_months <= 12:
            return "prospect"
        if lifecycle_months <= 18:
            return "breakout"
        if lifecycle_months <= 28:
            return "established"
        if lifecycle_months <= 40:
            return "prime"
        return "veteran"

    def infer_career_target_band(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        personality: PlayerPersonality,
        state: PlayerAgencyState,
        reference_on: date,
    ) -> str:
        stage = state.career_stage or self.infer_career_stage(
            player=player,
            regen=regen,
            personality=personality,
            reference_on=reference_on,
        )
        if personality.greed >= 78:
            return "money-first"
        if stage in {"wonderkid", "prospect"} and personality.development_focus >= 62:
            return "development-first"
        if state.playing_time_satisfaction < 45 or (personality.ego >= 75 and stage in {"breakout", "established"}):
            return "minutes-first"
        if stage == "veteran" and personality.loyalty + personality.professionalism >= 132:
            return "stability-first"
        if personality.ambition >= 82 and personality.trophy_hunger >= 72:
            return "trophy-first"
        if personality.ambition >= 72:
            return "prestige-first"
        return "stability-first"

    def infer_preferred_role_band(self, *, personality: PlayerPersonality, career_stage: str) -> str:
        if personality.ego >= 82 or personality.competitiveness >= 86:
            return "star"
        if career_stage in {"wonderkid", "prospect"} and personality.development_focus >= 68:
            return "breakthrough"
        if personality.ambition >= 66:
            return "starter"
        return "rotation"

    def position_depth(self, club_id: str | None, normalized_position: str | None) -> int:
        if club_id is None or normalized_position is None:
            return 0
        statement = (
            select(func.count(Player.id))
            .where(
                Player.current_club_profile_id == club_id,
                Player.normalized_position == normalized_position,
            )
        )
        count = self.session.scalar(statement)
        return int(count or 0)

    def decision_cooldown(self, decision_code: str, *, reference_on: date) -> datetime:
        days = 14 if decision_code in {"accept", "eager_to_join", "transfer_request", "public_unhappy_state", "requests_transfer_if_blocked"} else 7
        return datetime.combine(reference_on + timedelta(days=days), datetime.min.time())

    def review_time(self, decision_code: str, *, reference_on: date) -> datetime:
        days = 10 if decision_code in {"delay_undecided", "hesitant_needs_better_terms", "agent_warning", "private_unrest"} else 21
        return datetime.combine(reference_on + timedelta(days=days), datetime.min.time())

    def _latest_season_stat(self, player: Player) -> PlayerSeasonStat | None:
        if not player.season_stats:
            return None
        return max(player.season_stats, key=lambda item: (item.updated_at, item.created_at, item.id))

    def _league_quality_for_player(self, player: Player, reputation_score: float) -> float:
        if player.current_competition_id is None:
            return clamp(36.0 + (reputation_score * 0.48))
        competition = self.session.get(Competition, player.current_competition_id)
        if competition is None or competition.domestic_level is None:
            return clamp(36.0 + (reputation_score * 0.48))
        return clamp(100.0 - ((max(competition.domestic_level, 1) - 1) * 12.0))

    def _geography_score(self, *, profile: ClubProfile | None, origin: RegenOriginMetadata | None) -> float:
        if profile is None or origin is None:
            return 35.0
        if profile.city_name and origin.city_name and profile.city_name.lower() == origin.city_name.lower():
            return 100.0
        if profile.region_name and origin.region_name and profile.region_name.lower() == origin.region_name.lower():
            return 82.0
        if profile.country_code and origin.country_code and profile.country_code == origin.country_code:
            return 58.0
        return 28.0

    def _role_minutes_adjustment(self, role_label: str | None) -> float:
        normalized = (role_label or "").strip().lower()
        if normalized in {"star", "leading", "franchise"}:
            return 10.0
        if normalized in {"starter", "first_team"}:
            return 6.0
        if normalized in {"breakthrough", "prospect"}:
            return 2.0
        if normalized in {"rotation", "squad"}:
            return -4.0
        return 0.0
