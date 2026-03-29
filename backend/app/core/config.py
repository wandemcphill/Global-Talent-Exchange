from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path
import re
import tomllib

from pydantic import AliasChoices, Field, field_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - compatibility fallback when dependency bootstrap lags
    from pydantic import BaseModel, ConfigDict

    class BaseSettings(BaseModel):
        pass

    SettingsConfigDict = ConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_CONFIG_ROOT = BACKEND_ROOT / "config"
DEFAULT_DATABASE_URL = ""
DATABASE_URL_ENV_VARS = ("DATABASE_URL", "GTE_DATABASE_URL")

PLAYER_UNIVERSE_WEIGHTING_FILE = "player_universe_weighting.toml"
SUPPLY_TIERS_FILE = "supply_tiers.toml"
LIQUIDITY_BANDS_FILE = "liquidity_bands.toml"
IMAGE_POLICY_FILE = "image_policy.toml"
VALUE_ENGINE_WEIGHTING_FILE = "value_engine_weighting.toml"
SUSPICION_THRESHOLDS_FILE = "suspicion_thresholds.toml"
PLAYER_CARD_MARKET_INTEGRITY_FILE = "player_card_market_integrity.toml"
MEDIA_STORAGE_FILE = "media_storage.toml"
SPONSORSHIP_INVENTORY_FILE = "sponsorship_inventory.toml"
REGEN_GENERATION_FILE = "regen_generation.toml"
NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9]+")


class SettingsSource(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    app_name: str = Field(default="Global Talent Exchange API", validation_alias="GTE_APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="GTE_APP_VERSION")
    app_env: str = Field(default="development", validation_alias="GTE_APP_ENV")
    phase_marker: str = Field(default="phase-8", validation_alias="GTE_PHASE_MARKER")
    config_root_override: str | None = Field(default=None, validation_alias="GTE_CONFIG_DIR")
    database_read_url: str | None = Field(default=None, validation_alias="GTE_DATABASE_READ_URL")
    redis_url: str | None = Field(default=None, validation_alias="GTE_REDIS_URL")
    redis_event_channel: str = Field(default="gtex.events", validation_alias="GTE_REDIS_EVENT_CHANNEL")
    redis_realtime_channel: str = Field(default="gtex.realtime", validation_alias="GTE_REDIS_REALTIME_CHANNEL")
    broadcast_delay_seconds: int = Field(default=3, validation_alias="GTE_BROADCAST_DELAY_SECONDS")
    broadcast_presence_ttl_seconds: int = Field(
        default=45,
        validation_alias="GTE_BROADCAST_PRESENCE_TTL_SECONDS",
    )
    broadcast_presence_heartbeat_interval_seconds: int = Field(
        default=15,
        validation_alias="GTE_BROADCAST_HEARTBEAT_INTERVAL_SECONDS",
    )
    broadcast_max_pending_messages: int = Field(
        default=256,
        validation_alias="GTE_BROADCAST_MAX_PENDING_MESSAGES",
    )
    auth_secret: str = Field(default="gte-dev-secret-change-me", validation_alias="GTE_AUTH_SECRET")
    media_signing_secret: str = Field(default="gte-media-secret-change-me", validation_alias="GTE_MEDIA_SIGNING_SECRET")
    crypto_deposit_enabled: bool = Field(default=False, validation_alias="GTE_CRYPTO_DEPOSIT_ENABLED")
    crypto_provider_key: str = Field(default="crypto_fiat", validation_alias="GTE_CRYPTO_PROVIDER_KEY")
    run_migration_check: bool = Field(default=True, validation_alias="GTE_RUN_MIGRATION_CHECK")
    run_startup_seeding: bool = Field(
        default=True,
        validation_alias=AliasChoices("RUN_STARTUP_SEEDING", "GTE_RUN_STARTUP_SEEDING"),
    )
    bootstrap_admin_enabled: bool = Field(
        default=False,
        validation_alias="GTE_BOOTSTRAP_ADMIN_ENABLED",
    )
    bootstrap_admin_email: str | None = Field(
        default=None,
        validation_alias="GTE_BOOTSTRAP_ADMIN_EMAIL",
    )
    bootstrap_admin_password: str | None = Field(
        default=None,
        validation_alias="GTE_BOOTSTRAP_ADMIN_PASSWORD",
    )
    bootstrap_admin_username: str | None = Field(
        default=None,
        validation_alias="GTE_BOOTSTRAP_ADMIN_USERNAME",
    )
    bootstrap_admin_display_name: str | None = Field(
        default=None,
        validation_alias="GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME",
    )
    default_ingestion_provider: str = Field(default="mock", validation_alias="GTE_INGESTION_PROVIDER")
    real_player_mapping_auto_create_missing_entities: bool = Field(
        default=False,
        validation_alias="GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES",
    )
    provider_timeout_seconds: int = Field(default=20, validation_alias="GTE_PROVIDER_TIMEOUT_SECONDS")
    football_data_base_url: str = Field(
        default="https://api.football-data.org/v4",
        validation_alias="FOOTBALL_DATA_BASE_URL",
    )
    football_data_api_key: str | None = Field(default=None, validation_alias="FOOTBALL_DATA_API_KEY")
    value_snapshot_lookback_days: int = Field(default=7, validation_alias="GTE_VALUE_SNAPSHOT_LOOKBACK_DAYS")
    kafka_brokers: tuple[str, ...] = Field(default=(), validation_alias="GTE_KAFKA_BROKERS")
    kafka_client_id: str = Field(default="gtex-api", validation_alias="GTE_KAFKA_CLIENT_ID")
    kafka_topic_prefix: str = Field(default="gtex", validation_alias="GTE_KAFKA_TOPIC_PREFIX")
    kafka_queue_consumer_group: str = Field(
        default="gtex-api-queue",
        validation_alias="GTE_KAFKA_QUEUE_CONSUMER_GROUP",
    )
    kafka_projection_consumer_group: str = Field(
        default="gtex-projections",
        validation_alias="GTE_KAFKA_PROJECTION_CONSUMER_GROUP",
    )
    viral_event_consumer_group: str = Field(
        default="gtex-viral-analytics",
        validation_alias="GTE_VIRAL_EVENT_CONSUMER_GROUP",
    )
    viral_event_batch_size: int = Field(default=500, validation_alias="GTE_VIRAL_EVENT_BATCH_SIZE")
    viral_event_batch_interval_ms: int = Field(
        default=25,
        validation_alias="GTE_VIRAL_EVENT_BATCH_INTERVAL_MS",
    )
    viral_event_queue_maxsize: int = Field(default=50000, validation_alias="GTE_VIRAL_EVENT_QUEUE_MAXSIZE")
    viral_event_topic_partitions: int = Field(
        default=12,
        validation_alias="GTE_VIRAL_EVENT_TOPIC_PARTITIONS",
    )
    viral_event_topic_replication_factor: int = Field(
        default=1,
        validation_alias="GTE_VIRAL_EVENT_TOPIC_REPLICATION_FACTOR",
    )
    viral_event_dedupe_ttl_seconds: int = Field(
        default=86400,
        validation_alias="GTE_VIRAL_EVENT_DEDUPE_TTL_SECONDS",
    )
    outbox_relay_enabled: bool = Field(default=True, validation_alias="GTE_OUTBOX_RELAY_ENABLED")
    outbox_relay_batch_size: int = Field(default=100, validation_alias="GTE_OUTBOX_RELAY_BATCH_SIZE")
    outbox_relay_poll_interval_ms: int = Field(default=1000, validation_alias="GTE_OUTBOX_RELAY_POLL_INTERVAL_MS")
    kafka_api_queue_consumer_enabled: bool = Field(
        default=True,
        validation_alias="GTE_KAFKA_API_QUEUE_CONSUMER_ENABLED",
    )
    kafka_simulation_consumer_enabled: bool = Field(
        default=True,
        validation_alias="GTE_KAFKA_SIMULATION_CONSUMER_ENABLED",
    )
    projection_workers_enabled: bool = Field(default=True, validation_alias="GTE_PROJECTION_WORKERS_ENABLED")
    observability_metrics_enabled: bool = Field(default=True, validation_alias="GTE_METRICS_ENABLED")
    observability_metrics_port: int = Field(default=0, validation_alias="GTE_METRICS_PORT")
    observability_log_json: bool = Field(default=False, validation_alias="GTE_LOG_JSON")
    observability_tracing_enabled: bool = Field(
        default=False,
        validation_alias="GTE_OBSERVABILITY_TRACING_ENABLED",
    )
    observability_otlp_traces_endpoint: str | None = Field(
        default=None,
        validation_alias="GTE_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    )
    observability_trace_sample_ratio: float = Field(
        default=1.0,
        validation_alias="GTE_OTEL_TRACES_SAMPLER_RATIO",
    )
    observability_service_name: str | None = Field(default=None, validation_alias="GTE_OTEL_SERVICE_NAME")
    live_commentary_llm_enabled: bool = Field(
        default=False,
        validation_alias="GTE_LIVE_COMMENTARY_LLM_ENABLED",
    )
    live_commentary_llm_endpoint_url: str | None = Field(
        default=None,
        validation_alias="GTE_LIVE_COMMENTARY_LLM_ENDPOINT_URL",
    )
    live_commentary_llm_model: str | None = Field(default=None, validation_alias="GTE_LIVE_COMMENTARY_LLM_MODEL")
    live_commentary_llm_api_key: str | None = Field(
        default=None,
        validation_alias="GTE_LIVE_COMMENTARY_LLM_API_KEY",
    )
    live_commentary_llm_timeout_seconds: int = Field(
        default=8,
        validation_alias="GTE_LIVE_COMMENTARY_LLM_TIMEOUT_SECONDS",
    )
    live_commentary_max_llm_calls_per_match: int = Field(
        default=30,
        validation_alias="GTE_LIVE_COMMENTARY_MAX_LLM_CALLS_PER_MATCH",
    )
    live_commentary_memory_ttl_seconds: int = Field(
        default=21_600,
        validation_alias="GTE_LIVE_COMMENTARY_MEMORY_TTL_SECONDS",
    )
    social_content_llm_enabled: bool = Field(default=False, validation_alias="GTE_SOCIAL_CONTENT_LLM_ENABLED")
    social_content_llm_endpoint_url: str | None = Field(
        default=None,
        validation_alias="GTE_SOCIAL_CONTENT_LLM_ENDPOINT_URL",
    )
    social_content_llm_model: str | None = Field(default=None, validation_alias="GTE_SOCIAL_CONTENT_LLM_MODEL")
    social_content_llm_api_key: str | None = Field(default=None, validation_alias="GTE_SOCIAL_CONTENT_LLM_API_KEY")
    social_content_llm_timeout_seconds: int = Field(
        default=8,
        validation_alias="GTE_SOCIAL_CONTENT_LLM_TIMEOUT_SECONDS",
    )

    @field_validator("kafka_brokers", mode="before")
    @classmethod
    def _parse_kafka_brokers(cls, value: object) -> tuple[str, ...]:
        if value is None or value == "":
            return ()
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        if isinstance(value, (list, tuple)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        raise TypeError("GTE_KAFKA_BROKERS must be a comma-separated string or sequence of broker names.")


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


def _get_float(environ: Mapping[str, str], name: str, default: float) -> float:
    value = environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_csv(environ: Mapping[str, str], name: str) -> tuple[str, ...]:
    value = environ.get(name)
    if value is None:
        return tuple()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def normalize_database_url(database_url: str) -> str:
    normalized = database_url.strip()
    if not normalized:
        raise ValueError("DATABASE_URL must not be empty.")
    if normalized.startswith("postgres://"):
        return f"postgresql+psycopg://{normalized[len('postgres://'):]}"
    if normalized.startswith("postgresql://"):
        return f"postgresql+psycopg://{normalized[len('postgresql://'):]}"
    return normalized


def resolve_database_url(environ: Mapping[str, str]) -> str:
    for name in DATABASE_URL_ENV_VARS:
        value = environ.get(name)
        if value and value.strip():
            return normalize_database_url(value)
    raise ValueError(
        "DATABASE_URL is required for backend database access. "
        "GTE_DATABASE_URL is accepted only as a legacy fallback."
    )


def resolve_database_read_url(environ: Mapping[str, str], *, default_database_url: str) -> str:
    value = environ.get("GTE_DATABASE_READ_URL")
    if value is None or not value.strip():
        return default_database_url
    return normalize_database_url(value)


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
class RegenCountryTuningConfig:
    country_code: str
    academy_quality_bias: float
    elite_probability_boost: float
    urban_bias: float
    default_regions: tuple[str, ...]
    default_cities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RegenGenerationConfig:
    academy_intakes_per_season: int
    academy_intake_min_players: int
    academy_intake_max_players: int
    starter_regen_count: int
    starter_age_min: int
    starter_age_max: int
    starter_gsi_min: int
    starter_gsi_max: int
    seasonal_supply_cap_ratio: float
    base_elite_probability: float
    max_elite_probability: float
    default_active_player_base: int
    market_fee_bps_default: int
    market_fee_bps_min: int
    market_fee_bps_max: int
    ecosystem_target_regen_share: float
    elite_regen_share_cap: float
    demand_cooling_floor: float
    regen_lifecycle_growth_months: int
    regen_lifecycle_peak_months: int
    regen_lifecycle_decline_months: int
    regen_lifecycle_retirement_months: int
    player_lifecycle_growth_max_age: int
    player_lifecycle_peak_max_age: int
    player_lifecycle_decline_max_age: int
    lineage_base_probability: float
    lineage_legend_probability: float
    lineage_owner_probability: float
    lineage_retired_regen_probability: float
    lineage_hometown_probability: float
    twin_probability: float
    owner_son_lifetime_cap: int
    owner_son_rival_club_chance: float
    owner_son_paid_request_base_cost: int
    owner_son_paid_request_name_cost: int
    owner_son_paid_request_customization_cost: int
    owner_son_paid_request_limit: int
    default_country_code: str
    country_tuning: tuple[RegenCountryTuningConfig, ...]


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
class PlayerCardMarketIntegrityConfig:
    sale_reference_lookback_days: int
    minimum_reference_sales: int
    listing_price_floor_ratio: float
    listing_price_ceiling_ratio: float
    relist_cooldown_minutes: int
    pair_trade_lookback_hours: int
    pair_trade_alert_threshold: int
    asset_churn_window_hours: int
    asset_churn_alert_threshold: int
    circular_trade_window_hours: int
    price_spike_alert_ratio: float
    volume_cluster_window_minutes: int
    volume_cluster_trade_threshold: int


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
    real_player_bridge_enabled: bool
    real_player_bridge_version: str
    real_player_bridge_smoothing_factor: float
    real_player_bridge_floor_ratio: float
    real_player_bridge_ceiling_ratio: float
    competition_multipliers: dict[str, float]
    award_impacts: dict[str, float]
    demand_weights: dict[str, float]
    gsi_signal_weights: dict[str, float]
    egame_signal_weights: dict[str, float]
    liquidity_band_market_weights: dict[str, float]
    real_player_bridge_reference_weights: dict[str, float]
    real_player_bridge_tier_multipliers: dict[str, float]
    ftv_weight: float
    msv_weight: float
    sgv_weight: float
    egv_weight: float
    weight_profiles: tuple[ValueWeightProfile, ...]
    price_band_limits: tuple[PriceBandLimit, ...]


@dataclass(frozen=True, slots=True)
class RealPlayerImportConfig:
    provider_name: str
    batch_size: int
    max_pages_per_run: int
    rate_limit_per_minute: int
    timeout_seconds: int
    cursor_key: str


@dataclass(frozen=True, slots=True)
class BrevoSmtpConfig:
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    use_tls: bool = True
    use_ssl: bool = False


@dataclass(frozen=True, slots=True)
class EmailConfig:
    enabled: bool
    provider: str
    from_address: str
    from_name: str
    reply_to: str | None
    send_timeout_seconds: int
    signup_confirmation_ttl_minutes: int
    account_recovery_ttl_minutes: int
    signup_confirmation_url_base: str | None
    account_recovery_url_base: str | None
    brevo_smtp: BrevoSmtpConfig


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
    database_read_url: str
    redis_url: str | None
    redis_event_channel: str
    redis_realtime_channel: str
    broadcast_delay_seconds: int
    broadcast_presence_ttl_seconds: int
    broadcast_presence_heartbeat_interval_seconds: int
    broadcast_max_pending_messages: int
    auth_secret: str
    media_signing_secret: str
    crypto_deposit_enabled: bool
    crypto_provider_key: str
    run_migration_check: bool
    run_startup_seeding: bool
    bootstrap_admin_enabled: bool
    bootstrap_admin_email: str | None
    bootstrap_admin_password: str | None
    bootstrap_admin_username: str | None
    bootstrap_admin_display_name: str | None
    default_ingestion_provider: str
    real_player_mapping_auto_create_missing_entities: bool
    provider_timeout_seconds: int
    football_data_base_url: str
    football_data_api_key: str | None
    value_snapshot_lookback_days: int
    kafka_brokers: tuple[str, ...]
    kafka_client_id: str
    kafka_topic_prefix: str
    kafka_queue_consumer_group: str
    kafka_projection_consumer_group: str
    viral_event_consumer_group: str
    viral_event_batch_size: int
    viral_event_batch_interval_ms: int
    viral_event_queue_maxsize: int
    viral_event_topic_partitions: int
    viral_event_topic_replication_factor: int
    viral_event_dedupe_ttl_seconds: int
    outbox_relay_enabled: bool
    outbox_relay_batch_size: int
    outbox_relay_poll_interval_ms: int
    kafka_api_queue_consumer_enabled: bool
    kafka_simulation_consumer_enabled: bool
    projection_workers_enabled: bool
    observability_metrics_enabled: bool
    observability_metrics_port: int
    observability_log_json: bool
    observability_tracing_enabled: bool
    observability_otlp_traces_endpoint: str | None
    observability_trace_sample_ratio: float
    observability_service_name: str | None
    email: EmailConfig
    real_player_import: RealPlayerImportConfig
    player_universe_weighting: PlayerUniverseWeightingConfig
    supply_tiers: SupplyTiersConfig
    liquidity_bands: LiquidityBandsConfig
    image_policy: ImagePolicyConfig
    media_storage: MediaStorageConfig
    sponsorship_inventory: SponsorshipInventoryConfig
    regen_generation: RegenGenerationConfig
    suspicion_thresholds: SuspicionThresholdsConfig
    player_card_market_integrity: PlayerCardMarketIntegrityConfig
    value_engine_weighting: ValueEngineWeightingConfig
    live_commentary_llm_enabled: bool = False
    live_commentary_llm_endpoint_url: str | None = None
    live_commentary_llm_model: str | None = None
    live_commentary_llm_api_key: str | None = None
    live_commentary_llm_timeout_seconds: int = 8
    live_commentary_max_llm_calls_per_match: int = 30
    live_commentary_memory_ttl_seconds: int = 21_600
    social_content_llm_enabled: bool = False
    social_content_llm_endpoint_url: str | None = None
    social_content_llm_model: str | None = None
    social_content_llm_api_key: str | None = None
    social_content_llm_timeout_seconds: int = 8

    @property
    def environment(self) -> str:
        return self.app_env

    @property
    def kafka_enabled(self) -> bool:
        return bool(self.kafka_brokers)

    @property
    def cdn_base_url(self) -> str | None:
        return self.media_storage.cdn_base_url

    @property
    def highlight_temp_prefix(self) -> str:
        return self.media_storage.highlight_temp_prefix

    @property
    def highlight_archive_prefix(self) -> str:
        return self.media_storage.highlight_archive_prefix


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


def _default_regen_generation_config() -> RegenGenerationConfig:
    return RegenGenerationConfig(
        academy_intakes_per_season=1,
        academy_intake_min_players=2,
        academy_intake_max_players=4,
        starter_regen_count=2,
        starter_age_min=25,
        starter_age_max=30,
        starter_gsi_min=50,
        starter_gsi_max=68,
        seasonal_supply_cap_ratio=0.025,
        base_elite_probability=0.01,
        max_elite_probability=0.12,
        default_active_player_base=100_000,
        market_fee_bps_default=4500,
        market_fee_bps_min=4000,
        market_fee_bps_max=5000,
        ecosystem_target_regen_share=0.20,
        elite_regen_share_cap=0.08,
        demand_cooling_floor=0.55,
        regen_lifecycle_growth_months=9,
        regen_lifecycle_peak_months=21,
        regen_lifecycle_decline_months=30,
        regen_lifecycle_retirement_months=36,
        player_lifecycle_growth_max_age=23,
        player_lifecycle_peak_max_age=29,
        player_lifecycle_decline_max_age=34,
        lineage_base_probability=0.004,
        lineage_legend_probability=0.55,
        lineage_owner_probability=0.15,
        lineage_retired_regen_probability=0.20,
        lineage_hometown_probability=0.10,
        twin_probability=0.002,
        owner_son_lifetime_cap=3,
        owner_son_rival_club_chance=0.12,
        owner_son_paid_request_base_cost=125,
        owner_son_paid_request_name_cost=25,
        owner_son_paid_request_customization_cost=35,
        owner_son_paid_request_limit=1,
        default_country_code="NG",
        country_tuning=(
            RegenCountryTuningConfig(
                country_code="NG",
                academy_quality_bias=1.05,
                elite_probability_boost=0.015,
                urban_bias=0.10,
                default_regions=("Lagos", "Enugu", "Kano"),
                default_cities=("Lagos", "Enugu", "Kano"),
            ),
            RegenCountryTuningConfig(
                country_code="GH",
                academy_quality_bias=1.02,
                elite_probability_boost=0.008,
                urban_bias=0.06,
                default_regions=("Greater Accra", "Ashanti"),
                default_cities=("Accra", "Kumasi"),
            ),
            RegenCountryTuningConfig(
                country_code="MA",
                academy_quality_bias=1.01,
                elite_probability_boost=0.006,
                urban_bias=0.05,
                default_regions=("Casablanca-Settat", "Rabat-Sale-Kenitra"),
                default_cities=("Casablanca", "Rabat"),
            ),
        ),
    )


def _default_player_card_market_integrity_config() -> PlayerCardMarketIntegrityConfig:
    return PlayerCardMarketIntegrityConfig(
        sale_reference_lookback_days=14,
        minimum_reference_sales=2,
        listing_price_floor_ratio=0.60,
        listing_price_ceiling_ratio=1.80,
        relist_cooldown_minutes=30,
        pair_trade_lookback_hours=168,
        pair_trade_alert_threshold=3,
        asset_churn_window_hours=24,
        asset_churn_alert_threshold=6,
        circular_trade_window_hours=24,
        price_spike_alert_ratio=2.50,
        volume_cluster_window_minutes=60,
        volume_cluster_trade_threshold=12,
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


def load_regen_generation_config(config_root: Path) -> RegenGenerationConfig:
    document = _load_optional_toml_document(config_root / REGEN_GENERATION_FILE)
    defaults = _default_regen_generation_config()
    if not document:
        return defaults

    country_documents = _require_array(document.get("country_tuning", []), name="country_tuning")
    country_tuning = tuple(
        RegenCountryTuningConfig(
            country_code=str(_require_table(item, name="country_tuning[]").get("country_code", "")).strip().upper(),
            academy_quality_bias=float(_require_table(item, name="country_tuning[]").get("academy_quality_bias", 1.0)),
            elite_probability_boost=float(
                _require_table(item, name="country_tuning[]").get("elite_probability_boost", 0.0)
            ),
            urban_bias=float(_require_table(item, name="country_tuning[]").get("urban_bias", 0.0)),
            default_regions=_coerce_string_tuple(
                _require_table(item, name="country_tuning[]").get("default_regions", []),
                name="country_tuning[].default_regions",
            ),
            default_cities=_coerce_string_tuple(
                _require_table(item, name="country_tuning[]").get("default_cities", []),
                name="country_tuning[].default_cities",
            ),
        )
        for item in country_documents
    ) or defaults.country_tuning

    config = RegenGenerationConfig(
        academy_intakes_per_season=int(
            document.get("academy_intakes_per_season", defaults.academy_intakes_per_season)
        ),
        academy_intake_min_players=int(
            document.get("academy_intake_min_players", defaults.academy_intake_min_players)
        ),
        academy_intake_max_players=int(
            document.get("academy_intake_max_players", defaults.academy_intake_max_players)
        ),
        starter_regen_count=int(document.get("starter_regen_count", defaults.starter_regen_count)),
        starter_age_min=int(document.get("starter_age_min", defaults.starter_age_min)),
        starter_age_max=int(document.get("starter_age_max", defaults.starter_age_max)),
        starter_gsi_min=int(document.get("starter_gsi_min", defaults.starter_gsi_min)),
        starter_gsi_max=int(document.get("starter_gsi_max", defaults.starter_gsi_max)),
        seasonal_supply_cap_ratio=float(
            document.get("seasonal_supply_cap_ratio", defaults.seasonal_supply_cap_ratio)
        ),
        base_elite_probability=float(document.get("base_elite_probability", defaults.base_elite_probability)),
        max_elite_probability=float(document.get("max_elite_probability", defaults.max_elite_probability)),
        default_active_player_base=int(
            document.get("default_active_player_base", defaults.default_active_player_base)
        ),
        market_fee_bps_default=int(document.get("market_fee_bps_default", defaults.market_fee_bps_default)),
        market_fee_bps_min=int(document.get("market_fee_bps_min", defaults.market_fee_bps_min)),
        market_fee_bps_max=int(document.get("market_fee_bps_max", defaults.market_fee_bps_max)),
        ecosystem_target_regen_share=float(
            document.get("ecosystem_target_regen_share", defaults.ecosystem_target_regen_share)
        ),
        elite_regen_share_cap=float(document.get("elite_regen_share_cap", defaults.elite_regen_share_cap)),
        demand_cooling_floor=float(document.get("demand_cooling_floor", defaults.demand_cooling_floor)),
        regen_lifecycle_growth_months=int(
            document.get("regen_lifecycle_growth_months", defaults.regen_lifecycle_growth_months)
        ),
        regen_lifecycle_peak_months=int(
            document.get("regen_lifecycle_peak_months", defaults.regen_lifecycle_peak_months)
        ),
        regen_lifecycle_decline_months=int(
            document.get("regen_lifecycle_decline_months", defaults.regen_lifecycle_decline_months)
        ),
        regen_lifecycle_retirement_months=int(
            document.get("regen_lifecycle_retirement_months", defaults.regen_lifecycle_retirement_months)
        ),
        player_lifecycle_growth_max_age=int(
            document.get("player_lifecycle_growth_max_age", defaults.player_lifecycle_growth_max_age)
        ),
        player_lifecycle_peak_max_age=int(
            document.get("player_lifecycle_peak_max_age", defaults.player_lifecycle_peak_max_age)
        ),
        player_lifecycle_decline_max_age=int(
            document.get("player_lifecycle_decline_max_age", defaults.player_lifecycle_decline_max_age)
        ),
        lineage_base_probability=float(
            document.get("lineage_base_probability", defaults.lineage_base_probability)
        ),
        lineage_legend_probability=float(
            document.get("lineage_legend_probability", defaults.lineage_legend_probability)
        ),
        lineage_owner_probability=float(
            document.get("lineage_owner_probability", defaults.lineage_owner_probability)
        ),
        lineage_retired_regen_probability=float(
            document.get("lineage_retired_regen_probability", defaults.lineage_retired_regen_probability)
        ),
        lineage_hometown_probability=float(
            document.get("lineage_hometown_probability", defaults.lineage_hometown_probability)
        ),
        twin_probability=float(document.get("twin_probability", defaults.twin_probability)),
        owner_son_lifetime_cap=int(document.get("owner_son_lifetime_cap", defaults.owner_son_lifetime_cap)),
        owner_son_rival_club_chance=float(
            document.get("owner_son_rival_club_chance", defaults.owner_son_rival_club_chance)
        ),
        owner_son_paid_request_base_cost=int(
            document.get("owner_son_paid_request_base_cost", defaults.owner_son_paid_request_base_cost)
        ),
        owner_son_paid_request_name_cost=int(
            document.get("owner_son_paid_request_name_cost", defaults.owner_son_paid_request_name_cost)
        ),
        owner_son_paid_request_customization_cost=int(
            document.get(
                "owner_son_paid_request_customization_cost",
                defaults.owner_son_paid_request_customization_cost,
            )
        ),
        owner_son_paid_request_limit=int(
            document.get("owner_son_paid_request_limit", defaults.owner_son_paid_request_limit)
        ),
        default_country_code=str(document.get("default_country_code", defaults.default_country_code)).strip().upper(),
        country_tuning=country_tuning,
    )
    if config.academy_intakes_per_season <= 0:
        raise ValueError("Regen config academy_intakes_per_season must be greater than zero.")
    if config.academy_intake_min_players <= 0:
        raise ValueError("Regen config academy_intake_min_players must be greater than zero.")
    if config.academy_intake_max_players < config.academy_intake_min_players:
        raise ValueError(
            "Regen config academy_intake_max_players must be greater than or equal to academy_intake_min_players."
        )
    if config.starter_regen_count <= 0:
        raise ValueError("Regen config starter_regen_count must be greater than zero.")
    if config.starter_age_max < config.starter_age_min:
        raise ValueError("Regen config starter_age_max must be greater than or equal to starter_age_min.")
    if config.starter_gsi_max < config.starter_gsi_min:
        raise ValueError("Regen config starter_gsi_max must be greater than or equal to starter_gsi_min.")
    if config.regen_lifecycle_growth_months <= 0:
        raise ValueError("Regen config regen_lifecycle_growth_months must be greater than zero.")
    if config.regen_lifecycle_peak_months < config.regen_lifecycle_growth_months:
        raise ValueError(
            "Regen config regen_lifecycle_peak_months must be greater than or equal to regen_lifecycle_growth_months."
        )
    if config.regen_lifecycle_decline_months < config.regen_lifecycle_peak_months:
        raise ValueError(
            "Regen config regen_lifecycle_decline_months must be greater than or equal to regen_lifecycle_peak_months."
        )
    if config.regen_lifecycle_retirement_months < config.regen_lifecycle_decline_months:
        raise ValueError(
            "Regen config regen_lifecycle_retirement_months must be greater than or equal to regen_lifecycle_decline_months."
        )
    if config.player_lifecycle_peak_max_age < config.player_lifecycle_growth_max_age:
        raise ValueError(
            "Regen config player_lifecycle_peak_max_age must be greater than or equal to player_lifecycle_growth_max_age."
        )
    if config.player_lifecycle_decline_max_age < config.player_lifecycle_peak_max_age:
        raise ValueError(
            "Regen config player_lifecycle_decline_max_age must be greater than or equal to player_lifecycle_peak_max_age."
        )
    if not 0 < config.seasonal_supply_cap_ratio <= 1:
        raise ValueError("Regen config seasonal_supply_cap_ratio must be between 0 and 1.")
    if not 0 <= config.base_elite_probability <= 1:
        raise ValueError("Regen config base_elite_probability must be between 0 and 1.")
    if not 0 <= config.max_elite_probability <= 1:
        raise ValueError("Regen config max_elite_probability must be between 0 and 1.")
    if config.base_elite_probability > config.max_elite_probability:
        raise ValueError("Regen config base_elite_probability must not exceed max_elite_probability.")
    if config.default_active_player_base <= 0:
        raise ValueError("Regen config default_active_player_base must be greater than zero.")
    if not 0 <= config.market_fee_bps_min <= config.market_fee_bps_default <= config.market_fee_bps_max <= 10_000:
        raise ValueError(
            "Regen config market fee bps must satisfy 0 <= min <= default <= max <= 10000."
        )
    if not 0 < config.ecosystem_target_regen_share < 1:
        raise ValueError("Regen config ecosystem_target_regen_share must be between 0 and 1.")
    if not 0 < config.elite_regen_share_cap < 1:
        raise ValueError("Regen config elite_regen_share_cap must be between 0 and 1.")
    if not 0 < config.demand_cooling_floor <= 1:
        raise ValueError("Regen config demand_cooling_floor must be between 0 and 1.")
    if not 0 <= config.lineage_base_probability <= 1:
        raise ValueError("Regen config lineage_base_probability must be between 0 and 1.")
    if not 0 <= config.lineage_legend_probability <= 1:
        raise ValueError("Regen config lineage_legend_probability must be between 0 and 1.")
    if not 0 <= config.lineage_owner_probability <= 1:
        raise ValueError("Regen config lineage_owner_probability must be between 0 and 1.")
    if not 0 <= config.lineage_retired_regen_probability <= 1:
        raise ValueError("Regen config lineage_retired_regen_probability must be between 0 and 1.")
    if not 0 <= config.lineage_hometown_probability <= 1:
        raise ValueError("Regen config lineage_hometown_probability must be between 0 and 1.")
    if not 0 <= config.twin_probability <= 1:
        raise ValueError("Regen config twin_probability must be between 0 and 1.")
    if config.owner_son_lifetime_cap < 0:
        raise ValueError("Regen config owner_son_lifetime_cap must be zero or greater.")
    if not 0 <= config.owner_son_rival_club_chance <= 1:
        raise ValueError("Regen config owner_son_rival_club_chance must be between 0 and 1.")
    if config.owner_son_paid_request_base_cost < 0:
        raise ValueError("Regen config owner_son_paid_request_base_cost must be zero or greater.")
    if config.owner_son_paid_request_name_cost < 0:
        raise ValueError("Regen config owner_son_paid_request_name_cost must be zero or greater.")
    if config.owner_son_paid_request_customization_cost < 0:
        raise ValueError("Regen config owner_son_paid_request_customization_cost must be zero or greater.")
    if config.owner_son_paid_request_limit <= 0:
        raise ValueError("Regen config owner_son_paid_request_limit must be greater than zero.")
    if len({item.country_code for item in config.country_tuning}) != len(config.country_tuning):
        raise ValueError("Regen config country_tuning country codes must be unique.")
    return config


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


def load_player_card_market_integrity_config(config_root: Path) -> PlayerCardMarketIntegrityConfig:
    document = _load_optional_toml_document(config_root / PLAYER_CARD_MARKET_INTEGRITY_FILE)
    defaults = _default_player_card_market_integrity_config()
    if document is None:
        return defaults

    config = PlayerCardMarketIntegrityConfig(
        sale_reference_lookback_days=int(
            document.get("sale_reference_lookback_days", defaults.sale_reference_lookback_days)
        ),
        minimum_reference_sales=int(document.get("minimum_reference_sales", defaults.minimum_reference_sales)),
        listing_price_floor_ratio=float(
            document.get("listing_price_floor_ratio", defaults.listing_price_floor_ratio)
        ),
        listing_price_ceiling_ratio=float(
            document.get("listing_price_ceiling_ratio", defaults.listing_price_ceiling_ratio)
        ),
        relist_cooldown_minutes=int(document.get("relist_cooldown_minutes", defaults.relist_cooldown_minutes)),
        pair_trade_lookback_hours=int(
            document.get("pair_trade_lookback_hours", defaults.pair_trade_lookback_hours)
        ),
        pair_trade_alert_threshold=int(
            document.get("pair_trade_alert_threshold", defaults.pair_trade_alert_threshold)
        ),
        asset_churn_window_hours=int(
            document.get("asset_churn_window_hours", defaults.asset_churn_window_hours)
        ),
        asset_churn_alert_threshold=int(
            document.get("asset_churn_alert_threshold", defaults.asset_churn_alert_threshold)
        ),
        circular_trade_window_hours=int(
            document.get("circular_trade_window_hours", defaults.circular_trade_window_hours)
        ),
        price_spike_alert_ratio=float(
            document.get("price_spike_alert_ratio", defaults.price_spike_alert_ratio)
        ),
        volume_cluster_window_minutes=int(
            document.get("volume_cluster_window_minutes", defaults.volume_cluster_window_minutes)
        ),
        volume_cluster_trade_threshold=int(
            document.get("volume_cluster_trade_threshold", defaults.volume_cluster_trade_threshold)
        ),
    )
    if config.sale_reference_lookback_days <= 0:
        raise ValueError("Player card market integrity sale_reference_lookback_days must be greater than zero.")
    if config.minimum_reference_sales <= 0:
        raise ValueError("Player card market integrity minimum_reference_sales must be greater than zero.")
    if not 0 < config.listing_price_floor_ratio <= 1:
        raise ValueError("Player card market integrity listing_price_floor_ratio must be between 0 and 1.")
    if config.listing_price_ceiling_ratio < 1:
        raise ValueError("Player card market integrity listing_price_ceiling_ratio must be at least 1.")
    if config.listing_price_ceiling_ratio <= config.listing_price_floor_ratio:
        raise ValueError(
            "Player card market integrity listing_price_ceiling_ratio must exceed listing_price_floor_ratio."
        )
    if config.relist_cooldown_minutes < 0:
        raise ValueError("Player card market integrity relist_cooldown_minutes must be greater than or equal to zero.")
    if config.pair_trade_lookback_hours <= 0:
        raise ValueError("Player card market integrity pair_trade_lookback_hours must be greater than zero.")
    if config.pair_trade_alert_threshold <= 1:
        raise ValueError("Player card market integrity pair_trade_alert_threshold must be greater than one.")
    if config.asset_churn_window_hours <= 0:
        raise ValueError("Player card market integrity asset_churn_window_hours must be greater than zero.")
    if config.asset_churn_alert_threshold <= 1:
        raise ValueError("Player card market integrity asset_churn_alert_threshold must be greater than one.")
    if config.circular_trade_window_hours <= 0:
        raise ValueError("Player card market integrity circular_trade_window_hours must be greater than zero.")
    if config.price_spike_alert_ratio <= 1:
        raise ValueError("Player card market integrity price_spike_alert_ratio must be greater than one.")
    if config.volume_cluster_window_minutes <= 0:
        raise ValueError("Player card market integrity volume_cluster_window_minutes must be greater than zero.")
    if config.volume_cluster_trade_threshold <= 1:
        raise ValueError("Player card market integrity volume_cluster_trade_threshold must be greater than one.")
    return config


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
        real_player_bridge_enabled=bool(document.get("real_player_bridge_enabled", False)),
        real_player_bridge_version=str(document.get("real_player_bridge_version", "real-player-bridge-v1")),
        real_player_bridge_smoothing_factor=float(document.get("real_player_bridge_smoothing_factor", 0.35)),
        real_player_bridge_floor_ratio=float(document.get("real_player_bridge_floor_ratio", 0.85)),
        real_player_bridge_ceiling_ratio=float(document.get("real_player_bridge_ceiling_ratio", 1.15)),
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
        real_player_bridge_reference_weights=_coerce_float_map(
            document.get("real_player_bridge_reference_weights", {}),
            name="real_player_bridge_reference_weights",
        ),
        real_player_bridge_tier_multipliers=_coerce_float_map(
            document.get("real_player_bridge_tier_multipliers", {}),
            name="real_player_bridge_tier_multipliers",
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
    if not 0 < weighting.real_player_bridge_smoothing_factor <= 1:
        raise ValueError("Value engine real_player_bridge_smoothing_factor must be between 0 and 1.")
    if not 0 < weighting.real_player_bridge_floor_ratio <= 1:
        raise ValueError("Value engine real_player_bridge_floor_ratio must be between 0 and 1.")
    if weighting.real_player_bridge_ceiling_ratio < 1:
        raise ValueError("Value engine real_player_bridge_ceiling_ratio must be greater than or equal to 1.")
    if weighting.real_player_bridge_ceiling_ratio < weighting.real_player_bridge_floor_ratio:
        raise ValueError(
            "Value engine real_player_bridge_ceiling_ratio must be greater than or equal to real_player_bridge_floor_ratio."
        )
    for key, value in weighting.real_player_bridge_reference_weights.items():
        if not 0 <= value <= 1:
            raise ValueError(
                f"Value engine real_player_bridge_reference_weights[{key}] must be between 0 and 1."
            )
    for key, value in weighting.real_player_bridge_tier_multipliers.items():
        if value <= 0:
            raise ValueError(
                f"Value engine real_player_bridge_tier_multipliers[{key}] must be greater than zero."
            )
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


def load_real_player_import_config(
    environ: Mapping[str, str],
    *,
    default_provider_name: str,
    default_timeout_seconds: int,
) -> RealPlayerImportConfig:
    cursor_key = environ.get("GTE_REAL_PLAYER_IMPORT_CURSOR_KEY", "real-player-directory").strip()
    return RealPlayerImportConfig(
        provider_name=environ.get("GTE_REAL_PLAYER_IMPORT_PROVIDER", default_provider_name).strip() or default_provider_name,
        batch_size=min(5000, max(1, _get_int(environ, "GTE_REAL_PLAYER_IMPORT_BATCH_SIZE", 1000))),
        max_pages_per_run=max(1, _get_int(environ, "GTE_REAL_PLAYER_IMPORT_MAX_PAGES_PER_RUN", 40)),
        rate_limit_per_minute=max(1, _get_int(environ, "GTE_REAL_PLAYER_IMPORT_RATE_LIMIT_PER_MINUTE", 120)),
        timeout_seconds=max(
            1,
            _get_int(environ, "GTE_REAL_PLAYER_IMPORT_TIMEOUT_SECONDS", default_timeout_seconds),
        ),
        cursor_key=cursor_key or "real-player-directory",
    )


def _normalized_optional_setting(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    return candidate or None


def load_email_config(environ: Mapping[str, str]) -> EmailConfig:
    use_tls = _get_bool(environ, "BREVO_SMTP_USE_TLS", True)
    use_ssl = _get_bool(environ, "BREVO_SMTP_USE_SSL", False)
    if use_tls and use_ssl:
        raise ValueError("BREVO SMTP transport cannot enable both TLS and SSL.")

    return EmailConfig(
        enabled=_get_bool(environ, "EMAIL_ENABLED", False),
        provider=environ.get("EMAIL_PROVIDER", "brevo_smtp").strip().lower(),
        from_address=environ.get("EMAIL_FROM_ADDRESS", "vidzimedialtd@gmail.com").strip(),
        from_name=environ.get("EMAIL_FROM_NAME", "GTEX").strip(),
        reply_to=_normalized_optional_setting(environ.get("EMAIL_REPLY_TO", "vidzimedialtd@gmail.com")),
        send_timeout_seconds=_get_int(environ, "EMAIL_SEND_TIMEOUT_SECONDS", 15),
        signup_confirmation_ttl_minutes=_get_int(environ, "EMAIL_CONFIRMATION_TTL_MINUTES", 1440),
        account_recovery_ttl_minutes=_get_int(environ, "ACCOUNT_RECOVERY_TTL_MINUTES", 30),
        signup_confirmation_url_base=_normalized_optional_setting(environ.get("EMAIL_CONFIRMATION_URL_BASE")),
        account_recovery_url_base=_normalized_optional_setting(environ.get("ACCOUNT_RECOVERY_URL_BASE")),
        brevo_smtp=BrevoSmtpConfig(
            host=environ.get("BREVO_SMTP_HOST", "smtp-relay.brevo.com").strip(),
            port=_get_int(environ, "BREVO_SMTP_PORT", 587),
            username=environ.get("BREVO_SMTP_USERNAME", "a21b41001@smtp-brevo.com").strip(),
            password=environ.get("BREVO_SMTP_PASSWORD", ""),
            use_tls=use_tls,
            use_ssl=use_ssl,
        ),
    )


def load_settings(
    *,
    environ: Mapping[str, str] | None = None,
    config_root: str | Path | None = None,
) -> Settings:
    resolved_environ = os.environ if environ is None else environ
    source = SettingsSource.model_validate(dict(resolved_environ))
    resolved_config_root = _resolve_config_root(
        resolved_environ,
        config_root if config_root is not None else source.config_root_override,
    )
    database_url = resolve_database_url(resolved_environ)
    return Settings(
        app_name=source.app_name,
        app_version=source.app_version,
        app_env=source.app_env,
        phase_marker=source.phase_marker,
        project_root=PROJECT_ROOT,
        backend_root=BACKEND_ROOT,
        config_root=resolved_config_root,
        database_url=database_url,
        database_read_url=resolve_database_read_url(resolved_environ, default_database_url=database_url),
        redis_url=source.redis_url,
        redis_event_channel=source.redis_event_channel,
        redis_realtime_channel=source.redis_realtime_channel,
        broadcast_delay_seconds=source.broadcast_delay_seconds,
        broadcast_presence_ttl_seconds=source.broadcast_presence_ttl_seconds,
        broadcast_presence_heartbeat_interval_seconds=source.broadcast_presence_heartbeat_interval_seconds,
        broadcast_max_pending_messages=source.broadcast_max_pending_messages,
        auth_secret=source.auth_secret,
        media_signing_secret=source.media_signing_secret,
        crypto_deposit_enabled=source.crypto_deposit_enabled,
        crypto_provider_key=source.crypto_provider_key,
        run_migration_check=source.run_migration_check,
        run_startup_seeding=source.run_startup_seeding,
        bootstrap_admin_enabled=source.bootstrap_admin_enabled,
        bootstrap_admin_email=_normalized_optional_setting(source.bootstrap_admin_email),
        bootstrap_admin_password=_normalized_optional_setting(source.bootstrap_admin_password),
        bootstrap_admin_username=_normalized_optional_setting(source.bootstrap_admin_username),
        bootstrap_admin_display_name=_normalized_optional_setting(source.bootstrap_admin_display_name),
        default_ingestion_provider=source.default_ingestion_provider,
        real_player_mapping_auto_create_missing_entities=source.real_player_mapping_auto_create_missing_entities,
        provider_timeout_seconds=source.provider_timeout_seconds,
        football_data_base_url=source.football_data_base_url,
        football_data_api_key=source.football_data_api_key,
        value_snapshot_lookback_days=source.value_snapshot_lookback_days,
        kafka_brokers=source.kafka_brokers,
        kafka_client_id=source.kafka_client_id,
        kafka_topic_prefix=source.kafka_topic_prefix,
        kafka_queue_consumer_group=source.kafka_queue_consumer_group,
        kafka_projection_consumer_group=source.kafka_projection_consumer_group,
        viral_event_consumer_group=source.viral_event_consumer_group,
        viral_event_batch_size=max(1, source.viral_event_batch_size),
        viral_event_batch_interval_ms=max(1, source.viral_event_batch_interval_ms),
        viral_event_queue_maxsize=max(1, source.viral_event_queue_maxsize),
        viral_event_topic_partitions=max(1, source.viral_event_topic_partitions),
        viral_event_topic_replication_factor=max(1, source.viral_event_topic_replication_factor),
        viral_event_dedupe_ttl_seconds=max(60, source.viral_event_dedupe_ttl_seconds),
        outbox_relay_enabled=source.outbox_relay_enabled,
        outbox_relay_batch_size=source.outbox_relay_batch_size,
        outbox_relay_poll_interval_ms=source.outbox_relay_poll_interval_ms,
        kafka_api_queue_consumer_enabled=source.kafka_api_queue_consumer_enabled,
        kafka_simulation_consumer_enabled=source.kafka_simulation_consumer_enabled,
        projection_workers_enabled=source.projection_workers_enabled,
        observability_metrics_enabled=source.observability_metrics_enabled,
        observability_metrics_port=source.observability_metrics_port,
        observability_log_json=source.observability_log_json,
        observability_tracing_enabled=source.observability_tracing_enabled,
        observability_otlp_traces_endpoint=source.observability_otlp_traces_endpoint,
        observability_trace_sample_ratio=source.observability_trace_sample_ratio,
        observability_service_name=source.observability_service_name,
        email=load_email_config(resolved_environ),
        real_player_import=load_real_player_import_config(
            resolved_environ,
            default_provider_name=source.default_ingestion_provider,
            default_timeout_seconds=source.provider_timeout_seconds,
        ),
        player_universe_weighting=load_player_universe_weighting_config(resolved_config_root),
        supply_tiers=load_supply_tiers_config(resolved_config_root),
        liquidity_bands=load_liquidity_bands_config(resolved_config_root),
        image_policy=load_image_policy_config(resolved_config_root),
        media_storage=load_media_storage_config(resolved_config_root, resolved_environ),
        sponsorship_inventory=load_sponsorship_inventory_config(resolved_config_root),
        regen_generation=load_regen_generation_config(resolved_config_root),
        suspicion_thresholds=load_suspicion_thresholds_config(resolved_config_root),
        player_card_market_integrity=load_player_card_market_integrity_config(resolved_config_root),
        value_engine_weighting=load_value_engine_weighting_config(resolved_config_root),
        live_commentary_llm_enabled=source.live_commentary_llm_enabled,
        live_commentary_llm_endpoint_url=source.live_commentary_llm_endpoint_url,
        live_commentary_llm_model=source.live_commentary_llm_model,
        live_commentary_llm_api_key=source.live_commentary_llm_api_key,
        live_commentary_llm_timeout_seconds=source.live_commentary_llm_timeout_seconds,
        live_commentary_max_llm_calls_per_match=max(
            0,
            source.live_commentary_max_llm_calls_per_match,
        ),
        live_commentary_memory_ttl_seconds=source.live_commentary_memory_ttl_seconds,
        social_content_llm_enabled=source.social_content_llm_enabled,
        social_content_llm_endpoint_url=source.social_content_llm_endpoint_url,
        social_content_llm_model=source.social_content_llm_model,
        social_content_llm_api_key=source.social_content_llm_api_key,
        social_content_llm_timeout_seconds=source.social_content_llm_timeout_seconds,
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
