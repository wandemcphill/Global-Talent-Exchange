from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from app.services.referral_orchestrator import (
    AttributionRecord,
    ReferralStore,
    RewardLedgerRecord,
    RewardRecord,
    generate_id,
    utcnow,
)


class ReferralRewardService:
    """GTEX creator profiles, share codes, invite attribution, and referral rewards are community-growth features tied to qualified participation milestones in creator competitions and other skill-based platform activity. They are not betting affiliate flows, house-banked wagering products, or cash-settled prediction mechanics."""

    def __init__(self, store: ReferralStore) -> None:
        self.store = store

    def evaluate(self, attribution: AttributionRecord, *, milestone: str) -> list[RewardRecord]:
        created: list[RewardRecord] = []
        created.extend(self._create_for_referrer(attribution, milestone=milestone))
        created.extend(self._create_for_creator(attribution, milestone=milestone))
        return created

    def list_for_owner(self, *, user_id: str, creator_id: str | None) -> list[RewardRecord]:
        with self.store.lock:
            rewards = [
                reward
                for reward in self.store.rewards_by_id.values()
                if reward.beneficiary_user_id == user_id or (creator_id is not None and reward.beneficiary_creator_id == creator_id)
            ]
        return sorted(rewards, key=lambda reward: reward.created_at, reverse=True)

    def _create_for_referrer(self, attribution: AttributionRecord, *, milestone: str) -> list[RewardRecord]:
        if attribution.referrer_user_id is None:
            return []
        policies = {
            "verification_completed": ("points", "approved", Decimal("25"), "points", "Verified community invite"),
            "first_competition_joined": ("starter_pack", "approved", None, None, "First contest participation"),
            "first_paid_competition_joined": ("wallet_credit", "pending", Decimal("5.00"), "credit", "Qualified paid participation"),
            "retained_day_30": ("badge", "approved", None, None, "Thirty day community retention"),
        }
        if milestone not in policies:
            return []
        reward_type, status, amount, unit, label = policies[milestone]
        return [self._upsert_reward(
            attribution=attribution,
            beneficiary_user_id=attribution.referrer_user_id,
            beneficiary_creator_id=None,
            reward_type=reward_type,
            status=status,
            milestone=milestone,
            amount=amount,
            unit=unit,
            label=label,
            hold_until=utcnow() + timedelta(days=7) if reward_type == "wallet_credit" else None,
            review_reason="ledger_hook_pending" if reward_type == "wallet_credit" else None,
        )]

    def _create_for_creator(self, attribution: AttributionRecord, *, milestone: str) -> list[RewardRecord]:
        if attribution.creator_profile_id is None:
            return []
        if milestone != "first_creator_competition_joined":
            return []
        return [self._upsert_reward(
            attribution=attribution,
            beneficiary_user_id=None,
            beneficiary_creator_id=attribution.creator_profile_id,
            reward_type="creator_revshare",
            status="pending",
            milestone=milestone,
            amount=Decimal("2.50"),
            unit="credit",
            label="Creator competition qualified join",
            hold_until=utcnow() + timedelta(days=14),
            review_reason="fraud_and_ledger_review_pending",
        )]

    def _upsert_reward(
        self,
        *,
        attribution: AttributionRecord,
        beneficiary_user_id: str | None,
        beneficiary_creator_id: str | None,
        reward_type: str,
        status: str,
        milestone: str,
        amount: Decimal | None,
        unit: str | None,
        label: str,
        hold_until,
        review_reason: str | None,
    ) -> RewardRecord:
        with self.store.lock:
            for reward in self.store.rewards_by_id.values():
                if (
                    reward.attribution_id == attribution.attribution_id
                    and reward.beneficiary_user_id == beneficiary_user_id
                    and reward.beneficiary_creator_id == beneficiary_creator_id
                    and reward.reward_type == reward_type
                    and reward.trigger_milestone == milestone
                ):
                    if reward.status != status or reward.review_reason != review_reason or reward.hold_until != hold_until:
                        updated = replace(
                            reward,
                            status=status,
                            hold_until=hold_until,
                            review_reason=review_reason,
                            updated_at=utcnow(),
                        )
                        self.store.rewards_by_id[updated.reward_id] = updated
                        self._append_ledger_entry(
                            reward_id=updated.reward_id,
                            entry_type="reward_updated",
                            amount=updated.amount,
                            unit=updated.unit,
                            status_after=updated.status,
                            reference_id=updated.attribution_id,
                            payload_json={
                                "trigger_milestone": milestone,
                                "label": updated.label,
                                "review_reason": updated.review_reason or "",
                            },
                        )
                        return updated
                    return reward

            reward = RewardRecord(
                reward_id=generate_id("reward"),
                attribution_id=attribution.attribution_id,
                beneficiary_user_id=beneficiary_user_id,
                beneficiary_creator_id=beneficiary_creator_id,
                reward_type=reward_type,
                status=status,
                trigger_milestone=milestone,
                amount=amount,
                unit=unit,
                label=label,
                hold_until=hold_until,
                review_reason=review_reason,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.store.rewards_by_id[reward.reward_id] = reward
            self._append_ledger_entry(
                reward_id=reward.reward_id,
                entry_type="reward_created",
                amount=reward.amount,
                unit=reward.unit,
                status_after=reward.status,
                reference_id=reward.attribution_id,
                payload_json={
                    "trigger_milestone": milestone,
                    "label": reward.label,
                    "review_reason": reward.review_reason or "",
                },
            )
            if reward.hold_until is not None:
                self._append_ledger_entry(
                    reward_id=reward.reward_id,
                    entry_type="hold_applied",
                    amount=reward.amount,
                    unit=reward.unit,
                    status_after=reward.status,
                    reference_id=reward.attribution_id,
                    payload_json={"hold_until": reward.hold_until.isoformat()},
                )
            if reward.status == "blocked":
                self._append_ledger_entry(
                    reward_id=reward.reward_id,
                    entry_type="review_flagged",
                    amount=reward.amount,
                    unit=reward.unit,
                    status_after=reward.status,
                    reference_id=reward.attribution_id,
                    payload_json={"review_reason": reward.review_reason or ""},
                )
            return reward

    def _append_ledger_entry(
        self,
        *,
        reward_id: str,
        entry_type: str,
        amount: Decimal | None,
        unit: str | None,
        status_after: str,
        reference_id: str | None,
        payload_json: dict[str, str],
    ) -> None:
        entry_id = generate_id("reward-ledger")
        self.store.reward_ledger_by_id[entry_id] = RewardLedgerRecord(
            ledger_entry_id=entry_id,
            reward_id=reward_id,
            entry_key=entry_id,
            entry_type=entry_type,
            amount=amount,
            unit=unit,
            status_after=status_after,
            reference_id=reference_id,
            payload_json=payload_json,
            created_at=utcnow(),
        )
