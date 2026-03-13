from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from backend.app.ingestion.models import NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent

from .config import ValueEngineConfig, get_value_engine_config
from .models import (
    DemandSignal,
    EGameSignal,
    HistoricalValuePoint,
    MarketPulse,
    PlayerProfileContext,
    PlayerValueInput,
    ReferenceValueContext,
    ScoutingIndexBreakdown,
    ScoutingSignal,
    TradePrint,
    ValueBreakdown,
    ValueSnapshot,
)

PRICE_RELEVANT_DEMAND_KEYS = ("purchases", "sales", "follows")
WASH_TRADE_LOOKBACK = timedelta(hours=36)
WASH_TRADE_PRICE_DELTA_PCT = 0.06
CIRCULAR_TRADE_LOOKBACK = timedelta(days=3)
CIRCULAR_TRADE_PRICE_DELTA_PCT = 0.08
TRADE_PRICE_DEVIATION_SOFT_CAP = 0.12
TRADE_PRICE_DEVIATION_HARD_CAP = 0.45
MIN_TRADE_TRUST_WEIGHT = 0.05
THIN_MARKET_MIN_TRUSTED_TRADES = 3
THIN_MARKET_MIN_PARTICIPANTS = 4
THIN_MARKET_MIN_HOLDERS = 8
THIN_MARKET_MULTIPLIER = 0.75
MIN_MARKET_GUARD_MULTIPLIER = 0.25
TOP_HOLDER_SOFT_CAP = 0.25
TOP_3_HOLDERS_SOFT_CAP = 0.60
MAX_HOLDER_CONCENTRATION_PENALTY = 0.35

POSITION_BASE_VALUES_EUR = {
    "goalkeeper": 7_500_000.0,
    "defender": 11_000_000.0,
    "midfielder": 16_500_000.0,
    "forward": 20_000_000.0,
}

POSITION_EVENT_WEIGHTS = {
    "goalkeeper": {"goal": 3.0, "assist": 4.5, "save": 1.1, "clean_sheet": 8.5, "rating": 6.3},
    "defender": {"goal": 6.2, "assist": 5.2, "save": 0.2, "clean_sheet": 6.4, "rating": 6.0},
    "midfielder": {"goal": 7.3, "assist": 6.6, "save": 0.1, "clean_sheet": 2.4, "rating": 6.8},
    "forward": {"goal": 9.8, "assist": 6.1, "save": 0.0, "clean_sheet": 0.6, "rating": 7.2},
}

PROFILE_PRODUCTION_CAPS = {
    "goalkeeper": {"saves": 140.0, "clean_sheets": 20.0, "goals": 3.0, "assists": 2.0},
    "defender": {"saves": 10.0, "clean_sheets": 20.0, "goals": 10.0, "assists": 12.0},
    "midfielder": {"saves": 5.0, "clean_sheets": 10.0, "goals": 16.0, "assists": 16.0},
    "forward": {"saves": 0.0, "clean_sheets": 4.0, "goals": 28.0, "assists": 14.0},
}


def credits_from_real_world_value(real_world_value_eur: float, eur_per_credit: int = 100_000) -> float:
    if real_world_value_eur <= 0:
        return 0.0
    return round(real_world_value_eur / eur_per_credit, 2)


@dataclass(frozen=True, slots=True)
class GlobalScoutingIndexSnapshot:
    previous_score: float
    target_score: float
    movement_pct: float
    breakdown: ScoutingIndexBreakdown


@dataclass(frozen=True, slots=True)
class MarketManipulationAssessment:
    quoted_market_price_credits: float | None
    trusted_trade_price_credits: float | None
    trade_trust_score: float
    trusted_trade_count: int
    suspicious_trade_count: int
    wash_trade_count: int
    circular_trade_count: int
    shadow_ignored_trade_count: int
    unique_trade_participants: int
    holder_count: int | None
    top_holder_share_pct: float | None
    top_3_holder_share_pct: float | None
    holder_concentration_penalty_pct: float
    thin_market: bool
    participant_diversity_score: float
    price_discovery_confidence: float
    market_integrity_score: float
    signal_trust_score: float
    suspicious_signal_suppression_multiplier: float
    integrity_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TrendAssessment:
    trend_7d_pct: float
    trend_30d_pct: float
    direction: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ResolvedWeights:
    code: str
    ftv_weight: float
    msv_weight: float
    sgv_weight: float
    egv_weight: float


@dataclass(slots=True)
class GlobalScoutingIndexService:
    config: ValueEngineConfig = field(default_factory=get_value_engine_config)

    def score(self, payload: PlayerValueInput) -> GlobalScoutingIndexSnapshot:
        previous_score = payload.previous_gsi_score
        if previous_score is None:
            previous_score = self.config.gsi_neutral_score
        previous_score = self._clamp_score(previous_score)

        eligible_counts = payload.scouting_signal.eligible_counts()
        weighted_signal_volume = 0.0
        for key, eligible_count in eligible_counts.items():
            weighted_signal_volume += eligible_count * self.config.gsi_signal_weights.get(key, 0.0)

        anchor_adjustment_pct = (
            ((self.config.gsi_neutral_score - previous_score) / 100.0) * self.config.gsi_anchor_pull_strength
        )
        scouting_signal_adjustment_pct = min(
            weighted_signal_volume / self.config.gsi_signal_scale,
            self.config.gsi_signal_cap,
        )
        uncapped_adjustment_pct = anchor_adjustment_pct + scouting_signal_adjustment_pct
        capped_adjustment_pct = self._clamp(uncapped_adjustment_pct, self.config.gsi_daily_movement_cap)
        movement_pct = capped_adjustment_pct * self.config.gsi_smoothing_factor
        movement_base = max(previous_score, self.config.gsi_neutral_score, 1.0)
        target_score = self._clamp_score(previous_score + (movement_base * movement_pct))

        return GlobalScoutingIndexSnapshot(
            previous_score=round(previous_score, 2),
            target_score=round(target_score, 2),
            movement_pct=round(movement_pct, 4),
            breakdown=ScoutingIndexBreakdown(
                neutral_score=round(self.config.gsi_neutral_score, 2),
                previous_score=round(previous_score, 2),
                target_score=round(target_score, 2),
                weighted_signal_volume=round(weighted_signal_volume, 4),
                eligible_watchlist_adds=eligible_counts["watchlist_adds"],
                eligible_shortlist_adds=eligible_counts["shortlist_adds"],
                eligible_transfer_room_adds=eligible_counts["transfer_room_adds"],
                eligible_scouting_activity=eligible_counts["scouting_activity"],
                anchor_adjustment_pct=round(anchor_adjustment_pct, 4),
                scouting_signal_adjustment_pct=round(scouting_signal_adjustment_pct, 4),
                uncapped_adjustment_pct=round(uncapped_adjustment_pct, 4),
                capped_adjustment_pct=round(capped_adjustment_pct, 4),
            ),
        )

    def _clamp(self, value: float, movement_cap: float) -> float:
        return max(-movement_cap, min(movement_cap, value))

    def _clamp_score(self, score: float) -> float:
        return max(0.0, min(100.0, score))


@dataclass(slots=True)
class ValueEngine:
    config: ValueEngineConfig = field(default_factory=get_value_engine_config)

    def build_snapshot(self, payload: PlayerValueInput) -> ValueSnapshot:
        profile = payload.profile_context
        reference_context = payload.reference_context or self._default_reference_context(payload)
        seeded_reference_market_value_eur = self._seed_reference_market_value_eur(payload, reference_context, profile)
        baseline_credits = credits_from_real_world_value(
            seeded_reference_market_value_eur,
            eur_per_credit=self.config.baseline_eur_per_credit,
        )
        floor_from_baseline = baseline_credits * self.config.minimum_floor_ratio

        previous_ftv_credits = payload.previous_ftv_credits if payload.previous_ftv_credits is not None else baseline_credits
        previous_ftv_credits = max(previous_ftv_credits, floor_from_baseline)
        previous_published_credits = self._resolve_previous_published_credits(payload, baseline_credits)

        trend = self._compute_momentum(payload.historical_values, as_of=payload.as_of)
        anchor_adjustment_pct = self._anchor_adjustment(previous_ftv_credits, baseline_credits)
        performance_adjustment_pct = self._score_matches(payload.match_events, profile)
        transfer_adjustment_pct = self._score_transfers(payload.transfer_events, seeded_reference_market_value_eur)
        award_adjustment_pct = self._score_awards(payload.award_events)
        injury_adjustment_pct = self._injury_adjustment(profile)
        momentum_adjustment_pct = self._momentum_adjustment(trend)

        truth_uncapped_adjustment_pct = (
            anchor_adjustment_pct
            + performance_adjustment_pct
            + transfer_adjustment_pct
            + award_adjustment_pct
            + injury_adjustment_pct
            + momentum_adjustment_pct
        )
        truth_capped_adjustment_pct = self._clamp(truth_uncapped_adjustment_pct, self.config.daily_movement_cap)
        truth_movement_pct = truth_capped_adjustment_pct * self.config.smoothing_factor
        football_truth_value_credits = round(
            max(previous_ftv_credits * (1.0 + truth_movement_pct), floor_from_baseline),
            2,
        )

        manipulation_assessment = self._assess_market_manipulation(
            payload.market_pulse,
            football_truth_value_credits=football_truth_value_credits,
        )
        market_snapshot_price_credits = self._resolve_market_snapshot_price(
            payload.market_pulse,
            manipulation_assessment,
        )
        demand_adjustment_pct = self._score_demand(payload.demand_signal)
        market_price_adjustment_pct = self._score_market_price(
            football_truth_value_credits,
            market_snapshot_price_credits,
        )
        liquidity_weight = self._resolve_liquidity_weight(payload.liquidity_band)
        anti_manipulation_guard_multiplier = self._resolve_market_guard_multiplier(
            payload.market_pulse,
            manipulation_assessment,
        )
        low_liquidity_penalty_pct = self.config.low_liquidity_penalty if manipulation_assessment.thin_market else 0.0
        market_signal_adjustment_pct = self._clamp(
            (demand_adjustment_pct + market_price_adjustment_pct)
            * liquidity_weight
            * anti_manipulation_guard_multiplier
            * manipulation_assessment.suspicious_signal_suppression_multiplier
            * max(1.0 - low_liquidity_penalty_pct, 0.35),
            self.config.market_signal_cap,
        )
        market_signal_floor = football_truth_value_credits * self.config.minimum_floor_ratio
        market_signal_value_credits = round(
            max(
                football_truth_value_credits * (1.0 + market_signal_adjustment_pct),
                market_signal_floor,
            ),
            2,
        )

        scouting_adjustment_pct = self._score_scouting(payload.scouting_signal, manipulation_assessment)
        scouting_signal_value_credits = round(
            max(
                football_truth_value_credits * (1.0 + scouting_adjustment_pct),
                market_signal_floor,
            ),
            2,
        )

        egame_adjustment_pct = self._score_egame(payload.egame_signal, manipulation_assessment)
        egame_signal_value_credits = round(
            max(
                football_truth_value_credits * (1.0 + egame_adjustment_pct),
                market_signal_floor,
            ),
            2,
        )

        confidence_score = self._confidence_score(
            reference_context=reference_context,
            profile=profile,
            manipulation_assessment=manipulation_assessment,
            demand_signal=payload.demand_signal,
            scouting_signal=payload.scouting_signal,
            egame_signal=payload.egame_signal,
            historical_values=payload.historical_values,
        )
        confidence_tier = self._confidence_tier(confidence_score)
        liquidity_tier = self._normalize_lookup_key(payload.liquidity_band or "default")
        resolved_weights = self._resolve_weight_profile(
            liquidity_tier=liquidity_tier,
            confidence_tier=confidence_tier,
            player_class=profile.player_class,
        )

        blended_target_credits = round(
            (football_truth_value_credits * resolved_weights.ftv_weight)
            + (market_signal_value_credits * resolved_weights.msv_weight)
            + (scouting_signal_value_credits * resolved_weights.sgv_weight)
            + (egame_signal_value_credits * resolved_weights.egv_weight),
            2,
        )
        price_band_limit = self._resolve_price_band_limit(payload.liquidity_band)
        price_band_floor_credits = round(football_truth_value_credits * price_band_limit.min_ratio, 2)
        price_band_ceiling_credits = round(football_truth_value_credits * price_band_limit.max_ratio, 2)
        band_limited_target_credits = round(
            min(max(blended_target_credits, price_band_floor_credits), price_band_ceiling_credits),
            2,
        )

        uncapped_adjustment_pct = self._target_delta_pct(previous_published_credits, band_limited_target_credits)
        capped_adjustment_pct = self._clamp(uncapped_adjustment_pct, self.config.daily_movement_cap)
        smoothed_adjustment_pct = capped_adjustment_pct * self.config.smoothing_factor
        published_floor_credits = max(market_signal_floor, price_band_floor_credits)
        target_credits = round(
            min(
                max(
                    previous_published_credits * (1.0 + smoothed_adjustment_pct),
                    published_floor_credits,
                ),
                price_band_ceiling_credits,
            ),
            2,
        )

        gsi_snapshot = GlobalScoutingIndexService(config=self.config).score(payload)
        reason_codes = self._build_reason_codes(
            payload=payload,
            reference_context=reference_context,
            performance_adjustment_pct=performance_adjustment_pct,
            transfer_adjustment_pct=transfer_adjustment_pct,
            award_adjustment_pct=award_adjustment_pct,
            injury_adjustment_pct=injury_adjustment_pct,
            scouting_adjustment_pct=scouting_adjustment_pct,
            egame_adjustment_pct=egame_adjustment_pct,
            market_signal_adjustment_pct=market_signal_adjustment_pct,
            manipulation_assessment=manipulation_assessment,
            trend=trend,
        )
        drivers = self._build_drivers(
            payload=payload,
            manipulation_assessment=manipulation_assessment,
            price_band_guard_active=(band_limited_target_credits != blended_target_credits),
            reason_codes=reason_codes,
        )

        return ValueSnapshot(
            player_id=payload.player_id,
            player_name=payload.player_name,
            as_of=payload.as_of,
            previous_credits=round(previous_published_credits, 2),
            target_credits=target_credits,
            movement_pct=round(smoothed_adjustment_pct, 4),
            football_truth_value_credits=football_truth_value_credits,
            market_signal_value_credits=market_signal_value_credits,
            scouting_signal_value_credits=scouting_signal_value_credits,
            egame_signal_value_credits=egame_signal_value_credits,
            previous_global_scouting_index=gsi_snapshot.previous_score,
            global_scouting_index=gsi_snapshot.target_score,
            global_scouting_index_movement_pct=gsi_snapshot.movement_pct,
            confidence_score=round(confidence_score, 2),
            confidence_tier=confidence_tier,
            liquidity_tier=liquidity_tier,
            market_integrity_score=round(manipulation_assessment.market_integrity_score, 2),
            signal_trust_score=round(manipulation_assessment.signal_trust_score, 2),
            trend_7d_pct=round(trend.trend_7d_pct, 4),
            trend_30d_pct=round(trend.trend_30d_pct, 4),
            trend_direction=trend.direction,
            trend_confidence=round(trend.confidence, 4),
            snapshot_type=payload.snapshot_type,
            config_version=self.config.config_version,
            breakdown=ValueBreakdown(
                baseline_credits=baseline_credits,
                football_truth_value_credits=football_truth_value_credits,
                market_signal_value_credits=market_signal_value_credits,
                published_card_value_credits=target_credits,
                blended_target_credits=blended_target_credits,
                band_limited_target_credits=band_limited_target_credits,
                liquidity_weight=round(liquidity_weight, 4),
                snapshot_market_price_credits=market_snapshot_price_credits,
                quoted_market_price_credits=manipulation_assessment.quoted_market_price_credits,
                trusted_trade_price_credits=manipulation_assessment.trusted_trade_price_credits,
                price_band_floor_credits=price_band_floor_credits,
                price_band_ceiling_credits=price_band_ceiling_credits,
                anti_manipulation_guard_multiplier=round(anti_manipulation_guard_multiplier, 4),
                anchor_adjustment_pct=round(anchor_adjustment_pct, 4),
                performance_adjustment_pct=round(performance_adjustment_pct, 4),
                transfer_adjustment_pct=round(transfer_adjustment_pct, 4),
                award_adjustment_pct=round(award_adjustment_pct, 4),
                demand_adjustment_pct=round(demand_adjustment_pct, 4),
                market_price_adjustment_pct=round(market_price_adjustment_pct, 4),
                market_signal_adjustment_pct=round(market_signal_adjustment_pct, 4),
                truth_uncapped_adjustment_pct=round(truth_uncapped_adjustment_pct, 4),
                truth_capped_adjustment_pct=round(truth_capped_adjustment_pct, 4),
                uncapped_adjustment_pct=round(uncapped_adjustment_pct, 4),
                capped_adjustment_pct=round(capped_adjustment_pct, 4),
                trade_trust_score=round(manipulation_assessment.trade_trust_score, 4),
                trusted_trade_count=manipulation_assessment.trusted_trade_count,
                suspicious_trade_count=manipulation_assessment.suspicious_trade_count,
                wash_trade_count=manipulation_assessment.wash_trade_count,
                circular_trade_count=manipulation_assessment.circular_trade_count,
                shadow_ignored_trade_count=manipulation_assessment.shadow_ignored_trade_count,
                unique_trade_participants=manipulation_assessment.unique_trade_participants,
                holder_count=manipulation_assessment.holder_count,
                top_holder_share_pct=manipulation_assessment.top_holder_share_pct,
                top_3_holder_share_pct=manipulation_assessment.top_3_holder_share_pct,
                holder_concentration_penalty_pct=round(manipulation_assessment.holder_concentration_penalty_pct, 4),
                thin_market=manipulation_assessment.thin_market,
                scouting_signal_value_credits=scouting_signal_value_credits,
                egame_signal_value_credits=egame_signal_value_credits,
                reference_market_value_eur=round(payload.reference_market_value_eur, 2),
                seeded_reference_market_value_eur=round(seeded_reference_market_value_eur, 2),
                reference_value_source=reference_context.source,
                reference_confidence_tier=reference_context.confidence_tier,
                reference_confidence_score=round(reference_context.confidence_score, 2),
                reference_staleness_days=reference_context.staleness_days,
                position_family=profile.position_family,
                position_subrole=profile.position_subrole,
                player_class=profile.player_class,
                age_curve_multiplier=round(self._age_curve_multiplier(profile.age_years), 4),
                competition_quality_multiplier=round(self._competition_quality_multiplier(profile), 4),
                club_quality_multiplier=round(self._club_quality_multiplier(profile), 4),
                visibility_multiplier=round(self._visibility_multiplier(profile), 4),
                injury_adjustment_pct=round(injury_adjustment_pct, 4),
                scouting_adjustment_pct=round(scouting_adjustment_pct, 4),
                egame_adjustment_pct=round(egame_adjustment_pct, 4),
                momentum_7d_pct=round(trend.trend_7d_pct, 4),
                momentum_30d_pct=round(trend.trend_30d_pct, 4),
                momentum_adjustment_pct=round(momentum_adjustment_pct, 4),
                trend_confidence=round(trend.confidence, 4),
                confidence_score=round(confidence_score, 2),
                market_integrity_score=round(manipulation_assessment.market_integrity_score, 2),
                signal_trust_score=round(manipulation_assessment.signal_trust_score, 2),
                participant_diversity_score=round(manipulation_assessment.participant_diversity_score, 4),
                price_discovery_confidence=round(manipulation_assessment.price_discovery_confidence, 4),
                low_liquidity_penalty_pct=round(low_liquidity_penalty_pct, 4),
                suspicious_signal_suppression_multiplier=round(
                    manipulation_assessment.suspicious_signal_suppression_multiplier,
                    4,
                ),
                weight_profile_code=resolved_weights.code,
                reason_codes=reason_codes,
                integrity_flags=manipulation_assessment.integrity_flags,
            ),
            global_scouting_index_breakdown=gsi_snapshot.breakdown,
            drivers=drivers,
            reason_codes=reason_codes,
        )

    def _default_reference_context(self, payload: PlayerValueInput) -> ReferenceValueContext:
        return ReferenceValueContext(
            market_value_eur=max(payload.reference_market_value_eur, 1.0),
            source="legacy_reference",
            confidence_tier="heuristic_only",
            confidence_score=35.0,
            staleness_days=0,
            is_stale=False,
            blended_with_profile_baseline=False,
        )

    def _seed_reference_market_value_eur(
        self,
        payload: PlayerValueInput,
        reference_context: ReferenceValueContext,
        profile: PlayerProfileContext,
    ) -> float:
        profile_baseline = self._profile_baseline_market_value_eur(profile)
        explicit_reference = max(reference_context.market_value_eur, 1.0)
        if reference_context.confidence_tier == "direct_verified_reference" and not reference_context.is_stale:
            return round(explicit_reference, 2)
        if reference_context.confidence_tier == "heuristic_only":
            return round(max(profile_baseline, explicit_reference), 2)
        staleness_ratio = 0.0
        if reference_context.staleness_days >= self.config.reference_stale_days:
            spread = max(self.config.reference_very_stale_days - self.config.reference_stale_days, 1)
            staleness_ratio = min(
                (reference_context.staleness_days - self.config.reference_stale_days) / spread,
                1.0,
            )
        blend_ratio = min(self.config.reference_stale_blend + (staleness_ratio * 0.35), 0.85)
        blended = explicit_reference * (1.0 - blend_ratio) + profile_baseline * blend_ratio
        return round(max(blended, profile_baseline * 0.80), 2)

    def _profile_baseline_market_value_eur(self, profile: PlayerProfileContext) -> float:
        position_family = self._normalize_position_family(profile.position_family)
        base_value = POSITION_BASE_VALUES_EUR.get(position_family, POSITION_BASE_VALUES_EUR["midfielder"])
        caps = PROFILE_PRODUCTION_CAPS[position_family]

        appearances_factor = min(profile.appearances / 34.0, 1.0) * 0.20
        starts_factor = min(profile.starts / 28.0, 1.0) * 0.10
        minutes_factor = min(profile.minutes_played / 2_700.0, 1.0) * 0.20
        recent_form_factor = max(min(((profile.recent_form_rating or 6.5) - 6.5) * 0.12, 0.22), -0.10)
        production_factor = (
            self._diminishing_ratio(profile.goals, caps["goals"]) * self._production_goal_weight(position_family)
            + self._diminishing_ratio(profile.assists, caps["assists"]) * 0.18
            + self._diminishing_ratio(profile.clean_sheets, caps["clean_sheets"]) * self._production_clean_sheet_weight(position_family)
            + self._diminishing_ratio(profile.saves, caps["saves"]) * self._production_save_weight(position_family)
        )
        leadership_bonus = 0.04 if (profile.captaincy_flag or profile.leadership_flag) else 0.0
        transfer_interest_bonus = min(profile.transfer_interest_score / 20.0, 0.12)
        injury_multiplier = max(1.0 - min(profile.injury_absence_days / 160.0, 0.22), 0.72)
        age_curve_multiplier = self._age_curve_multiplier(profile.age_years)
        competition_quality_multiplier = self._competition_quality_multiplier(profile)
        club_quality_multiplier = self._club_quality_multiplier(profile)
        visibility_multiplier = self._visibility_multiplier(profile)

        combined_multiplier = max(
            0.42,
            0.72
            + appearances_factor
            + starts_factor
            + minutes_factor
            + recent_form_factor
            + production_factor
            + leadership_bonus
            + transfer_interest_bonus,
        )
        return round(
            base_value
            * combined_multiplier
            * age_curve_multiplier
            * competition_quality_multiplier
            * club_quality_multiplier
            * visibility_multiplier
            * injury_multiplier,
            2,
        )

    def _resolve_previous_published_credits(self, payload: PlayerValueInput, baseline_credits: float) -> float:
        previous_published_credits = payload.previous_pcv_credits
        if previous_published_credits is None:
            previous_published_credits = payload.current_credits
        if previous_published_credits is None:
            previous_published_credits = baseline_credits
        return max(previous_published_credits, baseline_credits * self.config.minimum_floor_ratio)

    def _anchor_adjustment(self, previous_credits: float, baseline_credits: float) -> float:
        if previous_credits <= 0:
            return 0.0
        return ((baseline_credits - previous_credits) / previous_credits) * self.config.anchor_pull_strength

    def _score_matches(self, events: tuple[NormalizedMatchEvent, ...], profile: PlayerProfileContext) -> float:
        points = sum(self._match_points(event, profile) for event in events)
        return points / self.config.performance_scale

    def _match_points(self, event: NormalizedMatchEvent, profile: PlayerProfileContext) -> float:
        position_family = self._position_family_from_event(event, profile)
        weights = POSITION_EVENT_WEIGHTS[position_family]
        minutes_factor = min(event.minutes / 90.0, 1.0)
        if event.minutes < 25:
            minutes_factor *= 0.55 if (event.goals or event.assists) else 0.30
        if event.started:
            minutes_factor = max(minutes_factor, 0.55)
        rating_component = max(event.rating - 6.0, -1.5) * weights["rating"]
        stat_component = (
            self._diminishing_count(event.goals) * weights["goal"]
            + self._diminishing_count(event.assists) * weights["assist"]
            + min(event.saves, 10) * weights["save"]
            + (weights["clean_sheet"] if event.clean_sheet else 0.0)
        )
        importance_multiplier = self._event_importance_multiplier(event)
        points = (rating_component + stat_component) * max(minutes_factor, 0.1) * importance_multiplier
        if event.big_moment:
            points += self.config.big_moment_bonus
        if event.won_final:
            points += self.config.big_moment_bonus * 0.45
        elif event.won_match:
            points += 2.0
        return points

    def _score_transfers(
        self,
        events: tuple[NormalizedTransferEvent, ...],
        reference_market_value_eur: float,
    ) -> float:
        points = 0.0
        denominator = max(reference_market_value_eur, 1.0)
        for event in events:
            status_weight = {
                "completed": 16.0,
                "agreed": 10.0,
                "advanced": 6.5,
                "rumour": 2.5,
            }.get(event.status.lower(), 2.5)
            destination_multiplier = self._competition_multiplier(event.to_competition or "")
            fee_ratio = 0.0
            if event.reported_fee_eur is not None:
                fee_ratio = min(event.reported_fee_eur / denominator, 2.0)
            points += (status_weight + (fee_ratio * 10.0)) * max(destination_multiplier, 1.0)
        return points / self.config.transfer_scale

    def _score_awards(self, events: tuple[NormalizedAwardEvent, ...]) -> float:
        points = 0.0
        for event in events:
            award_code = self._normalize_award_code(event)
            points += self.config.award_impacts.get(award_code, 0.0)
        return points / self.config.award_scale

    def _injury_adjustment(self, profile: PlayerProfileContext) -> float:
        if profile.injury_absence_days <= 0:
            return 0.0
        return -min(profile.injury_absence_days / 250.0, 0.10)

    def _compute_momentum(
        self,
        historical_values: tuple[HistoricalValuePoint, ...],
        *,
        as_of,
    ) -> TrendAssessment:
        ordered = tuple(sorted(historical_values, key=lambda point: point.as_of))
        trend_7d_pct = self._window_change_pct(ordered, as_of=as_of, days=self.config.momentum_short_window_days)
        trend_30d_pct = self._window_change_pct(ordered, as_of=as_of, days=self.config.momentum_medium_window_days)
        direction = "flat"
        if trend_7d_pct > 0.01 or trend_30d_pct > 0.02:
            direction = "up"
        elif trend_7d_pct < -0.01 or trend_30d_pct < -0.02:
            direction = "down"
        confidence = min(len(ordered) / 8.0, 1.0)
        if ordered:
            historical_confidence = [point.confidence_score for point in ordered if point.confidence_score is not None]
            if historical_confidence:
                confidence *= max(min(sum(historical_confidence) / (len(historical_confidence) * 100.0), 1.0), 0.35)
        return TrendAssessment(
            trend_7d_pct=round(trend_7d_pct, 4),
            trend_30d_pct=round(trend_30d_pct, 4),
            direction=direction,
            confidence=round(confidence, 4),
        )

    def _window_change_pct(
        self,
        history: tuple[HistoricalValuePoint, ...],
        *,
        as_of,
        days: int,
    ) -> float:
        if not history:
            return 0.0
        end_point = history[-1]
        cutoff = self._coerce_utc_datetime(as_of) - timedelta(days=days)
        baseline = next(
            (point for point in reversed(history) if self._coerce_utc_datetime(point.as_of) <= cutoff),
            history[0],
        )
        if baseline.published_value_credits <= 0:
            return 0.0
        return (end_point.published_value_credits - baseline.published_value_credits) / baseline.published_value_credits

    def _coerce_utc_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _momentum_adjustment(self, trend: TrendAssessment) -> float:
        raw = (
            trend.trend_7d_pct * self.config.momentum_short_sensitivity
            + trend.trend_30d_pct * self.config.momentum_medium_sensitivity
        ) * max(trend.confidence, 0.30)
        return self._clamp(raw, self.config.momentum_cap)

    def _score_demand(self, signal: DemandSignal) -> float:
        eligible_counts = signal.eligible_counts()
        weighted_sum = 0.0
        for key, eligible_count in eligible_counts.items():
            if key not in PRICE_RELEVANT_DEMAND_KEYS:
                continue
            weighted_sum += eligible_count * self.config.demand_weights.get(key, 0.0)
        purchases = eligible_counts.get("purchases", 0)
        sales = eligible_counts.get("sales", 0)
        total_flow = max(purchases + sales, 1)
        imbalance = (purchases - sales) / total_flow
        movement = (weighted_sum / self.config.demand_scale) + (imbalance * 0.03)
        return self._clamp(movement, self.config.demand_movement_cap)

    def _score_scouting(
        self,
        signal: ScoutingSignal,
        manipulation_assessment: MarketManipulationAssessment,
    ) -> float:
        weighted_volume = 0.0
        for key, eligible_count in signal.eligible_counts().items():
            weighted_volume += eligible_count * self.config.gsi_signal_weights.get(key, 0.0)
        movement = (
            (weighted_volume / self.config.scouting_scale)
            * manipulation_assessment.suspicious_signal_suppression_multiplier
        )
        return self._clamp(movement, self.config.scouting_signal_cap)

    def _score_egame(
        self,
        signal: EGameSignal,
        manipulation_assessment: MarketManipulationAssessment,
    ) -> float:
        weighted_volume = 0.0
        for key, eligible_count in signal.eligible_counts().items():
            weighted_volume += eligible_count * self.config.egame_signal_weights.get(key, 0.0)
        sample_penalty = min(signal.sample_size() / 20.0, 1.0)
        movement = (
            (weighted_volume / self.config.egame_scale)
            * sample_penalty
            * manipulation_assessment.suspicious_signal_suppression_multiplier
        )
        return self._clamp(movement, self.config.egame_signal_cap)

    def _score_market_price(self, football_truth_value_credits: float, snapshot_market_price: float | None) -> float:
        if snapshot_market_price is None or football_truth_value_credits <= 0:
            return 0.0
        return (
            ((snapshot_market_price - football_truth_value_credits) / football_truth_value_credits)
            * self.config.market_price_pull_strength
        )

    def _assess_market_manipulation(
        self,
        market_pulse: MarketPulse,
        *,
        football_truth_value_credits: float,
    ) -> MarketManipulationAssessment:
        quoted_market_price = market_pulse.snapshot_price_credits()
        trade_prints = tuple(sorted(market_pulse.trade_prints, key=lambda trade: (trade.occurred_at, trade.trade_id)))
        shadow_ignored_trade_ids = {trade.trade_id for trade in trade_prints if trade.shadow_ignored}
        wash_trade_ids = self._detect_wash_trades(trade_prints)
        circular_trade_ids = self._detect_circular_trades(trade_prints)
        repeated_counterparty_flag = self._repeated_counterparty_cluster(trade_prints)
        suspicious_trade_ids = shadow_ignored_trade_ids | wash_trade_ids | circular_trade_ids

        participant_ids: set[str] = set()
        trusted_trade_weights: dict[str, float] = {}
        trusted_trade_weight_total = 0.0
        trusted_trade_price_weighted_sum = 0.0
        for trade in trade_prints:
            participant_ids.add(trade.seller_user_id)
            participant_ids.add(trade.buyer_user_id)
            if trade.trade_id in suspicious_trade_ids:
                continue
            trust_weight = self._trade_trust_weight(
                trade,
                quoted_market_price_credits=quoted_market_price,
                football_truth_value_credits=football_truth_value_credits,
            )
            if trust_weight <= 0:
                continue
            trusted_trade_weights[trade.trade_id] = trust_weight
            weighted_size = trade.quantity * trust_weight
            trusted_trade_weight_total += weighted_size
            trusted_trade_price_weighted_sum += trade.price_credits * weighted_size

        trusted_trade_price = None
        if trusted_trade_weight_total > 0:
            trusted_trade_price = round(trusted_trade_price_weighted_sum / trusted_trade_weight_total, 2)

        trade_trust_score = 0.0
        if trade_prints:
            trade_trust_score = round(sum(trusted_trade_weights.values()) / len(trade_prints), 4)

        participant_diversity_score = min(
            len(participant_ids) / self.config.participant_diversity_scale,
            1.0,
        )
        holder_concentration_penalty_pct = self._holder_concentration_penalty(market_pulse)
        thin_market = self._is_thin_market(
            market_pulse,
            trusted_trade_count=len(trusted_trade_weights),
            unique_trade_participants=len(participant_ids),
        )
        price_discovery_confidence = self._price_discovery_confidence(
            quoted_market_price=quoted_market_price,
            trusted_trade_price=trusted_trade_price,
            trade_trust_score=trade_trust_score,
            participant_diversity_score=participant_diversity_score,
        )

        penalties = holder_concentration_penalty_pct
        integrity_flags: list[str] = []
        if shadow_ignored_trade_ids:
            penalties += min(len(shadow_ignored_trade_ids) * 0.06, 0.18)
            integrity_flags.append("shadow_ignored_trades")
        if wash_trade_ids:
            penalties += min(len(wash_trade_ids) * self.config.suspicious_trade_penalty * 0.55, 0.30)
            integrity_flags.append("wash_trade_cluster")
        if circular_trade_ids:
            penalties += min(len(circular_trade_ids) * self.config.suspicious_trade_penalty * 0.45, 0.28)
            integrity_flags.append("circular_trade_cluster")
        if repeated_counterparty_flag:
            penalties += 0.12
            integrity_flags.append("repeated_counterparty_cluster")
        if thin_market:
            penalties += self.config.low_liquidity_penalty
            integrity_flags.append("thin_market")
        if self._wide_spread_quote(market_pulse):
            penalties += 0.08
            integrity_flags.append("wide_spread_quote")

        suspicious_signal_suppression_multiplier = max(1.0 - penalties, 0.20)
        market_integrity_score = max((1.0 - penalties) * 100.0, 5.0)
        signal_trust_score = max(
            (
                (trade_trust_score * 45.0)
                + (participant_diversity_score * 25.0)
                + (price_discovery_confidence * 30.0)
            )
            * suspicious_signal_suppression_multiplier,
            5.0,
        )

        return MarketManipulationAssessment(
            quoted_market_price_credits=quoted_market_price,
            trusted_trade_price_credits=trusted_trade_price,
            trade_trust_score=trade_trust_score,
            trusted_trade_count=len(trusted_trade_weights),
            suspicious_trade_count=len(suspicious_trade_ids),
            wash_trade_count=len(wash_trade_ids),
            circular_trade_count=len(circular_trade_ids),
            shadow_ignored_trade_count=len(shadow_ignored_trade_ids),
            unique_trade_participants=len(participant_ids),
            holder_count=market_pulse.holder_count,
            top_holder_share_pct=market_pulse.top_holder_share_pct,
            top_3_holder_share_pct=market_pulse.top_3_holder_share_pct,
            holder_concentration_penalty_pct=holder_concentration_penalty_pct,
            thin_market=thin_market,
            participant_diversity_score=round(participant_diversity_score, 4),
            price_discovery_confidence=round(price_discovery_confidence, 4),
            market_integrity_score=round(market_integrity_score, 2),
            signal_trust_score=round(signal_trust_score, 2),
            suspicious_signal_suppression_multiplier=round(suspicious_signal_suppression_multiplier, 4),
            integrity_flags=tuple(integrity_flags),
        )

    def _resolve_market_snapshot_price(
        self,
        market_pulse: MarketPulse,
        manipulation_assessment: MarketManipulationAssessment,
    ) -> float | None:
        quoted_market_price = market_pulse.snapshot_price_credits()
        trusted_trade_price = manipulation_assessment.trusted_trade_price_credits
        if quoted_market_price is None:
            return trusted_trade_price
        if trusted_trade_price is None:
            return quoted_market_price
        divergence_pct = self._relative_gap(quoted_market_price, trusted_trade_price)
        if divergence_pct <= 0.08:
            return round((quoted_market_price + trusted_trade_price) / 2.0, 2)
        blend_weight = 0.20 + (manipulation_assessment.trade_trust_score * 0.80)
        blended_price = trusted_trade_price + ((quoted_market_price - trusted_trade_price) * blend_weight)
        return round(blended_price, 2)

    def _resolve_market_guard_multiplier(
        self,
        market_pulse: MarketPulse,
        manipulation_assessment: MarketManipulationAssessment,
    ) -> float:
        multiplier = 1.0
        if market_pulse.trade_prints:
            if manipulation_assessment.trusted_trade_count == 0:
                multiplier *= MIN_MARKET_GUARD_MULTIPLIER
            else:
                multiplier *= MIN_MARKET_GUARD_MULTIPLIER + (
                    manipulation_assessment.trade_trust_score * (1.0 - MIN_MARKET_GUARD_MULTIPLIER)
                )
        if manipulation_assessment.holder_concentration_penalty_pct > 0:
            multiplier *= max(1.0 - manipulation_assessment.holder_concentration_penalty_pct, 0.5)
        if manipulation_assessment.thin_market:
            multiplier *= THIN_MARKET_MULTIPLIER
        return max(round(multiplier, 4), MIN_MARKET_GUARD_MULTIPLIER)

    def _trade_trust_weight(
        self,
        trade: TradePrint,
        *,
        quoted_market_price_credits: float | None,
        football_truth_value_credits: float,
    ) -> float:
        if trade.seller_user_id == trade.buyer_user_id or trade.quantity <= 0 or trade.price_credits <= 0:
            return 0.0
        reference_price = quoted_market_price_credits or football_truth_value_credits
        if reference_price <= 0:
            return 1.0
        deviation_pct = self._relative_gap(trade.price_credits, reference_price)
        if deviation_pct >= TRADE_PRICE_DEVIATION_HARD_CAP:
            return 0.0
        if deviation_pct <= TRADE_PRICE_DEVIATION_SOFT_CAP:
            return 1.0
        scaled_penalty = (deviation_pct - TRADE_PRICE_DEVIATION_SOFT_CAP) / (
            TRADE_PRICE_DEVIATION_HARD_CAP - TRADE_PRICE_DEVIATION_SOFT_CAP
        )
        return round(max(1.0 - scaled_penalty, MIN_TRADE_TRUST_WEIGHT), 4)

    def _detect_wash_trades(self, trade_prints: tuple[TradePrint, ...]) -> set[str]:
        suspicious_trade_ids: set[str] = set()
        for index, left_trade in enumerate(trade_prints):
            for right_trade in trade_prints[index + 1 :]:
                if right_trade.occurred_at - left_trade.occurred_at > WASH_TRADE_LOOKBACK:
                    break
                is_reversal = (
                    left_trade.seller_user_id == right_trade.buyer_user_id
                    and left_trade.buyer_user_id == right_trade.seller_user_id
                )
                if not is_reversal:
                    continue
                if self._relative_gap(left_trade.price_credits, right_trade.price_credits) > WASH_TRADE_PRICE_DELTA_PCT:
                    continue
                suspicious_trade_ids.update({left_trade.trade_id, right_trade.trade_id})
        return suspicious_trade_ids

    def _detect_circular_trades(self, trade_prints: tuple[TradePrint, ...]) -> set[str]:
        suspicious_trade_ids: set[str] = set()
        for first_index, first_trade in enumerate(trade_prints):
            for second_index in range(first_index + 1, len(trade_prints)):
                second_trade = trade_prints[second_index]
                if second_trade.occurred_at - first_trade.occurred_at > CIRCULAR_TRADE_LOOKBACK:
                    break
                if first_trade.buyer_user_id != second_trade.seller_user_id:
                    continue
                for third_trade in trade_prints[second_index + 1 :]:
                    if third_trade.occurred_at - first_trade.occurred_at > CIRCULAR_TRADE_LOOKBACK:
                        break
                    if second_trade.buyer_user_id != third_trade.seller_user_id:
                        continue
                    if third_trade.buyer_user_id != first_trade.seller_user_id:
                        continue
                    participant_count = len(
                        {
                            first_trade.seller_user_id,
                            first_trade.buyer_user_id,
                            second_trade.buyer_user_id,
                        }
                    )
                    if participant_count < 3:
                        continue
                    circular_prices = (
                        first_trade.price_credits,
                        second_trade.price_credits,
                        third_trade.price_credits,
                    )
                    if self._relative_gap(max(circular_prices), min(circular_prices)) > CIRCULAR_TRADE_PRICE_DELTA_PCT:
                        continue
                    suspicious_trade_ids.update(
                        {
                            first_trade.trade_id,
                            second_trade.trade_id,
                            third_trade.trade_id,
                        }
                    )
        return suspicious_trade_ids

    def _repeated_counterparty_cluster(self, trade_prints: tuple[TradePrint, ...]) -> bool:
        pair_counts: dict[tuple[str, str], int] = {}
        for trade in trade_prints:
            pair = tuple(sorted((trade.seller_user_id, trade.buyer_user_id)))
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
        return bool(pair_counts) and max(pair_counts.values()) >= 3 and max(pair_counts.values()) / max(len(trade_prints), 1) >= 0.5

    def _holder_concentration_penalty(self, market_pulse: MarketPulse) -> float:
        penalty = 0.0
        if market_pulse.top_holder_share_pct is not None and market_pulse.top_holder_share_pct > TOP_HOLDER_SOFT_CAP:
            penalty += min((market_pulse.top_holder_share_pct - TOP_HOLDER_SOFT_CAP) * 1.4, 0.22)
        if market_pulse.top_3_holder_share_pct is not None and market_pulse.top_3_holder_share_pct > TOP_3_HOLDERS_SOFT_CAP:
            penalty += min((market_pulse.top_3_holder_share_pct - TOP_3_HOLDERS_SOFT_CAP) * 0.8, 0.18)
        return min(round(penalty, 4), MAX_HOLDER_CONCENTRATION_PENALTY)

    def _is_thin_market(
        self,
        market_pulse: MarketPulse,
        *,
        trusted_trade_count: int,
        unique_trade_participants: int,
    ) -> bool:
        if market_pulse.trade_prints and (
            trusted_trade_count < THIN_MARKET_MIN_TRUSTED_TRADES
            or unique_trade_participants < THIN_MARKET_MIN_PARTICIPANTS
        ):
            return True
        if market_pulse.holder_count is not None and market_pulse.holder_count < THIN_MARKET_MIN_HOLDERS:
            return True
        return self._wide_spread_quote(market_pulse)

    def _wide_spread_quote(self, market_pulse: MarketPulse) -> bool:
        if (
            market_pulse.best_bid_price_credits is None
            or market_pulse.best_ask_price_credits is None
            or market_pulse.best_bid_price_credits <= 0
            or market_pulse.best_ask_price_credits <= market_pulse.best_bid_price_credits
        ):
            return False
        quoted_market_price = market_pulse.snapshot_price_credits()
        if quoted_market_price is None or quoted_market_price <= 0:
            return False
        spread_bps = ((market_pulse.best_ask_price_credits - market_pulse.best_bid_price_credits) / quoted_market_price) * 10_000.0
        return spread_bps > self.config.order_book_wide_spread_bps

    def _price_discovery_confidence(
        self,
        *,
        quoted_market_price: float | None,
        trusted_trade_price: float | None,
        trade_trust_score: float,
        participant_diversity_score: float,
    ) -> float:
        convergence_score = 0.0
        if quoted_market_price is not None and trusted_trade_price is not None:
            convergence_score = max(1.0 - self._relative_gap(quoted_market_price, trusted_trade_price), 0.0)
        elif quoted_market_price is not None or trusted_trade_price is not None:
            convergence_score = 0.45
        return min((trade_trust_score * 0.45) + (participant_diversity_score * 0.30) + (convergence_score * 0.25), 1.0)

    def _competition_multiplier(self, competition_name: str) -> float:
        return self.config.competition_multipliers.get(competition_name.lower(), 1.0)

    def _competition_quality_multiplier(self, profile: PlayerProfileContext) -> float:
        strength = profile.competition_strength or 1.0
        return min(max(strength, 0.75), 1.35)

    def _club_quality_multiplier(self, profile: PlayerProfileContext) -> float:
        prestige = profile.club_prestige or 50.0
        return min(max(0.92 + (prestige / 100.0) * 0.18, 0.90), 1.12)

    def _visibility_multiplier(self, profile: PlayerProfileContext) -> float:
        visibility = profile.continental_visibility or 1.0
        return min(max(visibility, 0.92), 1.12)

    def _resolve_liquidity_weight(self, liquidity_band: str | None) -> float:
        if liquidity_band is None:
            return self.config.default_liquidity_weight
        lookup_key = self._normalize_lookup_key(liquidity_band)
        return self.config.liquidity_band_market_weights.get(lookup_key, self.config.default_liquidity_weight)

    def _resolve_price_band_limit(self, liquidity_band: str | None):
        lookup_key = self._normalize_lookup_key(liquidity_band) if liquidity_band is not None else "default"
        price_band_lookup = {limit.code: limit for limit in self.config.price_band_limits}
        return price_band_lookup.get(lookup_key) or price_band_lookup.get("default") or self.config.price_band_limits[0]

    def _resolve_weight_profile(
        self,
        *,
        liquidity_tier: str,
        confidence_tier: str,
        player_class: str,
    ) -> ResolvedWeights:
        normalized_player_class = self._normalize_lookup_key(player_class)
        best_match = None
        best_specificity = -1
        for profile in self.config.weight_profiles:
            if profile.liquidity_tiers and liquidity_tier not in profile.liquidity_tiers:
                continue
            if profile.confidence_tiers and confidence_tier not in profile.confidence_tiers:
                continue
            if profile.player_classes and normalized_player_class not in profile.player_classes:
                continue
            specificity = int(bool(profile.liquidity_tiers)) + int(bool(profile.confidence_tiers)) + int(bool(profile.player_classes))
            if specificity > best_specificity:
                best_match = profile
                best_specificity = specificity
        chosen = best_match or self.config.weight_profiles[0]
        return ResolvedWeights(
            code=chosen.code,
            ftv_weight=chosen.ftv_weight,
            msv_weight=chosen.msv_weight,
            sgv_weight=chosen.sgv_weight,
            egv_weight=chosen.egv_weight,
        )

    def _confidence_score(
        self,
        *,
        reference_context: ReferenceValueContext,
        profile: PlayerProfileContext,
        manipulation_assessment: MarketManipulationAssessment,
        demand_signal: DemandSignal,
        scouting_signal: ScoutingSignal,
        egame_signal: EGameSignal,
        historical_values: tuple[HistoricalValuePoint, ...],
    ) -> float:
        profile_completeness = profile.profile_completeness_score or 55.0
        workload_score = min((profile.minutes_played / 2_700.0) * 100.0, 100.0)
        historical_score = min(len(historical_values) * 12.0, 100.0)
        signal_breadth = min(
            (
                demand_signal.eligible_volume()
                + scouting_signal.eligible_volume()
                + egame_signal.sample_size()
                + manipulation_assessment.trusted_trade_count * 3
            )
            * 2.0,
            100.0,
        )
        return min(
            (reference_context.confidence_score * 0.35)
            + (max(profile_completeness, workload_score) * 0.20)
            + (manipulation_assessment.market_integrity_score * 0.25)
            + (max(signal_breadth, historical_score) * 0.20),
            100.0,
        )

    def _confidence_tier(self, score: float) -> str:
        if score >= 75:
            return "high"
        if score >= 55:
            return "medium"
        return "low"

    def _build_reason_codes(
        self,
        *,
        payload: PlayerValueInput,
        reference_context: ReferenceValueContext,
        performance_adjustment_pct: float,
        transfer_adjustment_pct: float,
        award_adjustment_pct: float,
        injury_adjustment_pct: float,
        scouting_adjustment_pct: float,
        egame_adjustment_pct: float,
        market_signal_adjustment_pct: float,
        manipulation_assessment: MarketManipulationAssessment,
        trend: TrendAssessment,
    ) -> tuple[str, ...]:
        reason_codes: list[str] = []
        if performance_adjustment_pct >= 0.02:
            reason_codes.append("strong_recent_form")
        if transfer_adjustment_pct >= 0.01:
            reason_codes.append("transfer_momentum")
        if award_adjustment_pct >= 0.01:
            reason_codes.append("award_signal")
        if market_signal_adjustment_pct >= 0.012:
            reason_codes.append("rising_market_demand")
        if scouting_adjustment_pct >= 0.008:
            reason_codes.append("scouting_interest_surge")
        if egame_adjustment_pct >= 0.004:
            reason_codes.append("egame_visibility_uplift")
        if injury_adjustment_pct < 0:
            reason_codes.append("injury_absence_drag")
        if reference_context.is_stale:
            reason_codes.append("stale_reference_rebase")
        if manipulation_assessment.holder_concentration_penalty_pct > 0:
            reason_codes.append("holder_concentration_penalty")
        if manipulation_assessment.thin_market:
            reason_codes.append("low_liquidity_suppression")
        if manipulation_assessment.suspicious_signal_suppression_multiplier < 1.0:
            reason_codes.append("integrity_suppression")
        if trend.direction == "up" and trend.confidence >= 0.35:
            reason_codes.append("seven_day_uptrend")
        if trend.direction == "down" and trend.confidence >= 0.35:
            reason_codes.append("thirty_day_cooldown")
        for candidate_reason in payload.candidate_reasons:
            normalized = self._normalize_lookup_key(candidate_reason)
            if normalized and normalized not in reason_codes:
                reason_codes.append(normalized)
        return tuple(reason_codes)

    def _build_drivers(
        self,
        *,
        payload: PlayerValueInput,
        manipulation_assessment: MarketManipulationAssessment,
        price_band_guard_active: bool,
        reason_codes: tuple[str, ...],
    ) -> tuple[str, ...]:
        drivers: list[str] = []
        if payload.match_events:
            drivers.append("football_truth")
        if any(event.big_moment for event in payload.match_events):
            drivers.append("big_moment")
        if payload.transfer_events:
            drivers.append("transfer_momentum")
        if payload.award_events:
            drivers.append("award_signal")
        if any(payload.demand_signal.eligible_counts().values()):
            drivers.append("market_demand")
        if any(payload.scouting_signal.eligible_counts().values()):
            drivers.append("global_scouting_index")
        if payload.scouting_signal.eligible_counts()["transfer_room_adds"] > 0:
            drivers.append("transfer_room_signal")
        if payload.scouting_signal.eligible_counts()["scouting_activity"] > 0:
            drivers.append("scouting_activity")
        if payload.egame_signal.sample_size() > 0:
            drivers.append("egame_visibility")
        if payload.market_pulse.snapshot_price_credits() is not None:
            drivers.append("market_snapshot")
        if payload.market_pulse.last_trade_price_credits is not None:
            drivers.append("last_trade_ignored")
            drivers.append("last_trade_context")
        if manipulation_assessment.trusted_trade_price_credits is not None:
            drivers.append("trusted_trade_support")
        if manipulation_assessment.shadow_ignored_trade_count > 0:
            drivers.append("shadow_ignored_trades")
        if manipulation_assessment.wash_trade_count > 0:
            drivers.append("wash_trade_detected")
        if manipulation_assessment.circular_trade_count > 0:
            drivers.append("circular_trade_detected")
        if manipulation_assessment.holder_concentration_penalty_pct > 0:
            drivers.append("holder_concentration_penalty")
        if manipulation_assessment.thin_market:
            drivers.append("thin_market")
        if price_band_guard_active:
            drivers.append("price_band_guard")
        if payload.liquidity_band:
            drivers.append(f"liquidity_{self._normalize_lookup_key(payload.liquidity_band)}")
        for reason_code in reason_codes:
            if reason_code not in drivers:
                drivers.append(reason_code)
        return tuple(drivers)

    def _normalize_award_code(self, event: NormalizedAwardEvent) -> str:
        if event.award_code in self.config.award_impacts:
            return event.award_code
        award_name = event.award_name.lower().replace("'", "")
        if "ballon d" in award_name and event.rank == 1:
            return "ballon_dor_winner"
        if "ballon d" in award_name and event.rank is not None and event.rank <= 3:
            return "ballon_dor_top_3"
        if "ballon d" in award_name and event.rank is not None and event.rank <= 10:
            return "ballon_dor_top_10"
        if "ballon d" in award_name and event.rank is not None and event.rank <= 20:
            return "ballon_dor_top_20"
        if "young player" in award_name:
            return "young_player_of_the_season"
        if "player of the season" in award_name:
            return "player_of_the_season"
        if "golden ball" in award_name:
            return "golden_ball"
        if "golden shoe" in award_name:
            return "golden_shoe"
        if "man of the match" in award_name:
            return "man_of_the_match"
        return event.award_code

    def _target_delta_pct(self, source_credits: float, target_credits: float) -> float:
        if source_credits <= 0:
            return 0.0
        return (target_credits - source_credits) / source_credits

    def _age_curve_multiplier(self, age_years: float | None) -> float:
        if age_years is None:
            return 1.0
        if age_years <= 19:
            return 1.06
        if age_years <= 22:
            return 1.12
        if age_years <= 26:
            return 1.18
        if age_years <= 29:
            return 1.14
        if age_years <= 32:
            return 1.00
        if age_years <= 35:
            return 0.84
        return 0.68

    def _event_importance_multiplier(self, event: NormalizedMatchEvent) -> float:
        multiplier = max(self._competition_multiplier(event.competition.name), 1.0)
        stage = event.competition.stage.lower()
        if "final" in stage:
            multiplier *= 1.18
        elif any(label in stage for label in ("semi", "quarter", "knockout", "playoff", "derby")):
            multiplier *= 1.10
        return multiplier

    def _position_family_from_event(self, event: NormalizedMatchEvent, profile: PlayerProfileContext) -> str:
        candidates = [profile.position_subrole or "", profile.position_family, *event.tags]
        for candidate in candidates:
            normalized = self._normalize_lookup_key(candidate)
            if "goal" in normalized:
                return "goalkeeper"
            if "def" in normalized or "back" in normalized:
                return "defender"
            if any(token in normalized for token in ("wing", "forward", "striker", "attack")):
                return "forward"
        return "midfielder"

    def _normalize_position_family(self, value: str | None) -> str:
        normalized = self._normalize_lookup_key(value or "midfielder")
        if "goal" in normalized:
            return "goalkeeper"
        if "def" in normalized or "back" in normalized:
            return "defender"
        if any(token in normalized for token in ("wing", "forward", "striker", "attack")):
            return "forward"
        return "midfielder"

    def _production_goal_weight(self, position_family: str) -> float:
        return {
            "goalkeeper": 0.03,
            "defender": 0.10,
            "midfielder": 0.20,
            "forward": 0.28,
        }[position_family]

    def _production_clean_sheet_weight(self, position_family: str) -> float:
        return {
            "goalkeeper": 0.24,
            "defender": 0.18,
            "midfielder": 0.04,
            "forward": 0.01,
        }[position_family]

    def _production_save_weight(self, position_family: str) -> float:
        return {
            "goalkeeper": 0.22,
            "defender": 0.02,
            "midfielder": 0.00,
            "forward": 0.00,
        }[position_family]

    def _diminishing_count(self, value: int) -> float:
        if value <= 0:
            return 0.0
        return min(value, 4) ** 0.92

    def _diminishing_ratio(self, value: int, cap: float) -> float:
        if cap <= 0 or value <= 0:
            return 0.0
        normalized = min(value / cap, 1.0)
        return normalized ** 0.85

    def _clamp(self, value: float, movement_cap: float) -> float:
        return max(-movement_cap, min(movement_cap, value))

    def _relative_gap(self, left_value: float, right_value: float) -> float:
        baseline = max(min(abs(left_value), abs(right_value)), 1.0)
        return abs(left_value - right_value) / baseline

    def _normalize_lookup_key(self, value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")
