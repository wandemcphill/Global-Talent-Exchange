from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.router import request_recovery_challenge, signup_player_frictionless
from app.auth.schemas import (
    AccountRecoveryQuestionResetRequest,
    AccountRecoveryRequest,
    DeviceTrustRequest,
    PlayerFrictionlessSignupRequest,
    RecoveryAnswerInput,
    RecoveryQuestionInput,
)
from app.auth.security import verify_password, verify_sensitive_secret
from app.auth.service import AuthService, InvalidCredentialsError, InvalidSessionError, SecurityCooldownError
from app.main import create_app
from app.models import AuthSession, Base, RecoveryQuestion, SecurityEvent, TrustedDevice
from app.models.user import User
from backend.tests.support.secrets import ALTERNATE_TEST_PASSWORD, TEST_PASSWORD


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _questions() -> list[RecoveryQuestionInput]:
    return [
        RecoveryQuestionInput(
            question="Which academy did I first train with?",
            answer="Ajegunle United Academy",
        ),
        RecoveryQuestionInput(
            question="What nickname did my first coach call me?",
            answer="Lefty",
        ),
    ]


def _player_payload_json(email: str = "player@example.com") -> dict[str, object]:
    return {
        "full_name": "Future Striker",
        "email": email,
        "password": TEST_PASSWORD,
        "country": "Nigeria",
        "preferred_position": "Forward",
        "date_of_birth": "2005-05-12",
        "pin": "1234",
        "recovery_questions": [
            {
                "question": "Which academy did I first train with?",
                "answer": "Ajegunle United Academy",
            },
            {
                "question": "What nickname did my first coach call me?",
                "answer": "Lefty",
            },
        ],
    }


def _player_payload(email: str = "player@example.com") -> PlayerFrictionlessSignupRequest:
    return PlayerFrictionlessSignupRequest(
        full_name="Future Striker",
        email=email,
        password=TEST_PASSWORD,
        phone_number=None,
        country="Nigeria",
        preferred_position="Forward",
        date_of_birth=date(2005, 5, 12),
        pin="1234",
        recovery_questions=_questions(),
        device=DeviceTrustRequest(
            device_id="ios-device-1",
            install_id="install-1",
            os="ios",
            device_model="iPhone",
            ip_region="NG-Lagos",
            biometric_enabled=True,
        ),
    )


def test_frictionless_player_signup_sets_pin_recovery_questions_and_trusted_device(session) -> None:
    response = signup_player_frictionless(_player_payload(), session)

    user = session.get(User, response.user.id)
    questions = session.scalars(select(RecoveryQuestion).where(RecoveryQuestion.user_id == response.user.id)).all()
    device = session.scalar(select(TrustedDevice).where(TrustedDevice.user_id == response.user.id))

    assert user is not None
    assert user.email == "player@example.com"
    assert user.country == "Nigeria"
    assert user.preferred_position == "Forward"
    assert user.pin_hash is not None
    assert user.pin_hash != "1234"
    assert verify_sensitive_secret("1234", user.pin_hash)
    assert len(questions) == 2
    assert all(question.answer_hash not in {"Ajegunle United Academy", "Lefty"} for question in questions)
    assert device is not None
    assert device.trusted is True
    assert device.biometric_enabled is True
    assert response.trusted_device_token
    assert response.trusted_device_id == "ios-device-1"
    assert response.device_trusted is True
    assert response.biometric_enabled is True


def test_frictionless_signup_rejects_generic_recovery_questions() -> None:
    with pytest.raises(ValidationError, match="custom football or personal recovery question"):
        PlayerFrictionlessSignupRequest(
            full_name="Future Striker",
            email="generic@example.com",
            password=TEST_PASSWORD,
            country="Nigeria",
            preferred_position="Forward",
            date_of_birth=date(2005, 5, 12),
            pin="1234",
            recovery_questions=[
                RecoveryQuestionInput(question="What is your favorite color?", answer="Blue"),
                RecoveryQuestionInput(question="Which academy did I first train with?", answer="Academy"),
            ],
        )


def test_recovery_questions_reset_password_and_revoke_existing_sessions(session) -> None:
    signup_response = signup_player_frictionless(_player_payload(email="recover@example.com"), session)
    challenge = request_recovery_challenge(AccountRecoveryRequest(email="recover@example.com"), session)

    assert [question.question for question in challenge.questions] == [
        "Custom recovery question 1",
        "Custom recovery question 2",
    ]

    reset_payload = AccountRecoveryQuestionResetRequest(
        email="recover@example.com",
        answers=[
            RecoveryAnswerInput(question_id=challenge.questions[0].id, answer="  ajegunle united academy  "),
            RecoveryAnswerInput(question_id=challenge.questions[1].id, answer="LEFTY"),
        ],
        pin="1234",
        new_password=ALTERNATE_TEST_PASSWORD,
        confirm_new_password=ALTERNATE_TEST_PASSWORD,
    )

    user = AuthService().reset_password_with_recovery_questions(session, payload=reset_payload)
    session.commit()

    auth_session = session.get(AuthSession, signup_response.session_id)
    assert verify_password(ALTERNATE_TEST_PASSWORD, user.password_hash)
    assert auth_session is not None
    assert auth_session.revoked_at is not None
    assert auth_session.revocation_reason == "account_recovery"
    with pytest.raises(InvalidSessionError):
        AuthService().refresh_session_tokens(session, refresh_token=signup_response.refresh_token)


def test_recovery_question_reset_rejects_wrong_pin(session) -> None:
    signup_player_frictionless(_player_payload(email="wrong-pin@example.com"), session)
    challenge = request_recovery_challenge(AccountRecoveryRequest(email="wrong-pin@example.com"), session)
    reset_payload = AccountRecoveryQuestionResetRequest(
        email="wrong-pin@example.com",
        answers=[
            RecoveryAnswerInput(question_id=challenge.questions[0].id, answer="Ajegunle United Academy"),
            RecoveryAnswerInput(question_id=challenge.questions[1].id, answer="Lefty"),
        ],
        pin="9999",
        new_password=ALTERNATE_TEST_PASSWORD,
        confirm_new_password=ALTERNATE_TEST_PASSWORD,
    )

    with pytest.raises(InvalidCredentialsError):
        AuthService().reset_password_with_recovery_questions(session, payload=reset_payload)

    events = session.scalars(select(SecurityEvent).where(SecurityEvent.event_type == "security_pin_failed")).all()
    assert len(events) == 1


def test_security_pin_failures_trigger_cooldown(session) -> None:
    signup_response = signup_player_frictionless(_player_payload(email="pin-lock@example.com"), session)
    user = session.get(User, signup_response.user.id)
    assert user is not None

    service = AuthService()
    for _ in range(5):
        with pytest.raises(InvalidCredentialsError):
            service.verify_security_pin(
                session,
                user=user,
                pin="9999",
                action_type="wallet.withdrawal.create",
            )

    with pytest.raises(SecurityCooldownError):
        service.verify_security_pin(
            session,
            user=user,
            pin="1234",
            action_type="wallet.withdrawal.create",
        )

    lock_events = session.scalars(select(SecurityEvent).where(SecurityEvent.event_type == "security_pin_locked")).all()
    assert len(lock_events) == 1


def test_fast_region_change_marks_new_device_suspicious(session) -> None:
    signup_response = signup_player_frictionless(_player_payload(email="risk@example.com"), session)
    user = session.get(User, signup_response.user.id)
    assert user is not None

    issued_session = AuthService().issue_session_tokens(
        user,
        session=session,
        device=DeviceTrustRequest(
            device_id="android-device-2",
            install_id="install-2",
            os="android",
            device_model="Pixel",
            ip_region="EU-East",
            biometric_enabled=False,
        ),
        ip_address="203.0.113.10",
    )

    device = session.scalar(
        select(TrustedDevice).where(
            TrustedDevice.user_id == user.id,
            TrustedDevice.device_id == "android-device-2",
        )
    )
    suspicious_events = session.scalars(
        select(SecurityEvent).where(SecurityEvent.event_type == "suspicious_login_detected")
    ).all()

    assert issued_session.device_trusted is False
    assert device is not None
    assert device.risk_score >= 80
    assert device.trusted is False
    assert len(suspicious_events) == 1


def test_duplicate_frictionless_signup_returns_conflict(session) -> None:
    signup_player_frictionless(_player_payload(email="dupe@example.com"), session)

    with pytest.raises(HTTPException) as exc_info:
        signup_player_frictionless(_player_payload(email="dupe@example.com"), session)

    assert exc_info.value.status_code == 409


def test_existing_trusted_device_requires_device_token(session) -> None:
    signup_response = signup_player_frictionless(_player_payload(email="device-token@example.com"), session)
    user = session.get(User, signup_response.user.id)
    assert user is not None
    assert signup_response.trusted_device_token is not None

    missing_token_session = AuthService().issue_session_tokens(
        user,
        session=session,
        device=DeviceTrustRequest(
            device_id="ios-device-1",
            install_id="ios-install-1",
            os="ios",
            device_model="iPhone",
            ip_region="NG-LA",
            biometric_enabled=True,
        ),
    )

    assert missing_token_session.trusted_device_token is None
    assert missing_token_session.device_trusted is False
    assert missing_token_session.biometric_enabled is False
    failed_events = session.scalars(
        select(SecurityEvent).where(SecurityEvent.event_type == "trusted_device_token_failed")
    ).all()
    assert len(failed_events) == 1

    matched_token_session = AuthService().issue_session_tokens(
        user,
        session=session,
        device=DeviceTrustRequest(
            device_id="ios-device-1",
            install_id="ios-install-1",
            os="ios",
            device_model="iPhone",
            ip_region="NG-LA",
            biometric_enabled=True,
            trusted_device_token=signup_response.trusted_device_token,
        ),
    )

    assert matched_token_session.trusted_device_token
    assert matched_token_session.device_trusted is True
    assert matched_token_session.biometric_enabled is True


def test_recovery_challenge_does_not_disclose_account_or_prompt_text() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = create_app(engine=engine, run_migration_check=False)
    with TestClient(app) as client:
        signup_response = client.post(
            "/api/v2/auth/signup/player",
            headers={"X-API-Version": "2"},
            json=_player_payload_json(email="privacy@example.com"),
        )
        assert signup_response.status_code == 201, signup_response.text

        known_response = client.post(
            "/api/v2/auth/recovery/challenge",
            headers={"X-API-Version": "2"},
            json={"email": "privacy@example.com"},
        )
        unknown_response = client.post(
            "/api/v2/auth/recovery/challenge",
            headers={"X-API-Version": "2"},
            json={"email": "missing@example.com"},
        )

        assert known_response.status_code == 200, known_response.text
        assert unknown_response.status_code == 200, unknown_response.text
        assert [question["question"] for question in known_response.json()["data"]["questions"]] == [
            "Custom recovery question 1",
            "Custom recovery question 2",
        ]
        assert [question["question"] for question in unknown_response.json()["data"]["questions"]] == [
            "Custom recovery question 1",
            "Custom recovery question 2",
        ]
        assert [question["id"] for question in known_response.json()["data"]["questions"]] == [
            "recovery-question-1",
            "recovery-question-2",
        ]
        assert [question["id"] for question in unknown_response.json()["data"]["questions"]] == [
            "recovery-question-1",
            "recovery-question-2",
        ]


def test_pin_failure_events_survive_api_error_rollbacks() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = create_app(engine=engine, run_migration_check=False)
    with TestClient(app) as client:
        signup_response = client.post(
            "/api/v2/auth/signup/player",
            headers={"X-API-Version": "2"},
            json=_player_payload_json(email="api-pin-fail@example.com"),
        )
        assert signup_response.status_code == 201, signup_response.text
        token = signup_response.json()["data"]["access_token"]
        headers = {"X-API-Version": "2", "Authorization": f"Bearer {token}"}

        for attempt in range(5):
            response = client.post(
                "/api/v2/auth/pin/verify",
                headers=headers,
                json={"pin": "9999", "action_type": "wallet.withdrawal.create"},
            )
            assert response.status_code == 401, (attempt, response.text)

        locked_response = client.post(
            "/api/v2/auth/pin/verify",
            headers=headers,
            json={"pin": "1234", "action_type": "wallet.withdrawal.create"},
        )
        assert locked_response.status_code == 429, locked_response.text


def test_recovery_failure_events_survive_api_error_rollbacks() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = create_app(engine=engine, run_migration_check=False)
    with TestClient(app) as client:
        signup_response = client.post(
            "/api/v2/auth/signup/player",
            headers={"X-API-Version": "2"},
            json=_player_payload_json(email="api-recovery-fail@example.com"),
        )
        assert signup_response.status_code == 201, signup_response.text
        challenge_response = client.post(
            "/api/v2/auth/recovery/challenge",
            headers={"X-API-Version": "2"},
            json={"email": "api-recovery-fail@example.com"},
        )
        assert challenge_response.status_code == 200, challenge_response.text
        questions = challenge_response.json()["data"]["questions"]

        payload = {
            "email": "api-recovery-fail@example.com",
            "answers": [
                {"question_id": questions[0]["id"], "answer": "wrong"},
                {"question_id": questions[1]["id"], "answer": "wrong"},
            ],
            "pin": "1234",
            "new_password": ALTERNATE_TEST_PASSWORD,
            "confirm_new_password": ALTERNATE_TEST_PASSWORD,
        }
        for attempt in range(5):
            response = client.post(
                "/api/v2/auth/recovery/reset-with-questions",
                headers={"X-API-Version": "2"},
                json=payload,
            )
            assert response.status_code == 400, (attempt, response.text)

        locked_response = client.post(
            "/api/v2/auth/recovery/reset-with-questions",
            headers={"X-API-Version": "2"},
            json=payload,
        )
        assert locked_response.status_code == 429, locked_response.text
