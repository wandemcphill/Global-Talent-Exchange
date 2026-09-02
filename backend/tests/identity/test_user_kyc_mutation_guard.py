import pytest

from app.models.user import KycStatus, User
from app.users.service import UserService


def test_legacy_user_service_cannot_mutate_kyc_status():
    user = User(
        id="user-kyc-guard",
        email="kyc-guard@example.com",
        username="kyc-guard",
        password_hash="unused",
    )

    with pytest.raises(RuntimeError, match="IdentityComplianceService"):
        UserService().set_kyc_status(None, user, kyc_status=KycStatus.VERIFIED)
