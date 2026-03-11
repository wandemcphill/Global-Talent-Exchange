from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SuspiciousPlayerAlertView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    as_of: datetime
    supply_tier: str | None
    liquidity_band: str | None
    suspicious_events: int
    total_events: int
    suspicious_share: float
    football_truth_value_credits: float
    market_signal_value_credits: float
    target_credits: float
    market_signal_ratio: float
    price_band_code: str
    price_band_min_ratio: float
    price_band_max_ratio: float
    price_band_breach_ratio: float
    reasons: tuple[str, ...]


class SuspiciousClusterAlertView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cluster_id: str
    member_user_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    interaction_count: int
    repeated_pair_count: int
    has_cycle: bool
    reasons: tuple[str, ...]


class ThinMarketAlertView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    ask_price: int | None
    best_offer_price: int | None
    pending_offer_count: int
    active_trade_intent_count: int
    reasons: tuple[str, ...]


class HolderConcentrationAlertView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holder_user_id: str
    observed_asset_count: int
    observed_holder_share: float
    asset_ids: tuple[str, ...]
    reasons: tuple[str, ...]


class CircularTradeAlertView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    cycle_user_ids: tuple[str, ...]
    cycle_length: int
    repetition_count: int
    trade_count: int
    accepted_offer_ids: tuple[str, ...]
    reasons: tuple[str, ...]
