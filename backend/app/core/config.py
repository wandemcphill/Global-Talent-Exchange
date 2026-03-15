from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import re
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_CONFIG_ROOT = BACKEND_ROOT / "config"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "gte_backend.db"
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"

PLAYER_UNIVERSE_WEIGHTING_FILE = "player_universe_weighting.toml"
SUPPLY_TIERS_FILE = "supply_tiers.toml"
LIQUIDITY_BANDS_FILE = "liquidity_bands.toml"
IMAGE_POLICY_FILE = "image_policy.toml"
VALUE_ENGINE_WEIGHTING_FILE = "value_engine_weighting.toml"
SUSPICION_THRESHOLDS_FILE = "suspicion_thresholds.toml"
MEDIA_STORAGE_FILE = "media_storage.toml"
SPONSORSHIP_INVENTORY_FILE = "sponsorship_inventory.toml"
NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9]+")


def _get_bool(environ: Mapping[str, str], name: str, default: bool) -> bool:
    value = environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(environ: Mapping[str, str], name: str, default: int) -> int:
    value = environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _load_toml_document(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Required config file was not found: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_optional_toml_document(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _resolve_config_root(
    environ: Mapping[str, str],
    config_root: str | Path | None,
) -> Path:
    raw_path = str(config_root) if config_root is not None else environ.get("GTE_CONFIG_DIR")
    if raw_path is None:
        return DEFAULT_CONFIG_ROOT.resolve()
    path = Path(raw_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path.resolve()


def _require_table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Config section '{name}' must be a table.")
    return value


def _require_array(value: object, *, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"Config section '{name}' must be an array.")
    return value


def _coerce_float_map(value: object, *, name: str) -> dict[str, float]:
    table = _require_table(value, name=name)
    normalized: dict[str, float] = {}
    for key, item in table.items():
        normalized[str(key)] = float(item)
    return normalized


def _coerce_string_tuple(value: object, *, name: str) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    items = _require_array(value, name=name)
    return tuple(str(item).strip() for item in items if str(item).strip())


def _catalog_code(name: str, raw_code: object) -> str:
    candidate = str(raw_code).strip().lower() if raw_code is not None else ""
    if not candidate:
        candidate = str(name).strip().lower()
    normalized = NON_ALPHANUMERIC_RE.sub("_", candidate).strip("_")
    if not normalized:
        raise ValueError("Catalog config entries must define a non-empty code or name.")
    return normalized


def _validate_fraction_sum(name: str, values: Mapping[str, float], *, target: float = 1.0) -> None:
    total = round(sum(values.values()), 6)
    if abs(total - target) > 0.001:
        raise ValueError(f"Config section '{name}' must sum to {target}, got {total}.")


@dataclass(frozen=True, slots=True)
class PlayerUniverseWeightingConfig:
    target_player_count: int
    rebalance_interval_hours: int
    weights: dict[str, float]
    age_curve_multipliers: dict[str, float]
    competition_tier_multipliers: dict[str, float]


@dataclass(frozen=True, slots=True)
class SupplyTier:
    code: str
    name: str
    min_score: float
    max_score: float
    target_share: float
    circulating_supply: int
    daily_pack_supply: int
    season_mint_cap: int


@dataclass(frozen=True, slots=True)
class SupplyTiersConfig:
    tiers: tuple[SupplyTier, ...]


@dataclass(frozen=True, slots=True)
class LiquidityBand:
    code: str
    name: str
    min_price_credits: int
    max_price_credits: int | None
    max_spread_bps: int
    maker_inventory_target: int
    instant_sell_fee_bps: int


@dataclass(frozen=True, slots=True)
class LiquidityBandsConfig:
    bands: tuple[LiquidityBand, ...]


@dataclass(frozen=True, slots=True)
class PriceBandLimit:
    code: str
    min_ratio: float
    max_ratio: float


@dataclass(frozen=True, slots=True)
class ValueWeightProfile:
    code: str
    description: str
    liquidity_tiers: tuple[str, ...]
    confidence_tiers: tuple[str, ...]
    player_classes: tuple[str, ...]
    ftv_weight: float
    msv_weight: float
    sgv_weight: float
    egv_weight: float


@dataclass(frozen=True, slots=True)
class ImageVariant:
    name: str
    width: int
    height: int
    format: str
    fit: str


@dataclass(frozen=True, slots=True)
class ImagePolicyConfig:
    source_mode: str
    moderation_required: bool
    watermark_enabled: bool
    allowed_formats: tuple[str, ...]
    max_source_bytes: int
    max_width: int
    max_height: int
    default_variant: str
    variants: tuple[ImageVariant, ...]


@dataclass(frozen=True, slots=True)
class MediaStorageConfig:
    storage_root: Path
    cdn_base_url: str | None
    download_base_url: str
    highlight_temp_prefix: str
    highlight_archive_prefix: str
    highlight_export_prefix: str
    highlight_temp_ttl_hours: int
    highlight_archive_ttl_days: int
    download_expiry_minutes: int
    download_rate_limit_count: int
    download_rate_limit_window_minutes: int
    watermark_enabled: bool


@dataclass(frozen=True, slots=True)
class SponsorshipCampaignConfig:
    code: str
    name: str
    sponsor_name: str
    priority: int
    is_internal: bool
    surfaces: tuple[str, ...]
    region_codes: tuple[str, ...]
    competition_ids: tuple[str, ...]
    stage_names: tuple[str, ...]
    creative_url: str | None


@dataclass(frozen=True, slots=True)
class SponsorshipInventoryConfig:
    default_campaign: str
    surfaces: tuple[str, ...]
    campaigns: tuple[SponsorshipCampaignConfig, ...]


@dataclass(frozen=True, slots=True)
class SuspicionThresholdsConfig:
    player_min_suspicious_events: int
    player_min_suspicious_share: float
    player_price_band_breach_ratio: float
    cluster_min_member_count: int
    cluster_min_interaction_count: int
    cluster_max_asset_count: int
    thin_market_min_price_credits: int
    thin_market_max_pending_offers: int
    thin_market_max_active_trade_intents: int
    holder_concentration_min_assets: int
    holder_concentration_share: float
    circular_trade_min_cycle_length: int
    circular_trade_min_repetitions: int


@dataclass(frozen=True, slots=True)
class ValueEngineWeightingConfig:
    config_version: str
    baseline_eur_per_credit: int
    smoothing_factor: float
    daily_movement_cap: float
    demand_movement_cap: float
    market_signal_cap: float
    scouting_signal_cap: float
    egame_signal_cap: float
    gsi_neutral_score: float
    gsi_smoothing_factor: float
    gsi_daily_movement_cap: float
    gsi_signal_cap: float
    gsi_signal_scale: float
    gsi_anchor_pull_strength: float
    anchor_pull_strength: float
    market_price_pull_strength: float
    default_liquidity_weight: float
    minimum_floor_ratio: float
    low_liquidity_penalty: float
    suspicious_trade_penalty: float
    performance_scale: float
    award_scale: float
    transfer_scale: float
    demand_scale: float
    scouting_scale: float
    egame_scale: float
    big_moment_bonus: float
    momentum_short_window_days: int
    momentum_medium_window_days: int
    momentum_short_sensitivity: float
    momentum_medium_sensitivity: float
    momentum_cap: float
    reference_stale_days: int
    reference_very_stale_days: int
    reference_stale_blend: float
    participant_diversity_scale: float
    order_book_wide_spread_bps: int
    competition_multipliers: dict[str, float]
    award_impacts: dict[str, float]
    demand_weights: dict[str, float]
    gsi_signal_weights: dict[str, float]
    egame_signal_weights: dict[str, float]
    liquidity_band_market_weights: dict[str, float]
    ftv_weight: float
    msv_weight: float
    sgv_weight: float
    egv_weight: float
    weight_profiles: tuple[ValueWeightProfile, ...]
    price_band_limits: tuple[PriceBandLimit, ...]


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_version: str
    app_env: str
    phase_marker: str
    project_root: Path
    backend_root: Path
    config_root: Path
    database_url: str
    redis_url: str | None
    auth_secret: str
    media_signing_secret: str
    crypto_deposit_enabled: bool
    crypto_provider_key: str
    run_migration_check: bool
    default_ingestion_provider: str
    provider_timeout_seconds: int
    football_data_base_url: str
    football_data_api_key: str | None
    value_snapshot_lookback_days: int
    player_universe_weighting: PlayerUniverseWeightingConfig
    supply_tiers: SupplyTiersConfig
    liquidity_bands: LiquidityBandsConfig
    image_policy: ImagePolicyConfig
    media_storage: MediaStorageConfig
    sponsorship_inventory: SponsorshipInventoryConfig
    suspicion_thresholds: SuspicionThresholdsConfig
    value_engine_weighting: ValueEngineWeightingConfig


def _default_suspicion_thresholds_config() -> SuspicionThresholdsConfig:
    return SuspicionThresholdsConfig(
        player_min_suspicious_events=10,
        player_min_suspicious_share=0.25,
        player_price_band_breach_ratio=0.05,
        cluster_min_member_count=3,
        cluster_min_interaction_count=6,
        cluster_max_asset_count=4,
        thin_market_min_price_credits=150,
        thin_market_max_pending_offers=1,
        thin_market_max_active_trade_intents=1,
        holder_concentration_min_assets=3,
        holder_concentration_share=0.40,
        circular_trade_min_cycle_length=3,
        circular_trade_min_repetitions=1,
    )


def _default_media_storage_config(config_root: Path) -> MediaStorageConfig:
    storage_root = BACKEND_ROOT / "storage"
    return MediaStorageConfig(
        storage_root=storage_root,
        cdn_base_url=None,
        download_base_url="/media-engine/downloads",
        highlight_temp_prefix="media/highlights/temp",
        highlight_archive_prefix="media/highlights/archive",
        highlight_export_prefix="media/exports",
        highlight_temp_ttl_hours=72,
        highlight_archive_ttl_days=365,
        download_expiry_minutes=15,
        download_rate_limit_count=5,
        download_rate_limit_window_minutes=10,
        watermark_enabled=True,
    )


def load_media_storage_config(config_root: Path, environ: Mapping[str, str]) -> MediaStorageConfig:
    document = _load_optional_toml_document(config_root / MEDIA_STORAGE_FILE) or {}
    defaults = _default_media_storage_config(config_root)

    raw_root = environ.get("GTE_MEDIA_STORAGE_ROOT") or document.get("storage_root")
    if raw_root:
        path = Path(str(raw_root))
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        storage_root = path
    else:
        storage_root = defaults.storage_root

    cdn_base_url = environ.get("GTE_MEDIA_CDN_BASE_URL") or document.get("cdn_base_url") or defaults.cdn_base_url
    download_base_url = environ.get("GTE_MEDIA_DOWNLOAD_BASE_URL") or document.get("download_base_url") or defaults.download_base_url

    watermark_enabled_value = document.get("watermark_enabled")
    if watermark_enabled_value is None:
        watermark_enabled_value = defaults.watermark_enabled

    return MediaStorageConfig(
        storage_root=storage_root,
        cdn_base_url=str(cdn_base_url) if cdn_base_url else None,
        download_base_url=str(download_base_url),
        highlight_temp_prefix=str(document.get("highlight_temp_prefix", defaults.highlight_temp_prefix)),
        highlight_archive_prefix=str(document.get("highlight_archive_prefix", defaults.highlight_archive_prefix)),
        highlight_export_prefix=str(document.get("highlight_export_prefix", defaults.highlight_export_prefix)),
        highlight_temp_ttl_hours=int(document.get("highlight_temp_ttl_hours", defaults.highlight_temp_ttl_hours)),
        highlight_archive_ttl_days=int(document.get("highlight_archive_ttl_days", defaults.highlight_archive_ttl_days)),
        download_expiry_minutes=int(document.get("download_expiry_minutes", defaults.download_expiry_minutes)),
        download_rate_limit_count=int(document.get("download_rate_limit_count", defaults.download_rate_limit_count)),
        download_rate_limit_window_minutes=int(document.get("download_rate_limit_window_minutes", defaults.download_rate_limit_window_minutes)),
        watermark_enabled=bool(watermark_enabled_value),
    )


def _default_sponsorship_inventory_config() -> SponsorshipInventoryConfig:
    surfaces = (
        "stadium_board",
        "tunnel_walkout",
        "replay_sting",
        "halftime_overlay",
        "lineup_strip",
        "finals_trophy_backdrop",
    )
    return SponsorshipInventoryConfig(
        default_campaign="gtex_internal",
        surfaces=surfaces,
        campaigns=(
            SponsorshipCampaignConfig(
                code="gtex_internal",
                name="GTEX Internal Promo",
                sponsor_name="GTEX",
                priority=0,
                is_internal=True,
                surfaces=surfaces,
                region_codes=(),
                competition_ids=(),
                stage_names=(),
                creative_url=None,
            ),
        ),
    )


def load_sponsorship_inventory_config(config_root: Path) -> SponsorshipInventoryConfig:
    document = _load_optional_toml_document(config_root / SPONSORSHIP_INVENTORY_FILE)
    defaults = _default_sponsorship_inventory_config()
    if not document:
        return defaults

    raw_surfaces = document.get("surfaces")
    if raw_surfaces is None:
        raw_surfaces = list(defaults.surfaces)
    surfaces = _coerce_string_tuple(raw_surfaces, name="surfaces")
    campaigns_raw = _require_array(document.get("campaigns", []), name="campaigns")
    campaigns: list[SponsorshipCampaignConfig] = []
    for item in campaigns_raw:
        table = _require_table(item, name="campaigns[]")
        code = _catalog_code(str(table.get("name") or table.get("code") or ""), table.get("code"))
        campaigns.append(
            SponsorshipCampaignConfig(
                code=code,
                name=str(table.get("name") or code),
                sponsor_name=str(table.get("sponsor_name") or "GTEX"),
                priority=int(table.get("priority", 0)),
                is_internal=bool(table.get("internal", False)),
                surfaces=_coerce_string_tuple(table.get("surfaces", list(surfaces)), name="campaigns[].surfaces"),
                region_codes=_coerce_string_tuple(table.get("region_codes", []), name="campaigns[].region_codes"),
                competition_ids=_coerce_string_tuple(table.get("competition_ids", []), name="campaigns[].competition_ids"),
                stage_names=_coerce_string_tuple(table.get("stage_names", []), name="campaigns[].stage_names"),
                creative_url=str(table.get("creative_url") or "") or None,
            )
        )
    if not campaigns:
        return defaults
    if len({campaign.code for campaign in campaigns}) != len(campaigns):
        raise ValueError("Sponsorship campaign codes must be unique.")
    default_code = str(document.get("default_campaign") or defaults.default_campaign)
    if default_code not in {campaign.code for campaign in campaigns}:
        default_code = campaigns[0].code
    return SponsorshipInventoryConfig(
        default_campaign=default_code,
        surfaces=surfaces,
        campaigns=tuple(campaigns),
    )


def _default_price_band_limits() -> tuple[PriceBandLimit, ...]:
    return (
        PriceBandLimit(code="default", min_ratio=0.80, max_ratio=1.20),
        PriceBandLimit(code="entry", min_ratio=0.88, max_ratio=1.08),
        PriceBandLimit(code="growth", min_ratio=0.84, max_ratio=1.12),
        PriceBandLimit(code="premium", min_ratio=0.80, max_ratio=1.18),
        PriceBandLimit(code="bluechip", min_ratio=0.76, max_ratio=1.24),
        PriceBandLimit(code="marquee", min_ratio=0.72, max_ratio=1.30),
    )


def load_player_universe_weighting_config(config_root: Path) -> PlayerUniverseWeightingConfig:
    document = _load_toml_document(config_root / PLAYER_UNIVERSE_WEIGHTING_FILE)
    weights = _coerce_float_map(document.get("weights", {}), name="weights")
    _validate_fraction_sum("weights", weights)
    age_curve_multipliers = _coerce_float_map(
        document.get("age_curve_multipliers", {}),
        name="age_curve_multipliers",
    )
    competition_tier_multipliers = _coerce_float_map(
        document.get("competition_tier_multipliers", {}),
        name="competition_tier_multipliers",
    )
    return PlayerUniverseWeightingConfig(
        target_player_count=int(document.get("target_player_count", 100_000)),
        rebalance_interval_hours=int(document.get("rebalance_interval_hours", 24)),
        weights=weights,
        age_curve_multipliers=age_curve_multipliers,
        competition_tier_multipliers=competition_tier_multipliers,
    )


def load_supply_tiers_config(config_root: Path) -> SupplyTiersConfig:
    document = _load_toml_document(config_root / SUPPLY_TIERS_FILE)
    tier_documents = _require_array(document.get("tiers", []), name="tiers")
    tiers: tuple[SupplyTier, ...] = tuple(
        SupplyTier(
            code=_catalog_code(
                str(_require_table(item, name="tiers[]").get("name")),
                _require_table(item, name="tiers[]").get("code"),
            ),
            name=str(_require_table(item, name="tiers[]").get("name")),
            min_score=float(_require_table(item, name="tiers[]").get("min_score")),
            max_score=float(_require_table(item, name="tiers[]").get("max_score")),
            target_share=float(_require_table(item, name="tiers[]").get("target_share")),
            circulating_supply=int(_require_table(item, name="tiers[]").get("circulating_supply")),
            daily_pack_supply=int(_require_table(item, name="tiers[]").get("daily_pack_supply")),
            season_mint_cap=int(_require_table(item, name="tiers[]").get("season_mint_cap")),
        )
        for item in tier_documents
    )
    if not tiers:
        raise ValueError("Config section 'tiers' must contain at least one supply tier.")
    if len({tier.code for tier in tiers}) != len(tiers):
        raise ValueError("Supply tier codes must be unique.")
    _validate_fraction_sum("tiers.target_share", {tier.name: tier.target_share for tier in tiers})
    previous_max: float | None = None
    for tier in sorted(tiers, key=lambda item: item.min_score):
        if tier.max_score < tier.min_score:
            raise ValueError(f"Supply tier '{tier.name}' has an invalid score range.")
        if previous_max is not None and tier.min_score <= previous_max:
            raise ValueError("Supply tiers must be ordered and non-overlapping.")
        previous_max = tier.max_score
    return SupplyTiersConfig(tiers=tiers)


def load_liquidity_bands_config(config_root: Path) -> LiquidityBandsConfig:
    document = _load_toml_document(config_root / LIQUIDITY_BANDS_FILE)
    band_documents = _require_array(document.get("bands", []), name="bands")
    bands = tuple(
        LiquidityBand(
            code=_catalog_code(
                str(_require_table(item, name="bands[]").get("name")),
                _require_table(item, name="bands[]").get("code"),
            ),
            name=str(_require_table(item, name="bands[]").get("name")),
            min_price_credits=int(_require_table(item, name="bands[]").get("min_price_credits")),
            max_price_credits=(
                int(max_price)
                if (max_price := _require_table(item, name="bands[]").get("max_price_credits")) is not None
                else None
            ),
            max_spread_bps=int(_require_table(item, name="bands[]").get("max_spread_bps")),
            maker_inventory_target=int(_require_table(item, name="bands[]").get("maker_inventory_target")),
            instant_sell_fee_bps=int(_require_table(item, name="bands[]").get("instant_sell_fee_bps")),
        )
        for item in band_documents
    )
    if not bands:
        raise ValueError("Config section 'bands' must contain at least one liquidity band.")
    if len({band.code for band in bands}) != len(bands):
        raise ValueError("Liquidity band codes must be unique.")
    previous_ceiling: int | None = None
    for index, band in enumerate(bands):
        if index > 0 and previous_ceiling is None:
            raise ValueError("Open-ended liquidity bands must be the final band.")
        if previous_ceiling is not None and band.min_price_credits <= previous_ceiling:
            raise ValueError("Liquidity bands must be ordered and non-overlapping.")
        if band.max_price_credits is not None and band.max_price_credits < band.min_price_credits:
            raise ValueError(f"Liquidity band '{band.name}' has an invalid price range.")
        previous_ceiling = band.max_price_credits
    return LiquidityBandsConfig(bands=bands)


def load_image_policy_config(config_root: Path) -> ImagePolicyConfig:
    document = _load_toml_document(config_root / IMAGE_POLICY_FILE)
    processing = _require_table(document.get("processing", {}), name="processing")
    source = _require_table(document.get("source", {}), name="source")
    variants_document = _require_array(document.get("variants", []), name="variants")
    variants = tuple(
        ImageVariant(
            name=str(_require_table(item, name="variants[]").get("name")),
            width=int(_require_table(item, name="variants[]").get("width")),
            height=int(_require_table(item, name="variants[]").get("height")),
            format=str(_require_table(item, name="variants[]").get("format")).lower(),
            fit=str(_require_table(item, name="variants[]").get("fit")),
        )
        for item in variants_document
    )
    if not variants:
        raise ValueError("Config section 'variants' must define at least one image variant.")
    allowed_formats = tuple(str(item).lower() for item in _require_array(source.get("allowed_formats", []), name="source.allowed_formats"))
    if not allowed_formats:
        raise ValueError("Image policy must define at least one allowed source format.")
    default_variant = str(processing.get("default_variant"))
    if default_variant not in {variant.name for variant in variants}:
        raise ValueError(f"Image policy default_variant '{default_variant}' is not defined in variants.")
    return ImagePolicyConfig(
        source_mode=str(source.get("source_mode", "licensed-only")),
        moderation_required=bool(source.get("moderation_required", True)),
        watermark_enabled=bool(processing.get("watermark_enabled", True)),
        allowed_formats=allowed_formats,
        max_source_bytes=int(source.get("max_source_bytes", 8_000_000)),
        max_width=int(processing.get("max_width", 2400)),
        max_height=int(processing.get("max_height", 2400)),
        default_variant=default_variant,
        variants=variants,
    )


def load_suspicion_thresholds_config(config_root: Path) -> SuspicionThresholdsConfig:
    document = _load_optional_toml_document(config_root / SUSPICION_THRESHOLDS_FILE)
    if document is None:
        return _default_suspicion_thresholds_config()

    defaults = _default_suspicion_thresholds_config()
    thresholds = SuspicionThresholdsConfig(
        player_min_suspicious_events=int(
            document.get("player_min_suspicious_events", defaults.player_min_suspicious_events)
        ),
        player_min_suspicious_share=float(
            document.get("player_min_suspicious_share", defaults.player_min_suspicious_share)
        ),
        player_price_band_breach_ratio=float(
            document.get("player_price_band_breach_ratio", defaults.player_price_band_breach_ratio)
        ),
        cluster_min_member_count=int(document.get("cluster_min_member_count", defaults.cluster_min_member_count)),
        cluster_min_interaction_count=int(
            document.get("cluster_min_interaction_count", defaults.cluster_min_interaction_count)
        ),
        cluster_max_asset_count=int(document.get("cluster_max_asset_count", defaults.cluster_max_asset_count)),
        thin_market_min_price_credits=int(
            document.get("thin_market_min_price_credits", defaults.thin_market_min_price_credits)
        ),
        thin_market_max_pending_offers=int(
            document.get("thin_market_max_pending_offers", defaults.thin_market_max_pending_offers)
        ),
        thin_market_max_active_trade_intents=int(
            document.get(
                "thin_market_max_active_trade_intents",
                defaults.thin_market_max_active_trade_intents,
            )
        ),
        holder_concentration_min_assets=int(
            document.get("holder_concentration_min_assets", defaults.holder_concentration_min_assets)
        ),
        holder_concentration_share=float(
            document.get("holder_concentration_share", defaults.holder_concentration_share)
        ),
        circular_trade_min_cycle_length=int(
            document.get("circular_trade_min_cycle_length", defaults.circular_trade_min_cycle_length)
        ),
        circular_trade_min_repetitions=int(
            document.get("circular_trade_min_repetitions", defaults.circular_trade_min_repetitions)
        ),
    )
    if thresholds.player_min_suspicious_events <= 0:
        raise ValueError("Suspicion thresholds player_min_suspicious_events must be greater than zero.")
    if not 0 < thresholds.player_min_suspicious_share <= 1:
        raise ValueError("Suspicion thresholds player_min_suspicious_share must be between 0 and 1.")
    if thresholds.player_price_band_breach_ratio < 0:
        raise ValueError("Suspicion thresholds player_price_band_breach_ratio must be greater than or equal to zero.")
    if thresholds.cluster_min_member_count < 2:
        raise ValueError("Suspicion thresholds cluster_min_member_count must be at least 2.")
    if thresholds.cluster_min_interaction_count <= 0:
        raise ValueError("Suspicion thresholds cluster_min_interaction_count must be greater than zero.")
    if thresholds.cluster_max_asset_count <= 0:
        raise ValueError("Suspicion thresholds cluster_max_asset_count must be greater than zero.")
    if thresholds.thin_market_min_price_credits < 0:
        raise ValueError("Suspicion thresholds thin_market_min_price_credits must be greater than or equal to zero.")
    if thresholds.thin_market_max_pending_offers < 0:
        raise ValueError("Suspicion thresholds thin_market_max_pending_offers must be greater than or equal to zero.")
    if thresholds.thin_market_max_active_trade_intents < 0:
        raise ValueError("Suspicion thresholds thin_market_max_active_trade_intents must be greater than or equal to zero.")
    if thresholds.holder_concentration_min_assets <= 0:
        raise ValueError("Suspicion thresholds holder_concentration_min_assets must be greater than zero.")
    if not 0 < thresholds.holder_concentration_share <= 1:
        raise ValueError("Suspicion thresholds holder_concentration_share must be between 0 and 1.")
    if thresholds.circular_trade_min_cycle_length < 2:
        raise ValueError("Suspicion thresholds circular_trade_min_cycle_length must be at least 2.")
    if thresholds.circular_trade_min_repetitions <= 0:
        raise ValueError("Suspicion thresholds circular_trade_min_repetitions must be greater than zero.")
    return thresholds


def load_value_engine_weighting_config(config_root: Path) -> ValueEngineWeightingConfig:
    document = _load_toml_document(config_root / VALUE_ENGINE_WEIGHTING_FILE)
    ftv_msv_blend_weights = _require_table(
        document.get("ftv_msv_blend_weights", {}),
        name="ftv_msv_blend_weights",
    )
    component_weights = _require_table(
        document.get("component_weights", {}),
        name="component_weights",
    )
    has_component_weights = bool(component_weights)
    price_band_documents = _require_array(document.get("price_band_limits", []), name="price_band_limits")
    default_ftv_weight = float(component_weights.get("ftv_weight", ftv_msv_blend_weights.get("ftv_weight", 0.70)))
    default_msv_weight = float(component_weights.get("msv_weight", ftv_msv_blend_weights.get("msv_weight", 0.18)))
    price_band_limits = tuple(
        PriceBandLimit(
            code=_catalog_code(
                str(_require_table(item, name="price_band_limits[]").get("code")),
                _require_table(item, name="price_band_limits[]").get("code"),
            ),
            min_ratio=float(_require_table(item, name="price_band_limits[]").get("min_ratio")),
            max_ratio=float(_require_table(item, name="price_band_limits[]").get("max_ratio")),
        )
        for item in price_band_documents
    ) or _default_price_band_limits()
    weight_profile_documents = _require_array(document.get("weight_profiles", []), name="weight_profiles")
    weight_profiles = tuple(
        ValueWeightProfile(
            code=_catalog_code(
                str(_require_table(item, name="weight_profiles[]").get("code")),
                _require_table(item, name="weight_profiles[]").get("code"),
            ),
            description=str(_require_table(item, name="weight_profiles[]").get("description", "Value weighting profile")),
            liquidity_tiers=_coerce_string_tuple(
                _require_table(item, name="weight_profiles[]").get("liquidity_tiers", []),
                name="weight_profiles[].liquidity_tiers",
            ),
            confidence_tiers=_coerce_string_tuple(
                _require_table(item, name="weight_profiles[]").get("confidence_tiers", []),
                name="weight_profiles[].confidence_tiers",
            ),
            player_classes=_coerce_string_tuple(
                _require_table(item, name="weight_profiles[]").get("player_classes", []),
                name="weight_profiles[].player_classes",
            ),
            ftv_weight=float(_require_table(item, name="weight_profiles[]").get("ftv_weight", default_ftv_weight)),
            msv_weight=float(_require_table(item, name="weight_profiles[]").get("msv_weight", default_msv_weight)),
            sgv_weight=float(_require_table(item, name="weight_profiles[]").get("sgv_weight", component_weights.get("sgv_weight", 0.08 if has_component_weights else 0.0))),
            egv_weight=float(_require_table(item, name="weight_profiles[]").get("egv_weight", component_weights.get("egv_weight", 0.04 if has_component_weights else 0.0))),
        )
        for item in weight_profile_documents
    ) or (
        ValueWeightProfile(
            code="default",
            description="Default production weighting profile.",
            liquidity_tiers=(),
            confidence_tiers=(),
            player_classes=(),
            ftv_weight=default_ftv_weight,
            msv_weight=default_msv_weight,
            sgv_weight=float(component_weights.get("sgv_weight", 0.08 if has_component_weights else 0.0)),
            egv_weight=float(component_weights.get("egv_weight", 0.04 if has_component_weights else 0.0)),
        ),
    )
    weighting = ValueEngineWeightingConfig(
        config_version=str(document.get("config_version", "baseline-v1")),
        baseline_eur_per_credit=int(document.get("baseline_eur_per_credit", 100_000)),
        smoothing_factor=float(document.get("smoothing_factor", 0.70)),
        daily_movement_cap=float(document.get("daily_movement_cap", 0.12)),
        demand_movement_cap=float(document.get("demand_movement_cap", 0.05)),
        market_signal_cap=float(document.get("market_signal_cap", 0.18)),
        scouting_signal_cap=float(document.get("scouting_signal_cap", 0.08)),
        egame_signal_cap=float(document.get("egame_signal_cap", 0.05)),
        gsi_neutral_score=float(document.get("gsi_neutral_score", 50.0)),
        gsi_smoothing_factor=float(document.get("gsi_smoothing_factor", 1.0)),
        gsi_daily_movement_cap=float(document.get("gsi_daily_movement_cap", 0.30)),
        gsi_signal_cap=float(document.get("gsi_signal_cap", 0.45)),
        gsi_signal_scale=float(document.get("gsi_signal_scale", 140.0)),
        gsi_anchor_pull_strength=float(document.get("gsi_anchor_pull_strength", 0.08)),
        anchor_pull_strength=float(document.get("anchor_pull_strength", 0.20)),
        market_price_pull_strength=float(document.get("market_price_pull_strength", 0.65)),
        default_liquidity_weight=float(document.get("default_liquidity_weight", 0.20)),
        minimum_floor_ratio=float(document.get("minimum_floor_ratio", 0.60)),
        low_liquidity_penalty=float(document.get("low_liquidity_penalty", 0.10)),
        suspicious_trade_penalty=float(document.get("suspicious_trade_penalty", 0.15)),
        performance_scale=float(document.get("performance_scale", 850.0)),
        award_scale=float(document.get("award_scale", 600.0)),
        transfer_scale=float(document.get("transfer_scale", 900.0)),
        demand_scale=float(document.get("demand_scale", 1200.0)),
        scouting_scale=float(document.get("scouting_scale", 900.0)),
        egame_scale=float(document.get("egame_scale", 1400.0)),
        big_moment_bonus=float(document.get("big_moment_bonus", 18.0)),
        momentum_short_window_days=int(document.get("momentum_short_window_days", 7)),
        momentum_medium_window_days=int(document.get("momentum_medium_window_days", 30)),
        momentum_short_sensitivity=float(document.get("momentum_short_sensitivity", 0.35)),
        momentum_medium_sensitivity=float(document.get("momentum_medium_sensitivity", 0.20)),
        momentum_cap=float(document.get("momentum_cap", 0.04)),
        reference_stale_days=int(document.get("reference_stale_days", 21)),
        reference_very_stale_days=int(document.get("reference_very_stale_days", 60)),
        reference_stale_blend=float(document.get("reference_stale_blend", 0.45)),
        participant_diversity_scale=float(document.get("participant_diversity_scale", 6.0)),
        order_book_wide_spread_bps=int(document.get("order_book_wide_spread_bps", 1800)),
        competition_multipliers=_coerce_float_map(
            document.get("competition_multipliers", {}),
            name="competition_multipliers",
        ),
        award_impacts=_coerce_float_map(document.get("award_impacts", {}), name="award_impacts"),
        demand_weights=_coerce_float_map(document.get("demand_weights", {}), name="demand_weights"),
        gsi_signal_weights=_coerce_float_map(document.get("gsi_signal_weights", {}), name="gsi_signal_weights"),
        egame_signal_weights=_coerce_float_map(document.get("egame_signal_weights", {}), name="egame_signal_weights"),
        liquidity_band_market_weights=_coerce_float_map(
            document.get("liquidity_band_market_weights", {}),
            name="liquidity_band_market_weights",
        ),
        ftv_weight=default_ftv_weight,
        msv_weight=default_msv_weight,
        sgv_weight=float(component_weights.get("sgv_weight", 0.08 if has_component_weights else 0.0)),
        egv_weight=float(component_weights.get("egv_weight", 0.04 if has_component_weights else 0.0)),
        weight_profiles=weight_profiles,
        price_band_limits=price_band_limits,
    )
    if (
        weighting.performance_scale <= 0
        or weighting.award_scale <= 0
        or weighting.transfer_scale <= 0
        or weighting.demand_scale <= 0
        or weighting.scouting_scale <= 0
        or weighting.egame_scale <= 0
    ):
        raise ValueError("Value engine scales must be greater than zero.")
    if not 0 < weighting.minimum_floor_ratio <= 1:
        raise ValueError("Value engine minimum_floor_ratio must be between 0 and 1.")
    if not 0 < weighting.smoothing_factor <= 1:
        raise ValueError("Value engine smoothing_factor must be between 0 and 1.")
    if not 0 <= weighting.gsi_neutral_score <= 100:
        raise ValueError("Value engine gsi_neutral_score must be between 0 and 100.")
    if not 0 < weighting.gsi_smoothing_factor <= 1:
        raise ValueError("Value engine gsi_smoothing_factor must be between 0 and 1.")
    if weighting.daily_movement_cap <= 0 or weighting.demand_movement_cap <= 0 or weighting.market_signal_cap <= 0:
        raise ValueError("Value engine movement caps must be greater than zero.")
    if weighting.gsi_daily_movement_cap <= 0 or weighting.gsi_signal_cap <= 0 or weighting.gsi_signal_scale <= 0:
        raise ValueError("Value engine GSI controls must be greater than zero.")
    if weighting.gsi_anchor_pull_strength < 0:
        raise ValueError("Value engine gsi_anchor_pull_strength must be greater than or equal to zero.")
    if weighting.market_price_pull_strength < 0:
        raise ValueError("Value engine market_price_pull_strength must be greater than or equal to zero.")
    if not 0 <= weighting.default_liquidity_weight <= 1:
        raise ValueError("Value engine default_liquidity_weight must be between 0 and 1.")
    if not 0 <= weighting.low_liquidity_penalty <= 1:
        raise ValueError("Value engine low_liquidity_penalty must be between 0 and 1.")
    if not 0 <= weighting.suspicious_trade_penalty <= 1:
        raise ValueError("Value engine suspicious_trade_penalty must be between 0 and 1.")
    if weighting.momentum_short_window_days <= 0 or weighting.momentum_medium_window_days <= 0:
        raise ValueError("Value engine momentum windows must be greater than zero.")
    if weighting.momentum_medium_window_days < weighting.momentum_short_window_days:
        raise ValueError("Value engine momentum_medium_window_days must be greater than or equal to momentum_short_window_days.")
    if weighting.reference_stale_days <= 0 or weighting.reference_very_stale_days <= 0:
        raise ValueError("Value engine reference staleness windows must be greater than zero.")
    if weighting.reference_very_stale_days < weighting.reference_stale_days:
        raise ValueError("Value engine reference_very_stale_days must be greater than or equal to reference_stale_days.")
    if not 0 <= weighting.reference_stale_blend <= 1:
        raise ValueError("Value engine reference_stale_blend must be between 0 and 1.")
    if weighting.participant_diversity_scale <= 0:
        raise ValueError("Value engine participant_diversity_scale must be greater than zero.")
    if weighting.order_book_wide_spread_bps <= 0:
        raise ValueError("Value engine order_book_wide_spread_bps must be greater than zero.")
    if not 0 <= weighting.ftv_weight <= 1 or not 0 <= weighting.msv_weight <= 1:
        raise ValueError("Value engine FTV/MSV blend weights must each be between 0 and 1.")
    if weighting.ftv_weight + weighting.msv_weight <= 0:
        raise ValueError("Value engine FTV/MSV legacy weights must sum to a positive value.")
    _validate_fraction_sum(
        "component_weights",
        {
            "ftv_weight": weighting.ftv_weight,
            "msv_weight": weighting.msv_weight,
            "sgv_weight": weighting.sgv_weight,
            "egv_weight": weighting.egv_weight,
        },
    )
    for key, value in weighting.gsi_signal_weights.items():
        if value < 0:
            raise ValueError(
                f"Value engine GSI weight for '{key}' must be greater than or equal to zero, got {value}."
            )
    for key, value in weighting.egame_signal_weights.items():
        if value < 0:
            raise ValueError(
                f"Value engine e-game weight for '{key}' must be greater than or equal to zero, got {value}."
            )
    for key, value in weighting.liquidity_band_market_weights.items():
        if not 0 <= value <= 1:
            raise ValueError(
                f"Value engine liquidity weight for '{key}' must be between 0 and 1, got {value}."
            )
    if len({profile.code for profile in weighting.weight_profiles}) != len(weighting.weight_profiles):
        raise ValueError("Value engine weight profile codes must be unique.")
    for profile in weighting.weight_profiles:
        _validate_fraction_sum(
            f"weight_profiles.{profile.code}",
            {
                "ftv_weight": profile.ftv_weight,
                "msv_weight": profile.msv_weight,
                "sgv_weight": profile.sgv_weight,
                "egv_weight": profile.egv_weight,
            },
        )
    if len({limit.code for limit in weighting.price_band_limits}) != len(weighting.price_band_limits):
        raise ValueError("Value engine price band limit codes must be unique.")
    for limit in weighting.price_band_limits:
        if limit.min_ratio <= 0 or limit.max_ratio <= 0:
            raise ValueError(f"Value engine price band '{limit.code}' ratios must be greater than zero.")
        if limit.max_ratio < limit.min_ratio:
            raise ValueError(
                f"Value engine price band '{limit.code}' max_ratio must be greater than or equal to min_ratio."
            )
        if limit.max_ratio < weighting.minimum_floor_ratio:
            raise ValueError(
                f"Value engine price band '{limit.code}' max_ratio must be greater than or equal to minimum_floor_ratio."
            )
    return weighting


def load_settings(
    *,
    environ: Mapping[str, str] | None = None,
    config_root: str | Path | None = None,
) -> Settings:
    resolved_environ = os.environ if environ is None else environ
    resolved_config_root = _resolve_config_root(resolved_environ, config_root)
    return Settings(
        app_name=resolved_environ.get("GTE_APP_NAME", "Global Talent Exchange API"),
        app_version=resolved_environ.get("GTE_APP_VERSION", "0.1.0"),
        app_env=resolved_environ.get("GTE_APP_ENV", "development"),
        phase_marker=resolved_environ.get("GTE_PHASE_MARKER", "phase-8"),
        project_root=PROJECT_ROOT,
        backend_root=BACKEND_ROOT,
        config_root=resolved_config_root,
        database_url=resolved_environ.get("GTE_DATABASE_URL", DEFAULT_DATABASE_URL),
        redis_url=resolved_environ.get("GTE_REDIS_URL"),
        auth_secret=resolved_environ.get("GTE_AUTH_SECRET", "gte-dev-secret-change-me"),
        media_signing_secret=resolved_environ.get("GTE_MEDIA_SIGNING_SECRET", "gte-media-secret-change-me"),
        crypto_deposit_enabled=_get_bool(resolved_environ, "GTE_CRYPTO_DEPOSIT_ENABLED", False),
        crypto_provider_key=resolved_environ.get("GTE_CRYPTO_PROVIDER_KEY", "crypto_fiat"),
        run_migration_check=_get_bool(resolved_environ, "GTE_RUN_MIGRATION_CHECK", True),
        default_ingestion_provider=resolved_environ.get("GTE_INGESTION_PROVIDER", "mock"),
        provider_timeout_seconds=_get_int(resolved_environ, "GTE_PROVIDER_TIMEOUT_SECONDS", 20),
        football_data_base_url=resolved_environ.get("FOOTBALL_DATA_BASE_URL", "https://api.football-data.org/v4"),
        football_data_api_key=resolved_environ.get("FOOTBALL_DATA_API_KEY"),
        value_snapshot_lookback_days=_get_int(resolved_environ, "GTE_VALUE_SNAPSHOT_LOOKBACK_DAYS", 7),
        player_universe_weighting=load_player_universe_weighting_config(resolved_config_root),
        supply_tiers=load_supply_tiers_config(resolved_config_root),
        liquidity_bands=load_liquidity_bands_config(resolved_config_root),
        image_policy=load_image_policy_config(resolved_config_root),
        media_storage=load_media_storage_config(resolved_config_root, resolved_environ),
        sponsorship_inventory=load_sponsorship_inventory_config(resolved_config_root),
        suspicion_thresholds=load_suspicion_thresholds_config(resolved_config_root),
        value_engine_weighting=load_value_engine_weighting_config(resolved_config_root),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
