from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.app.services.referral_rule_engine import ReferralRuleEngine
from backend.app.schemas.creator_core import CreatorProfileCore
from backend.app.schemas.referral_core import (
    ReferralAttributionCore,
    ReferralEventCore,
    ReferralRewardPolicy,
    ReferralValidationResult,
)
from backend.app.schemas.share_code_core import ShareCodeCore


def _attribution() -> ReferralAttributionCore:
    return ReferralAttributionCore.model_validate(
        {
            "referred_user_id": "user-9",
            "referrer_user_id": "user-1",
            "creator_profile_id": "creator-1",
            "share_code_id": "share-1",
            "source_channel": "creator_profile",
            "first_touch_at": datetime(2026, 3, 12, 9, 0, tzinfo=timezone.utc),
            "attribution_status": "qualified",
        }
    )


def _creator_profile() -> CreatorProfileCore:
    return CreatorProfileCore.model_validate(
        {
            "creator_profile_id": "creator-1",
            "user_id": "user-1",
            "handle": "creatorone",
            "display_name": "Creator One",
            "status": "active",
        }
    )


def _share_code() -> ShareCodeCore:
    return ShareCodeCore.model_validate(
        {
            "code": "CREATOR01",
            "code_type": "creator_share",
            "owner_user_id": "user-1",
            "owner_creator_id": "creator-1",
            "is_active": True,
            "current_uses": 0,
        }
    )


def test_rule_engine_builds_holdback_and_creator_revshare_rewards_for_qualified_participation() -> None:
    engine = ReferralRuleEngine()
    event = ReferralEventCore.model_validate(
        {
            "event_key": "event-creator-join-1",
            "event_type": "first_creator_competition_joined",
            "referred_user_id": "user-9",
            "referrer_user_id": "user-1",
            "creator_profile_id": "creator-1",
            "share_code_id": "share-1",
            "source_channel": "creator_profile",
            "occurred_at": datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc),
            "verified": True,
        }
    )
    policies = (
        ReferralRewardPolicy.model_validate(
            {
                "event_type": "first_creator_competition_joined",
                "reward_type": "wallet_credit",
                "beneficiary": "referrer_user",
                "amount": "25.00",
                "unit": "credit",
                "hold_days": 3,
            }
        ),
        ReferralRewardPolicy.model_validate(
            {
                "event_type": "first_creator_competition_joined",
                "reward_type": "creator_revshare",
                "beneficiary": "creator_profile",
                "amount": "12.50",
                "unit": "percent",
            }
        ),
    )
    validation = ReferralValidationResult.model_validate(
        {
            "is_valid": True,
            "attribution_status": "qualified",
            "resolved_referrer_user_id": "user-1",
            "resolved_creator_profile_id": "creator-1",
        }
    )

    evaluation = engine.evaluate_event(
        attribution=_attribution(),
        event=event,
        policies=policies,
        validation=validation,
        creator_profile=_creator_profile(),
        share_code=_share_code(),
    )

    assert evaluation.blocked_reason_codes == ()
    assert len(evaluation.rewards) == 2
    assert evaluation.rewards[0].status.value == "pending"
    assert evaluation.rewards[0].hold_until == event.occurred_at + timedelta(days=7)
    assert evaluation.rewards[0].amount == Decimal("25.00")
    assert evaluation.rewards[1].status.value == "approved"
    assert evaluation.rewards[1].beneficiary_creator_id == "creator-1"
    assert len(evaluation.ledger_entries) == 3


def test_rule_engine_does_not_issue_signup_reward_without_explicit_low_value_policy() -> None:
    engine = ReferralRuleEngine()
    event = ReferralEventCore.model_validate(
        {
            "event_key": "event-signup-1",
            "event_type": "signup_completed",
            "referred_user_id": "user-9",
            "source_channel": "direct_share",
            "occurred_at": datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc),
            "verified": True,
        }
    )
    policies = (
        ReferralRewardPolicy.model_validate(
            {
                "event_type": "signup_completed",
                "reward_type": "points",
                "beneficiary": "referred_user",
                "amount": "50",
                "unit": "points",
            }
        ),
    )

    evaluation = engine.evaluate_event(
        attribution=_attribution(),
        event=event,
        policies=policies,
        validation=ReferralValidationResult.model_validate(
            {"is_valid": True, "attribution_status": "qualified"}
        ),
    )

    assert evaluation.rewards == ()
    assert "signup_reward_not_allowed" in evaluation.blocked_reason_codes


def test_rule_engine_flags_fraudged_rewards_for_reviewable_blocking() -> None:
    engine = ReferralRuleEngine()
    event = ReferralEventCore.model_validate(
        {
            "event_key": "event-wallet-1",
            "event_type": "wallet_funded",
            "referred_user_id": "user-9",
            "referrer_user_id": "user-1",
            "source_channel": "community_invite",
            "occurred_at": datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc),
            "verified": True,
            "fraud_suspected": True,
        }
    )
    policies = (
        ReferralRewardPolicy.model_validate(
            {
                "event_type": "wallet_funded",
                "reward_type": "points",
                "beneficiary": "referrer_user",
                "amount": "150",
                "unit": "points",
            }
        ),
    )

    evaluation = engine.evaluate_event(
        attribution=_attribution(),
        event=event,
        policies=policies,
        validation=ReferralValidationResult.model_validate(
            {
                "is_valid": True,
                "attribution_status": "qualified",
                "resolved_referrer_user_id": "user-1",
            }
        ),
    )

    assert len(evaluation.rewards) == 1
    assert evaluation.rewards[0].status.value == "blocked"
    assert evaluation.rewards[0].review_reason is not None
    assert len(evaluation.ledger_entries) == 2
    assert evaluation.ledger_entries[-1].entry_type == "review_flagged"
