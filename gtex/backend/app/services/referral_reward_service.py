from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.common.enums.referral_event_type import ReferralEventType
from app.common.enums.referral_reward_status import ReferralRewardStatus
from app.common.enums.referral_reward_type import ReferralRewardType
from app.models.referral_event import ReferralEvent
from app.models.referral_reward import ReferralReward
from app.models.referral_reward_ledger import ReferralRewardLedger
from app.services.referral_orchestrator import (
    AttributionRecord,
    ReferralActionError,
    ReferralRuntimeStore,
    RewardLedgerRecord,
    RewardRecord,
    generate_id,
    utcnow,
)


class ReferralRewardService:
    """GTEX creator profiles, share codes, invite attribution, and referral rewards are community-growth features tied to qualified participation milestones in creator competitions and other skill-based platform activity. They are not betting affiliate flows, house-banked wagering products, or cash-settled prediction mechanics."""

    def __init__(self, store: ReferralRuntimeStore, session: Session | None = None) -> None:
        self.store = store
        self.session = session

    def evaluate(self, attribution: AttributionRecord, *, milestone: str) -> list[RewardRecord]:
        created: list[RewardRecord] = []
        created.extend(self._create_for_referrer(attribution, milestone=milestone))
        created.extend(self._create_for_creator(attribution, milestone=milestone))
        return created

    def list_for_owner(self, *, user_id: str, creator_id: str | None) -> list[RewardRecord]:
        if self.session is not None:
            filters = [ReferralReward.beneficiary_user_id == user_id]
            if creator_id is not None:
                filters.append(ReferralReward.beneficiary_creator_id == creator_id)
            rewards = tuple(
                self.session.scalars(
                    select(ReferralReward)
                    .where(or_(*filters))
                    .order_by(ReferralReward.created_at.desc(), ReferralReward.id.desc())
                ).all()
            )
            records = [self._from_model(reward) for reward in rewards]
            for record in records:
                self._cache_reward(record)
            return records
        with self.store.lock:
            rewards = [
                reward
                for reward in self.store.rewards_by_id.values()
                if reward.beneficiary_user_id == user_id
                or (creator_id is not None and reward.beneficiary_creator_id == creator_id)
            ]
        return sorted(rewards, key=lambda reward: reward.created_at, reverse=True)

    def list_all(self) -> tuple[RewardRecord, ...]:
        if self.session is not None:
            rewards = tuple(
                self.session.scalars(
                    select(ReferralReward).order_by(ReferralReward.created_at.desc(), ReferralReward.id.desc())
                ).all()
            )
            records = tuple(self._from_model(reward) for reward in rewards)
            for record in records:
                self._cache_reward(record)
            return records
        with self.store.lock:
            rewards = tuple(self.store.rewards_by_id.values())
        return tuple(sorted(rewards, key=lambda reward: reward.created_at, reverse=True))

    def get_by_id(self, reward_id: str) -> RewardRecord | None:
        if self.session is not None:
            reward = self.session.get(ReferralReward, reward_id)
            if reward is None:
                return None
            record = self._from_model(reward)
            self._cache_reward(record)
            return record
        with self.store.lock:
            return self.store.rewards_by_id.get(reward_id)

    def apply_review_decision(
        self,
        *,
        reward_id: str,
        action: str,
        reason: str | None,
        reference: str | None,
        admin_user_id: str,
    ) -> RewardRecord:
        status_after = "approved" if action == "approve" else "blocked"
        changed_at = utcnow()
        if self.session is not None:
            reward = self.session.get(ReferralReward, reward_id)
            if reward is None:
                raise ReferralActionError("reward_not_found")
            reward.status = ReferralRewardStatus(status_after)
            reward.review_reason = reason
            reward.reward_reference = reference
            reward.updated_at = changed_at
            self._apply_status_timestamps(reward, status_after=status_after, changed_at=changed_at)
            self.session.flush()
            updated = self._from_model(reward)
            self._cache_reward(updated)
            self._append_ledger_entry(
                reward_id=updated.reward_id,
                entry_type=f"reward_{status_after}",
                amount=updated.amount,
                unit=updated.unit,
                status_after=updated.status,
                reference_id=reference or updated.attribution_id,
                payload_json={
                    "action": action,
                    "admin_user_id": admin_user_id,
                    "reason": reason or "",
                    "reference": reference or "",
                },
            )
            return updated
        with self.store.lock:
            reward = self.store.rewards_by_id.get(reward_id)
            if reward is None:
                raise ReferralActionError("reward_not_found")
            updated = replace(
                reward,
                status=status_after,
                review_reason=reason,
                updated_at=changed_at,
                approved_at=changed_at if status_after == "approved" else None,
                blocked_at=changed_at if status_after == "blocked" else None,
            )
            self.store.rewards_by_id[reward_id] = updated
        self._append_ledger_entry(
            reward_id=updated.reward_id,
            entry_type=f"reward_{status_after}",
            amount=updated.amount,
            unit=updated.unit,
            status_after=updated.status,
            reference_id=reference or updated.attribution_id,
            payload_json={
                "action": action,
                "admin_user_id": admin_user_id,
                "reason": reason or "",
                "reference": reference or "",
            },
        )
        return updated

    def _create_for_referrer(self, attribution: AttributionRecord, *, milestone: str) -> list[RewardRecord]:
        if attribution.referrer_user_id is None:
            return []
        policies = {
            "verification_completed": ("points", "approved", Decimal("25"), "points", "Verified community invite"),
            "first_competition_joined": ("starter_pack", "approved", None, None, "First contest participation"),
            "first_paid_competition_joined": (
                "wallet_credit",
                "pending",
                Decimal("5.00"),
                "credit",
                "Qualified paid participation",
            ),
            "retained_day_30": ("badge", "approved", None, None, "Thirty day community retention"),
        }
        if milestone not in policies:
            return []
        reward_type, status, amount, unit, label = policies[milestone]
        return [
            self._upsert_reward(
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
            )
        ]

    def _create_for_creator(self, attribution: AttributionRecord, *, milestone: str) -> list[RewardRecord]:
        if attribution.creator_profile_id is None:
            return []
        if milestone != "first_creator_competition_joined":
            return []
        return [
            self._upsert_reward(
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
            )
        ]

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
        if self.session is not None:
            reward_key = self._reward_key(
                attribution=attribution,
                beneficiary_user_id=beneficiary_user_id,
                beneficiary_creator_id=beneficiary_creator_id,
                reward_type=reward_type,
                milestone=milestone,
            )
            reward = self.session.scalar(select(ReferralReward).where(ReferralReward.reward_key == reward_key))
            payload_json = {
                "trigger_milestone": milestone,
                "label": label,
            }
            source_event_id = self._resolve_source_event_id(
                attribution_id=attribution.attribution_id,
                milestone=milestone,
            )
            if reward is not None:
                changed_at = utcnow()
                previous = self._from_model(reward)
                changed = False
                updates = {
                    "referral_attribution_id": attribution.attribution_id,
                    "reward_source_event_id": source_event_id,
                    "referred_user_id": attribution.referred_user_id,
                    "beneficiary_user_id": beneficiary_user_id,
                    "beneficiary_creator_id": beneficiary_creator_id,
                    "trigger_event_type": ReferralEventType(milestone),
                    "reward_type": ReferralRewardType(reward_type),
                    "status": ReferralRewardStatus(status),
                    "reward_amount": amount,
                    "reward_unit": unit,
                    "hold_until": hold_until,
                    "review_reason": review_reason,
                    "reward_payload_json": payload_json,
                }
                for field_name, value in updates.items():
                    if getattr(reward, field_name) != value:
                        setattr(reward, field_name, value)
                        changed = True
                if changed:
                    reward.updated_at = changed_at
                    self._apply_status_timestamps(reward, status_after=status, changed_at=changed_at)
                    self.session.flush()
                    updated = self._from_model(reward)
                    self._cache_reward(updated)
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
                self._cache_reward(previous)
                return previous

            changed_at = utcnow()
            reward = ReferralReward(
                id=generate_id("reward"),
                reward_key=reward_key,
                referral_attribution_id=attribution.attribution_id,
                reward_source_event_id=source_event_id,
                referred_user_id=attribution.referred_user_id,
                beneficiary_user_id=beneficiary_user_id,
                beneficiary_creator_id=beneficiary_creator_id,
                trigger_event_type=ReferralEventType(milestone),
                reward_type=ReferralRewardType(reward_type),
                status=ReferralRewardStatus(status),
                reward_amount=amount,
                reward_unit=unit,
                hold_until=hold_until,
                review_reason=review_reason,
                reward_payload_json=payload_json,
            )
            self._apply_status_timestamps(reward, status_after=status, changed_at=changed_at)
            self.session.add(reward)
            self.session.flush()
            record = self._from_model(reward)
            self._cache_reward(record)
            self._append_ledger_entry(
                reward_id=record.reward_id,
                entry_type="reward_created",
                amount=record.amount,
                unit=record.unit,
                status_after=record.status,
                reference_id=record.attribution_id,
                payload_json={
                    "trigger_milestone": milestone,
                    "label": record.label,
                    "review_reason": record.review_reason or "",
                },
            )
            if record.hold_until is not None:
                self._append_ledger_entry(
                    reward_id=record.reward_id,
                    entry_type="hold_applied",
                    amount=record.amount,
                    unit=record.unit,
                    status_after=record.status,
                    reference_id=record.attribution_id,
                    payload_json={"hold_until": record.hold_until.isoformat()},
                )
            if record.status == "blocked":
                self._append_ledger_entry(
                    reward_id=record.reward_id,
                    entry_type="review_flagged",
                    amount=record.amount,
                    unit=record.unit,
                    status_after=record.status,
                    reference_id=record.attribution_id,
                    payload_json={"review_reason": record.review_reason or ""},
                )
            return record
        with self.store.lock:
            for reward in self.store.rewards_by_id.values():
                if (
                    reward.attribution_id == attribution.attribution_id
                    and reward.beneficiary_user_id == beneficiary_user_id
                    and reward.beneficiary_creator_id == beneficiary_creator_id
                    and reward.reward_type == reward_type
                    and reward.trigger_milestone == milestone
                ):
                    if (
                        reward.status != status
                        or reward.review_reason != review_reason
                        or reward.hold_until != hold_until
                    ):
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
        if self.session is not None:
            entry = ReferralRewardLedger(
                id=entry_id,
                entry_key=entry_id,
                reward_id=reward_id,
                entry_type=entry_type,
                amount=amount,
                unit=unit,
                status_after=ReferralRewardStatus(status_after),
                reference_id=reference_id,
                payload_json=dict(payload_json),
            )
            self.session.add(entry)
            self.session.flush()
            self._cache_ledger_entry(self._ledger_from_model(entry))
            return
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

    def _reward_key(
        self,
        *,
        attribution: AttributionRecord,
        beneficiary_user_id: str | None,
        beneficiary_creator_id: str | None,
        reward_type: str,
        milestone: str,
    ) -> str:
        beneficiary_scope = beneficiary_user_id
        if beneficiary_scope is None and beneficiary_creator_id is not None:
            beneficiary_scope = f"creator:{beneficiary_creator_id}"
        if beneficiary_scope is None:
            beneficiary_scope = "unknown"
        return f"{attribution.attribution_id}:{reward_type}:{milestone}:{beneficiary_scope}"

    def _resolve_source_event_id(self, *, attribution_id: str, milestone: str) -> str | None:
        if self.session is None:
            return None
        event = self.session.scalar(
            select(ReferralEvent)
            .where(
                ReferralEvent.referral_attribution_id == attribution_id,
                ReferralEvent.event_type == ReferralEventType(milestone),
            )
            .order_by(ReferralEvent.occurred_at.desc(), ReferralEvent.id.desc())
        )
        return event.id if event is not None else None

    def _apply_status_timestamps(
        self,
        reward: ReferralReward,
        *,
        status_after: str,
        changed_at: datetime,
    ) -> None:
        if status_after == "approved":
            reward.approved_at = changed_at
            reward.blocked_at = None
        elif status_after == "blocked":
            reward.blocked_at = changed_at
            reward.approved_at = None
        elif status_after == "reversed":
            reward.reversed_at = changed_at
        elif status_after == "paid":
            reward.paid_at = changed_at

    def _from_model(self, reward: ReferralReward) -> RewardRecord:
        payload_json = dict(reward.reward_payload_json or {})
        return RewardRecord(
            reward_id=reward.id,
            attribution_id=reward.referral_attribution_id or "",
            beneficiary_user_id=reward.beneficiary_user_id,
            beneficiary_creator_id=reward.beneficiary_creator_id,
            reward_type=reward.reward_type.value,
            status=reward.status.value,
            trigger_milestone=payload_json.get("trigger_milestone") or reward.trigger_event_type.value,
            amount=reward.reward_amount,
            unit=reward.reward_unit,
            label=str(payload_json.get("label") or ""),
            hold_until=reward.hold_until,
            review_reason=reward.review_reason,
            created_at=reward.created_at,
            updated_at=reward.updated_at,
            approved_at=reward.approved_at,
            blocked_at=reward.blocked_at,
            reversed_at=reward.reversed_at,
            paid_at=reward.paid_at,
        )

    def _ledger_from_model(self, entry: ReferralRewardLedger) -> RewardLedgerRecord:
        return RewardLedgerRecord(
            ledger_entry_id=entry.id,
            reward_id=entry.reward_id,
            entry_key=entry.entry_key,
            entry_type=entry.entry_type,
            amount=entry.amount,
            unit=entry.unit,
            status_after=entry.status_after.value,
            reference_id=entry.reference_id,
            payload_json={str(key): str(value) for key, value in dict(entry.payload_json or {}).items()},
            created_at=entry.created_at,
        )

    def _cache_reward(self, reward: RewardRecord) -> None:
        with self.store.lock:
            self.store.rewards_by_id[reward.reward_id] = reward

    def _cache_ledger_entry(self, entry: RewardLedgerRecord) -> None:
        with self.store.lock:
            self.store.reward_ledger_by_id[entry.ledger_entry_id] = entry
