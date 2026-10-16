from __future__ import annotations

from pathlib import Path

from app.core.config import load_settings


def test_load_settings_reads_live_commentary_configuration() -> None:
    config_root = Path(__file__).resolve().parents[2] / "config"

    settings = load_settings(
        environ={
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_LIVE_COMMENTARY_LLM_ENABLED": "true",
            "GTE_LIVE_COMMENTARY_LLM_ENDPOINT_URL": "https://commentary.example.com/v1/responses",
            "GTE_LIVE_COMMENTARY_LLM_MODEL": "gpt-football-live",
            "GTE_LIVE_COMMENTARY_LLM_API_KEY": "test-key",
            "GTE_LIVE_COMMENTARY_LLM_TIMEOUT_SECONDS": "12",
            "GTE_LIVE_COMMENTARY_MAX_LLM_CALLS_PER_MATCH": "18",
            "GTE_LIVE_COMMENTARY_MEMORY_TTL_SECONDS": "900",
        },
        config_root=config_root,
    )

    assert settings.live_commentary_llm_enabled is True
    assert settings.live_commentary_llm_endpoint_url == "https://commentary.example.com/v1/responses"
    assert settings.live_commentary_llm_model == "gpt-football-live"
    assert settings.live_commentary_llm_api_key == "test-key"
    assert settings.live_commentary_llm_timeout_seconds == 12
    assert settings.live_commentary_max_llm_calls_per_match == 18
    assert settings.live_commentary_memory_ttl_seconds == 900
