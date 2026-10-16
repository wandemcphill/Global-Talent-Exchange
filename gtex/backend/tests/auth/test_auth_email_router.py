from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select

from backend.tests.support.secrets import (
    EMAIL_PROVIDER_TEST_PASSWORD,
    RECOVERY_TEST_PASSWORD,
    TEST_PASSWORD,
)
from app.core.config import BrevoSmtpConfig, EmailConfig
from app.main import create_app
from app.models.user import User
from app.services.email.email_service import EmailService
from app.services.email.providers.base import EmailProvider
from app.services.email.schemas import EmailMessage, EmailSendResult
from backend.tests.support.signup_payloads import user_signup_payload


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
            password=EMAIL_PROVIDER_TEST_PASSWORD,
            use_tls=True,
            use_ssl=False,
        ),
    )


class RecordingEmailProvider(EmailProvider):
    provider_name = "recording"

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send_email(self, *, message: EmailMessage) -> EmailSendResult:
        self.messages.append(message)
        return EmailSendResult(success=True, provider=self.provider_name, message_id=f"message-{len(self.messages)}")


class FailingEmailProvider(EmailProvider):
    provider_name = "failing"

    def send_email(self, *, message: EmailMessage) -> EmailSendResult:
        return EmailSendResult(success=False, provider=self.provider_name, error="smtp_down")


@pytest.fixture(scope="module")
def app_client(tmp_path_factory: pytest.TempPathFactory):
    database_url = (
        f"sqlite+pysqlite:///{(tmp_path_factory.mktemp('auth-email-router') / 'auth-email-router.db').as_posix()}"
    )
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        yield app, client
    engine.dispose()


def _build_email_service(provider: EmailProvider) -> EmailService:
    return EmailService(provider=provider, config=_email_config())


def _extract_code(message: EmailMessage) -> str:
    lines = [line.strip() for line in message.text_body.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if "code below" in line.lower():
            return lines[index + 1]
    raise AssertionError("Expected code line in email body.")


def test_user_signup_route_triggers_confirmation_email_and_preserves_signup_response(app_client) -> None:
    app, client = app_client
    provider = RecordingEmailProvider()
    app.state.email_service = _build_email_service(provider)

    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email="fan.confirm@example.com",
            username="fanconfirm",
            full_name="Fan User",
            password=TEST_PASSWORD,
        ),
    )

    assert response.status_code == 201, response.text
    assert response.json()["access_token"]
    assert response.json()["user"]["email"] == "fan.confirm@example.com"
    assert len(provider.messages) == 1
    assert provider.messages[0].subject == "Confirm your GTEX account"
    assert "Confirmation code" in provider.messages[0].html_body

    confirm_response = client.post("/auth/confirm-email", json={"code": _extract_code(provider.messages[0])})

    assert confirm_response.status_code == 200, confirm_response.text

    with app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "fan.confirm@example.com"))
        assert user is not None
        assert user.email_verified_at is not None


def test_recovery_request_triggers_email_and_reset_route_updates_password(app_client) -> None:
    app, client = app_client
    provider = RecordingEmailProvider()
    app.state.email_service = _build_email_service(provider)

    register_response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email="fan.recover@example.com",
            username="fanrecover",
            full_name="Fan User",
            password=TEST_PASSWORD,
        ),
    )
    assert register_response.status_code == 201, register_response.text
    provider.messages.clear()

    recovery_response = client.post("/auth/recovery/request", json={"email": "fan.recover@example.com"})

    assert recovery_response.status_code == 200, recovery_response.text
    assert (
        recovery_response.json()["detail"]
        == "If an account exists for that email, recovery instructions have been sent."
    )
    assert len(provider.messages) == 1
    assert provider.messages[0].subject == "Recover your GTEX account"
    assert "Recovery code" in provider.messages[0].html_body

    reset_response = client.post(
        "/auth/recovery/reset",
        json={
            "code": _extract_code(provider.messages[0]),
            "new_password": RECOVERY_TEST_PASSWORD,
            "confirm_new_password": RECOVERY_TEST_PASSWORD,
        },
    )
    assert reset_response.status_code == 200, reset_response.text

    login_response = client.post(
        "/auth/login",
        json={"email": "fan.recover@example.com", "password": RECOVERY_TEST_PASSWORD},
    )

    assert login_response.status_code == 200, login_response.text


def test_user_signup_route_does_not_fail_when_email_delivery_fails(app_client) -> None:
    app, client = app_client
    app.state.email_service = _build_email_service(FailingEmailProvider())

    response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email="fan.failure@example.com",
            username="fanfailure",
            full_name="Fan User",
            password=TEST_PASSWORD,
        ),
    )

    assert response.status_code == 201, response.text
    assert response.json()["user"]["email"] == "fan.failure@example.com"
