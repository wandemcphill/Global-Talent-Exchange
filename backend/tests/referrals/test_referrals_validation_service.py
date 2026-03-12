from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app.services.referral_validation_service import ReferralValidationService
from backend.app.schemas.creator_core import CreatorProfileCore
from backend.app.schemas.share_code_core import ShareCodeCore


def test_validation_service_blocks_self_referral_for_user_and_creator_owner() -> None:
    service = ReferralValidationService()
    creator_profile = CreatorProfileCore.model_validate(
        {
            "creator_profile_id": "creator-1",
            "user_id": "user-1",
            "handle": "creatorone",
            "display_name": "Creator One",
            "status": "active",
        }
    )
    share_code = ShareCodeCore.model_validate(
        {
            "code": "SELF01",
            "code_type": "creator_share",
            "owner_user_id": "user-1",
            "owner_creator_id": "creator-1",
            "is_active": True,
            "current_uses": 0,
        }
    )

    result = service.validate_attribution(
        referred_user_id="user-1",
        share_code=share_code,
        creator_profile=creator_profile,
    )

    assert result.is_valid is False
    assert result.attribution_status == "blocked"
    assert "self_referral_blocked" in result.reason_codes
    assert "owner_self_referral_blocked" in result.reason_codes
    assert "creator_self_referral_blocked" in result.reason_codes


def test_validation_service_blocks_inactive_expired_and_exhausted_share_codes() -> None:
    service = ReferralValidationService()
    share_code = ShareCodeCore.model_validate(
        {
            "code": "COMMUNITY01",
            "code_type": "competition_invite",
            "is_active": False,
            "max_uses": 2,
            "current_uses": 2,
            "ends_at": datetime.now(timezone.utc) - timedelta(days=1),
        }
    )

    result = service.validate_attribution(
        referred_user_id="user-9",
        share_code=share_code,
    )

    assert result.is_valid is False
    assert result.attribution_status == "blocked"
    assert "share_code_inactive" in result.reason_codes
    assert "share_code_expired" in result.reason_codes
    assert "share_code_exhausted" in result.reason_codes


def test_validation_service_resolves_valid_creator_share_attribution() -> None:
    service = ReferralValidationService()
    creator_profile = CreatorProfileCore.model_validate(
        {
            "creator_profile_id": "creator-9",
            "user_id": "referrer-9",
            "handle": "communitycaptain",
            "display_name": "Community Captain",
            "status": "active",
        }
    )
    share_code = ShareCodeCore.model_validate(
        {
            "code": "CAPTAIN9",
            "code_type": "creator_share",
            "owner_user_id": "referrer-9",
            "owner_creator_id": "creator-9",
            "is_active": True,
            "current_uses": 1,
            "max_uses": 10,
            "starts_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "ends_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
        }
    )

    result = service.validate_attribution(
        referred_user_id="user-44",
        share_code=share_code,
        creator_profile=creator_profile,
        occurred_at=datetime(2026, 3, 12, tzinfo=timezone.utc),
    )

    assert result.is_valid is True
    assert result.attribution_status == "qualified"
    assert result.resolved_referrer_user_id == "referrer-9"
    assert result.resolved_creator_profile_id == "creator-9"
    assert result.reason_codes == ()
