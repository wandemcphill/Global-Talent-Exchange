from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os
from typing import Mapping


AMOUNT_QUANTUM = Decimal("0.0001")


def _decimal(environ: Mapping[str, str], name: str, default: str) -> Decimal:
    raw_value = environ.get(name, default)
    try:
        return Decimal(str(raw_value)).quantize(AMOUNT_QUANTUM)
    except Exception:
        return Decimal(default).quantize(AMOUNT_QUANTUM)


def _fraction(environ: Mapping[str, str], name: str, default: str) -> Decimal:
    value = _decimal(environ, name, default)
    if value < Decimal("0.0000"):
        return Decimal("0.0000")
    if value > Decimal("1.0000"):
        return Decimal("1.0000")
    return value


def _integer(environ: Mapping[str, str], name: str, default: int, *, minimum: int = 0) -> int:
    raw_value = environ.get(name)
    try:
        resolved = int(raw_value) if raw_value is not None else default
    except ValueError:
        resolved = default
    return max(minimum, resolved)


@dataclass(frozen=True, slots=True)
class GtexSettings:
    jackpot_threshold_amount: Decimal
    jackpot_probability_limit: Decimal
    jackpot_probability_cap: Decimal
    jackpot_failsafe_hours: int
    jackpot_contribution_rate: Decimal
    jackpot_distribution_mode: str
    jackpot_top_split_percent: Decimal
    jackpot_min_activity_score: Decimal
    creator_default_base_price: Decimal
    creator_win_rate_multiplier: Decimal
    creator_demand_multiplier: Decimal
    creator_momentum_multiplier: Decimal
    creator_trade_cooldown_seconds: int
    creator_max_ownership_ratio: Decimal
    creator_anomaly_window_seconds: int
    creator_anomaly_notional_threshold: Decimal
    creator_price_floor: Decimal
    creator_price_ceiling_multiplier: Decimal
    creator_trending_limit: int
    ai_queue_timeout_seconds: int
    ai_match_stream_block_ms: int
    ai_simulation_event_count: int
    ai_recent_pair_window_minutes: int
    ai_default_entry_fee: Decimal
    ai_ranked_k_factor: int
    leaderboard_size: int
    worker_poll_interval_seconds: float


def load_gtex_settings(environ: Mapping[str, str] | None = None) -> GtexSettings:
    resolved_environ = dict(os.environ if environ is None else environ)
    return GtexSettings(
        jackpot_threshold_amount=_decimal(resolved_environ, "GTEX_JACKPOT_THRESHOLD_AMOUNT", "500.0000"),
        jackpot_probability_limit=_decimal(resolved_environ, "GTEX_JACKPOT_PROBABILITY_LIMIT", "1000.0000"),
        jackpot_probability_cap=_fraction(resolved_environ, "GTEX_JACKPOT_PROBABILITY_CAP", "0.5000"),
        jackpot_failsafe_hours=_integer(resolved_environ, "GTEX_JACKPOT_FAILSAFE_HOURS", 6, minimum=1),
        jackpot_contribution_rate=_fraction(resolved_environ, "GTEX_JACKPOT_CONTRIBUTION_RATE", "0.1000"),
        jackpot_distribution_mode=(resolved_environ.get("GTEX_JACKPOT_DISTRIBUTION_MODE", "single_winner").strip() or "single_winner"),
        jackpot_top_split_percent=_fraction(resolved_environ, "GTEX_JACKPOT_TOP_SPLIT_PERCENT", "0.1000"),
        jackpot_min_activity_score=_decimal(resolved_environ, "GTEX_JACKPOT_MIN_ACTIVITY_SCORE", "1.0000"),
        creator_default_base_price=_decimal(resolved_environ, "GTEX_CREATOR_DEFAULT_BASE_PRICE", "100.0000"),
        creator_win_rate_multiplier=_decimal(resolved_environ, "GTEX_CREATOR_WIN_RATE_MULTIPLIER", "125.0000"),
        creator_demand_multiplier=_decimal(resolved_environ, "GTEX_CREATOR_DEMAND_MULTIPLIER", "2.5000"),
        creator_momentum_multiplier=_decimal(resolved_environ, "GTEX_CREATOR_MOMENTUM_MULTIPLIER", "5.0000"),
        creator_trade_cooldown_seconds=_integer(
            resolved_environ,
            "GTEX_CREATOR_TRADE_COOLDOWN_SECONDS",
            5,
            minimum=0,
        ),
        creator_max_ownership_ratio=_fraction(resolved_environ, "GTEX_CREATOR_MAX_OWNERSHIP_RATIO", "0.2500"),
        creator_anomaly_window_seconds=_integer(
            resolved_environ,
            "GTEX_CREATOR_ANOMALY_WINDOW_SECONDS",
            300,
            minimum=30,
        ),
        creator_anomaly_notional_threshold=_decimal(
            resolved_environ,
            "GTEX_CREATOR_ANOMALY_NOTIONAL_THRESHOLD",
            "10000.0000",
        ),
        creator_price_floor=_decimal(resolved_environ, "GTEX_CREATOR_PRICE_FLOOR", "10.0000"),
        creator_price_ceiling_multiplier=_decimal(
            resolved_environ,
            "GTEX_CREATOR_PRICE_CEILING_MULTIPLIER",
            "25.0000",
        ),
        creator_trending_limit=_integer(resolved_environ, "GTEX_CREATOR_TRENDING_LIMIT", 20, minimum=1),
        ai_queue_timeout_seconds=_integer(resolved_environ, "GTEX_AI_QUEUE_TIMEOUT_SECONDS", 15, minimum=1),
        ai_match_stream_block_ms=_integer(resolved_environ, "GTEX_AI_MATCH_STREAM_BLOCK_MS", 1000, minimum=100),
        ai_simulation_event_count=_integer(resolved_environ, "GTEX_AI_SIMULATION_EVENT_COUNT", 12, minimum=4),
        ai_recent_pair_window_minutes=_integer(resolved_environ, "GTEX_AI_RECENT_PAIR_WINDOW_MINUTES", 30, minimum=1),
        ai_default_entry_fee=_decimal(resolved_environ, "GTEX_AI_DEFAULT_ENTRY_FEE", "25.0000"),
        ai_ranked_k_factor=_integer(resolved_environ, "GTEX_AI_RANKED_K_FACTOR", 32, minimum=8),
        leaderboard_size=_integer(resolved_environ, "GTEX_LEADERBOARD_SIZE", 100, minimum=10),
        worker_poll_interval_seconds=max(
            0.2,
            float(resolved_environ.get("GTEX_WORKER_POLL_INTERVAL_SECONDS", "1.0") or "1.0"),
        ),
    )


__all__ = ["AMOUNT_QUANTUM", "GtexSettings", "load_gtex_settings"]
