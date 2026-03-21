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
    ValueWeightProfile,
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


class ComponentWeightsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ftv_weight: float = Field(ge=0, le=1)
    msv_weight: float = Field(ge=0, le=1)
    sgv_weight: float = Field(ge=0, le=1)
    egv_weight: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total_weight(self) -> "ComponentWeightsPayload":
        total = round(self.ftv_weight + self.msv_weight + self.sgv_weight + self.egv_weight, 6)
        if total <= 0 or total > 1.001:
            raise ValueError("Component weights must sum to more than 0 and no more than 1.0.")
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


class MovementCapsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    daily_movement_cap: float = Field(gt=0, le=1)
    demand_movement_cap: float = Field(gt=0, le=1)
    momentum_cap: float = Field(gt=0, le=1)


class InfluenceCapsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market_signal_cap: float = Field(gt=0, le=1)
    scouting_signal_cap: float = Field(gt=0, le=1)
    egame_signal_cap: float = Field(gt=0, le=1)
    low_liquidity_penalty: float = Field(ge=0, le=1)
    suspicious_trade_penalty: float = Field(ge=0, le=1)


class MomentumSettingsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_window_days: int = Field(gt=0)
    medium_window_days: int = Field(gt=0)
    short_sensitivity: float = Field(ge=0, le=1)
    medium_sensitivity: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_windows(self) -> "MomentumSettingsPayload":
        if self.medium_window_days < self.short_window_days:
            raise ValueError("medium_window_days must be greater than or equal to short_window_days.")
        return self


class ReferenceStalenessPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stale_days: int = Field(gt=0)
    very_stale_days: int = Field(gt=0)
    stale_blend: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_windows(self) -> "ReferenceStalenessPayload":
        if self.very_stale_days < self.stale_days:
            raise ValueError("very_stale_days must be greater than or equal to stale_days.")
        return self


class EngineTuningPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    baseline_eur_per_credit: int = Field(gt=0)
    smoothing_factor: float = Field(gt=0, le=1)
    anchor_pull_strength: float = Field(ge=0, le=1)
    market_price_pull_strength: float = Field(ge=0, le=1)
    default_liquidity_weight: float = Field(ge=0, le=1)
    minimum_floor_ratio: float = Field(gt=0, le=1)
    participant_diversity_scale: float = Field(gt=0)
    order_book_wide_spread_bps: int = Field(gt=0)
    performance_scale: float = Field(gt=0)
    award_scale: float = Field(gt=0)
    transfer_scale: float = Field(gt=0)
    demand_scale: float = Field(gt=0)
    scouting_scale: float = Field(gt=0)
    egame_scale: float = Field(gt=0)
    big_moment_bonus: float = Field(ge=0)
    gsi_neutral_score: float = Field(ge=0, le=100)
    gsi_smoothing_factor: float = Field(gt=0, le=1)
    gsi_daily_movement_cap: float = Field(gt=0)
    gsi_signal_cap: float = Field(gt=0)
    gsi_signal_scale: float = Field(gt=0)
    gsi_anchor_pull_strength: float = Field(ge=0)


class ValueWeightProfilePayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(min_length=1)
    description: str = Field(min_length=1)
    liquidity_tiers: list[str] = Field(default_factory=list)
    confidence_tiers: list[str] = Field(default_factory=list)
    player_classes: list[str] = Field(default_factory=list)
    ftv_weight: float = Field(ge=0, le=1)
    msv_weight: float = Field(ge=0, le=1)
    sgv_weight: float = Field(ge=0, le=1)
    egv_weight: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total_weight(self) -> "ValueWeightProfilePayload":
        total = round(self.ftv_weight + self.msv_weight + self.sgv_weight + self.egv_weight, 6)
        if total <= 0 or total > 1.001:
            raise ValueError("Weight profile components must sum to more than 0 and no more than 1.0.")
        return self

    def to_domain(self) -> ValueWeightProfile:
        return ValueWeightProfile(
            code=self.code,
            description=self.description,
            liquidity_tiers=tuple(item for item in self.liquidity_tiers if item),
            confidence_tiers=tuple(item for item in self.confidence_tiers if item),
            player_classes=tuple(item for item in self.player_classes if item),
            ftv_weight=self.ftv_weight,
            msv_weight=self.msv_weight,
            sgv_weight=self.sgv_weight,
            egv_weight=self.egv_weight,
        )


class ValueControlsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_version: str | None = None
    component_weights: ComponentWeightsPayload | None = None
    ftv_msv_blend_weights: FtvMsvBlendWeightsPayload | None = None
    movement_caps: MovementCapsPayload | None = None
    influence_caps: InfluenceCapsPayload | None = None
    momentum_settings: MomentumSettingsPayload | None = None
    reference_staleness: ReferenceStalenessPayload | None = None
    engine_tuning: EngineTuningPayload | None = None
    price_band_limits: list[PriceBandLimitPayload] | None = None
    liquidity_band_market_weights: dict[str, float] | None = None
    gsi_signal_weights: dict[str, float] | None = None
    egame_signal_weights: dict[str, float] | None = None
    competition_multipliers: dict[str, float] | None = None
    award_impacts: dict[str, float] | None = None
    weight_profiles: list[ValueWeightProfilePayload] | None = None

    @model_validator(mode="after")
    def validate_legacy_weights_match_components(self) -> "ValueControlsPayload":
        if self.component_weights is None or self.ftv_msv_blend_weights is None:
            return self
        legacy_total = self.component_weights.ftv_weight + self.component_weights.msv_weight
        if legacy_total <= 0:
            raise ValueError("component_weights ftv/msv total must remain positive when ftv_msv_blend_weights are provided.")
        normalized_ftv = self.component_weights.ftv_weight / legacy_total
        normalized_msv = self.component_weights.msv_weight / legacy_total
        if abs(normalized_ftv - self.ftv_msv_blend_weights.ftv_weight) > 0.001:
            raise ValueError("component_weights.ftv_weight must match ftv_msv_blend_weights.ftv_weight when both are provided.")
        if abs(normalized_msv - self.ftv_msv_blend_weights.msv_weight) > 0.001:
            raise ValueError("component_weights.msv_weight must match ftv_msv_blend_weights.msv_weight when both are provided.")
        return self

    @classmethod
    def from_domain(cls, config: ValueEngineWeightingConfig) -> "ValueControlsPayload":
        legacy_total = max(config.ftv_weight + config.msv_weight, 0.0001)
        return cls(
            config_version=config.config_version,
            component_weights=ComponentWeightsPayload(
                ftv_weight=config.ftv_weight,
                msv_weight=config.msv_weight,
                sgv_weight=config.sgv_weight,
                egv_weight=config.egv_weight,
            ),
            ftv_msv_blend_weights=FtvMsvBlendWeightsPayload(
                ftv_weight=config.ftv_weight / legacy_total,
                msv_weight=config.msv_weight / legacy_total,
            ),
            movement_caps=MovementCapsPayload(
                daily_movement_cap=config.daily_movement_cap,
                demand_movement_cap=config.demand_movement_cap,
                momentum_cap=config.momentum_cap,
            ),
            influence_caps=InfluenceCapsPayload(
                market_signal_cap=config.market_signal_cap,
                scouting_signal_cap=config.scouting_signal_cap,
                egame_signal_cap=config.egame_signal_cap,
                low_liquidity_penalty=config.low_liquidity_penalty,
                suspicious_trade_penalty=config.suspicious_trade_penalty,
            ),
            momentum_settings=MomentumSettingsPayload(
                short_window_days=config.momentum_short_window_days,
                medium_window_days=config.momentum_medium_window_days,
                short_sensitivity=config.momentum_short_sensitivity,
                medium_sensitivity=config.momentum_medium_sensitivity,
            ),
            reference_staleness=ReferenceStalenessPayload(
                stale_days=config.reference_stale_days,
                very_stale_days=config.reference_very_stale_days,
                stale_blend=config.reference_stale_blend,
            ),
            engine_tuning=EngineTuningPayload(
                baseline_eur_per_credit=config.baseline_eur_per_credit,
                smoothing_factor=config.smoothing_factor,
                anchor_pull_strength=config.anchor_pull_strength,
                market_price_pull_strength=config.market_price_pull_strength,
                default_liquidity_weight=config.default_liquidity_weight,
                minimum_floor_ratio=config.minimum_floor_ratio,
                participant_diversity_scale=config.participant_diversity_scale,
                order_book_wide_spread_bps=config.order_book_wide_spread_bps,
                performance_scale=config.performance_scale,
                award_scale=config.award_scale,
                transfer_scale=config.transfer_scale,
                demand_scale=config.demand_scale,
                scouting_scale=config.scouting_scale,
                egame_scale=config.egame_scale,
                big_moment_bonus=config.big_moment_bonus,
                gsi_neutral_score=config.gsi_neutral_score,
                gsi_smoothing_factor=config.gsi_smoothing_factor,
                gsi_daily_movement_cap=config.gsi_daily_movement_cap,
                gsi_signal_cap=config.gsi_signal_cap,
                gsi_signal_scale=config.gsi_signal_scale,
                gsi_anchor_pull_strength=config.gsi_anchor_pull_strength,
            ),
            price_band_limits=[PriceBandLimitPayload.model_validate(item) for item in config.price_band_limits],
            liquidity_band_market_weights=dict(config.liquidity_band_market_weights),
            gsi_signal_weights=dict(config.gsi_signal_weights),
            egame_signal_weights=dict(config.egame_signal_weights),
            competition_multipliers=dict(config.competition_multipliers),
            award_impacts=dict(config.award_impacts),
            weight_profiles=[ValueWeightProfilePayload.model_validate(item) for item in config.weight_profiles],
        )

    def merge_into(self, current: ValueEngineWeightingConfig) -> ValueEngineWeightingConfig:
        legacy_budget = max(1.0 - current.sgv_weight - current.egv_weight, 0.0)
        component_weights = self.component_weights or ComponentWeightsPayload(
            ftv_weight=(self.ftv_msv_blend_weights.ftv_weight * legacy_budget) if self.ftv_msv_blend_weights is not None else current.ftv_weight,
            msv_weight=(self.ftv_msv_blend_weights.msv_weight * legacy_budget) if self.ftv_msv_blend_weights is not None else current.msv_weight,
            sgv_weight=current.sgv_weight,
            egv_weight=current.egv_weight,
        )
        movement_caps = self.movement_caps
        influence_caps = self.influence_caps
        momentum_settings = self.momentum_settings
        reference_staleness = self.reference_staleness
        engine_tuning = self.engine_tuning
        price_band_limits = self.price_band_limits
        weight_profiles = self.weight_profiles

        return replace(
            current,
            config_version=self.config_version or current.config_version,
            ftv_weight=component_weights.ftv_weight,
            msv_weight=component_weights.msv_weight,
            sgv_weight=component_weights.sgv_weight,
            egv_weight=component_weights.egv_weight,
            daily_movement_cap=movement_caps.daily_movement_cap if movement_caps is not None else current.daily_movement_cap,
            demand_movement_cap=movement_caps.demand_movement_cap if movement_caps is not None else current.demand_movement_cap,
            momentum_cap=movement_caps.momentum_cap if movement_caps is not None else current.momentum_cap,
            market_signal_cap=influence_caps.market_signal_cap if influence_caps is not None else current.market_signal_cap,
            scouting_signal_cap=influence_caps.scouting_signal_cap if influence_caps is not None else current.scouting_signal_cap,
            egame_signal_cap=influence_caps.egame_signal_cap if influence_caps is not None else current.egame_signal_cap,
            low_liquidity_penalty=influence_caps.low_liquidity_penalty if influence_caps is not None else current.low_liquidity_penalty,
            suspicious_trade_penalty=influence_caps.suspicious_trade_penalty if influence_caps is not None else current.suspicious_trade_penalty,
            momentum_short_window_days=momentum_settings.short_window_days if momentum_settings is not None else current.momentum_short_window_days,
            momentum_medium_window_days=momentum_settings.medium_window_days if momentum_settings is not None else current.momentum_medium_window_days,
            momentum_short_sensitivity=momentum_settings.short_sensitivity if momentum_settings is not None else current.momentum_short_sensitivity,
            momentum_medium_sensitivity=momentum_settings.medium_sensitivity if momentum_settings is not None else current.momentum_medium_sensitivity,
            reference_stale_days=reference_staleness.stale_days if reference_staleness is not None else current.reference_stale_days,
            reference_very_stale_days=reference_staleness.very_stale_days if reference_staleness is not None else current.reference_very_stale_days,
            reference_stale_blend=reference_staleness.stale_blend if reference_staleness is not None else current.reference_stale_blend,
            baseline_eur_per_credit=engine_tuning.baseline_eur_per_credit if engine_tuning is not None else current.baseline_eur_per_credit,
            smoothing_factor=engine_tuning.smoothing_factor if engine_tuning is not None else current.smoothing_factor,
            anchor_pull_strength=engine_tuning.anchor_pull_strength if engine_tuning is not None else current.anchor_pull_strength,
            market_price_pull_strength=engine_tuning.market_price_pull_strength if engine_tuning is not None else current.market_price_pull_strength,
            default_liquidity_weight=engine_tuning.default_liquidity_weight if engine_tuning is not None else current.default_liquidity_weight,
            minimum_floor_ratio=engine_tuning.minimum_floor_ratio if engine_tuning is not None else current.minimum_floor_ratio,
            participant_diversity_scale=engine_tuning.participant_diversity_scale if engine_tuning is not None else current.participant_diversity_scale,
            order_book_wide_spread_bps=engine_tuning.order_book_wide_spread_bps if engine_tuning is not None else current.order_book_wide_spread_bps,
            performance_scale=engine_tuning.performance_scale if engine_tuning is not None else current.performance_scale,
            award_scale=engine_tuning.award_scale if engine_tuning is not None else current.award_scale,
            transfer_scale=engine_tuning.transfer_scale if engine_tuning is not None else current.transfer_scale,
            demand_scale=engine_tuning.demand_scale if engine_tuning is not None else current.demand_scale,
            scouting_scale=engine_tuning.scouting_scale if engine_tuning is not None else current.scouting_scale,
            egame_scale=engine_tuning.egame_scale if engine_tuning is not None else current.egame_scale,
            big_moment_bonus=engine_tuning.big_moment_bonus if engine_tuning is not None else current.big_moment_bonus,
            gsi_neutral_score=engine_tuning.gsi_neutral_score if engine_tuning is not None else current.gsi_neutral_score,
            gsi_smoothing_factor=engine_tuning.gsi_smoothing_factor if engine_tuning is not None else current.gsi_smoothing_factor,
            gsi_daily_movement_cap=engine_tuning.gsi_daily_movement_cap if engine_tuning is not None else current.gsi_daily_movement_cap,
            gsi_signal_cap=engine_tuning.gsi_signal_cap if engine_tuning is not None else current.gsi_signal_cap,
            gsi_signal_scale=engine_tuning.gsi_signal_scale if engine_tuning is not None else current.gsi_signal_scale,
            gsi_anchor_pull_strength=engine_tuning.gsi_anchor_pull_strength if engine_tuning is not None else current.gsi_anchor_pull_strength,
            price_band_limits=tuple(item.to_domain() for item in price_band_limits) if price_band_limits is not None else current.price_band_limits,
            liquidity_band_market_weights=dict(self.liquidity_band_market_weights) if self.liquidity_band_market_weights is not None else current.liquidity_band_market_weights,
            gsi_signal_weights=dict(self.gsi_signal_weights) if self.gsi_signal_weights is not None else current.gsi_signal_weights,
            egame_signal_weights=dict(self.egame_signal_weights) if self.egame_signal_weights is not None else current.egame_signal_weights,
            competition_multipliers=dict(self.competition_multipliers) if self.competition_multipliers is not None else current.competition_multipliers,
            award_impacts=dict(self.award_impacts) if self.award_impacts is not None else current.award_impacts,
            weight_profiles=tuple(item.to_domain() for item in weight_profiles) if weight_profiles is not None else current.weight_profiles,
        )
