from __future__ import annotations

from pathlib import Path

from app.core.config import load_settings


def test_load_settings_reads_email_env_overrides() -> None:
    settings = load_settings(
        environ={
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "EMAIL_ENABLED": "true",
            "EMAIL_PROVIDER": "brevo_smtp",
            "EMAIL_FROM_ADDRESS": "vidzimedialtd@gmail.com",
            "EMAIL_FROM_NAME": "GTEX",
            "EMAIL_REPLY_TO": "vidzimedialtd@gmail.com",
            "BREVO_SMTP_HOST": "smtp-relay.brevo.com",
            "BREVO_SMTP_PORT": "587",
            "BREVO_SMTP_USERNAME": "a21b41001@smtp-brevo.com",
            "BREVO_SMTP_PASSWORD": "regenerated-key",
            "BREVO_SMTP_USE_TLS": "true",
            "BREVO_SMTP_USE_SSL": "false",
            "EMAIL_SEND_TIMEOUT_SECONDS": "15",
            "EMAIL_CONFIRMATION_TTL_MINUTES": "720",
            "ACCOUNT_RECOVERY_TTL_MINUTES": "45",
            "EMAIL_CONFIRMATION_URL_BASE": "https://app.gtex.example/confirm-email",
            "ACCOUNT_RECOVERY_URL_BASE": "https://app.gtex.example/recover-account",
        },
        config_root=(Path(__file__).resolve().parents[2] / "config"),
    )

    assert settings.email.enabled is True
    assert settings.email.provider == "brevo_smtp"
    assert settings.email.from_address == "vidzimedialtd@gmail.com"
    assert settings.email.from_name == "GTEX"
    assert settings.email.reply_to == "vidzimedialtd@gmail.com"
    assert settings.email.send_timeout_seconds == 15
    assert settings.email.signup_confirmation_ttl_minutes == 720
    assert settings.email.account_recovery_ttl_minutes == 45
    assert settings.email.signup_confirmation_url_base == "https://app.gtex.example/confirm-email"
    assert settings.email.account_recovery_url_base == "https://app.gtex.example/recover-account"
    assert settings.email.brevo_smtp.host == "smtp-relay.brevo.com"
    assert settings.email.brevo_smtp.port == 587
    assert settings.email.brevo_smtp.username == "a21b41001@smtp-brevo.com"
    assert settings.email.brevo_smtp.password == "regenerated-key"
    assert settings.email.brevo_smtp.use_tls is True
    assert settings.email.brevo_smtp.use_ssl is False
    assert "regenerated-key" not in repr(settings.email.brevo_smtp)
