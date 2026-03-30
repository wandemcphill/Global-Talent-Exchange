from __future__ import annotations

from pathlib import Path

from app.core.config import load_settings


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"


def test_real_player_import_config_inherits_global_provider_defaults() -> None:
    settings = load_settings(
        environ={
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_INGESTION_PROVIDER": "football-data",
            "GTE_PROVIDER_TIMEOUT_SECONDS": "45",
        },
        config_root=CONFIG_ROOT,
    )

    assert settings.real_player_import.provider_name == "football-data"
    assert settings.real_player_import.batch_size == 1000
    assert settings.real_player_import.max_pages_per_run == 40
    assert settings.real_player_import.rate_limit_per_minute == 120
    assert settings.real_player_import.timeout_seconds == 45
    assert settings.real_player_import.cursor_key == "real-player-directory"


def test_real_player_import_config_honors_overrides_and_clamps_invalid_values() -> None:
    settings = load_settings(
        environ={
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_INGESTION_PROVIDER": "mock",
            "GTE_PROVIDER_TIMEOUT_SECONDS": "30",
            "GTE_REAL_PLAYER_IMPORT_PROVIDER": "curated-feed",
            "GTE_REAL_PLAYER_IMPORT_BATCH_SIZE": "9000",
            "GTE_REAL_PLAYER_IMPORT_MAX_PAGES_PER_RUN": "-3",
            "GTE_REAL_PLAYER_IMPORT_RATE_LIMIT_PER_MINUTE": "-50",
            "GTE_REAL_PLAYER_IMPORT_TIMEOUT_SECONDS": "0",
            "GTE_REAL_PLAYER_IMPORT_CURSOR_KEY": "   ",
        },
        config_root=CONFIG_ROOT,
    )

    assert settings.real_player_import.provider_name == "curated-feed"
    assert settings.real_player_import.batch_size == 5000
    assert settings.real_player_import.max_pages_per_run == 1
    assert settings.real_player_import.rate_limit_per_minute == 1
    assert settings.real_player_import.timeout_seconds == 1
    assert settings.real_player_import.cursor_key == "real-player-directory"


def test_real_player_import_defaults_to_api_sports_when_key_is_present() -> None:
    settings = load_settings(
        environ={
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_INGESTION_PROVIDER": "mock",
            "API_SPORTS_API_KEY": "test-api-sports-key",
            "API_SPORTS_BASE_URL": "https://v3.football.api-sports.io",
        },
        config_root=CONFIG_ROOT,
    )

    assert settings.api_sports_api_key == "test-api-sports-key"
    assert settings.api_sports_base_url == "https://v3.football.api-sports.io"
    assert settings.real_player_import.provider_name == "api_sports"
