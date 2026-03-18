from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from backend.app.core.config import (
    LIQUIDITY_BANDS_FILE,
    PLAYER_CARD_MARKET_INTEGRITY_FILE,
    SUPPLY_TIERS_FILE,
    SUSPICION_THRESHOLDS_FILE,
    VALUE_ENGINE_WEIGHTING_FILE,
    LiquidityBandsConfig,
    PlayerCardMarketIntegrityConfig,
    Settings,
    SupplyTiersConfig,
    SuspicionThresholdsConfig,
    ValueEngineWeightingConfig,
    load_settings,
    reset_settings_cache,
)
from backend.app.ingestion.market_profile import PlayerMarketProfileService


def _toml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, int | float):
        return json.dumps(value)
    raise TypeError(f"Unsupported TOML value: {type(value)!r}")


def render_supply_tiers_config(config: SupplyTiersConfig) -> str:
    lines: list[str] = []
    for tier in config.tiers:
        lines.extend(
            [
                "[[tiers]]",
                f"code = {_toml_scalar(tier.code)}",
                f"name = {_toml_scalar(tier.name)}",
                f"min_score = {_toml_scalar(tier.min_score)}",
                f"max_score = {_toml_scalar(tier.max_score)}",
                f"target_share = {_toml_scalar(tier.target_share)}",
                f"circulating_supply = {_toml_scalar(tier.circulating_supply)}",
                f"daily_pack_supply = {_toml_scalar(tier.daily_pack_supply)}",
                f"season_mint_cap = {_toml_scalar(tier.season_mint_cap)}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_liquidity_bands_config(config: LiquidityBandsConfig) -> str:
    lines: list[str] = []
    for band in config.bands:
        lines.extend(
            [
                "[[bands]]",
                f"code = {_toml_scalar(band.code)}",
                f"name = {_toml_scalar(band.name)}",
                f"min_price_credits = {_toml_scalar(band.min_price_credits)}",
            ]
        )
        if band.max_price_credits is not None:
            lines.append(f"max_price_credits = {_toml_scalar(band.max_price_credits)}")
        lines.extend(
            [
                f"max_spread_bps = {_toml_scalar(band.max_spread_bps)}",
                f"maker_inventory_target = {_toml_scalar(band.maker_inventory_target)}",
                f"instant_sell_fee_bps = {_toml_scalar(band.instant_sell_fee_bps)}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_suspicion_thresholds_config(config: SuspicionThresholdsConfig) -> str:
    lines = [
        f"player_min_suspicious_events = {_toml_scalar(config.player_min_suspicious_events)}",
        f"player_min_suspicious_share = {_toml_scalar(config.player_min_suspicious_share)}",
        f"player_price_band_breach_ratio = {_toml_scalar(config.player_price_band_breach_ratio)}",
        f"cluster_min_member_count = {_toml_scalar(config.cluster_min_member_count)}",
        f"cluster_min_interaction_count = {_toml_scalar(config.cluster_min_interaction_count)}",
        f"cluster_max_asset_count = {_toml_scalar(config.cluster_max_asset_count)}",
        f"thin_market_min_price_credits = {_toml_scalar(config.thin_market_min_price_credits)}",
        f"thin_market_max_pending_offers = {_toml_scalar(config.thin_market_max_pending_offers)}",
        f"thin_market_max_active_trade_intents = {_toml_scalar(config.thin_market_max_active_trade_intents)}",
        f"holder_concentration_min_assets = {_toml_scalar(config.holder_concentration_min_assets)}",
        f"holder_concentration_share = {_toml_scalar(config.holder_concentration_share)}",
        f"circular_trade_min_cycle_length = {_toml_scalar(config.circular_trade_min_cycle_length)}",
        f"circular_trade_min_repetitions = {_toml_scalar(config.circular_trade_min_repetitions)}",
    ]
    return "\n".join(lines) + "\n"


def render_player_card_market_integrity_config(config: PlayerCardMarketIntegrityConfig) -> str:
    lines = [
        f"sale_reference_lookback_days = {_toml_scalar(config.sale_reference_lookback_days)}",
        f"minimum_reference_sales = {_toml_scalar(config.minimum_reference_sales)}",
        f"listing_price_floor_ratio = {_toml_scalar(config.listing_price_floor_ratio)}",
        f"listing_price_ceiling_ratio = {_toml_scalar(config.listing_price_ceiling_ratio)}",
        f"relist_cooldown_minutes = {_toml_scalar(config.relist_cooldown_minutes)}",
        f"pair_trade_lookback_hours = {_toml_scalar(config.pair_trade_lookback_hours)}",
        f"pair_trade_alert_threshold = {_toml_scalar(config.pair_trade_alert_threshold)}",
        f"asset_churn_window_hours = {_toml_scalar(config.asset_churn_window_hours)}",
        f"asset_churn_alert_threshold = {_toml_scalar(config.asset_churn_alert_threshold)}",
        f"circular_trade_window_hours = {_toml_scalar(config.circular_trade_window_hours)}",
        f"price_spike_alert_ratio = {_toml_scalar(config.price_spike_alert_ratio)}",
        f"volume_cluster_window_minutes = {_toml_scalar(config.volume_cluster_window_minutes)}",
        f"volume_cluster_trade_threshold = {_toml_scalar(config.volume_cluster_trade_threshold)}",
    ]
    return "\n".join(lines) + "\n"


def _render_mapping_table(name: str, values: dict[str, float]) -> list[str]:
    lines = [f"[{name}]"]
    for key, value in values.items():
        lines.append(f"{json.dumps(key)} = {_toml_scalar(value)}")
    lines.append("")
    return lines


def _render_string_array(name: str, values: tuple[str, ...]) -> list[str]:
    serialized = ", ".join(json.dumps(value) for value in values)
    return [f"{name} = [{serialized}]"]


def render_value_engine_weighting_config(config: ValueEngineWeightingConfig) -> str:
    legacy_total = max(config.ftv_weight + config.msv_weight, 0.0001)
    scalar_lines = [
        f"config_version = {_toml_scalar(config.config_version)}",
        f"baseline_eur_per_credit = {_toml_scalar(config.baseline_eur_per_credit)}",
        f"smoothing_factor = {_toml_scalar(config.smoothing_factor)}",
        f"daily_movement_cap = {_toml_scalar(config.daily_movement_cap)}",
        f"demand_movement_cap = {_toml_scalar(config.demand_movement_cap)}",
        f"market_signal_cap = {_toml_scalar(config.market_signal_cap)}",
        f"scouting_signal_cap = {_toml_scalar(config.scouting_signal_cap)}",
        f"egame_signal_cap = {_toml_scalar(config.egame_signal_cap)}",
        f"gsi_neutral_score = {_toml_scalar(config.gsi_neutral_score)}",
        f"gsi_smoothing_factor = {_toml_scalar(config.gsi_smoothing_factor)}",
        f"gsi_daily_movement_cap = {_toml_scalar(config.gsi_daily_movement_cap)}",
        f"gsi_signal_cap = {_toml_scalar(config.gsi_signal_cap)}",
        f"gsi_signal_scale = {_toml_scalar(config.gsi_signal_scale)}",
        f"gsi_anchor_pull_strength = {_toml_scalar(config.gsi_anchor_pull_strength)}",
        f"anchor_pull_strength = {_toml_scalar(config.anchor_pull_strength)}",
        f"market_price_pull_strength = {_toml_scalar(config.market_price_pull_strength)}",
        f"default_liquidity_weight = {_toml_scalar(config.default_liquidity_weight)}",
        f"minimum_floor_ratio = {_toml_scalar(config.minimum_floor_ratio)}",
        f"low_liquidity_penalty = {_toml_scalar(config.low_liquidity_penalty)}",
        f"suspicious_trade_penalty = {_toml_scalar(config.suspicious_trade_penalty)}",
        f"performance_scale = {_toml_scalar(config.performance_scale)}",
        f"award_scale = {_toml_scalar(config.award_scale)}",
        f"transfer_scale = {_toml_scalar(config.transfer_scale)}",
        f"demand_scale = {_toml_scalar(config.demand_scale)}",
        f"scouting_scale = {_toml_scalar(config.scouting_scale)}",
        f"egame_scale = {_toml_scalar(config.egame_scale)}",
        f"big_moment_bonus = {_toml_scalar(config.big_moment_bonus)}",
        f"momentum_short_window_days = {_toml_scalar(config.momentum_short_window_days)}",
        f"momentum_medium_window_days = {_toml_scalar(config.momentum_medium_window_days)}",
        f"momentum_short_sensitivity = {_toml_scalar(config.momentum_short_sensitivity)}",
        f"momentum_medium_sensitivity = {_toml_scalar(config.momentum_medium_sensitivity)}",
        f"momentum_cap = {_toml_scalar(config.momentum_cap)}",
        f"reference_stale_days = {_toml_scalar(config.reference_stale_days)}",
        f"reference_very_stale_days = {_toml_scalar(config.reference_very_stale_days)}",
        f"reference_stale_blend = {_toml_scalar(config.reference_stale_blend)}",
        f"participant_diversity_scale = {_toml_scalar(config.participant_diversity_scale)}",
        f"order_book_wide_spread_bps = {_toml_scalar(config.order_book_wide_spread_bps)}",
        "",
        "[component_weights]",
        f"ftv_weight = {_toml_scalar(config.ftv_weight)}",
        f"msv_weight = {_toml_scalar(config.msv_weight)}",
        f"sgv_weight = {_toml_scalar(config.sgv_weight)}",
        f"egv_weight = {_toml_scalar(config.egv_weight)}",
        "",
        "[ftv_msv_blend_weights]",
        f"ftv_weight = {_toml_scalar(round(config.ftv_weight / legacy_total, 6))}",
        f"msv_weight = {_toml_scalar(round(config.msv_weight / legacy_total, 6))}",
        "",
    ]
    sections = [
        *_render_mapping_table("competition_multipliers", config.competition_multipliers),
        *_render_mapping_table("award_impacts", config.award_impacts),
        *_render_mapping_table("demand_weights", config.demand_weights),
        *_render_mapping_table("gsi_signal_weights", config.gsi_signal_weights),
        *_render_mapping_table("egame_signal_weights", config.egame_signal_weights),
        *_render_mapping_table("liquidity_band_market_weights", config.liquidity_band_market_weights),
    ]
    weight_profile_lines: list[str] = []
    for profile in config.weight_profiles:
        weight_profile_lines.extend(
            [
                "[[weight_profiles]]",
                f"code = {_toml_scalar(profile.code)}",
                f"description = {_toml_scalar(profile.description)}",
                *_render_string_array("liquidity_tiers", profile.liquidity_tiers),
                *_render_string_array("confidence_tiers", profile.confidence_tiers),
                *_render_string_array("player_classes", profile.player_classes),
                f"ftv_weight = {_toml_scalar(profile.ftv_weight)}",
                f"msv_weight = {_toml_scalar(profile.msv_weight)}",
                f"sgv_weight = {_toml_scalar(profile.sgv_weight)}",
                f"egv_weight = {_toml_scalar(profile.egv_weight)}",
                "",
            ]
        )
    price_band_lines: list[str] = []
    for price_band in config.price_band_limits:
        price_band_lines.extend(
            [
                "[[price_band_limits]]",
                f"code = {_toml_scalar(price_band.code)}",
                f"min_ratio = {_toml_scalar(price_band.min_ratio)}",
                f"max_ratio = {_toml_scalar(price_band.max_ratio)}",
                "",
            ]
        )
    return "\n".join([*scalar_lines, *sections, *weight_profile_lines, *price_band_lines]).strip() + "\n"


def _settings_environ(settings: Settings) -> dict[str, str]:
    environ = {
        "GTE_APP_NAME": settings.app_name,
        "GTE_APP_VERSION": settings.app_version,
        "GTE_APP_ENV": settings.app_env,
        "GTE_DATABASE_URL": settings.database_url,
        "GTE_AUTH_SECRET": settings.auth_secret,
        "GTE_RUN_MIGRATION_CHECK": "1" if settings.run_migration_check else "0",
        "GTE_INGESTION_PROVIDER": settings.default_ingestion_provider,
        "GTE_PROVIDER_TIMEOUT_SECONDS": str(settings.provider_timeout_seconds),
        "FOOTBALL_DATA_BASE_URL": settings.football_data_base_url,
        "GTE_VALUE_SNAPSHOT_LOOKBACK_DAYS": str(settings.value_snapshot_lookback_days),
    }
    if settings.redis_url is not None:
        environ["GTE_REDIS_URL"] = settings.redis_url
    if settings.football_data_api_key is not None:
        environ["FOOTBALL_DATA_API_KEY"] = settings.football_data_api_key
    return environ


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@dataclass(slots=True)
class ConfigAdminService:
    def update_supply_tiers(
        self,
        app: FastAPI,
        session: Session,
        config: SupplyTiersConfig,
    ) -> Settings:
        current_settings = app.state.settings
        _write_file(current_settings.config_root / SUPPLY_TIERS_FILE, render_supply_tiers_config(config))
        refreshed_settings = self._reload_settings(current_settings)
        PlayerMarketProfileService(settings=refreshed_settings).refresh_player_profiles(session)
        self._apply_runtime_settings(app, refreshed_settings)
        return refreshed_settings

    def update_liquidity_bands(
        self,
        app: FastAPI,
        session: Session,
        config: LiquidityBandsConfig,
    ) -> Settings:
        current_settings = app.state.settings
        _write_file(current_settings.config_root / LIQUIDITY_BANDS_FILE, render_liquidity_bands_config(config))
        refreshed_settings = self._reload_settings(current_settings)
        PlayerMarketProfileService(settings=refreshed_settings).refresh_player_profiles(session)
        self._apply_runtime_settings(app, refreshed_settings)
        return refreshed_settings

    def update_suspicion_thresholds(
        self,
        app: FastAPI,
        config: SuspicionThresholdsConfig,
    ) -> Settings:
        current_settings = app.state.settings
        _write_file(
            current_settings.config_root / SUSPICION_THRESHOLDS_FILE,
            render_suspicion_thresholds_config(config),
        )
        refreshed_settings = self._reload_settings(current_settings)
        self._apply_runtime_settings(app, refreshed_settings)
        return refreshed_settings

    def update_player_card_market_integrity(
        self,
        app: FastAPI,
        config: PlayerCardMarketIntegrityConfig,
    ) -> Settings:
        current_settings = app.state.settings
        _write_file(
            current_settings.config_root / PLAYER_CARD_MARKET_INTEGRITY_FILE,
            render_player_card_market_integrity_config(config),
        )
        refreshed_settings = self._reload_settings(current_settings)
        self._apply_runtime_settings(app, refreshed_settings)
        return refreshed_settings

    def update_value_controls(
        self,
        app: FastAPI,
        config: ValueEngineWeightingConfig,
    ) -> Settings:
        current_settings = app.state.settings
        _write_file(
            current_settings.config_root / VALUE_ENGINE_WEIGHTING_FILE,
            render_value_engine_weighting_config(config),
        )
        refreshed_settings = self._reload_settings(current_settings)
        self._apply_runtime_settings(app, refreshed_settings)
        return refreshed_settings

    def _reload_settings(self, current_settings: Settings) -> Settings:
        reset_settings_cache()
        return load_settings(
            environ=_settings_environ(current_settings),
            config_root=current_settings.config_root,
        )

    def _apply_runtime_settings(self, app: FastAPI, settings: Settings) -> None:
        app.state.settings = settings
        if hasattr(app.state, "context"):
            app.state.context.settings = settings
            app.state.context.database.settings = settings
            app.state.context.value_engine_bridge.settings = settings
            app.state.context.value_engine_bridge.default_lookback_days = settings.value_snapshot_lookback_days
        if hasattr(app.state, "value_engine_bridge"):
            app.state.value_engine_bridge.settings = settings
            app.state.value_engine_bridge.default_lookback_days = settings.value_snapshot_lookback_days
