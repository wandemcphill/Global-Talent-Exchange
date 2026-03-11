from __future__ import annotations

from dataclasses import dataclass, field


def _competition_multipliers() -> dict[str, float]:
    return {
        "world cup": 1.35,
        "uefa club championship": 1.30,
        "afcon": 1.25,
        "copa america": 1.25,
        "euros": 1.25,
        "league a": 1.20,
        "league b": 1.10,
        "league c": 1.05,
    }


def _award_impacts() -> dict[str, float]:
    return {
        "ballon_dor_winner": 82.0,
        "ballon_dor_top_3": 56.0,
        "ballon_dor_top_10": 32.0,
        "ballon_dor_top_20": 16.0,
        "player_of_the_season": 34.0,
        "young_player_of_the_season": 28.0,
        "golden_ball": 30.0,
        "golden_shoe": 26.0,
        "u20_golden": 24.0,
        "u20_silver": 18.0,
        "u20_bronze": 12.0,
        "u17_golden": 18.0,
        "u17_silver": 12.0,
        "u17_bronze": 8.0,
        "man_of_the_match": 6.0,
    }


def _demand_weights() -> dict[str, float]:
    return {
        "purchases": 6.0,
        "sales": 5.0,
        "shortlist_adds": 2.5,
        "watchlist_adds": 1.0,
        "follows": 0.5,
    }


@dataclass(frozen=True, slots=True)
class ValueEngineConfig:
    baseline_eur_per_credit: int = 100_000
    smoothing_factor: float = 0.70
    daily_movement_cap: float = 0.12
    demand_movement_cap: float = 0.05
    anchor_pull_strength: float = 0.20
    minimum_floor_ratio: float = 0.60
    performance_scale: float = 850.0
    award_scale: float = 600.0
    transfer_scale: float = 900.0
    demand_scale: float = 1200.0
    big_moment_bonus: float = 18.0
    competition_multipliers: dict[str, float] = field(default_factory=_competition_multipliers)
    award_impacts: dict[str, float] = field(default_factory=_award_impacts)
    demand_weights: dict[str, float] = field(default_factory=_demand_weights)
