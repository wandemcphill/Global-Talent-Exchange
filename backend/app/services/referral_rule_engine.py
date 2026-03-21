from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.common.enums.referral_event_type import ReferralEventType
from app.common.enums.referral_reward_status import ReferralRewardStatus
from app.common.enums.referral_reward_type import ReferralRewardType
from app.schemas.creator_core import CreatorProfileCore
from app.schemas.referral_core import (
    ReferralAttributionCore,
    ReferralEventCore,
    ReferralRewardComputation,
    ReferralRewardEvaluation,
    ReferralRewardLedgerEntryCore,
    ReferralRewardPolicy,
    ReferralValidationResult,
)
from app.schemas.share_code_core import ShareCodeCore

_CURRENCY_QUANTUM = Decimal("0.01")


@dataclass(slots=True)
class ReferralRuleEngine:
    """GTEX creator sharing and referral rewards are community-growth mechanics tied to qualified participation milestones in skill-based competitions and platform activity, not house-banked wagering or cash-settled event prediction."""

    default_wallet_credit_hold_days: int = 7

    def evaluate_event(
        self,
        *,
        attribution: ReferralAttributionCore,
        event: ReferralEventCore,
        policies: tuple[ReferralRewardPolicy, ...],
        validation: ReferralValidationResult | None = None,
        creator_profile: CreatorProfileCore | None = None,
        share_code: ShareCodeCore | None = None,
    ) -> ReferralRewardEvaluation:
        blocked_reasons = list(validation.reason_codes if validation is not None else ())
        if attribution.attribution_status in {"blocked", "superseded"}:
            blocked_reasons.append("attribution_not_qualified")

        reward_entries: list[ReferralRewardComputation] = []
        ledger_entries: list[ReferralRewardLedgerEntryCore] = []

        for policy in policies:
            if policy.event_type != event.event_type:
                continue

            policy_blockers: list[str] = []
            if policy.require_verified_event and not event.verified:
                policy_blockers.append("event_not_verified")
            if event.event_type == ReferralEventType.SIGNUP_COMPLETED and not policy.allow_signup_reward:
                policy_blockers.append("signup_reward_not_allowed")

            beneficiary_user_id, beneficiary_creator_id = self._resolve_beneficiary(
                policy=policy,
                attribution=attribution,
                creator_profile=creator_profile,
                share_code=share_code,
            )
            if beneficiary_user_id is None and beneficiary_creator_id is None:
                policy_blockers.append("beneficiary_not_resolved")

            if policy_blockers:
                blocked_reasons.extend(policy_blockers)
                continue

            status = ReferralRewardStatus.APPROVED
            review_reason: str | None = None
            hold_until = None
            if event.fraud_suspected or event.manual_review_requested or policy.require_manual_review:
                status = ReferralRewardStatus.BLOCKED
                review_reason = "Manual review is required before community-growth rewards can be released."
            elif self._requires_hold(policy):
                status = ReferralRewardStatus.PENDING
                hold_days = max(policy.hold_days, self.default_wallet_credit_hold_days if policy.reward_type == ReferralRewardType.WALLET_CREDIT else 0)
                hold_until = event.occurred_at + timedelta(days=hold_days)

            amount = self._quantize(policy.amount) if policy.amount is not None else None
            reward_key = self._reward_key(event.event_key, policy, beneficiary_user_id, beneficiary_creator_id)
            reward_payload = {
                "event_type": event.event_type.value,
                "source_channel": event.source_channel.value,
                "share_code_type": share_code.code_type.value if share_code is not None else None,
                "community_growth": True,
                "policy_metadata": policy.metadata_json,
            }
            reward = ReferralRewardComputation(
                reward_key=reward_key,
                reward_type=policy.reward_type,
                status=status,
                beneficiary_user_id=beneficiary_user_id,
                beneficiary_creator_id=beneficiary_creator_id,
                amount=amount,
                unit=policy.unit,
                reference_code=policy.reference_code,
                hold_until=hold_until,
                review_reason=review_reason,
                reward_payload=reward_payload,
            )
            reward_entries.append(reward)
            ledger_entries.append(
                ReferralRewardLedgerEntryCore(
                    entry_key=f"{reward_key}:created",
                    reward_key=reward_key,
                    entry_type="reward_created",
                    amount=amount,
                    unit=policy.unit,
                    status_after=status,
                    payload_json=reward_payload,
                )
            )
            if hold_until is not None:
                ledger_entries.append(
                    ReferralRewardLedgerEntryCore(
                        entry_key=f"{reward_key}:hold",
                        reward_key=reward_key,
                        entry_type="hold_applied",
                        amount=amount,
                        unit=policy.unit,
                        status_after=status,
                        payload_json={"hold_until": hold_until.isoformat()},
                    )
                )
            if review_reason is not None:
                ledger_entries.append(
                    ReferralRewardLedgerEntryCore(
                        entry_key=f"{reward_key}:review",
                        reward_key=reward_key,
                        entry_type="review_flagged",
                        amount=amount,
                        unit=policy.unit,
                        status_after=status,
                        payload_json={"review_reason": review_reason},
                    )
                )

        return ReferralRewardEvaluation(
            attribution_status=validation.attribution_status if validation is not None else attribution.attribution_status,
            blocked_reason_codes=tuple(dict.fromkeys(blocked_reasons)),
            rewards=tuple(reward_entries),
            ledger_entries=tuple(ledger_entries),
        )

    def _resolve_beneficiary(
        self,
        *,
        policy: ReferralRewardPolicy,
        attribution: ReferralAttributionCore,
        creator_profile: CreatorProfileCore | None,
        share_code: ShareCodeCore | None,
    ) -> tuple[str | None, str | None]:
        if policy.beneficiary == "referred_user":
            return attribution.referred_user_id, None
        if policy.beneficiary == "referrer_user":
            return attribution.referrer_user_id or (share_code.owner_user_id if share_code is not None else None), None
        creator_id = attribution.creator_profile_id
        if creator_id is None and share_code is not None:
            creator_id = share_code.owner_creator_id
        if creator_id is None and creator_profile is not None:
            creator_id = creator_profile.creator_profile_id
        return None, creator_id

    def _requires_hold(self, policy: ReferralRewardPolicy) -> bool:
        return policy.hold_days > 0 or policy.reward_type == ReferralRewardType.WALLET_CREDIT

    def _reward_key(
        self,
        event_key: str,
        policy: ReferralRewardPolicy,
        beneficiary_user_id: str | None,
        beneficiary_creator_id: str | None,
    ) -> str:
        beneficiary = beneficiary_user_id or beneficiary_creator_id or "unresolved"
        return f"{event_key}:{policy.reward_type.value}:{beneficiary}"

    def _quantize(self, amount: Decimal) -> Decimal:
        return amount.quantize(_CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
