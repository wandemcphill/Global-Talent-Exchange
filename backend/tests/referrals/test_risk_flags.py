from __future__ import annotations

from dataclasses import dataclass, replace

from app.schemas.creator_requests import CreatorProfileCreateRequest
from app.schemas.referral_requests import AttributionCaptureRequest, ShareCodeRedeemRequest
from app.services.referral_orchestrator import ReferralOrchestrator
from app.services.referral_risk_service import ReferralRiskContext, ReferralRiskService


@dataclass(frozen=True, slots=True)
class StubUser:
    id: str
    username: str
    display_name: str
    email: str
    role: str = "user"


def test_risk_service_flags_concentrated_bursts_low_retention_and_same_device_clusters() -> None:
    orchestrator = ReferralOrchestrator()
    creator = StubUser("user-alpha", "alpha", "Alpha Creator", "alpha@example.com")
    referred_users = [
        StubUser(f"user-r{index}", f"referred{index}", f"Referred {index}", f"r{index}@example.com")
        for index in range(1, 5)
    ]

    creator_profile = orchestrator.create_creator_profile(
        current_user=creator,
        payload=CreatorProfileCreateRequest.model_validate(
            {
                "handle": "alphaone",
                "display_name": "Alpha One",
                "tier": "featured",
                "status": "active",
                "default_competition_id": "comp-alpha",
                "revenue_share_percent": "15",
            }
        ),
    )
    share_code = creator_profile.default_share_code
    assert share_code is not None

    for user in referred_users:
        orchestrator.redeem_share_code(
            current_user=user,
            code=share_code,
            payload=ShareCodeRedeemRequest.model_validate(
                {
                    "source_channel": "community_post",
                    "campaign_name": "alpha-growth",
                    "linked_competition_id": "comp-alpha",
                }
            ),
        )
        orchestrator.capture_attribution(
            current_user=user,
            payload=AttributionCaptureRequest.model_validate(
                {
                    "share_code": share_code,
                    "source_channel": "community_post",
                    "milestone": "first_creator_competition_joined",
                    "campaign_name": "alpha-growth",
                    "linked_competition_id": "comp-alpha",
                }
            ),
        )

    with orchestrator.store.lock:
        rewards = list(orchestrator.store.rewards_by_id.values())
        for reward in rewards[:2]:
            orchestrator.store.rewards_by_id[reward.reward_id] = replace(
                reward,
                status="blocked",
                review_reason="manual_risk_hold",
                updated_at=reward.updated_at,
            )

    risk_service = ReferralRiskService(orchestrator)
    flags = risk_service.scan(
        user_contexts={
            referred_users[0].id: ReferralRiskContext(device_fingerprint="device-1"),
            referred_users[1].id: ReferralRiskContext(device_fingerprint="device-1"),
            referred_users[2].id: ReferralRiskContext(device_fingerprint="device-1"),
            referred_users[3].id: ReferralRiskContext(device_fingerprint="device-2"),
        }
    )
    flag_types = {flag.flag_type for flag in flags}

    assert "same_device_multi_account_cluster" in flag_types
    assert "redemption_concentration" in flag_types
    assert "instant_signup_join_burst" in flag_types
    assert "abnormal_low_retention" in flag_types
    assert "repeated_blocked_rewards" in flag_types
