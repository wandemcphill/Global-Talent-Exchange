from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import random

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.ingestion.models import Player
from backend.app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardSale
from backend.app.models.player_contract import PlayerContract
from backend.app.models.regen import (
    RegenDemandSignal,
    RegenLineageProfile,
    RegenMarketActivity,
    RegenOnboardingFlag,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenRelationshipTag,
    RegenRecommendationItem,
    RegenScoutReport,
    RegenTransferFeeRule,
    RegenAward,
    RegenDiscoveryBadge,
    RegenLegacyRecord,
    RegenTwinsGroup,
    RegenValueSnapshot,
)
from backend.app.schemas.regen_core import (
    AbilityRangeView,
    RegenLineageView,
    RegenOriginView,
    RegenPersonalityView,
    RegenProfileView,
    RegenRecommendationItemView,
    RegenScoutReportView,
    RegenSearchResultView,
    RegenTransferSettlementView,
    RegenValueSnapshotView,
)

_STANDARD_RULE_KEY = "default"
_STYLE_DEFAULT = "balanced"
_SCOUTING_STYLES = {"balanced", "youth_developer", "market_analyst", "star_recruiter", "tactical_specialist"}
_AWARD_IMPACT_SCORES = {
    "mvp": 6.0,
    "golden_boy_shortlist": 11.0,
    "gtex_best_player": 16.0,
    "gtex_best_player_shortlist": 13.0,
    "gtex_golden_boy": 12.5,
    "gtex_best_u21_player": 12.0,
    "gtex_continental_player": 14.0,
    "gtex_best_goalkeeper": 11.5,
    "gtex_top_scorer": 13.0,
    "gtex_team_of_the_year": 10.0,
    "tournament_top_scorer": 14.0,
    "title_winner": 9.0,
    "giant_killer": 10.0,
}

_GTEX_AWARD_CATALOG = {
    "gtex_best_player": "GTEX Best Player",
    "gtex_golden_boy": "GTEX Golden Boy",
    "gtex_best_u21_player": "GTEX Best U21 Player",
    "gtex_continental_player": "GTEX Continental Player of the Year",
    "gtex_best_goalkeeper": "GTEX Best Goalkeeper",
    "gtex_top_scorer": "GTEX Top Scorer",
    "gtex_team_of_the_year": "GTEX Team of the Year",
}


class RegenMarketError(ValueError):
    pass


class RegenNotFoundError(RegenMarketError):
    pass


class RegenTradeRestrictedError(RegenMarketError):
    pass


@dataclass(frozen=True, slots=True)
class RegenPerformanceEvent:
    match_rating: float
    goals: int = 0
    assists: int = 0
    clean_sheet: bool = False
    saves: int = 0
    appearances: int = 1
    mvp_award: bool = False
    club_success_score: float = 0.0
    fan_demand_score: float = 0.0
    narrative_significance: float = 0.0
    competition_code: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RegenAwardEvent:
    award_code: str
    award_name: str | None = None
    award_category: str | None = None
    season_label: str | None = None
    rank: int | None = None
    weight: float | None = None
    fan_demand_score: float = 0.0
    narrative_significance: float = 0.0
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RegenDemandEvent:
    signal_type: str
    signal_strength: float
    supporting_count: int = 1
    signal_weight: float = 1.0
    source_scope: str = "market"
    occurred_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegenSearchFilters:
    position_needs: tuple[str, ...] = ()
    age_min: int | None = None
    age_max: int | None = None
    current_ability_min: int | None = None
    current_ability_max: int | None = None
    potential_min: int | None = None
    potential_max: int | None = None
    academy_prospects_only: bool = False
    transfer_listed_only: bool | None = None
    contract_expires_within_days: int | None = None
    special_lineage_only: bool = False
    sons_of_legends_only: bool = False
    sons_of_owners_only: bool = False
    sons_of_retired_regens_only: bool = False
    twins_only: bool = False
    hometown_heroes_only: bool = False
    hometown_affinity: str | None = None
    award_winners_only: bool = False
    min_appearances: int | None = None
    min_goals: int | None = None
    retired_legends_only: bool = False
    celebrity_linked_only: bool = False
    award_codes: tuple[str, ...] = ()
    wonderkid_only: bool = False


@dataclass(frozen=True, slots=True)
class RegenRecommendationRequest:
    club_id: str | None = None
    manager_style: str = _STYLE_DEFAULT
    position_needs: tuple[str, ...] = ()
    system_profile: str | None = None
    budget_coin: int | None = None
    premium_service: bool = False
    limit: int = 5


@dataclass(frozen=True, slots=True)
class MarketBalanceSnapshot:
    regen_market_share: float
    elite_regen_share: float
    regen_sale_count: int
    real_player_sale_count: int
    regen_listing_share: float


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_int(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, round(value)))


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _midpoint(value_range: dict[str, int]) -> int:
    return round((int(value_range.get("minimum", 0)) + int(value_range.get("maximum", 0))) / 2)


def _compute_age(date_of_birth: date | None, *, today: date | None = None) -> int:
    if date_of_birth is None:
        return 18
    current = today or date.today()
    years = current.year - date_of_birth.year
    if (current.month, current.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(0, years)


def _recency_decay(occurred_at: datetime, as_of: datetime, *, half_life_days: int) -> float:
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    elapsed = max((as_of - occurred_at).total_seconds(), 0.0)
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (elapsed / float(half_life_days * 86_400))


def _validate_award_name(name: str) -> None:
    if "regen" in name.lower():
        raise ValueError("award_name_contains_regen")


class RegenMarketService:
    def __init__(self, session: Session, *, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def refresh_value(self, regen_id: str, *, as_of: datetime | None = None) -> RegenValueSnapshotView:
        profile = self._get_profile(regen_id)
        player = self._get_player(profile.player_id)
        origin = self._get_origin(profile.id)
        rule = self.ensure_fee_rule()
        current = as_of or _utcnow()
        activities = self.session.scalars(
            select(RegenMarketActivity)
            .where(RegenMarketActivity.regen_id == profile.id)
            .order_by(RegenMarketActivity.occurred_at.asc(), RegenMarketActivity.created_at.asc())
        ).all()
        demand_signals = self.session.scalars(
            select(RegenDemandSignal)
            .where(RegenDemandSignal.regen_id == profile.id)
            .order_by(RegenDemandSignal.occurred_at.asc())
        ).all()
        age = _compute_age(player.date_of_birth if player is not None else None)
        current_mid = _midpoint(profile.current_ability_range_json)
        potential_mid = _midpoint(profile.potential_range_json)

        performance_score = 0.0
        award_score = 0.0
        reputation_score = 0.0
        narrative_score = 0.0
        appearances_total = 0
        club_success_total = 0.0
        for activity in activities:
            decay = _recency_decay(activity.occurred_at, current, half_life_days=90 if activity.activity_type == "award" else 45)
            stat_line = activity.stat_line_json or {}
            appearances_total += int(stat_line.get("appearances", 0))
            club_success_total += float(activity.metadata_json.get("club_success_score", 0.0)) * decay
            if activity.activity_type == "match_performance":
                performance_score += activity.impact_score * decay
                narrative_score += (len(activity.narrative_tags_json) + float(activity.metadata_json.get("narrative_significance", 0.0))) * decay
            elif activity.activity_type == "award":
                award_score += activity.impact_score * decay
                reputation_score += activity.impact_score * 1.2 * decay
                narrative_score += (1.4 + len(activity.narrative_tags_json) + float(activity.metadata_json.get("narrative_significance", 0.0))) * decay
            else:
                reputation_score += activity.impact_score * 0.6 * decay
                narrative_score += len(activity.narrative_tags_json) * 0.5 * decay

        demand_raw = 0.0
        for signal in demand_signals:
            decay = _recency_decay(signal.occurred_at, current, half_life_days=21)
            demand_raw += signal.signal_strength * signal.signal_weight * max(signal.supporting_count, 1) * decay

        lineage_bonus = 0.0
        if profile.is_special_lineage:
            lineage_bonus += 5.0
        lineage_profile = self._get_lineage(profile.id)
        if lineage_profile is not None:
            if lineage_profile.is_real_legend_lineage:
                lineage_bonus += 6.0
            if lineage_profile.is_owner_son:
                lineage_bonus += 4.0
            if lineage_profile.is_retired_regen_lineage:
                lineage_bonus += 5.0
            if lineage_profile.relationship_type == "hometown_legacy":
                lineage_bonus += 3.0
            if lineage_profile.is_celebrity_lineage and lineage_profile.is_celebrity_licensed:
                lineage_bonus += 4.0
        else:
            if profile.metadata_json.get("son_of_legend"):
                lineage_bonus += 6.0
            if profile.metadata_json.get("club_owner_son"):
                lineage_bonus += 4.0
            if profile.metadata_json.get("hall_of_fame_bound"):
                lineage_bonus += 6.0
        if origin is not None and origin.hometown_club_affinity:
            lineage_bonus += 3.0

        longevity_bonus = max(age - 20, 0) * 0.8
        ability_component = max(350, round((profile.current_gsi * 24) + (current_mid * 42) + (performance_score * 90)))
        potential_component = max(200, round((potential_mid * 26) + (max(potential_mid - current_mid, 0) * 44)))
        reputation_component = max(
            0,
            round((award_score * 170) + (reputation_score * 85) + (club_success_total * 70) + ((appearances_total + longevity_bonus) * 22)),
        )
        narrative_component = max(
            0,
            round(((lineage_bonus + narrative_score) * 85) + (120 if origin is not None and origin.hometown_club_affinity else 0)),
        )
        guardrail_multiplier, market_snapshot = self._guardrail_multiplier(rule)
        demand_component = max(0, round(demand_raw * 125 * guardrail_multiplier))
        current_value_coin = max(500, ability_component + potential_component + reputation_component + narrative_component + demand_component)

        snapshot = RegenValueSnapshot(
            regen_id=profile.id,
            current_value_coin=current_value_coin,
            ability_component=ability_component,
            potential_component=potential_component,
            reputation_component=reputation_component,
            narrative_component=narrative_component,
            demand_component=demand_component,
            guardrail_multiplier=guardrail_multiplier,
            metadata_json={
                "appearances_total": appearances_total,
                "club_success_total": round(club_success_total, 3),
                "market_balance": {
                    "regen_market_share": round(market_snapshot.regen_market_share, 4),
                    "elite_regen_share": round(market_snapshot.elite_regen_share, 4),
                    "regen_listing_share": round(market_snapshot.regen_listing_share, 4),
                },
            },
            calculated_at=current,
        )
        self.session.add(snapshot)
        self.session.flush()
        return self._to_value_snapshot_view(snapshot, profile)

    def record_match_performance(
        self,
        regen_id: str,
        event: RegenPerformanceEvent,
        *,
        club_id: str | None = None,
    ) -> RegenValueSnapshotView:
        profile = self._get_profile(regen_id)
        occurred_at = event.occurred_at or _utcnow()
        impact_score = (
            max(event.match_rating - 6.0, 0.0) * 1.8
            + (event.goals * 2.6)
            + (event.assists * 1.9)
            + (1.4 if event.clean_sheet else 0.0)
            + (event.saves * 0.08)
            + (event.club_success_score * 1.3)
            + event.narrative_significance
            + (4.5 if event.mvp_award else 0.0)
        )
        activity = RegenMarketActivity(
            regen_id=profile.id,
            club_id=club_id,
            activity_type="match_performance",
            source_scope="competition",
            impact_score=round(impact_score, 4),
            value_delta_coin=max(0, round(impact_score * 30)),
            stat_line_json={
                "match_rating": event.match_rating,
                "goals": event.goals,
                "assists": event.assists,
                "clean_sheet": event.clean_sheet,
                "saves": event.saves,
                "appearances": event.appearances,
            },
            narrative_tags_json=self._performance_tags(event),
            occurred_at=occurred_at,
            metadata_json={
                "competition_code": event.competition_code,
                "club_success_score": event.club_success_score,
                "narrative_significance": event.narrative_significance,
            },
        )
        self.session.add(activity)
        if event.match_rating >= 8.3:
            self._persist_demand_signal(
                profile,
                RegenDemandEvent(
                    signal_type="standout_match_rating",
                    signal_strength=1.0 + max(event.match_rating - 8.3, 0.0),
                    supporting_count=max(event.appearances, 1),
                    signal_weight=1.15,
                    source_scope="competition",
                    occurred_at=occurred_at,
                    metadata={"competition_code": event.competition_code or "unknown"},
                ),
            )
        if event.mvp_award:
            self._persist_demand_signal(
                profile,
                RegenDemandEvent(
                    signal_type="mvp",
                    signal_strength=2.5,
                    supporting_count=1,
                    signal_weight=1.35,
                    source_scope="competition",
                    occurred_at=occurred_at,
                ),
            )
        if event.fan_demand_score > 0:
            self._persist_demand_signal(
                profile,
                RegenDemandEvent(
                    signal_type="fan_demand",
                    signal_strength=event.fan_demand_score,
                    supporting_count=max(event.appearances, 1),
                    signal_weight=1.1,
                    source_scope="fans",
                    occurred_at=occurred_at,
                ),
            )
        self.session.flush()
        return self.refresh_value(profile.id, as_of=occurred_at)

    def record_award(self, regen_id: str, event: RegenAwardEvent, *, club_id: str | None = None) -> RegenValueSnapshotView:
        profile = self._get_profile(regen_id)
        occurred_at = event.occurred_at or _utcnow()
        impact_score = event.weight if event.weight is not None else _AWARD_IMPACT_SCORES.get(event.award_code, 8.0)
        award_name = event.award_name or _GTEX_AWARD_CATALOG.get(event.award_code) or event.award_code.replace("_", " ").title()
        _validate_award_name(award_name)
        award_category = event.award_category or ("gtex" if event.award_code.startswith("gtex_") else None)
        tags = [event.award_code]
        if "shortlist" in event.award_code:
            tags.append("award_shortlist")
        activity = RegenMarketActivity(
            regen_id=profile.id,
            club_id=club_id,
            activity_type="award",
            source_scope="awards",
            impact_score=round(impact_score, 4),
            value_delta_coin=max(0, round(impact_score * 55)),
            stat_line_json={"appearances": 0},
            narrative_tags_json=tags,
            occurred_at=occurred_at,
            metadata_json={
                "award_code": event.award_code,
                "award_name": award_name,
                "club_success_score": 0.0,
                "narrative_significance": event.narrative_significance,
            },
        )
        self.session.add(activity)
        award = RegenAward(
            regen_id=profile.id,
            club_id=club_id,
            award_code=event.award_code,
            award_name=award_name,
            award_category=award_category,
            season_label=event.season_label,
            awarded_at=occurred_at,
            rank=event.rank,
            source_scope="gtex" if event.award_code.startswith("gtex_") else "awards",
            impact_score=round(impact_score, 4),
            metadata_json={
                "award_code": event.award_code,
                "award_name": award_name,
                "award_category": award_category,
            },
        )
        self.session.add(award)
        self._persist_demand_signal(
            profile,
            RegenDemandEvent(
                signal_type=event.award_code,
                signal_strength=max(1.0, impact_score / 3.0) + event.fan_demand_score,
                supporting_count=1,
                signal_weight=1.3,
                source_scope="awards",
                occurred_at=occurred_at,
                metadata={"award_code": event.award_code},
            ),
        )
        self.session.flush()
        return self.refresh_value(profile.id, as_of=occurred_at)

    def record_demand_signal(self, regen_id: str, event: RegenDemandEvent) -> RegenValueSnapshotView:
        profile = self._get_profile(regen_id)
        self._persist_demand_signal(profile, event)
        self.session.flush()
        return self.refresh_value(profile.id, as_of=event.occurred_at or _utcnow())

    def create_scout_report(
        self,
        regen_id: str,
        *,
        club_id: str | None = None,
        scout_identity: str | None = None,
        scout_rating: int = 50,
        manager_style: str = _STYLE_DEFAULT,
        system_profile: str | None = None,
        premium_service: bool = False,
    ) -> RegenScoutReportView:
        profile = self._get_profile(regen_id)
        player = self._get_player(profile.player_id)
        personality = self._get_personality(profile.id)
        latest_value = self._latest_snapshot_or_refresh(profile)
        age = _compute_age(player.date_of_birth if player is not None else None)
        actual_current = _midpoint(profile.current_ability_range_json)
        actual_potential = _midpoint(profile.potential_range_json)
        style = self._normalize_style(manager_style)
        lifecycle_phase = self._career_lifecycle_phase(age)
        role_fit = self._role_fit_score(profile, personality, (), system_profile)
        style_bonus = self._style_confidence_bonus(style, age, actual_current, actual_potential, latest_value)
        style_bonus += self._lifecycle_confidence_bonus(style, lifecycle_phase)
        confidence_bps = _clamp_int((scout_rating * 110) + style_bonus + (600 if premium_service else 0) + 2_500, 3_000, 9_600)
        error_span = max(2, round((10_000 - confidence_bps) / 550))
        rng = self._scout_rng(profile.regen_id, scout_identity or "system", style, scout_rating, premium_service)
        current_estimate = _clamp_int(actual_current + rng.randint(-error_span, error_span), 1, 99)
        potential_estimate = _clamp_int(actual_potential + rng.randint(-error_span * 2, error_span * 2), current_estimate, 99)
        wonderkid = self._is_wonderkid(profile, age)
        hidden_gem_score = round(
            max(actual_potential - actual_current, 0)
            * (10_000 - confidence_bps)
            / 120.0
            * self._lifecycle_hidden_gem_multiplier(lifecycle_phase),
            2,
        )
        tags = [style, lifecycle_phase]
        if wonderkid:
            tags.append("wonderkid")
        if hidden_gem_score >= 10:
            tags.append("hidden_gem")
        if premium_service:
            tags.append("premium_intel")
        report = RegenScoutReport(
            regen_id=profile.id,
            club_id=club_id,
            scout_identity=scout_identity,
            manager_style=style,
            system_profile=system_profile,
            current_ability_estimate=current_estimate,
            future_potential_estimate=potential_estimate,
            scout_confidence_bps=confidence_bps,
            role_fit_score=round(role_fit, 4),
            hidden_gem_score=hidden_gem_score,
            wonderkid_signal=wonderkid,
            value_hint_coin=latest_value.current_value_coin,
            summary_text=self._scout_summary(
                style,
                lifecycle_phase,
                current_estimate,
                potential_estimate,
                confidence_bps,
                wonderkid,
                hidden_gem_score,
            ),
            tags_json=tags,
            metadata_json={
                "premium_service": premium_service,
                "actual_current": actual_current,
                "actual_potential": actual_potential,
                "lifecycle_phase": lifecycle_phase,
            },
        )
        self.session.add(report)
        if wonderkid or premium_service:
            self._persist_demand_signal(
                profile,
                RegenDemandEvent(
                    signal_type="scouting_buzz",
                    signal_strength=max(1.0, hidden_gem_score / 10.0),
                    supporting_count=1,
                    signal_weight=1.1 if premium_service else 0.8,
                    source_scope="scouting",
                    occurred_at=_utcnow(),
                    metadata={"manager_style": style},
                ),
            )
        self.session.flush()
        return self._to_scout_report_view(report, profile)

    def search_regens(self, filters: RegenSearchFilters) -> tuple[RegenSearchResultView, ...]:
        profiles = self.session.scalars(select(RegenProfile).order_by(RegenProfile.generated_at.desc())).all()
        results: list[RegenSearchResultView] = []
        requested_awards = {code.strip().lower() for code in filters.award_codes if code.strip()}
        for profile in profiles:
            player = self._get_player(profile.player_id)
            age = _compute_age(player.date_of_birth if player is not None else None)
            current_mid = _midpoint(profile.current_ability_range_json)
            potential_mid = _midpoint(profile.potential_range_json)
            if filters.academy_prospects_only and (profile.generation_source != "academy" or age > 20):
                continue
            if filters.position_needs and not self._matches_position_need(profile, filters.position_needs):
                continue
            if filters.age_min is not None and age < filters.age_min:
                continue
            if filters.age_max is not None and age > filters.age_max:
                continue
            if filters.current_ability_min is not None and current_mid < filters.current_ability_min:
                continue
            if filters.current_ability_max is not None and current_mid > filters.current_ability_max:
                continue
            if filters.potential_min is not None and potential_mid < filters.potential_min:
                continue
            if filters.potential_max is not None and potential_mid > filters.potential_max:
                continue
            transfer_listed = self._is_transfer_listed(profile.linked_unique_card_id)
            if filters.transfer_listed_only is True and not transfer_listed:
                continue
            if filters.transfer_listed_only is False and transfer_listed:
                continue
            contract = self._active_contract(profile.player_id)
            if filters.contract_expires_within_days is not None:
                if contract is None or contract.ends_on is None:
                    continue
                if contract.ends_on > (date.today() + timedelta(days=filters.contract_expires_within_days)):
                    continue
            if filters.special_lineage_only and not profile.is_special_lineage:
                continue
            lineage = None
            lineage_filters_active = (
                filters.sons_of_legends_only
                or filters.sons_of_owners_only
                or filters.sons_of_retired_regens_only
                or filters.hometown_heroes_only
                or filters.celebrity_linked_only
            )
            if lineage_filters_active:
                lineage = self._get_lineage(profile.id)
            if filters.sons_of_legends_only and (lineage is None or not lineage.is_real_legend_lineage):
                continue
            if filters.sons_of_owners_only and (lineage is None or not lineage.is_owner_son):
                continue
            if filters.sons_of_retired_regens_only and (lineage is None or not lineage.is_retired_regen_lineage):
                continue
            if filters.celebrity_linked_only and (
                lineage is None or not (lineage.is_celebrity_lineage and lineage.is_celebrity_licensed)
            ):
                continue
            origin = self._get_origin(profile.id)
            if filters.hometown_affinity and (origin is None or origin.hometown_club_affinity != filters.hometown_affinity):
                continue
            if filters.hometown_heroes_only:
                hometown_match = lineage is not None and lineage.relationship_type == "hometown_legacy"
                hometown_match = hometown_match or (origin is not None and origin.hometown_club_affinity is not None)
                if not hometown_match:
                    continue
            if requested_awards and not self._profile_has_any_award(profile.id, requested_awards):
                continue
            if filters.award_winners_only and not self._profile_has_any_award(profile.id, None):
                continue
            if filters.twins_only and not self._is_twin(profile.id):
                continue
            legacy = None
            if filters.min_appearances is not None or filters.min_goals is not None or filters.retired_legends_only:
                legacy = self._get_legacy_record(profile.id)
            if filters.min_appearances is not None and (legacy is None or legacy.appearances_total < filters.min_appearances):
                continue
            if filters.min_goals is not None and (legacy is None or legacy.goals_total < filters.min_goals):
                continue
            if filters.retired_legends_only and (
                legacy is None or not legacy.is_legend or profile.status != "retired"
            ):
                continue
            wonderkid = self._is_wonderkid(profile, age)
            if filters.wonderkid_only and not wonderkid:
                continue
            latest_value = self._latest_snapshot_or_refresh(profile)
            results.append(
                RegenSearchResultView(
                    profile=self._to_profile_view(profile, player=player, origin=origin),
                    latest_value=self._to_value_snapshot_view(latest_value, profile),
                    transfer_listed=transfer_listed,
                    contract_expires_on=contract.ends_on if contract is not None else None,
                    wonderkid=wonderkid,
                )
            )
        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.latest_value.current_value_coin if item.latest_value is not None else 0,
                    item.profile.potential_range.maximum,
                ),
                reverse=True,
            )
        )

    def recommend_regens(self, request: RegenRecommendationRequest) -> tuple[RegenRecommendationItemView, ...]:
        candidates = self.search_regens(
            RegenSearchFilters(
                position_needs=request.position_needs,
                wonderkid_only=request.manager_style == "youth_developer" and request.premium_service,
            )
        )
        style = self._normalize_style(request.manager_style)
        ranked: list[tuple[float, RegenSearchResultView]] = []
        for candidate in candidates:
            latest_value = candidate.latest_value
            if latest_value is None:
                continue
            if request.budget_coin is not None and latest_value.current_value_coin > request.budget_coin:
                continue
            personality = self._get_personality(candidate.profile.id)
            priority_score = self._recommendation_priority(style, candidate, personality, request)
            ranked.append((priority_score, candidate))
        top_results = sorted(ranked, key=lambda item: item[0], reverse=True)[: max(request.limit, 1)]
        premium_tier = "premium" if request.premium_service else "standard"
        views: list[RegenRecommendationItemView] = []
        for priority_score, candidate in top_results:
            phase = self._career_lifecycle_phase(candidate.profile.age)
            summary = self._recommendation_summary(style, candidate, phase)
            tags = [style, phase]
            if candidate.wonderkid:
                tags.append("wonderkid")
            if request.position_needs:
                tags.extend(sorted({need.lower() for need in request.position_needs}))
            if request.premium_service and candidate.latest_value is not None and candidate.profile.potential_range.maximum - candidate.profile.current_ability_range.maximum >= 10:
                tags.append("hidden_gem_shortlist")
            profile = self._get_profile(candidate.profile.id)
            item = RegenRecommendationItem(
                regen_id=profile.id,
                club_id=request.club_id,
                manager_style=style,
                premium_tier=premium_tier,
                position_need=request.position_needs[0] if request.position_needs else None,
                system_profile=request.system_profile,
                budget_coin=request.budget_coin,
                priority_score=round(priority_score, 4),
                role_fit_score=round(self._role_fit_score(profile, self._get_personality(candidate.profile.id), request.position_needs, request.system_profile), 4),
                market_value_score=round(self._market_value_score(candidate), 4),
                summary_text=summary,
                tags_json=tags,
                metadata_json={
                    "regen_public_id": candidate.profile.regen_id,
                    "wonderkid": candidate.wonderkid,
                },
            )
            self.session.add(item)
            self.session.flush()
            views.append(self._to_recommendation_view(item, profile))
        return tuple(views)

    def quote_transfer_settlement(self, regen_id: str, gross_amount_coin: int) -> RegenTransferSettlementView:
        profile = self._get_profile(regen_id)
        onboarding = self._get_onboarding_flag(profile.id)
        if onboarding is not None and onboarding.is_non_tradable:
            raise RegenTradeRestrictedError("starter_regen_non_tradable")
        rule = self.ensure_fee_rule()
        market_snapshot = self.market_balance_snapshot()
        excess_share = max(0.0, market_snapshot.regen_market_share - rule.regen_share_soft_cap)
        applied_fee_bps = _clamp_int(rule.fee_bps + (excess_share * 2_000), rule.min_fee_bps, rule.max_fee_bps)
        fee_amount_coin = round(gross_amount_coin * applied_fee_bps / 10_000)
        seller_net_coin = max(gross_amount_coin - fee_amount_coin, 0)
        return RegenTransferSettlementView(
            regen_id=profile.regen_id,
            gross_amount_coin=gross_amount_coin,
            fee_amount_coin=fee_amount_coin,
            seller_net_coin=seller_net_coin,
            applied_fee_bps=applied_fee_bps,
            regen_market_share=round(market_snapshot.regen_market_share, 4),
            guardrail_triggered=applied_fee_bps > rule.fee_bps,
        )

    def ensure_fee_rule(self, *, rule_key: str = _STANDARD_RULE_KEY) -> RegenTransferFeeRule:
        rule = self.session.scalar(
            select(RegenTransferFeeRule)
            .where(
                RegenTransferFeeRule.rule_key == rule_key,
                RegenTransferFeeRule.is_active.is_(True),
            )
            .order_by(RegenTransferFeeRule.updated_at.desc())
        )
        if rule is not None:
            return rule
        settings = self.settings.regen_generation
        rule = RegenTransferFeeRule(
            rule_key=rule_key,
            fee_bps=settings.market_fee_bps_default,
            min_fee_bps=settings.market_fee_bps_min,
            max_fee_bps=settings.market_fee_bps_max,
            regen_share_soft_cap=settings.ecosystem_target_regen_share,
            elite_regen_share_cap=settings.elite_regen_share_cap,
            demand_cooling_floor=settings.demand_cooling_floor,
            is_active=True,
            policy_source="settings_seed",
            metadata_json={"seeded_from": "regen_generation"},
        )
        self.session.add(rule)
        self.session.flush()
        return rule

    def market_balance_snapshot(self, *, window_days: int = 30) -> MarketBalanceSnapshot:
        cutoff = _utcnow() - timedelta(days=window_days)
        total_sales = self.session.scalar(
            select(func.count(PlayerCardSale.id)).where(
                PlayerCardSale.status == "settled",
                PlayerCardSale.created_at >= cutoff,
            )
        ) or 0
        regen_sales = self.session.scalar(
            select(func.count(PlayerCardSale.id))
            .join(PlayerCard, PlayerCard.id == PlayerCardSale.player_card_id)
            .join(RegenProfile, RegenProfile.linked_unique_card_id == PlayerCard.id)
            .where(
                PlayerCardSale.status == "settled",
                PlayerCardSale.created_at >= cutoff,
            )
        ) or 0
        total_open_listings = self.session.scalar(
            select(func.count(PlayerCardListing.id)).where(PlayerCardListing.status == "open")
        ) or 0
        regen_open_listings = self.session.scalar(
            select(func.count(PlayerCardListing.id))
            .join(PlayerCard, PlayerCard.id == PlayerCardListing.player_card_id)
            .join(RegenProfile, RegenProfile.linked_unique_card_id == PlayerCard.id)
            .where(PlayerCardListing.status == "open")
        ) or 0
        profiles = self.session.scalars(select(RegenProfile)).all()
        elite_regens = sum(1 for profile in profiles if int(profile.potential_range_json.get("maximum", 0)) >= 88)
        regen_share = regen_sales / total_sales if total_sales else 0.0
        listing_share = regen_open_listings / total_open_listings if total_open_listings else 0.0
        return MarketBalanceSnapshot(
            regen_market_share=max(regen_share, listing_share),
            elite_regen_share=(elite_regens / len(profiles)) if profiles else 0.0,
            regen_sale_count=int(regen_sales),
            real_player_sale_count=int(max(total_sales - regen_sales, 0)),
            regen_listing_share=listing_share,
        )

    def _guardrail_multiplier(self, rule: RegenTransferFeeRule) -> tuple[float, MarketBalanceSnapshot]:
        market_snapshot = self.market_balance_snapshot()
        share_pressure = max(market_snapshot.regen_market_share - rule.regen_share_soft_cap, 0.0)
        elite_pressure = max(market_snapshot.elite_regen_share - rule.elite_regen_share_cap, 0.0)
        multiplier = 1.0 - min(share_pressure * 1.5, 0.30) - min(elite_pressure * 1.8, 0.20)
        return max(rule.demand_cooling_floor, round(multiplier, 4)), market_snapshot

    def _get_profile(self, regen_id: str) -> RegenProfile:
        profile = self.session.scalar(
            select(RegenProfile).where(
                or_(
                    RegenProfile.id == regen_id,
                    RegenProfile.regen_id == regen_id,
                )
            )
        )
        if profile is None:
            raise RegenNotFoundError("regen_not_found")
        return profile

    def _get_player(self, player_id: str | None) -> Player | None:
        if player_id is None:
            return None
        return self.session.get(Player, player_id)

    def _get_personality(self, profile_id: str) -> RegenPersonalityProfile | None:
        return self.session.scalar(select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == profile_id))

    def _get_origin(self, profile_id: str) -> RegenOriginMetadata | None:
        return self.session.scalar(select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == profile_id))

    def _active_contract(self, player_id: str | None) -> PlayerContract | None:
        if player_id is None:
            return None
        return self.session.scalar(
            select(PlayerContract)
            .where(
                PlayerContract.player_id == player_id,
                PlayerContract.status == "active",
            )
            .order_by(PlayerContract.ends_on.asc())
        )

    def _latest_snapshot_or_refresh(self, profile: RegenProfile) -> RegenValueSnapshot:
        snapshot = self.session.scalar(
            select(RegenValueSnapshot)
            .where(RegenValueSnapshot.regen_id == profile.id)
            .order_by(RegenValueSnapshot.calculated_at.desc(), RegenValueSnapshot.id.desc())
        )
        if snapshot is not None:
            return snapshot
        self.refresh_value(profile.id)
        snapshot = self.session.scalar(
            select(RegenValueSnapshot)
            .where(RegenValueSnapshot.regen_id == profile.id)
            .order_by(RegenValueSnapshot.calculated_at.desc(), RegenValueSnapshot.id.desc())
        )
        assert snapshot is not None
        return snapshot

    def _get_onboarding_flag(self, profile_id: str) -> RegenOnboardingFlag | None:
        return self.session.scalar(select(RegenOnboardingFlag).where(RegenOnboardingFlag.regen_id == profile_id))

    def _persist_demand_signal(self, profile: RegenProfile, event: RegenDemandEvent) -> None:
        signal = RegenDemandSignal(
            regen_id=profile.id,
            signal_type=event.signal_type,
            source_scope=event.source_scope,
            signal_strength=event.signal_strength,
            supporting_count=max(event.supporting_count, 1),
            signal_weight=event.signal_weight,
            occurred_at=event.occurred_at or _utcnow(),
            metadata_json=event.metadata,
        )
        self.session.add(signal)

    def _is_transfer_listed(self, player_card_id: str) -> bool:
        return bool(
            self.session.scalar(
                select(func.count(PlayerCardListing.id)).where(
                    PlayerCardListing.player_card_id == player_card_id,
                    PlayerCardListing.status == "open",
                )
            )
        )

    def _get_lineage(self, profile_id: str) -> RegenLineageProfile | None:
        return self.session.scalar(select(RegenLineageProfile).where(RegenLineageProfile.regen_id == profile_id))

    def _get_relationship_tags(self, profile_id: str) -> tuple[str, ...]:
        tags = self.session.scalars(
            select(RegenRelationshipTag.tag).where(RegenRelationshipTag.regen_id == profile_id)
        ).all()
        return tuple(dict.fromkeys(tags))

    def _is_twin(self, profile_id: str) -> bool:
        return bool(
            self.session.scalar(
                select(func.count(RegenTwinsGroup.id)).where(RegenTwinsGroup.regen_id == profile_id)
            )
        )

    def _get_legacy_record(self, profile_id: str) -> RegenLegacyRecord | None:
        return self.session.scalar(select(RegenLegacyRecord).where(RegenLegacyRecord.regen_id == profile_id))

    def _profile_has_any_award(self, profile_id: str, award_codes: set[str] | None) -> bool:
        if award_codes is None:
            return bool(
                self.session.scalar(
                    select(func.count(RegenAward.id)).where(RegenAward.regen_id == profile_id)
                )
            )
        if award_codes:
            direct_award = self.session.scalar(
                select(RegenAward.id).where(
                    RegenAward.regen_id == profile_id,
                    RegenAward.award_code.in_(award_codes),
                )
            )
            if direct_award is not None:
                return True
        activities = self.session.scalars(
            select(RegenMarketActivity).where(
                RegenMarketActivity.regen_id == profile_id,
                RegenMarketActivity.activity_type == "award",
            )
        ).all()
        for activity in activities:
            award_code = str(activity.metadata_json.get("award_code", "")).lower()
            if award_codes is None or award_code in award_codes:
                return True
        return False

    def _matches_position_need(self, profile: RegenProfile, position_needs: tuple[str, ...]) -> bool:
        wanted = {item.upper() for item in position_needs}
        if not wanted:
            return True
        return profile.primary_position.upper() in wanted or any(position.upper() in wanted for position in profile.secondary_positions_json)

    def _is_wonderkid(self, profile: RegenProfile, age: int) -> bool:
        return age <= 20 and int(profile.potential_range_json.get("maximum", 0)) >= 84

    def _normalize_style(self, manager_style: str) -> str:
        normalized = manager_style.strip().lower().replace(" ", "_")
        if normalized not in _SCOUTING_STYLES:
            return _STYLE_DEFAULT
        return normalized

    def _career_lifecycle_phase(self, age: int) -> str:
        if age <= self.settings.regen_generation.player_lifecycle_growth_max_age:
            return "breakout_growth"
        if age <= self.settings.regen_generation.player_lifecycle_peak_max_age:
            return "peak"
        if age <= self.settings.regen_generation.player_lifecycle_decline_max_age:
            return "decline"
        return "late_career"

    def _lifecycle_confidence_bonus(self, style: str, lifecycle_phase: str) -> int:
        if lifecycle_phase == "breakout_growth":
            return 220 if style == "youth_developer" else 90
        if lifecycle_phase == "peak":
            return 180 if style in {"star_recruiter", "tactical_specialist"} else 80
        if lifecycle_phase == "decline":
            return 140 if style == "market_analyst" else -60
        return -220

    def _lifecycle_hidden_gem_multiplier(self, lifecycle_phase: str) -> float:
        if lifecycle_phase == "breakout_growth":
            return 1.15
        if lifecycle_phase == "peak":
            return 1.0
        if lifecycle_phase == "decline":
            return 0.85
        return 0.7

    def _lifecycle_market_multiplier(self, lifecycle_phase: str) -> float:
        if lifecycle_phase == "breakout_growth":
            return 1.18
        if lifecycle_phase == "peak":
            return 1.0
        if lifecycle_phase == "decline":
            return 0.82
        return 0.66

    def _lifecycle_priority_bonus(self, style: str, lifecycle_phase: str) -> float:
        if style == "youth_developer":
            return {"breakout_growth": 70.0, "peak": 8.0, "decline": -22.0, "late_career": -40.0}.get(lifecycle_phase, 0.0)
        if style == "market_analyst":
            return {"breakout_growth": 22.0, "peak": 14.0, "decline": 18.0, "late_career": -12.0}.get(lifecycle_phase, 0.0)
        if style == "star_recruiter":
            return {"breakout_growth": 14.0, "peak": 42.0, "decline": -10.0, "late_career": -20.0}.get(lifecycle_phase, 0.0)
        if style == "tactical_specialist":
            return {"breakout_growth": 8.0, "peak": 28.0, "decline": 12.0, "late_career": -18.0}.get(lifecycle_phase, 0.0)
        return {"breakout_growth": 18.0, "peak": 20.0, "decline": -4.0, "late_career": -16.0}.get(lifecycle_phase, 0.0)

    def _style_confidence_bonus(
        self,
        style: str,
        age: int,
        actual_current: int,
        actual_potential: int,
        latest_value: RegenValueSnapshot,
    ) -> int:
        if style == "youth_developer":
            return 900 if age <= 20 or actual_potential >= 84 else 300
        if style == "market_analyst":
            return 700 if latest_value.current_value_coin < ((actual_potential - actual_current) * 180) + 2_500 else 250
        if style == "star_recruiter":
            return 650 if latest_value.reputation_component + latest_value.narrative_component >= 1_200 else 200
        if style == "tactical_specialist":
            return 600
        return 350

    def _performance_tags(self, event: RegenPerformanceEvent) -> list[str]:
        tags: list[str] = []
        if event.match_rating >= 8.5:
            tags.append("standout_match")
        if event.mvp_award:
            tags.append("mvp")
        if event.club_success_score >= 2:
            tags.append("title_swing")
        if event.narrative_significance >= 2:
            tags.append("giant_killer")
        return tags

    def _role_fit_score(
        self,
        profile: RegenProfile,
        personality: RegenPersonalityProfile | None,
        position_needs: tuple[str, ...],
        system_profile: str | None,
    ) -> float:
        fit = 0.35
        if self._matches_position_need(profile, position_needs):
            fit += 0.30
        if personality is None:
            return round(_clamp_float(fit, 0.0, 1.0), 4)
        system = (system_profile or "").strip().lower()
        if "press" in system:
            fit += ((personality.work_rate + personality.resilience + personality.ambition) / 300.0) * 0.30
            if profile.primary_position in {"ST", "RW", "LW", "CM"}:
                fit += 0.08
        elif "possession" in system:
            fit += ((personality.flair + personality.temperament + personality.leadership) / 300.0) * 0.28
            if profile.primary_position in {"DM", "CM", "AM", "RB", "LB"}:
                fit += 0.08
        elif "counter" in system:
            fit += ((personality.flair + personality.ambition + personality.work_rate) / 300.0) * 0.26
            if profile.primary_position in {"RW", "LW", "AM", "ST"}:
                fit += 0.08
        elif "block" in system or "defensive" in system:
            fit += ((personality.resilience + personality.loyalty + personality.temperament) / 300.0) * 0.30
            if profile.primary_position in {"GK", "CB", "RB", "LB", "DM"}:
                fit += 0.08
        else:
            fit += ((personality.work_rate + personality.flair) / 200.0) * 0.18
        return round(_clamp_float(fit, 0.0, 1.0), 4)

    def _market_value_score(self, candidate: RegenSearchResultView) -> float:
        latest_value = candidate.latest_value
        if latest_value is None:
            return 0.0
        current = _midpoint(
            {
                "minimum": candidate.profile.current_ability_range.minimum,
                "maximum": candidate.profile.current_ability_range.maximum,
            }
        )
        potential = _midpoint(
            {
                "minimum": candidate.profile.potential_range.minimum,
                "maximum": candidate.profile.potential_range.maximum,
            }
        )
        return round(
            (((potential - current) * 40 + potential * 5) / max(latest_value.current_value_coin, 1))
            * self._lifecycle_market_multiplier(self._career_lifecycle_phase(candidate.profile.age)),
            6,
        )

    def _recommendation_priority(
        self,
        style: str,
        candidate: RegenSearchResultView,
        personality: RegenPersonalityProfile | None,
        request: RegenRecommendationRequest,
    ) -> float:
        latest_value = candidate.latest_value
        assert latest_value is not None
        current = _midpoint(
            {
                "minimum": candidate.profile.current_ability_range.minimum,
                "maximum": candidate.profile.current_ability_range.maximum,
            }
        )
        potential = _midpoint(
            {
                "minimum": candidate.profile.potential_range.minimum,
                "maximum": candidate.profile.potential_range.maximum,
            }
        )
        age = candidate.profile.age
        gap = max(potential - current, 0)
        role_fit = self._role_fit_score(self._get_profile(candidate.profile.id), personality, request.position_needs, request.system_profile)
        lifecycle_phase = self._career_lifecycle_phase(age)
        lifecycle_bonus = self._lifecycle_priority_bonus(style, lifecycle_phase)
        if style == "youth_developer":
            return (gap * 18) + (max(0, 22 - age) * 14) + (role_fit * 180) + (50 if candidate.wonderkid else 0) + lifecycle_bonus - (latest_value.current_value_coin / 90)
        if style == "market_analyst":
            return (self._market_value_score(candidate) * 10_000) + (gap * 10) + (role_fit * 120) + lifecycle_bonus
        if style == "star_recruiter":
            return (current * 16) + (latest_value.reputation_component / 14) + (latest_value.narrative_component / 12) + (role_fit * 90) + lifecycle_bonus
        if style == "tactical_specialist":
            return (role_fit * 260) + (current * 12) + ((personality.work_rate + personality.flair) if personality is not None else 80) + lifecycle_bonus
        return (current * 12) + (gap * 9) + (role_fit * 110) + lifecycle_bonus

    def _recommendation_summary(self, style: str, candidate: RegenSearchResultView, lifecycle_phase: str) -> str:
        value = candidate.latest_value.current_value_coin if candidate.latest_value is not None else 0
        if style == "youth_developer":
            return f"{lifecycle_phase.replace('_', ' ').title()} upside play with strong development headroom and value around {value} coin."
        if style == "market_analyst":
            return f"{lifecycle_phase.replace('_', ' ').title()} profile that looks undervalued relative to upside and market value around {value} coin."
        if style == "star_recruiter":
            return f"{lifecycle_phase.replace('_', ' ').title()} target with marquee upside and market value around {value} coin."
        if style == "tactical_specialist":
            return f"{lifecycle_phase.replace('_', ' ').title()} system-fit option with role alignment and market value around {value} coin."
        return f"{lifecycle_phase.replace('_', ' ').title()} target with playable floor and market value around {value} coin."

    def _scout_summary(
        self,
        style: str,
        lifecycle_phase: str,
        current_estimate: int,
        potential_estimate: int,
        confidence_bps: int,
        wonderkid: bool,
        hidden_gem_score: float,
    ) -> str:
        label = style.replace("_", " ")
        wonderkid_note = " Wonderkid indicators present." if wonderkid else ""
        gem_note = " Hidden-gem profile." if hidden_gem_score >= 10 else ""
        return (
            f"{label.title()} read on a {lifecycle_phase.replace('_', ' ')} profile: current ability about {current_estimate}, future ceiling about {potential_estimate}, "
            f"confidence {confidence_bps / 100:.1f}%."
            f"{wonderkid_note}{gem_note}"
        )

    def _scout_rng(
        self,
        regen_public_id: str,
        scout_identity: str,
        style: str,
        scout_rating: int,
        premium_service: bool,
    ) -> random.Random:
        seed_material = "|".join(
            (
                regen_public_id,
                scout_identity,
                style,
                str(scout_rating),
                "premium" if premium_service else "standard",
            )
        )
        seed = int.from_bytes(sha256(seed_material.encode("utf-8")).digest()[:8], "big")
        return random.Random(seed)

    def _to_profile_view(
        self,
        profile: RegenProfile,
        *,
        player: Player | None = None,
        origin: RegenOriginMetadata | None = None,
    ) -> RegenProfileView:
        resolved_player = player or self._get_player(profile.player_id)
        resolved_origin = origin or self._get_origin(profile.id)
        personality = self._get_personality(profile.id)
        age = _compute_age(resolved_player.date_of_birth if resolved_player is not None else None)
        lineage_profile = self._get_lineage(profile.id)
        lineage_tags = self._get_relationship_tags(profile.id)
        lineage_view = None
        if lineage_profile is not None:
            lineage_view = RegenLineageView(
                relationship_type=lineage_profile.relationship_type,
                related_legend_type=lineage_profile.related_legend_type,
                related_legend_ref_id=lineage_profile.related_legend_ref_id,
                lineage_country_code=lineage_profile.lineage_country_code,
                lineage_hometown_code=lineage_profile.lineage_hometown_code,
                is_owner_son=lineage_profile.is_owner_son,
                is_retired_regen_lineage=lineage_profile.is_retired_regen_lineage,
                is_real_legend_lineage=lineage_profile.is_real_legend_lineage,
                is_celebrity_lineage=lineage_profile.is_celebrity_lineage,
                is_celebrity_licensed=lineage_profile.is_celebrity_licensed,
                lineage_tier=lineage_profile.lineage_tier,
                narrative_text=lineage_profile.narrative_text,
                tags=tuple(lineage_tags),
                metadata=dict(lineage_profile.metadata_json or {}),
            )
        return RegenProfileView(
            id=profile.id,
            regen_id=profile.regen_id,
            club_id=profile.generated_for_club_id,
            player_id=profile.player_id,
            linked_unique_card_id=profile.linked_unique_card_id,
            display_name=resolved_player.full_name if resolved_player is not None else profile.regen_id,
            age=age,
            birth_country_code=profile.birth_country_code,
            birth_region=profile.birth_region,
            birth_city=profile.birth_city,
            primary_position=profile.primary_position,
            secondary_positions=tuple(profile.secondary_positions_json),
            current_gsi=profile.current_gsi,
            current_ability_range=AbilityRangeView(**profile.current_ability_range_json),
            potential_range=AbilityRangeView(**profile.potential_range_json),
            scout_confidence=profile.scout_confidence,
            generation_source=profile.generation_source,
            status=profile.status,
            is_special_lineage=profile.is_special_lineage,
            generated_at=profile.generated_at,
            club_quality_score=profile.club_quality_score,
            personality=RegenPersonalityView(
                temperament=personality.temperament if personality is not None else 50,
                leadership=personality.leadership if personality is not None else 50,
                ambition=personality.ambition if personality is not None else 50,
                loyalty=personality.loyalty if personality is not None else 50,
                work_rate=personality.work_rate if personality is not None else 50,
                flair=personality.flair if personality is not None else 50,
                resilience=personality.resilience if personality is not None else 50,
                personality_tags=tuple(personality.personality_tags_json) if personality is not None else (),
            ),
            origin=RegenOriginView(
                country_code=resolved_origin.country_code if resolved_origin is not None else profile.birth_country_code,
                region_name=resolved_origin.region_name if resolved_origin is not None else profile.birth_region,
                city_name=resolved_origin.city_name if resolved_origin is not None else profile.birth_city,
                ethnolinguistic_profile=resolved_origin.ethnolinguistic_profile if resolved_origin is not None else None,
                religion_naming_pattern=resolved_origin.religion_naming_pattern if resolved_origin is not None else None,
                urbanicity=resolved_origin.urbanicity if resolved_origin is not None else None,
            ),
            lineage=lineage_view,
            metadata=profile.metadata_json,
        )

    def _to_value_snapshot_view(self, snapshot: RegenValueSnapshot, profile: RegenProfile) -> RegenValueSnapshotView:
        return RegenValueSnapshotView(
            id=snapshot.id,
            regen_id=profile.regen_id,
            current_value_coin=snapshot.current_value_coin,
            ability_component=snapshot.ability_component,
            potential_component=snapshot.potential_component,
            reputation_component=snapshot.reputation_component,
            narrative_component=snapshot.narrative_component,
            demand_component=snapshot.demand_component,
            guardrail_multiplier=snapshot.guardrail_multiplier,
            calculated_at=snapshot.calculated_at,
            metadata=snapshot.metadata_json,
        )

    def _to_scout_report_view(self, report: RegenScoutReport, profile: RegenProfile) -> RegenScoutReportView:
        return RegenScoutReportView(
            id=report.id,
            regen_id=profile.regen_id,
            club_id=report.club_id,
            scout_identity=report.scout_identity,
            manager_style=report.manager_style,
            system_profile=report.system_profile,
            current_ability_estimate=report.current_ability_estimate,
            future_potential_estimate=report.future_potential_estimate,
            scout_confidence_bps=report.scout_confidence_bps,
            role_fit_score=report.role_fit_score,
            hidden_gem_score=report.hidden_gem_score,
            wonderkid_signal=report.wonderkid_signal,
            value_hint_coin=report.value_hint_coin,
            summary_text=report.summary_text,
            tags=tuple(report.tags_json),
            metadata=report.metadata_json,
            created_at=report.created_at,
        )

    def _to_recommendation_view(self, item: RegenRecommendationItem, profile: RegenProfile) -> RegenRecommendationItemView:
        return RegenRecommendationItemView(
            id=item.id,
            regen_id=profile.regen_id,
            club_id=item.club_id,
            manager_style=item.manager_style,
            premium_tier=item.premium_tier,
            position_need=item.position_need,
            system_profile=item.system_profile,
            budget_coin=item.budget_coin,
            priority_score=item.priority_score,
            role_fit_score=item.role_fit_score,
            market_value_score=item.market_value_score,
            summary_text=item.summary_text,
            tags=tuple(item.tags_json),
            metadata=item.metadata_json,
            created_at=item.created_at,
        )


__all__ = [
    "MarketBalanceSnapshot",
    "RegenAwardEvent",
    "RegenDemandEvent",
    "RegenMarketError",
    "RegenMarketService",
    "RegenNotFoundError",
    "RegenPerformanceEvent",
    "RegenRecommendationRequest",
    "RegenSearchFilters",
    "RegenTradeRestrictedError",
]
