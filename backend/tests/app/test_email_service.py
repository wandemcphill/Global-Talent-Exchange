from __future__ import annotations

import logging
import smtplib

import pytest

from app.core.config import BrevoSmtpConfig, EmailConfig
from app.services.email.email_service import EmailService
from app.services.email.providers.brevo_smtp_provider import BrevoSmtpProvider
from app.services.email.schemas import EmailMessage


def _email_config() -> EmailConfig:
    return EmailConfig(
        enabled=True,
        provider="brevo_smtp",
        from_address="vidzimedialtd@gmail.com",
        from_name="GTEX",
        reply_to="vidzimedialtd@gmail.com",
        send_timeout_seconds=15,
        signup_confirmation_ttl_minutes=1440,
        account_recovery_ttl_minutes=30,
        signup_confirmation_url_base="https://app.gtex.example/confirm-email",
        account_recovery_url_base="https://app.gtex.example/recover-account",
        brevo_smtp=BrevoSmtpConfig(
            host="smtp-relay.brevo.com",
            port=587,
            username="a21b41001@smtp-brevo.com",
            password="super-secret-password",
            use_tls=True,
            use_ssl=False,
        ),
    )


class RecordingSMTP:
    last_message = None
    last_login = None
    starttls_called = False

    def __init__(self, host: str, port: int, timeout: int | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> "RecordingSMTP":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def ehlo(self) -> None:
        return None

    def starttls(self) -> None:
        type(self).starttls_called = True

    def login(self, username: str, password: str) -> None:
        type(self).last_login = (username, password)

    def send_message(self, message) -> None:
        type(self).last_message = message


class FailingSMTP(RecordingSMTP):
    def login(self, username: str, password: str) -> None:
        raise RuntimeError(f"auth failed with {password}")


def test_brevo_provider_builds_multipart_message(monkeypatch) -> None:
    monkeypatch.setattr(smtplib, "SMTP", RecordingSMTP)
    provider = BrevoSmtpProvider(
        host="smtp-relay.brevo.com",
        port=587,
        username="a21b41001@smtp-brevo.com",
        password="super-secret-password",
        from_address="vidzimedialtd@gmail.com",
        from_name="GTEX",
        reply_to="vidzimedialtd@gmail.com",
        timeout_seconds=15,
        use_tls=True,
        use_ssl=False,
    )

    result = provider.send_email(
        message=EmailMessage(
            to_email="fan@example.com",
            subject="Confirm your GTEX account",
            text_body="Confirmation code: 123456",
            html_body="<p>Confirmation code: <strong>123456</strong></p>",
            reply_to="reply@example.com",
        )
    )

    assert result.success is True
    assert RecordingSMTP.starttls_called is True
    assert RecordingSMTP.last_login == ("a21b41001@smtp-brevo.com", "super-secret-password")
    assert RecordingSMTP.last_message["Subject"] == "Confirm your GTEX account"
    assert RecordingSMTP.last_message["To"] == "fan@example.com"
    assert RecordingSMTP.last_message["Reply-To"] == "reply@example.com"
    assert RecordingSMTP.last_message.get_body(preferencelist=("plain",)).get_content().strip() == "Confirmation code: 123456"
    assert "<strong>123456</strong>" in RecordingSMTP.last_message.get_body(preferencelist=("html",)).get_content()


def test_brevo_provider_redacts_secret_in_logs(monkeypatch, caplog) -> None:
    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)
    provider = BrevoSmtpProvider(
        host="smtp-relay.brevo.com",
        port=587,
        username="a21b41001@smtp-brevo.com",
        password="super-secret-password",
        from_address="vidzimedialtd@gmail.com",
        from_name="GTEX",
        reply_to="vidzimedialtd@gmail.com",
        timeout_seconds=15,
        use_tls=True,
        use_ssl=False,
    )

    with caplog.at_level(logging.WARNING):
        result = provider.send_email(
            message=EmailMessage(
                to_email="fan@example.com",
                subject="Recover your GTEX account",
                text_body="Recovery code: 654321",
                html_body="<p>Recovery code: <strong>654321</strong></p>",
            )
        )

    assert result.success is False
    assert "super-secret-password" not in caplog.text
    assert "[redacted]" in caplog.text


def test_email_service_returns_failure_safely_on_smtp_exception(monkeypatch) -> None:
    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)
    config = _email_config()
    service = EmailService(config=config)

    result = service.send_account_recovery_email(
        "fan@example.com",
        "recovery-code",
        recipient_name="Fan User",
        recovery_link="https://app.gtex.example/recover-account?code=recovery-code",
    )

    assert result.success is False
    assert result.provider == "brevo_smtp"
    assert result.error is not None
