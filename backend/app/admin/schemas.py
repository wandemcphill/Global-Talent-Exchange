from __future__ import annotations

from dataclasses import replace

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.core.config import (
    LiquidityBand,
    LiquidityBandsConfig,
    PriceBandLimit,
    SupplyTier,
    SupplyTiersConfig,
    SuspicionThresholdsConfig,
    ValueEngineWeightingConfig,
)


class SupplyTierConfigItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    min_score: float = Field(ge=0)
    max_score: float = Field(ge=0)
    target_share: float = Field(gt=0)
    circulating_supply: int = Field(gt=0)
    daily_pack_supply: int = Field(ge=0)
    season_mint_cap: int = Field(gt=0)

    def to_domain(self) -> SupplyTier:
        return SupplyTier(
            code=self.code,
            name=self.name,
            min_score=self.min_score,
            max_score=self.max_score,
            target_share=self.target_share,
            circulating_supply=self.circulating_supply,
            daily_pack_supply=self.daily_pack_supply,
            season_mint_cap=self.season_mint_cap,
        )


class SupplyTierConfigPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tiers: list[SupplyTierConfigItem] = Field(min_length=1)

    def to_domain(self) -> SupplyTiersConfig:
        return SupplyTiersConfig(tiers=tuple(item.to_domain() for item in self.tiers))


class LiquidityBandConfigItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    min_price_credits: int = Field(ge=0)
    max_price_credits: int | None = Field(default=None, ge=0)
    max_spread_bps: int = Field(gt=0)
    maker_inventory_target: int = Field(gt=0)
    instant_sell_fee_bps: int = Field(ge=0)

    def to_domain(self) -> LiquidityBand:
        return LiquidityBand(
            code=self.code,
            name=self.name,
            min_price_credits=self.min_price_credits,
            max_price_credits=self.max_price_credits,
            max_spread_bps=self.max_spread_bps,
            maker_inventory_target=self.maker_inventory_target,
            instant_sell_fee_bps=self.instant_sell_fee_bps,
        )


class LiquidityBandConfigPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bands: list[LiquidityBandConfigItem] = Field(min_length=1)

    def to_domain(self) -> LiquidityBandsConfig:
        return LiquidityBandsConfig(bands=tuple(item.to_domain() for item in self.bands))


class SuspicionThresholdsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_min_suspicious_events: int = Field(gt=0)
    player_min_suspicious_share: float = Field(gt=0, le=1)
    player_price_band_breach_ratio: float = Field(ge=0)
    cluster_min_member_count: int = Field(ge=2)
    cluster_min_interaction_count: int = Field(gt=0)
    cluster_max_asset_count: int = Field(gt=0)
    thin_market_min_price_credits: int = Field(ge=0)
    thin_market_max_pending_offers: int = Field(ge=0)
    thin_market_max_active_trade_intents: int = Field(ge=0)
    holder_concentration_min_assets: int = Field(gt=0)
    holder_concentration_share: float = Field(gt=0, le=1)
    circular_trade_min_cycle_length: int = Field(ge=2)
    circular_trade_min_repetitions: int = Field(gt=0)

    def to_domain(self) -> SuspicionThresholdsConfig:
        return SuspicionThresholdsConfig(**self.model_dump())


class FtvMsvBlendWeightsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ftv_weight: float = Field(ge=0, le=1)
    msv_weight: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total_weight(self) -> "FtvMsvBlendWeightsPayload":
        total = round(self.ftv_weight + self.msv_weight, 6)
        if abs(total - 1.0) > 0.001:
            raise ValueError("FTV/MSV blend weights must sum to 1.0.")
        return self


class PriceBandLimitPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(min_length=1)
    min_ratio: float = Field(gt=0)
    max_ratio: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "PriceBandLimitPayload":
        if self.max_ratio < self.min_ratio:
            raise ValueError("max_ratio must be greater than or equal to min_ratio.")
        return self

    def to_domain(self) -> PriceBandLimit:
        return PriceBandLimit(
            code=self.code,
            min_ratio=self.min_ratio,
            max_ratio=self.max_ratio,
        )


class ValueControlsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ftv_msv_blend_weights: FtvMsvBlendWeightsPayload
    price_band_limits: list[PriceBandLimitPayload] = Field(min_length=1)

    def merge_into(self, current: ValueEngineWeightingConfig) -> ValueEngineWeightingConfig:
        return replace(
            current,
            ftv_weight=self.ftv_msv_blend_weights.ftv_weight,
            msv_weight=self.ftv_msv_blend_weights.msv_weight,
            price_band_limits=tuple(item.to_domain() for item in self.price_band_limits),
        )
