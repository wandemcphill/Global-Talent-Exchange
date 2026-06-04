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

API_V2_HEADERS = {"X-API-Version": "2"}


def _response_data(response) -> dict[str, object]:
    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


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


def _player_signup_payload(*, email: str, full_name: str = "Fan User", password: str = TEST_PASSWORD) -> dict[str, object]:
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "country": "NG",
        "preferred_position": "Forward",
        "date_of_birth": "2006-05-12",
        "pin": "2718",
        "recovery_questions": [
            {
                "question": "Which academy did I first train with?",
                "answer": "Surulere Stars",
            },
            {
                "question": "What nickname did my first coach call me?",
                "answer": "Flash",
            },
        ],
    }


def test_player_signup_route_preserves_response_without_confirmation_email(app_client) -> None:
    app, client = app_client
    provider = RecordingEmailProvider()
    app.state.email_service = _build_email_service(provider)

    response = client.post(
        "/api/v2/auth/signup/player",
        json=_player_signup_payload(
            email="fan.confirm@example.com",
            full_name="Fan User",
            password=TEST_PASSWORD,
        ),
        headers=API_V2_HEADERS,
    )

    assert response.status_code == 201, response.text
    payload = _response_data(response)
    assert payload["access_token"]
    assert payload["user"]["email"] == "fan.confirm@example.com"
    assert provider.messages == []

    with app.state.session_factory() as session:
        user = session.scalar(select(User).where(User.email == "fan.confirm@example.com"))
        assert user is not None
        assert user.email_verified_at is None


def test_recovery_request_triggers_email_and_reset_route_updates_password(app_client) -> None:
    app, client = app_client
    provider = RecordingEmailProvider()
    app.state.email_service = _build_email_service(provider)

    register_response = client.post(
        "/api/v2/auth/signup/player",
        json=_player_signup_payload(
            email="fan.recover@example.com",
            full_name="Fan User",
            password=TEST_PASSWORD,
        ),
        headers=API_V2_HEADERS,
    )
    assert register_response.status_code == 201, register_response.text
    provider.messages.clear()

    recovery_response = client.post(
        "/api/v2/auth/recovery/request",
        json={"email": "fan.recover@example.com"},
        headers=API_V2_HEADERS,
    )

    assert recovery_response.status_code == 200, recovery_response.text
    assert (
        _response_data(recovery_response)["detail"]
        == "If an account exists for that email, recovery instructions have been sent."
    )
    assert len(provider.messages) == 1
    assert provider.messages[0].subject == "Recover your GTEX account"
    assert "Recovery code" in provider.messages[0].html_body

    reset_response = client.post(
        "/api/v2/auth/recovery/reset",
        json={
            "code": _extract_code(provider.messages[0]),
            "new_password": RECOVERY_TEST_PASSWORD,
            "confirm_new_password": RECOVERY_TEST_PASSWORD,
        },
        headers=API_V2_HEADERS,
    )
    assert reset_response.status_code == 200, reset_response.text

    login_response = client.post(
        "/api/v2/auth/login",
        json={"email": "fan.recover@example.com", "password": RECOVERY_TEST_PASSWORD},
        headers=API_V2_HEADERS,
    )

    assert login_response.status_code == 200, login_response.text


def test_player_signup_route_does_not_depend_on_email_delivery(app_client) -> None:
    app, client = app_client
    app.state.email_service = _build_email_service(FailingEmailProvider())

    response = client.post(
        "/api/v2/auth/signup/player",
        json=_player_signup_payload(
            email="fan.failure@example.com",
            full_name="Fan User",
            password=TEST_PASSWORD,
        ),
        headers=API_V2_HEADERS,
    )

    assert response.status_code == 201, response.text
    assert _response_data(response)["user"]["email"] == "fan.failure@example.com"
