from datetime import datetime, timedelta, timezone

import pytest

from app.identity.compliance_service import IdentityComplianceError, IdentityComplianceService, VerificationEvidence
from app.models.user import KycStatus


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


def test_verified_state_is_written_with_audit_record(db_session, user_factory):
    user = user_factory()
    service = IdentityComplianceService(db_session)

    service.verify(user=user, evidence=_evidence(), actor_user_id=user.id)
    db_session.commit()
    db_session.refresh(user)

    assert user.kyc_status is KycStatus.VERIFIED
    audit = db_session.query(__import__("app.models.risk_ops", fromlist=["AuditLog"]).AuditLog).filter_by(
        action_key="identity.kyc.verify", resource_id=user.id
    ).one()
    assert audit.metadata_json["provider"] == "didit"
    assert audit.metadata_json["provider_subject"] == "didit-subject-123"


def test_rejection_requires_reason_and_audits(db_session, user_factory):
    user = user_factory()
    service = IdentityComplianceService(db_session)

    with pytest.raises(IdentityComplianceError):
        service.reject(user=user, reason=" ")

    service.reject(user=user, reason="document mismatch", actor_user_id=user.id)
    db_session.commit()
    db_session.refresh(user)

    assert user.kyc_status is KycStatus.REJECTED
