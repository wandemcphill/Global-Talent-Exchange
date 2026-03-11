from __future__ import annotations

from pathlib import Path
import textwrap

from backend.app.core.config import DEFAULT_DATABASE_URL, load_settings
from backend.app.core.database import get_target_metadata
from backend.app.value_engine.scoring import ValueEngine


def _write_config(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_load_settings_reads_file_backed_product_configs(tmp_path: Path) -> None:
    _write_config(
        tmp_path / "player_universe_weighting.toml",
        """
        target_player_count = 100000
        rebalance_interval_hours = 12

        [weights]
        performance = 0.40
        projected_ceiling = 0.35
        market_interest = 0.25

        [age_curve_multipliers]
        u21 = 1.15
        prime = 1.00

        [competition_tier_multipliers]
        elite = 1.20
        pro = 1.00
        """,
    )
    _write_config(
        tmp_path / "supply_tiers.toml",
        """
        [[tiers]]
        name = "elite"
        min_score = 0.80
        max_score = 1.00
        target_share = 0.30
        circulating_supply = 240
        daily_pack_supply = 6
        season_mint_cap = 300

        [[tiers]]
        name = "core"
        min_score = 0.00
        max_score = 0.7999
        target_share = 0.70
        circulating_supply = 600
        daily_pack_supply = 18
        season_mint_cap = 1200
        """,
    )
    _write_config(
        tmp_path / "liquidity_bands.toml",
        """
        [[bands]]
        name = "entry"
        min_price_credits = 0
        max_price_credits = 99
        max_spread_bps = 1200
        maker_inventory_target = 30
        instant_sell_fee_bps = 1000

        [[bands]]
        name = "prime"
        min_price_credits = 100
        max_spread_bps = 500
        maker_inventory_target = 70
        instant_sell_fee_bps = 650
        """,
    )
    _write_config(
        tmp_path / "image_policy.toml",
        """
        [source]
        source_mode = "licensed-only"
        moderation_required = true
        allowed_formats = ["jpeg", "webp"]
        max_source_bytes = 4000000

        [processing]
        watermark_enabled = false
        max_width = 1600
        max_height = 2000
        default_variant = "card"

        [[variants]]
        name = "card"
        width = 768
        height = 1024
        format = "webp"
        fit = "contain"
        """,
    )
    _write_config(
        tmp_path / "value_engine_weighting.toml",
        """
        baseline_eur_per_credit = 95000
        smoothing_factor = 0.65
        daily_movement_cap = 0.10
        demand_movement_cap = 0.04
        market_signal_cap = 0.16
        gsi_neutral_score = 48.0
        gsi_smoothing_factor = 1.0
        gsi_daily_movement_cap = 0.28
        gsi_signal_cap = 0.40
        gsi_signal_scale = 120.0
        gsi_anchor_pull_strength = 0.10
        anchor_pull_strength = 0.18
        market_price_pull_strength = 0.60
        default_liquidity_weight = 0.22
        minimum_floor_ratio = 0.58
        performance_scale = 800.0
        award_scale = 500.0
        transfer_scale = 850.0
        demand_scale = 1000.0
        big_moment_bonus = 21.0

        [competition_multipliers]
        "world cup" = 1.4

        [award_impacts]
        ballon_dor_winner = 88.0

        [demand_weights]
        purchases = 7.0
        sales = 5.5
        shortlist_adds = 3.0
        watchlist_adds = 1.5
        follows = 0.6

        [gsi_signal_weights]
        watchlist_adds = 2.2
        shortlist_adds = 4.0
        transfer_room_adds = 5.8
        scouting_activity = 6.4

        [liquidity_band_market_weights]
        entry = 0.15
        marquee = 0.80

        [ftv_msv_blend_weights]
        ftv_weight = 0.62
        msv_weight = 0.38

        [[price_band_limits]]
        code = "default"
        min_ratio = 0.82
        max_ratio = 1.18

        [[price_band_limits]]
        code = "marquee"
        min_ratio = 0.74
        max_ratio = 1.28
        """,
    )
    _write_config(
        tmp_path / "suspicion_thresholds.toml",
        """
        player_min_suspicious_events = 12
        player_min_suspicious_share = 0.30
        player_price_band_breach_ratio = 0.08
        cluster_min_member_count = 4
        cluster_min_interaction_count = 7
        cluster_max_asset_count = 3
        thin_market_min_price_credits = 200
        thin_market_max_pending_offers = 1
        thin_market_max_active_trade_intents = 1
        holder_concentration_min_assets = 4
        holder_concentration_share = 0.55
        circular_trade_min_cycle_length = 3
        circular_trade_min_repetitions = 2
        """,
    )

    settings = load_settings(environ={}, config_root=tmp_path)

    assert settings.config_root == tmp_path.resolve()
    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.player_universe_weighting.rebalance_interval_hours == 12
    assert settings.player_universe_weighting.weights["performance"] == 0.40
    assert settings.supply_tiers.tiers[0].code == "elite"
    assert settings.supply_tiers.tiers[0].name == "elite"
    assert settings.liquidity_bands.bands[0].code == "entry"
    assert settings.liquidity_bands.bands[-1].max_price_credits is None
    assert settings.image_policy.default_variant == "card"
    assert settings.suspicion_thresholds.player_min_suspicious_events == 12
    assert settings.suspicion_thresholds.holder_concentration_share == 0.55
    assert settings.value_engine_weighting.baseline_eur_per_credit == 95_000
    assert settings.value_engine_weighting.big_moment_bonus == 21.0
    assert settings.value_engine_weighting.market_signal_cap == 0.16
    assert settings.value_engine_weighting.gsi_neutral_score == 48.0
    assert settings.value_engine_weighting.gsi_signal_weights["transfer_room_adds"] == 5.8
    assert settings.value_engine_weighting.liquidity_band_market_weights["marquee"] == 0.80
    assert settings.value_engine_weighting.ftv_weight == 0.62
    assert settings.value_engine_weighting.msv_weight == 0.38
    assert settings.value_engine_weighting.price_band_limits[-1].code == "marquee"
    assert settings.value_engine_weighting.price_band_limits[-1].max_ratio == 1.28


def test_default_supply_config_reduces_supply_for_obscure_players() -> None:
    settings = load_settings()
    supply_by_code = {tier.code: tier for tier in settings.supply_tiers.tiers}

    assert supply_by_code["discovery"].circulating_supply < supply_by_code["prospect"].circulating_supply
    assert supply_by_code["prospect"].circulating_supply < supply_by_code["elite"].circulating_supply
    assert supply_by_code["elite"].circulating_supply < supply_by_code["icon"].circulating_supply


def test_target_metadata_includes_phase_one_read_models() -> None:
    metadata = get_target_metadata()

    assert "player_summary_read_models" in metadata.tables
    assert "market_summary_read_models" in metadata.tables
    assert "player_value_snapshots" in metadata.tables


def test_value_engine_uses_central_value_weighting_config() -> None:
    engine = ValueEngine()
    settings = load_settings()

    assert engine.config.baseline_eur_per_credit == settings.value_engine_weighting.baseline_eur_per_credit
    assert engine.config.competition_multipliers["world cup"] == settings.value_engine_weighting.competition_multipliers["world cup"]
