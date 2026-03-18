from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.admin_engine.schemas import AdminGiftStabilityControlConfig, AdminRewardLoopControlConfig
from backend.app.admin_engine.service import AdminEngineService
from backend.app.models.base import utcnow
from backend.app.models.creator_monetization import (
    CreatorBroadcastPurchase,
    CreatorMatchGiftEvent,
    CreatorSeasonPass,
    CreatorStadiumTicketPurchase,
)
from backend.app.models.gift_transaction import GiftTransaction
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.spending_control import SpendingControlAuditEvent, SpendingControlDecision
from backend.app.models.wallet import LedgerUnit

AMOUNT_QUANTUM = Decimal("0.0001")
DAY_WINDOW = timedelta(hours=24)


class SpendingControlViolation(ValueError):
    def __init__(self, detail: str, *, code: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code


@dataclass(frozen=True, slots=True)
class SpendingControlTrigger:
    code: str
    detail: str
    observed: str
    threshold: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "detail": self.detail,
            "observed": self.observed,
            "threshold": self.threshold,
        }


@dataclass(frozen=True, slots=True)
class SpendingControlEvaluation:
    event_type: str
    control_scope: str
    reference_key: str
    amount: Decimal
    ledger_unit: LedgerUnit
    actor_user_id: str | None
    target_user_id: str | None
    decision: SpendingControlDecision
    triggers: tuple[SpendingControlTrigger, ...]
    metadata_json: dict[str, Any]


@dataclass(slots=True)
class SpendingControlService:
    session: Session

    def evaluate_gift(
        self,
        *,
        event_type: str,
        control_scope: str,
        reference_key: str,
        amount: Decimal,
        ledger_unit: LedgerUnit,
        actor_user_id: str,
        target_user_id: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> SpendingControlEvaluation:
        controls = self._gift_controls(control_scope)
        normalized_amount = self._normalize_amount(amount)
        now = utcnow()
        day_start = now - DAY_WINDOW
        burst_start = now - timedelta(seconds=controls.burst_window_seconds)

        if normalized_amount > controls.max_amount:
            self._block(
                event_type=event_type,
                control_scope=control_scope,
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="max_amount_exceeded",
                detail=f"Gift amount exceeds the configured {control_scope} max amount.",
                observed=normalized_amount,
                threshold=controls.max_amount,
                metadata_json=metadata_json,
            )

        daily_sender_total = self._sum_recent_gift_amount(
            control_scope=control_scope,
            user_id=actor_user_id,
            role="sender",
            since=day_start,
        ) + normalized_amount
        if daily_sender_total > controls.daily_sender_limit:
            self._block(
                event_type=event_type,
                control_scope=control_scope,
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="daily_sender_limit_exceeded",
                detail=f"Gift exceeds the configured {control_scope} daily sender limit.",
                observed=daily_sender_total,
                threshold=controls.daily_sender_limit,
                metadata_json=metadata_json,
            )

        daily_recipient_total = self._sum_recent_gift_amount(
            control_scope=control_scope,
            user_id=target_user_id,
            role="recipient",
            since=day_start,
        ) + normalized_amount
        if daily_recipient_total > controls.daily_recipient_limit:
            self._block(
                event_type=event_type,
                control_scope=control_scope,
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="daily_recipient_limit_exceeded",
                detail=f"Gift exceeds the configured {control_scope} daily recipient limit.",
                observed=daily_recipient_total,
                threshold=controls.daily_recipient_limit,
                metadata_json=metadata_json,
            )

        daily_pair_total = self._sum_recent_gift_pair_amount(
            control_scope=control_scope,
            sender_user_id=actor_user_id,
            recipient_user_id=target_user_id,
            since=day_start,
        ) + normalized_amount
        if daily_pair_total > controls.daily_pair_limit:
            self._block(
                event_type=event_type,
                control_scope=control_scope,
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="daily_pair_limit_exceeded",
                detail=f"Gift exceeds the configured {control_scope} pair limit.",
                observed=daily_pair_total,
                threshold=controls.daily_pair_limit,
                metadata_json=metadata_json,
            )

        burst_count = self._count_recent_gifts(
            control_scope=control_scope,
            sender_user_id=actor_user_id,
            since=burst_start,
        ) + 1
        if burst_count > controls.burst_max_count:
            self._block(
                event_type=event_type,
                control_scope=control_scope,
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="burst_limit_exceeded",
                detail=f"Gift exceeds the configured {control_scope} burst limit.",
                observed=burst_count,
                threshold=controls.burst_max_count,
                metadata_json=metadata_json,
            )

        if controls.cooldown_seconds > 0:
            latest_sent_at = self._latest_gift_sent_at(
                control_scope=control_scope,
                sender_user_id=actor_user_id,
            )
            if latest_sent_at is not None:
                if latest_sent_at.tzinfo is None:
                    latest_sent_at = latest_sent_at.replace(tzinfo=now.tzinfo)
                elapsed_seconds = int((now - latest_sent_at).total_seconds())
                if elapsed_seconds < controls.cooldown_seconds:
                    self._block(
                        event_type=event_type,
                        control_scope=control_scope,
                        reference_key=reference_key,
                        amount=normalized_amount,
                        ledger_unit=ledger_unit,
                        actor_user_id=actor_user_id,
                        target_user_id=target_user_id,
                        code="cooldown_active",
                        detail=f"Gift was sent before the {control_scope} cooldown elapsed.",
                        observed=elapsed_seconds,
                        threshold=controls.cooldown_seconds,
                        metadata_json=metadata_json,
                    )

        triggers: list[SpendingControlTrigger] = []
        self._append_threshold_review(
            triggers=triggers,
            code="daily_sender_limit_near",
            detail=f"Gift sender is close to the configured {control_scope} daily sender limit.",
            observed=daily_sender_total,
            threshold=controls.daily_sender_limit,
            review_threshold_bps=controls.review_threshold_bps,
        )
        self._append_threshold_review(
            triggers=triggers,
            code="daily_recipient_limit_near",
            detail=f"Gift recipient is close to the configured {control_scope} daily recipient limit.",
            observed=daily_recipient_total,
            threshold=controls.daily_recipient_limit,
            review_threshold_bps=controls.review_threshold_bps,
        )
        self._append_threshold_review(
            triggers=triggers,
            code="daily_pair_limit_near",
            detail=f"Gift pair is close to the configured {control_scope} pair limit.",
            observed=daily_pair_total,
            threshold=controls.daily_pair_limit,
            review_threshold_bps=controls.review_threshold_bps,
        )
        if burst_count == controls.burst_max_count:
            triggers.append(
                SpendingControlTrigger(
                    code="burst_limit_near",
                    detail=f"Gift sender is at the configured {control_scope} burst limit.",
                    observed=str(burst_count),
                    threshold=str(controls.burst_max_count),
                )
            )
        return SpendingControlEvaluation(
            event_type=event_type,
            control_scope=control_scope,
            reference_key=reference_key,
            amount=normalized_amount,
            ledger_unit=ledger_unit,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            decision=SpendingControlDecision.REVIEW if triggers else SpendingControlDecision.APPROVED,
            triggers=tuple(triggers),
            metadata_json=dict(metadata_json or {}),
        )

    def evaluate_reward(
        self,
        *,
        reference_key: str,
        amount: Decimal,
        ledger_unit: LedgerUnit,
        actor_user_id: str | None,
        target_user_id: str,
        competition_key: str,
        reward_source: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> SpendingControlEvaluation:
        controls = self._reward_controls()
        normalized_amount = self._normalize_amount(amount)
        now = utcnow()
        day_start = now - DAY_WINDOW
        burst_start = now - timedelta(seconds=controls.burst_window_seconds)
        duplicate_start = now - timedelta(seconds=controls.duplicate_window_seconds)

        if normalized_amount > controls.max_amount:
            self._block(
                event_type="reward_settlement",
                control_scope="reward",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="max_amount_exceeded",
                detail="Reward exceeds the configured maximum amount.",
                observed=normalized_amount,
                threshold=controls.max_amount,
                metadata_json=metadata_json,
            )

        daily_total = self._sum_recent_reward_amount(user_id=target_user_id, since=day_start) + normalized_amount
        if daily_total > controls.daily_user_limit:
            self._block(
                event_type="reward_settlement",
                control_scope="reward",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="daily_user_limit_exceeded",
                detail="Reward exceeds the configured daily user reward limit.",
                observed=daily_total,
                threshold=controls.daily_user_limit,
                metadata_json=metadata_json,
            )

        daily_count = self._count_recent_rewards(user_id=target_user_id, since=day_start) + 1
        if daily_count > controls.daily_user_count_limit:
            self._block(
                event_type="reward_settlement",
                control_scope="reward",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="daily_user_count_limit_exceeded",
                detail="Reward exceeds the configured daily user reward count limit.",
                observed=daily_count,
                threshold=controls.daily_user_count_limit,
                metadata_json=metadata_json,
            )

        burst_count = self._count_recent_rewards(user_id=target_user_id, since=burst_start) + 1
        if burst_count > controls.burst_max_count:
            self._block(
                event_type="reward_settlement",
                control_scope="reward",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                code="burst_limit_exceeded",
                detail="Reward exceeds the configured burst reward limit.",
                observed=burst_count,
                threshold=controls.burst_max_count,
                metadata_json=metadata_json,
            )

        duplicate_count = self._count_duplicate_rewards(
            user_id=target_user_id,
            competition_key=competition_key,
            reward_source=reward_source,
            amount=normalized_amount,
            since=duplicate_start,
        )

        triggers: list[SpendingControlTrigger] = []
        self._append_threshold_review(
            triggers=triggers,
            code="daily_user_limit_near",
            detail="Reward recipient is close to the configured daily reward limit.",
            observed=daily_total,
            threshold=controls.daily_user_limit,
            review_threshold_bps=controls.review_threshold_bps,
        )
        if daily_count >= self._review_count_threshold(
            limit=controls.daily_user_count_limit,
            review_threshold_bps=controls.review_threshold_bps,
        ):
            triggers.append(
                SpendingControlTrigger(
                    code="daily_user_count_limit_near",
                    detail="Reward recipient is close to the configured daily reward count limit.",
                    observed=str(daily_count),
                    threshold=str(controls.daily_user_count_limit),
                )
            )
        if burst_count == controls.burst_max_count:
            triggers.append(
                SpendingControlTrigger(
                    code="burst_limit_near",
                    detail="Reward recipient is at the configured burst reward limit.",
                    observed=str(burst_count),
                    threshold=str(controls.burst_max_count),
                )
            )
        if duplicate_count > 0:
            triggers.append(
                SpendingControlTrigger(
                    code="duplicate_reward_window",
                    detail="A matching reward landed inside the duplicate review window.",
                    observed=str(duplicate_count + 1),
                    threshold=str(controls.duplicate_window_seconds),
                )
            )
        return SpendingControlEvaluation(
            event_type="reward_settlement",
            control_scope="reward",
            reference_key=reference_key,
            amount=normalized_amount,
            ledger_unit=ledger_unit,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            decision=SpendingControlDecision.REVIEW if triggers else SpendingControlDecision.APPROVED,
            triggers=tuple(triggers),
            metadata_json=dict(metadata_json or {}),
        )

    def evaluate_purchase(
        self,
        *,
        reference_key: str,
        amount: Decimal,
        ledger_unit: LedgerUnit,
        actor_user_id: str,
        purchase_scope: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> SpendingControlEvaluation:
        controls = self._creator_purchase_controls()
        normalized_amount = self._normalize_amount(amount)
        now = utcnow()
        day_start = now - DAY_WINDOW
        burst_start = now - timedelta(seconds=controls.burst_window_seconds)

        if normalized_amount > controls.max_amount:
            self._block(
                event_type="creator_purchase",
                control_scope="creator_viewer_purchase",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=None,
                code="max_amount_exceeded",
                detail="Creator purchase exceeds the configured maximum amount.",
                observed=normalized_amount,
                threshold=controls.max_amount,
                metadata_json=metadata_json,
            )

        daily_total = self._sum_recent_creator_purchase_amount(user_id=actor_user_id, since=day_start) + normalized_amount
        if daily_total > controls.daily_user_limit:
            self._block(
                event_type="creator_purchase",
                control_scope="creator_viewer_purchase",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=None,
                code="daily_user_limit_exceeded",
                detail="Creator purchase exceeds the configured daily spend limit.",
                observed=daily_total,
                threshold=controls.daily_user_limit,
                metadata_json=metadata_json,
            )

        daily_count = self._count_recent_creator_purchases(user_id=actor_user_id, since=day_start) + 1
        if daily_count > controls.daily_user_count_limit:
            self._block(
                event_type="creator_purchase",
                control_scope="creator_viewer_purchase",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=None,
                code="daily_user_count_limit_exceeded",
                detail="Creator purchase exceeds the configured daily transaction count limit.",
                observed=daily_count,
                threshold=controls.daily_user_count_limit,
                metadata_json=metadata_json,
            )

        burst_count = self._count_recent_creator_purchases(user_id=actor_user_id, since=burst_start) + 1
        if burst_count > controls.burst_max_count:
            self._block(
                event_type="creator_purchase",
                control_scope="creator_viewer_purchase",
                reference_key=reference_key,
                amount=normalized_amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=None,
                code="burst_limit_exceeded",
                detail="Creator purchase exceeds the configured burst transaction limit.",
                observed=burst_count,
                threshold=controls.burst_max_count,
                metadata_json=metadata_json,
            )

        triggers: list[SpendingControlTrigger] = []
        self._append_threshold_review(
            triggers=triggers,
            code="daily_user_limit_near",
            detail="Creator purchase is close to the configured daily spend limit.",
            observed=daily_total,
            threshold=controls.daily_user_limit,
            review_threshold_bps=controls.review_threshold_bps,
        )
        if daily_count >= self._review_count_threshold(
            limit=controls.daily_user_count_limit,
            review_threshold_bps=controls.review_threshold_bps,
        ):
            triggers.append(
                SpendingControlTrigger(
                    code="daily_user_count_limit_near",
                    detail="Creator purchase is close to the configured daily transaction count limit.",
                    observed=str(daily_count),
                    threshold=str(controls.daily_user_count_limit),
                )
            )
        if burst_count == controls.burst_max_count:
            triggers.append(
                SpendingControlTrigger(
                    code="burst_limit_near",
                    detail="Creator purchase reached the configured burst transaction threshold.",
                    observed=str(burst_count),
                    threshold=str(controls.burst_max_count),
                )
            )
        payload = dict(metadata_json or {})
        payload["purchase_scope"] = purchase_scope
        return SpendingControlEvaluation(
            event_type="creator_purchase",
            control_scope="creator_viewer_purchase",
            reference_key=reference_key,
            amount=normalized_amount,
            ledger_unit=ledger_unit,
            actor_user_id=actor_user_id,
            target_user_id=None,
            decision=SpendingControlDecision.REVIEW if triggers else SpendingControlDecision.APPROVED,
            triggers=tuple(triggers),
            metadata_json=payload,
        )

    def record_evaluation(
        self,
        evaluation: SpendingControlEvaluation,
        *,
        entity_id: str | None = None,
        ledger_transaction_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> SpendingControlAuditEvent:
        payload = dict(evaluation.metadata_json)
        if metadata_json:
            payload.update(metadata_json)
        item = SpendingControlAuditEvent(
            event_type=evaluation.event_type,
            control_scope=evaluation.control_scope,
            decision=evaluation.decision,
            actor_user_id=evaluation.actor_user_id,
            target_user_id=evaluation.target_user_id,
            reference_key=evaluation.reference_key,
            entity_id=entity_id,
            ledger_transaction_id=ledger_transaction_id,
            amount=evaluation.amount,
            ledger_unit=evaluation.ledger_unit,
            primary_reason_code=evaluation.triggers[0].code if evaluation.triggers else None,
            reason_detail=evaluation.triggers[0].detail if evaluation.triggers else None,
            triggered_rules_json=[item.as_dict() for item in evaluation.triggers],
            metadata_json=payload,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def _block(
        self,
        *,
        event_type: str,
        control_scope: str,
        reference_key: str,
        amount: Decimal,
        ledger_unit: LedgerUnit,
        actor_user_id: str | None,
        target_user_id: str | None,
        code: str,
        detail: str,
        observed: Decimal | int,
        threshold: Decimal | int,
        metadata_json: dict[str, Any] | None,
    ) -> None:
        trigger = SpendingControlTrigger(
            code=code,
            detail=detail,
            observed=self._format_metric(observed),
            threshold=self._format_metric(threshold),
        )
        self.record_evaluation(
            SpendingControlEvaluation(
                event_type=event_type,
                control_scope=control_scope,
                reference_key=reference_key,
                amount=amount,
                ledger_unit=ledger_unit,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                decision=SpendingControlDecision.BLOCKED,
                triggers=(trigger,),
                metadata_json=dict(metadata_json or {}),
            )
        )
        raise SpendingControlViolation(detail, code=code)

    def _gift_controls(self, control_scope: str) -> AdminGiftStabilityControlConfig:
        controls = AdminEngineService(self.session).get_active_stability_controls()
        if control_scope == "user_hosted_gift":
            return controls.user_hosted_gift
        if control_scope == "gtex_competition_gift":
            return controls.gtex_competition_gift
        if control_scope == "creator_match_gift":
            return controls.creator_match_gift
        raise SpendingControlViolation(f"Unsupported gift control scope: {control_scope}", code="unsupported_control_scope")

    def _reward_controls(self) -> AdminRewardLoopControlConfig:
        return AdminEngineService(self.session).get_active_stability_controls().reward

    def _creator_purchase_controls(self) -> AdminRewardLoopControlConfig:
        return AdminEngineService(self.session).get_active_stability_controls().creator_viewer_purchase

    def _sum_recent_gift_amount(
        self,
        *,
        control_scope: str,
        user_id: str,
        role: str,
        since: datetime,
    ) -> Decimal:
        model, sender_column, recipient_column, amount_column, filters = self._gift_query_parts(control_scope)
        user_column = sender_column if role == "sender" else recipient_column
        value = self.session.scalar(
            select(func.coalesce(func.sum(amount_column), 0))
            .select_from(model)
            .where(*filters, user_column == user_id, model.created_at >= since)
        )
        return self._normalize_amount(value or 0)

    def _sum_recent_gift_pair_amount(
        self,
        *,
        control_scope: str,
        sender_user_id: str,
        recipient_user_id: str,
        since: datetime,
    ) -> Decimal:
        model, sender_column, recipient_column, amount_column, filters = self._gift_query_parts(control_scope)
        value = self.session.scalar(
            select(func.coalesce(func.sum(amount_column), 0))
            .select_from(model)
            .where(
                *filters,
                sender_column == sender_user_id,
                recipient_column == recipient_user_id,
                model.created_at >= since,
            )
        )
        return self._normalize_amount(value or 0)

    def _count_recent_gifts(
        self,
        *,
        control_scope: str,
        sender_user_id: str,
        since: datetime,
    ) -> int:
        model, sender_column, _recipient_column, _amount_column, filters = self._gift_query_parts(control_scope)
        value = self.session.scalar(
            select(func.count())
            .select_from(model)
            .where(*filters, sender_column == sender_user_id, model.created_at >= since)
        )
        return int(value or 0)

    def _latest_gift_sent_at(
        self,
        *,
        control_scope: str,
        sender_user_id: str,
    ) -> datetime | None:
        model, sender_column, _recipient_column, _amount_column, filters = self._gift_query_parts(control_scope)
        return self.session.scalar(
            select(model.created_at)
            .where(*filters, sender_column == sender_user_id)
            .order_by(model.created_at.desc())
            .limit(1)
        )

    def _gift_query_parts(self, control_scope: str):
        if control_scope == "creator_match_gift":
            return (
                CreatorMatchGiftEvent,
                CreatorMatchGiftEvent.sender_user_id,
                CreatorMatchGiftEvent.recipient_creator_user_id,
                CreatorMatchGiftEvent.gross_amount_coin,
                [],
            )
        source_scope = "user_hosted" if control_scope == "user_hosted_gift" else "gtex_competition"
        return (
            GiftTransaction,
            GiftTransaction.sender_user_id,
            GiftTransaction.recipient_user_id,
            GiftTransaction.gross_amount,
            [GiftTransaction.source_scope == source_scope],
        )

    def _sum_recent_reward_amount(self, *, user_id: str, since: datetime) -> Decimal:
        value = self.session.scalar(
            select(func.coalesce(func.sum(RewardSettlement.gross_amount), 0))
            .where(RewardSettlement.user_id == user_id, RewardSettlement.created_at >= since)
        )
        return self._normalize_amount(value or 0)

    def _count_recent_rewards(self, *, user_id: str, since: datetime) -> int:
        value = self.session.scalar(
            select(func.count())
            .select_from(RewardSettlement)
            .where(RewardSettlement.user_id == user_id, RewardSettlement.created_at >= since)
        )
        return int(value or 0)

    def _count_duplicate_rewards(
        self,
        *,
        user_id: str,
        competition_key: str,
        reward_source: str,
        amount: Decimal,
        since: datetime,
    ) -> int:
        value = self.session.scalar(
            select(func.count())
            .select_from(RewardSettlement)
            .where(
                RewardSettlement.user_id == user_id,
                RewardSettlement.competition_key == competition_key,
                RewardSettlement.reward_source == reward_source,
                RewardSettlement.gross_amount == amount,
                RewardSettlement.created_at >= since,
            )
        )
        return int(value or 0)

    def _sum_recent_creator_purchase_amount(self, *, user_id: str, since: datetime) -> Decimal:
        total = Decimal("0.0000")
        for model, amount_column in (
            (CreatorBroadcastPurchase, CreatorBroadcastPurchase.price_coin),
            (CreatorSeasonPass, CreatorSeasonPass.price_coin),
            (CreatorStadiumTicketPurchase, CreatorStadiumTicketPurchase.price_coin),
        ):
            value = self.session.scalar(
                select(func.coalesce(func.sum(amount_column), 0))
                .select_from(model)
                .where(model.user_id == user_id, model.created_at >= since)
            )
            total += self._normalize_amount(value or 0)
        return self._normalize_amount(total)

    def _count_recent_creator_purchases(self, *, user_id: str, since: datetime) -> int:
        total = 0
        for model in (CreatorBroadcastPurchase, CreatorSeasonPass, CreatorStadiumTicketPurchase):
            value = self.session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.user_id == user_id, model.created_at >= since)
            )
            total += int(value or 0)
        return total

    def _append_threshold_review(
        self,
        *,
        triggers: list[SpendingControlTrigger],
        code: str,
        detail: str,
        observed: Decimal,
        threshold: Decimal,
        review_threshold_bps: int,
    ) -> None:
        if threshold <= Decimal("0.0000"):
            return
        review_threshold = (threshold * Decimal(review_threshold_bps) / Decimal(10_000)).quantize(AMOUNT_QUANTUM)
        if observed >= review_threshold:
            triggers.append(
                SpendingControlTrigger(
                    code=code,
                    detail=detail,
                    observed=self._format_metric(observed),
                    threshold=self._format_metric(threshold),
                )
            )

    @staticmethod
    def _review_count_threshold(*, limit: int, review_threshold_bps: int) -> int:
        value = Decimal(limit) * Decimal(review_threshold_bps) / Decimal(10_000)
        return max(1, int(value.to_integral_value(rounding=ROUND_CEILING)))

    @staticmethod
    def _normalize_amount(amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _format_metric(value: Decimal | int) -> str:
        if isinstance(value, Decimal):
            return str(value.quantize(AMOUNT_QUANTUM))
        return str(value)
