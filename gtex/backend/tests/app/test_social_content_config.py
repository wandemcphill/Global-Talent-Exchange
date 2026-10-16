from __future__ import annotations

from pathlib import Path

from app.core.config import load_settings


def test_load_settings_reads_social_content_llm_configuration() -> None:
    config_root = Path(__file__).resolve().parents[2] / "config"

    settings = load_settings(
        environ={
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "GTE_SOCIAL_CONTENT_LLM_ENABLED": "true",
            "GTE_SOCIAL_CONTENT_LLM_ENDPOINT_URL": "https://social.example.com/v1/responses",
            "GTE_SOCIAL_CONTENT_LLM_MODEL": "gpt-social-football",
            "GTE_SOCIAL_CONTENT_LLM_API_KEY": "social-key",
            "GTE_SOCIAL_CONTENT_LLM_TIMEOUT_SECONDS": "15",
        },
        config_root=config_root,
    )

    assert settings.social_content_llm_enabled is True
    assert settings.social_content_llm_endpoint_url == "https://social.example.com/v1/responses"
    assert settings.social_content_llm_model == "gpt-social-football"
    assert settings.social_content_llm_api_key == "social-key"
    assert settings.social_content_llm_timeout_seconds == 15
