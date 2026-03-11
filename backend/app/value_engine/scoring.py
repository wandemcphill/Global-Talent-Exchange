from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from backend.app.ingestion.models import NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent

from .config import ValueEngineConfig, get_value_engine_config
from .models import (
    DemandSignal,
    MarketPulse,
    PlayerValueInput,
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
        baseline_credits = credits_from_real_world_value(
            payload.reference_market_value_eur,
            eur_per_credit=self.config.baseline_eur_per_credit,
        )
        floor_from_baseline = baseline_credits * self.config.minimum_floor_ratio

        previous_ftv_credits = payload.previous_ftv_credits if payload.previous_ftv_credits is not None else baseline_credits
        previous_ftv_credits = max(previous_ftv_credits, floor_from_baseline)

        anchor_adjustment_pct = self._anchor_adjustment(previous_ftv_credits, baseline_credits)
        performance_adjustment_pct = self._score_matches(payload.match_events)
        transfer_adjustment_pct = self._score_transfers(payload.transfer_events, payload.reference_market_value_eur)
        award_adjustment_pct = self._score_awards(payload.award_events)

        truth_uncapped_adjustment_pct = (
            anchor_adjustment_pct
            + performance_adjustment_pct
            + transfer_adjustment_pct
            + award_adjustment_pct
        )
        truth_capped_adjustment_pct = self._clamp(truth_uncapped_adjustment_pct, self.config.daily_movement_cap)
        truth_movement_pct = truth_capped_adjustment_pct * self.config.smoothing_factor
        football_truth_value_credits = round(
            max(
                previous_ftv_credits * (1.0 + truth_movement_pct),
                floor_from_baseline,
            ),
            2,
        )

        demand_adjustment_pct = self._score_demand(payload.demand_signal)
        manipulation_assessment = self._assess_market_manipulation(
            payload.market_pulse,
            football_truth_value_credits=football_truth_value_credits,
        )
        market_snapshot_price_credits = self._resolve_market_snapshot_price(
            payload.market_pulse,
            manipulation_assessment,
        )
        market_price_adjustment_pct = self._score_market_price(
            football_truth_value_credits,
            market_snapshot_price_credits,
        )
        liquidity_weight = self._resolve_liquidity_weight(payload.liquidity_band)
        anti_manipulation_guard_multiplier = self._resolve_market_guard_multiplier(
            payload.market_pulse,
            manipulation_assessment,
        )
        market_signal_adjustment_pct = self._clamp(
            (demand_adjustment_pct + market_price_adjustment_pct)
            * liquidity_weight
            * anti_manipulation_guard_multiplier,
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
        blended_target_credits = round(
            (football_truth_value_credits * self.config.ftv_weight)
            + (market_signal_value_credits * self.config.msv_weight),
            2,
        )
        price_band_limit = self._resolve_price_band_limit(payload.liquidity_band)
        price_band_floor_credits = round(
            football_truth_value_credits * price_band_limit.min_ratio,
            2,
        )
        price_band_ceiling_credits = round(
            football_truth_value_credits * price_band_limit.max_ratio,
            2,
        )
        band_limited_target_credits = round(
            min(max(blended_target_credits, price_band_floor_credits), price_band_ceiling_credits),
            2,
        )

        previous_published_credits = self._resolve_previous_published_credits(payload, football_truth_value_credits)
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
        price_band_guard_active = band_limited_target_credits != blended_target_credits

        return ValueSnapshot(
            player_id=payload.player_id,
            player_name=payload.player_name,
            as_of=payload.as_of,
            previous_credits=round(previous_published_credits, 2),
            target_credits=target_credits,
            movement_pct=round(smoothed_adjustment_pct, 4),
            football_truth_value_credits=football_truth_value_credits,
            market_signal_value_credits=market_signal_value_credits,
            previous_global_scouting_index=gsi_snapshot.previous_score,
            global_scouting_index=gsi_snapshot.target_score,
            global_scouting_index_movement_pct=gsi_snapshot.movement_pct,
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
                holder_concentration_penalty_pct=round(
                    manipulation_assessment.holder_concentration_penalty_pct,
                    4,
                ),
                thin_market=manipulation_assessment.thin_market,
            ),
            global_scouting_index_breakdown=gsi_snapshot.breakdown,
            drivers=self._build_drivers(
                payload,
                manipulation_assessment,
                price_band_guard_active=price_band_guard_active,
            ),
        )

    def _resolve_previous_published_credits(self, payload: PlayerValueInput, football_truth_value_credits: float) -> float:
        previous_published_credits = payload.previous_pcv_credits
        if previous_published_credits is None:
            previous_published_credits = payload.current_credits
        if previous_published_credits is None:
            previous_published_credits = football_truth_value_credits
        return max(previous_published_credits, football_truth_value_credits * self.config.minimum_floor_ratio)

    def _anchor_adjustment(self, previous_credits: float, baseline_credits: float) -> float:
        if previous_credits <= 0:
            return 0.0
        return ((baseline_credits - previous_credits) / previous_credits) * self.config.anchor_pull_strength

    def _score_matches(self, events: tuple[NormalizedMatchEvent, ...]) -> float:
        points = sum(self._match_points(event) for event in events)
        return points / self.config.performance_scale

    def _match_points(self, event: NormalizedMatchEvent) -> float:
        minutes_factor = min(max(event.minutes / 90.0, 0.25 if (event.goals or event.assists) else 0.0), 1.0)
        rating_component = (event.rating - 6.5) * 7.0
        stat_component = (event.goals * 10.0) + (event.assists * 7.0) + (4.0 if event.clean_sheet else 0.0)
        save_component = min(event.saves, 8) * 0.6
        competition_multiplier = self._competition_multiplier(event.competition.name)
        points = (rating_component + stat_component + save_component) * competition_multiplier * minutes_factor
        if event.big_moment:
            points += self.config.big_moment_bonus
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
                "completed": 14.0,
                "agreed": 9.0,
                "advanced": 6.0,
                "rumour": 3.0,
            }.get(event.status.lower(), 3.0)
            destination_multiplier = self._competition_multiplier(event.to_competition or "")
            fee_ratio = 0.0
            if event.reported_fee_eur is not None:
                fee_ratio = min(event.reported_fee_eur / denominator, 2.0)
            points += (status_weight + (fee_ratio * 12.0)) * max(destination_multiplier, 1.0)
        return points / self.config.transfer_scale

    def _score_awards(self, events: tuple[NormalizedAwardEvent, ...]) -> float:
        points = 0.0
        for event in events:
            award_code = self._normalize_award_code(event)
            points += self.config.award_impacts.get(award_code, 0.0)
        return points / self.config.award_scale

    def _score_demand(self, signal: DemandSignal) -> float:
        weighted_sum = 0.0
        for key, eligible_count in signal.eligible_counts().items():
            if key not in PRICE_RELEVANT_DEMAND_KEYS:
                continue
            weighted_sum += eligible_count * self.config.demand_weights[key]
        movement = weighted_sum / self.config.demand_scale
        return min(movement, self.config.demand_movement_cap)

    def _score_market_price(self, football_truth_value_credits: float, snapshot_market_price: float | None) -> float:
        if snapshot_market_price is None or football_truth_value_credits <= 0:
            return 0.0
        return (
            ((snapshot_market_price - football_truth_value_credits) / football_truth_value_credits)
            * self.config.market_price_pull_strength
        )

    def _build_drivers(
        self,
        payload: PlayerValueInput,
        manipulation_assessment: MarketManipulationAssessment,
        *,
        price_band_guard_active: bool,
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
        if payload.market_pulse.snapshot_price_credits() is not None:
            drivers.append("market_snapshot")
        if payload.market_pulse.last_trade_price_credits is not None:
            drivers.append("last_trade_ignored")
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
        return tuple(drivers)

    def _assess_market_manipulation(
        self,
        market_pulse: MarketPulse,
        *,
        football_truth_value_credits: float,
    ) -> MarketManipulationAssessment:
        quoted_market_price = market_pulse.snapshot_price_credits()
        trade_prints = tuple(
            sorted(
                market_pulse.trade_prints,
                key=lambda trade: (trade.occurred_at, trade.trade_id),
            )
        )
        shadow_ignored_trade_ids = {trade.trade_id for trade in trade_prints if trade.shadow_ignored}
        wash_trade_ids = self._detect_wash_trades(trade_prints)
        circular_trade_ids = self._detect_circular_trades(trade_prints)
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
            trade_trust_score = round(
                sum(trusted_trade_weights.values()) / len(trade_prints),
                4,
            )

        holder_concentration_penalty_pct = self._holder_concentration_penalty(market_pulse)
        thin_market = self._is_thin_market(
            market_pulse,
            trusted_trade_count=len(trusted_trade_weights),
            unique_trade_participants=len(participant_ids),
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
        blend_weight = 0.25 + (manipulation_assessment.trade_trust_score * 0.75)
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
        if (
            market_pulse.best_bid_price_credits is not None
            and market_pulse.best_bid_price_credits > 0
            and market_pulse.best_ask_price_credits is not None
            and market_pulse.best_ask_price_credits > market_pulse.best_bid_price_credits
        ):
            quoted_market_price = market_pulse.snapshot_price_credits()
            if quoted_market_price is not None:
                spread_pct = (
                    (market_pulse.best_ask_price_credits - market_pulse.best_bid_price_credits)
                    / quoted_market_price
                )
                if spread_pct > 0.18:
                    return True
        return False

    def _competition_multiplier(self, competition_name: str) -> float:
        return self.config.competition_multipliers.get(competition_name.lower(), 1.0)

    def _resolve_liquidity_weight(self, liquidity_band: str | None) -> float:
        if liquidity_band is None:
            return self.config.default_liquidity_weight
        lookup_key = self._normalize_lookup_key(liquidity_band)
        return self.config.liquidity_band_market_weights.get(lookup_key, self.config.default_liquidity_weight)

    def _resolve_price_band_limit(self, liquidity_band: str | None):
        lookup_key = self._normalize_lookup_key(liquidity_band) if liquidity_band is not None else "default"
        price_band_lookup = {limit.code: limit for limit in self.config.price_band_limits}
        return price_band_lookup.get(lookup_key) or price_band_lookup.get("default") or self.config.price_band_limits[0]

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

    def _clamp(self, value: float, movement_cap: float) -> float:
        return max(-movement_cap, min(movement_cap, value))

    def _relative_gap(self, left_value: float, right_value: float) -> float:
        baseline = max(min(abs(left_value), abs(right_value)), 1.0)
        return abs(left_value - right_value) / baseline

    def _normalize_lookup_key(self, value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")
