from datetime import datetime, timedelta, timezone

import pytest

from app.identity.compliance_service import IdentityComplianceError, IdentityComplianceService, VerificationEvidence
from app.models.risk_ops import AuditLog
from app.models.user import KycStatus, User


class _Session:
    def __init__(self):
        self.added = []
        self.flush_count = 0

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_count += 1


def _user():
    return User(
        id="user-identity-test",
        email="identity-test@example.com",
        username="identity-test",
        password_hash="unused",
    )


def _evidence(**overrides):
    values = {
        "provider": "didit",
        "provider_subject": "didit-subject-123",
        "decision": "verified",
        "verified_at": datetime.now(timezone.utc) - timedelta(minutes=5),
        "checks": {"document": "pass", "face_match": "pass", "liveness": "pass"},
    }
    values.update(overrides)
    return VerificationEvidence(**values)


def test_verification_requires_didit_evidence():
    with pytest.raises(IdentityComplianceError):
        _evidence(provider="manual").validate()


def test_verification_rejects_expired_evidence():
    with pytest.raises(IdentityComplianceError):
        _evidence(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)).validate()


def test_verification_requires_explicit_verified_decision():
    with pytest.raises(IdentityComplianceError):
        _evidence(decision="pending").validate()


def test_verified_state_requires_and_records_provider_evidence():
    session = _Session()
    user = _user()

    IdentityComplianceService(session).verify(user=user, evidence=_evidence(), actor_user_id=user.id)

    assert user.kyc_status is KycStatus.VERIFIED
    assert session.flush_count == 1
    audit = next(item for item in session.added if isinstance(item, AuditLog))
    assert audit.action_key == "identity.kyc.verify"
    assert audit.metadata_json["provider"] == "didit"
    assert audit.metadata_json["provider_subject"] == "didit-subject-123"


def test_rejection_requires_reason_and_is_audited():
    session = _Session()
    user = _user()
    service = IdentityComplianceService(session)

    with pytest.raises(IdentityComplianceError):
        service.reject(user=user, reason=" ")

    service.reject(user=user, reason="document mismatch", actor_user_id=user.id)

    assert user.kyc_status is KycStatus.REJECTED
    audit = next(item for item in session.added if isinstance(item, AuditLog))
    assert audit.action_key == "identity.kyc.reject"
    assert audit.detail == "document mismatch"
