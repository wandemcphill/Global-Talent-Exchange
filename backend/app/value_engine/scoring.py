from __future__ import annotations

from dataclasses import dataclass

from backend.app.ingestion.models import NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent

from .config import ValueEngineConfig
from .models import DemandSignal, PlayerValueInput, ValueBreakdown, ValueSnapshot


def credits_from_real_world_value(real_world_value_eur: float, eur_per_credit: int = 100_000) -> float:
    if real_world_value_eur <= 0:
        return 0.0
    return round(real_world_value_eur / eur_per_credit, 2)


@dataclass(slots=True)
class ValueEngine:
    config: ValueEngineConfig = ValueEngineConfig()

    def build_snapshot(self, payload: PlayerValueInput) -> ValueSnapshot:
        baseline_credits = credits_from_real_world_value(
            payload.reference_market_value_eur,
            eur_per_credit=self.config.baseline_eur_per_credit,
        )
        previous_credits = payload.current_credits if payload.current_credits is not None else baseline_credits
        previous_credits = max(previous_credits, baseline_credits * self.config.minimum_floor_ratio)

        anchor_adjustment_pct = self._anchor_adjustment(previous_credits, baseline_credits)
        performance_adjustment_pct = self._score_matches(payload.match_events)
        transfer_adjustment_pct = self._score_transfers(payload.transfer_events, payload.reference_market_value_eur)
        award_adjustment_pct = self._score_awards(payload.award_events)
        demand_adjustment_pct = self._score_demand(payload.demand_signal)

        uncapped_adjustment_pct = (
            anchor_adjustment_pct
            + performance_adjustment_pct
            + transfer_adjustment_pct
            + award_adjustment_pct
            + demand_adjustment_pct
        )
        capped_adjustment_pct = max(
            -self.config.daily_movement_cap,
            min(self.config.daily_movement_cap, uncapped_adjustment_pct),
        )
        smoothed_adjustment_pct = capped_adjustment_pct * self.config.smoothing_factor
        target_credits = round(
            max(previous_credits * (1.0 + smoothed_adjustment_pct), baseline_credits * self.config.minimum_floor_ratio),
            2,
        )

        return ValueSnapshot(
            player_id=payload.player_id,
            player_name=payload.player_name,
            as_of=payload.as_of,
            previous_credits=round(previous_credits, 2),
            target_credits=target_credits,
            movement_pct=round(smoothed_adjustment_pct, 4),
            breakdown=ValueBreakdown(
                baseline_credits=baseline_credits,
                anchor_adjustment_pct=round(anchor_adjustment_pct, 4),
                performance_adjustment_pct=round(performance_adjustment_pct, 4),
                transfer_adjustment_pct=round(transfer_adjustment_pct, 4),
                award_adjustment_pct=round(award_adjustment_pct, 4),
                demand_adjustment_pct=round(demand_adjustment_pct, 4),
                uncapped_adjustment_pct=round(uncapped_adjustment_pct, 4),
                capped_adjustment_pct=round(capped_adjustment_pct, 4),
            ),
            drivers=self._build_drivers(payload),
        )

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
            weighted_sum += eligible_count * self.config.demand_weights[key]
        movement = weighted_sum / self.config.demand_scale
        return min(movement, self.config.demand_movement_cap)

    def _build_drivers(self, payload: PlayerValueInput) -> tuple[str, ...]:
        drivers: list[str] = []
        if payload.match_events:
            drivers.append("match_performance")
        if any(event.big_moment for event in payload.match_events):
            drivers.append("big_moment")
        if payload.transfer_events:
            drivers.append("transfer_momentum")
        if payload.award_events:
            drivers.append("award_signal")
        if any(payload.demand_signal.eligible_counts().values()):
            drivers.append("market_demand")
        return tuple(drivers)

    def _competition_multiplier(self, competition_name: str) -> float:
        return self.config.competition_multipliers.get(competition_name.lower(), 1.0)

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
