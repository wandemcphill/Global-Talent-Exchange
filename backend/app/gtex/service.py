from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import math
import random
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.event_backbone import (
    build_outbox_event,
    defer_event_publish_until_commit,
    defer_session_callback_until_commit,
)
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.core.global_ids import global_match_id
from app.gtex.config import AMOUNT_QUANTUM, GtexSettings
from app.gtex import redis_keys
from app.gtex.store import InMemoryStateStore, RedisStateStore
from app.models.base import generate_uuid, utcnow
from app.models.gtex_economy import (
    GtexAIProfile,
    GtexAiProfileType,
    GtexAssetSubjectType,
    GtexContributionSourceType,
    GtexCreatorAsset,
    GtexCreatorHolding,
    GtexCreatorPriceHistory,
    GtexCreatorTrade,
    GtexJackpotContribution,
    GtexJackpotDistributionMode,
    GtexJackpotPayout,
    GtexJackpotRound,
    GtexJackpotRoundStatus,
    GtexJackpotTriggerMode,
    GtexLeague,
    GtexLeagueStanding,
    GtexLeagueType,
    GtexMatch,
    GtexMatchEvent,
    GtexMatchQueueEntry,
    GtexMatchStatus,
    GtexParticipantType,
    GtexQueueEntryStatus,
    GtexRiskFlag,
    GtexRiskFlagStatus,
    GtexTradeSide,
)
from app.models.notification_record import NotificationRecord
from app.models.risk_ops import RiskSignalType
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.risk_ops_engine.service import RiskOpsService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

StateStore = InMemoryStateStore | RedisStateStore


class GtexError(ValueError):
    pass


class GtexNotFoundError(GtexError):
    pass


class GtexConflictError(GtexError):
    pass


class GtexValidationError(GtexError):
    pass


@dataclass(frozen=True, slots=True)
class MatchmakingResult:
    queue_entry: GtexMatchQueueEntry
    match: GtexMatch | None


@dataclass(frozen=True, slots=True)
class SimulatedParticipant:
    participant_type: GtexParticipantType
    user: User | None
    ai: GtexAIProfile | None
    standing: GtexLeagueStanding
    strength: Decimal
    label: str
    subject_key: str


class GtexBaseService:
    def __init__(
        self,
        *,
        settings: GtexSettings,
        wallet_service: WalletService,
        state_store: StateStore,
        event_publisher: EventPublisher | None = None,
        realtime_channel: str = "gtex.realtime",
    ) -> None:
        self.settings = settings
        self.wallet_service = wallet_service
        self.state_store = state_store
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        self.realtime_channel = realtime_channel
        self._random = random.Random()

    @staticmethod
    def _amount(value: Decimal | int | float | str | None) -> Decimal:
        return Decimal(str(value or "0")).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _subject_key(*, user: User | None = None, ai: GtexAIProfile | None = None) -> str:
        if user is not None:
            return f"user:{user.id}"
        if ai is not None:
            return f"ai:{ai.id}"
        raise ValueError("A user or AI profile is required.")

    def _stage_event(
        self,
        session: Session,
        *,
        name: str,
        payload: dict[str, Any],
        aggregate_id: str | None,
        aggregate_type: str,
        partition_key: str | None = None,
        realtime_topic: str | None = None,
    ) -> None:
        event = DomainEvent(
            name=name,
            payload=payload,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            producer="gtex",
            partition_key=partition_key or aggregate_id,
            headers={"delivery_mode": "durable"},
        )
        session.add(build_outbox_event(domain_event=event))
        defer_event_publish_until_commit(session, publisher=self.event_publisher, event=event)
        if realtime_topic is not None:
            defer_session_callback_until_commit(
                session,
                callback=lambda topic=realtime_topic, body=dict(payload): self.state_store.publish(
                    self.realtime_channel,
                    {
                        "topic": topic,
                        "emitted_at": datetime.now(UTC).isoformat(),
                        "payload": body,
                    },
                ),
            )

    @staticmethod
    def _supports_row_locks(session: Session) -> bool:
        bind = session.get_bind()
        if bind is None:
            return False
        return bind.dialect.name not in {"sqlite"}

    def _audit_log(
        self,
        session: Session,
        *,
        actor_user_id: str | None,
        action_key: str,
        resource_type: str,
        resource_id: str | None,
        detail: str,
        metadata_json: dict[str, Any] | None = None,
        outcome: str = "success",
    ) -> None:
        RiskOpsService(session).log_audit(
            actor_user_id=actor_user_id,
            action_key=action_key,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata_json,
            outcome=outcome,
        )


class JackpotService(GtexBaseService):
    def ensure_open_round(self, session: Session, *, pool_key: str = "global") -> GtexJackpotRound:
        current_round = session.scalar(
            select(GtexJackpotRound)
            .where(
                GtexJackpotRound.pool_key == pool_key,
                GtexJackpotRound.status == GtexJackpotRoundStatus.OPEN,
            )
            .order_by(GtexJackpotRound.round_number.desc())
        )
        if current_round is not None:
            return current_round
        next_round_number = (
            int(
                session.scalar(
                    select(func.coalesce(func.max(GtexJackpotRound.round_number), 0)).where(
                        GtexJackpotRound.pool_key == pool_key
                    )
                )
                or 0
            )
            + 1
        )
        distribution_mode = GtexJackpotDistributionMode(self.settings.jackpot_distribution_mode)
        current_round = GtexJackpotRound(
            pool_key=pool_key,
            round_number=next_round_number,
            status=GtexJackpotRoundStatus.OPEN,
            distribution_mode=distribution_mode,
            threshold_amount=self.settings.jackpot_threshold_amount,
            max_probability_limit=self.settings.jackpot_probability_limit,
            probability_cap=self.settings.jackpot_probability_cap,
            contribution_rate=self.settings.jackpot_contribution_rate,
            current_balance=Decimal("0.0000"),
            winner_count=1,
            top_split_percent=self.settings.jackpot_top_split_percent,
            min_activity_score=self.settings.jackpot_min_activity_score,
            failsafe_at=utcnow() + timedelta(hours=self.settings.jackpot_failsafe_hours),
            metadata_json={},
        )
        session.add(current_round)
        session.flush()
        self._schedule_round_cache(session, current_round)
        return current_round

    def get_state(self, session: Session, *, pool_key: str = "global") -> dict[str, Any]:
        current_round = self.ensure_open_round(session, pool_key=pool_key)
        last_winner = self.state_store.get_json(redis_keys.jackpot_last_winner(pool_key)) or {}
        return {
            "round_id": current_round.id,
            "round_number": current_round.round_number,
            "status": current_round.status.value,
            "balance": self._amount(current_round.current_balance),
            "threshold_amount": self._amount(current_round.threshold_amount),
            "probability_limit": self._amount(current_round.max_probability_limit),
            "probability_cap": self._amount(current_round.probability_cap),
            "contribution_rate": self._amount(current_round.contribution_rate),
            "participant_count": self.state_store.scard(redis_keys.jackpot_participants(current_round.id)),
            "failsafe_at": current_round.failsafe_at,
            "distribution_mode": current_round.distribution_mode.value,
            "last_winner_user_id": (
                str(last_winner.get("user_id")) if last_winner.get("user_id") else current_round.winning_user_id
            ),
            "last_trigger_mode": (
                str(last_winner.get("trigger_mode"))
                if last_winner.get("trigger_mode")
                else (current_round.trigger_mode.value if current_round.trigger_mode is not None else None)
            ),
        }

    def get_runtime_state(self, session: Session, *, pool_key: str = "global") -> dict[str, Any]:
        current_round = self.ensure_open_round(session, pool_key=pool_key)
        state = self.get_state(session, pool_key=pool_key)
        state.update(
            {
                "top_split_percent": self._amount(current_round.top_split_percent),
                "min_activity_score": self._amount(current_round.min_activity_score),
                "failsafe_hours": int(self.settings.jackpot_failsafe_hours),
                "settings_source": "runtime",
            }
        )
        return state

    def apply_runtime_settings(
        self,
        session: Session,
        *,
        threshold_amount: Decimal,
        probability_limit: Decimal,
        probability_cap: Decimal,
        failsafe_hours: int,
        contribution_rate: Decimal,
        distribution_mode: str,
        top_split_percent: Decimal,
        min_activity_score: Decimal,
        pool_key: str = "global",
    ) -> GtexSettings:
        try:
            resolved_distribution_mode = GtexJackpotDistributionMode(distribution_mode)
        except ValueError as exc:
            raise GtexValidationError("Unsupported jackpot distribution mode.") from exc
        updated_settings = replace(
            self.settings,
            jackpot_threshold_amount=self._amount(threshold_amount),
            jackpot_probability_limit=self._amount(probability_limit),
            jackpot_probability_cap=self._amount(probability_cap),
            jackpot_failsafe_hours=max(1, int(failsafe_hours)),
            jackpot_contribution_rate=self._amount(contribution_rate),
            jackpot_distribution_mode=resolved_distribution_mode.value,
            jackpot_top_split_percent=self._amount(top_split_percent),
            jackpot_min_activity_score=self._amount(min_activity_score),
        )
        self.settings = updated_settings
        current_round = self.ensure_open_round(session, pool_key=pool_key)
        current_round.threshold_amount = updated_settings.jackpot_threshold_amount
        current_round.max_probability_limit = updated_settings.jackpot_probability_limit
        current_round.probability_cap = updated_settings.jackpot_probability_cap
        current_round.contribution_rate = updated_settings.jackpot_contribution_rate
        current_round.distribution_mode = resolved_distribution_mode
        current_round.top_split_percent = updated_settings.jackpot_top_split_percent
        current_round.min_activity_score = updated_settings.jackpot_min_activity_score
        current_round.failsafe_at = utcnow() + timedelta(hours=updated_settings.jackpot_failsafe_hours)
        session.flush()
        self._schedule_round_cache(session, current_round)
        return updated_settings

    def set_current_balance(
        self,
        session: Session,
        *,
        balance: Decimal,
        actor: User,
        reason: str | None = None,
        pool_key: str = "global",
    ) -> GtexJackpotRound:
        target_balance = self._amount(balance)
        if target_balance < Decimal("0.0000"):
            raise GtexValidationError("Jackpot balance cannot be negative.")
        current_round = self.ensure_open_round(session, pool_key=pool_key)
        previous_balance = self._amount(current_round.current_balance)
        delta = self._amount(target_balance - previous_balance)
        if delta != Decimal("0.0000"):
            lottery_pool = self.wallet_service.ensure_lottery_pool_account(session, LedgerUnit.COIN)
            platform_clearing = self.wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
            if delta > Decimal("0.0000"):
                postings = [
                    LedgerPosting(
                        account=platform_clearing, amount=-delta, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT
                    ),
                    LedgerPosting(account=lottery_pool, amount=delta, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
                ]
            else:
                postings = [
                    LedgerPosting(account=lottery_pool, amount=delta, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
                    LedgerPosting(
                        account=platform_clearing, amount=-delta, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT
                    ),
                ]
            self.wallet_service.append_transaction(
                session,
                postings=postings,
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                reference=f"gtex-jackpot-admin-balance:{current_round.id}:{generate_uuid()}",
                description="Admin jackpot balance adjustment",
                actor=actor,
                metadata={
                    "round_id": current_round.id,
                    "previous_balance": str(previous_balance),
                    "target_balance": str(target_balance),
                    "delta": str(delta),
                    "reason": reason,
                },
            )
        metadata = dict(current_round.metadata_json or {})
        metadata["admin_balance_override"] = {
            "actor_user_id": actor.id,
            "previous_balance": str(previous_balance),
            "target_balance": str(target_balance),
            "reason": reason,
            "updated_at": utcnow().isoformat(),
        }
        current_round.current_balance = target_balance
        current_round.metadata_json = metadata
        self._audit_log(
            session,
            actor_user_id=actor.id,
            action_key="gtex.jackpot.balance.updated",
            resource_type="gtex_jackpot",
            resource_id=current_round.id,
            detail="Admin updated the live GTEX jackpot balance.",
            metadata_json=metadata["admin_balance_override"],
        )
        self._schedule_round_cache(session, current_round)
        self._stage_event(
            session,
            name="JACKPOT_BALANCE_UPDATED",
            payload={
                "round_id": current_round.id,
                "round_number": current_round.round_number,
                "previous_balance": str(previous_balance),
                "balance": str(target_balance),
                "delta": str(delta),
            },
            aggregate_id=current_round.id,
            aggregate_type="jackpot_round",
            partition_key=current_round.id,
            realtime_topic="jackpot.balance",
        )
        session.flush()
        return current_round

    def manual_trigger(
        self,
        session: Session,
        *,
        pool_key: str = "global",
    ) -> dict[str, Any]:
        current_round = self.ensure_open_round(session, pool_key=pool_key)
        triggered_round_id = current_round.id
        triggered_round_number = current_round.round_number
        self.trigger_round(
            session,
            round_record=current_round,
            trigger_mode=GtexJackpotTriggerMode.MANUAL,
        )
        next_round = self.ensure_open_round(session, pool_key=pool_key)
        return {
            "detail": f"Manual jackpot trigger processed for round {triggered_round_number}.",
            "triggered_round_id": triggered_round_id,
            "triggered_round_number": triggered_round_number,
            "next_round_id": next_round.id,
            "next_round_number": next_round.round_number,
        }

    def list_history(self, session: Session, *, limit: int = 20) -> list[GtexJackpotRound]:
        rounds = session.scalars(
            select(GtexJackpotRound).order_by(GtexJackpotRound.round_number.desc()).limit(limit)
        ).all()
        for round_record in rounds:
            round_record.payouts
        return list(rounds)

    def contribute_from_wallet(
        self,
        session: Session,
        *,
        actor: User,
        source_type: GtexContributionSourceType | str,
        source_id: str | None,
        entry_fee: Decimal,
        contribution_amount: Decimal | None = None,
        eligibility_score: Decimal,
        metadata: dict[str, Any] | None = None,
    ) -> GtexJackpotContribution:
        resolved_contribution_amount = self._amount(
            contribution_amount
            if contribution_amount is not None
            else self._amount(entry_fee) * self.settings.jackpot_contribution_rate
        )
        if resolved_contribution_amount <= Decimal("0.0000"):
            raise GtexValidationError("Jackpot contribution amount must be greater than zero.")
        lottery_pool = self.wallet_service.ensure_lottery_pool_account(session, LedgerUnit.COIN)
        actor_account = self.wallet_service.get_user_account(session, actor, LedgerUnit.COIN)
        try:
            self.wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(account=actor_account, amount=-resolved_contribution_amount),
                    LedgerPosting(account=lottery_pool, amount=resolved_contribution_amount),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                reference=f"gtex-jackpot:{actor.id}:{utcnow().timestamp()}",
                description="GTEX jackpot contribution",
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise GtexConflictError(str(exc)) from exc
        return self.record_contribution(
            session,
            participant_user_id=actor.id,
            source_type=source_type,
            source_id=source_id,
            entry_fee=entry_fee,
            contribution_amount=resolved_contribution_amount,
            eligibility_score=eligibility_score,
            metadata=metadata,
        )

    def record_contribution(
        self,
        session: Session,
        *,
        participant_user_id: str | None,
        source_type: GtexContributionSourceType | str,
        source_id: str | None,
        entry_fee: Decimal,
        contribution_amount: Decimal | None = None,
        eligibility_score: Decimal = Decimal("1.0000"),
        metadata: dict[str, Any] | None = None,
    ) -> GtexJackpotContribution:
        current_round = self.ensure_open_round(session)
        resolved_amount = self._amount(
            contribution_amount or (self._amount(entry_fee) * self.settings.jackpot_contribution_rate)
        )
        contribution = GtexJackpotContribution(
            round_id=current_round.id,
            participant_user_id=participant_user_id,
            source_type=GtexContributionSourceType(str(source_type)),
            source_id=source_id,
            entry_fee=self._amount(entry_fee),
            contribution_amount=resolved_amount,
            eligibility_score=self._amount(eligibility_score),
            metadata_json=dict(metadata or {}),
        )
        current_round.current_balance = self._amount(current_round.current_balance + resolved_amount)
        session.add(contribution)
        session.flush()
        self._schedule_round_cache(session, current_round)
        if participant_user_id:
            defer_session_callback_until_commit(
                session,
                callback=lambda round_id=current_round.id, user_id=participant_user_id: self.state_store.sadd(
                    redis_keys.jackpot_participants(round_id),
                    user_id,
                ),
            )
        defer_session_callback_until_commit(
            session,
            callback=lambda amount=resolved_amount: self.state_store.increment_decimal(
                redis_keys.jackpot_balance(),
                amount,
            ),
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda round_id=current_round.id: self.state_store.enqueue(
                redis_keys.stream_jackpot(),
                {"round_id": round_id},
            ),
        )
        self._stage_event(
            session,
            name="JACKPOT_CONTRIBUTION_RECORDED",
            payload={
                "round_id": current_round.id,
                "participant_user_id": participant_user_id,
                "source_type": contribution.source_type.value,
                "source_id": source_id,
                "entry_fee": str(contribution.entry_fee),
                "contribution_amount": str(contribution.contribution_amount),
                "eligibility_score": str(contribution.eligibility_score),
            },
            aggregate_id=contribution.id,
            aggregate_type="jackpot_contribution",
            partition_key=current_round.id,
            realtime_topic="jackpot.contribution",
        )
        return contribution

    def evaluate_trigger(
        self, session: Session, *, pool_key: str = "global"
    ) -> tuple[GtexJackpotRound, GtexJackpotTriggerMode] | None:
        current_round = self.ensure_open_round(session, pool_key=pool_key)
        if self._amount(current_round.current_balance) <= Decimal("0.0000"):
            return None
        now = utcnow()
        if self._amount(current_round.current_balance) >= self._amount(current_round.threshold_amount):
            return current_round, GtexJackpotTriggerMode.THRESHOLD
        if now >= current_round.failsafe_at:
            return current_round, GtexJackpotTriggerMode.FAILSAFE
        if self._amount(current_round.max_probability_limit) <= Decimal("0.0000"):
            return None
        probability = min(
            float(self._amount(current_round.probability_cap)),
            float(self._amount(current_round.current_balance) / self._amount(current_round.max_probability_limit)),
        )
        if self._random.random() < probability:
            return current_round, GtexJackpotTriggerMode.PROBABILITY
        return None

    def process_due_round(self, session: Session) -> GtexJackpotRound | None:
        outcome = self.evaluate_trigger(session)
        if outcome is None:
            return None
        current_round, trigger_mode = outcome
        self.trigger_round(session, round_record=current_round, trigger_mode=trigger_mode)
        return current_round

    def trigger_round(
        self,
        session: Session,
        *,
        round_record: GtexJackpotRound,
        trigger_mode: GtexJackpotTriggerMode,
    ) -> GtexJackpotRound:
        if round_record.status != GtexJackpotRoundStatus.OPEN:
            raise GtexConflictError("Jackpot round is no longer open.")
        entries = session.execute(
            select(
                GtexJackpotContribution.participant_user_id,
                func.sum(GtexJackpotContribution.contribution_amount),
                func.max(GtexJackpotContribution.eligibility_score),
            )
            .select_from(GtexJackpotContribution)
            .join(User, User.id == GtexJackpotContribution.participant_user_id)
            .where(
                GtexJackpotContribution.round_id == round_record.id,
                GtexJackpotContribution.participant_user_id.is_not(None),
                User.is_active.is_(True),
            )
            .group_by(GtexJackpotContribution.participant_user_id)
        ).all()
        eligible: list[dict[str, Any]] = []
        for user_id, total_amount, max_score in entries:
            if user_id is None:
                continue
            weight = self._amount(total_amount) * max(self._amount(max_score), Decimal("1.0000"))
            if self._amount(max_score) < self._amount(round_record.min_activity_score):
                continue
            eligible.append(
                {
                    "user_id": str(user_id),
                    "weight": self._amount(weight),
                }
            )
        round_record.trigger_mode = trigger_mode
        round_record.trigger_reason = f"{trigger_mode.value}_trigger"
        round_record.triggered_at = utcnow()
        if not eligible:
            next_round = self._roll_round(
                session, round_record=round_record, carryover_balance=self._amount(round_record.current_balance)
            )
            self._stage_event(
                session,
                name="JACKPOT_TRIGGERED",
                payload={
                    "round_id": round_record.id,
                    "trigger_mode": trigger_mode.value,
                    "winners": [],
                    "carryover_balance": str(next_round.current_balance),
                },
                aggregate_id=round_record.id,
                aggregate_type="jackpot_round",
                partition_key=round_record.id,
                realtime_topic="jackpot.triggered",
            )
            return round_record
        payouts = self._build_payouts(round_record=round_record, eligible=eligible)
        lottery_pool = self.wallet_service.ensure_lottery_pool_account(session, LedgerUnit.COIN)
        postings = [LedgerPosting(account=lottery_pool, amount=-self._amount(item["amount"])) for item in payouts]
        for payout in payouts:
            user = session.get(User, payout["user_id"])
            if user is None:
                continue
            user_account = self.wallet_service.get_user_account(session, user, LedgerUnit.COIN)
            postings.append(LedgerPosting(account=user_account, amount=self._amount(payout["amount"])))
        self.wallet_service.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
            transaction_type=LedgerTransactionType.LOTTERY_REWARD,
            reference=f"gtex-jackpot-payout:{round_record.id}",
            description=f"GTEX jackpot round {round_record.round_number} payout",
        )
        round_record.status = GtexJackpotRoundStatus.SETTLED
        round_record.settled_at = utcnow()
        round_record.winning_user_id = payouts[0]["user_id"]
        for index, payout in enumerate(payouts, start=1):
            payout_amount = self._amount(payout["amount"])
            session.add(
                GtexJackpotPayout(
                    round_id=round_record.id,
                    user_id=payout["user_id"],
                    rank=index,
                    payout_amount=payout_amount,
                    payout_ratio=self._amount(payout["ratio"]),
                    eligibility_weight=self._amount(payout["weight"]),
                )
            )
            session.add(
                NotificationRecord(
                    user_id=payout["user_id"],
                    topic="jackpot",
                    template_key="GTEX_JACKPOT_WON",
                    resource_type="gtex_jackpot_round",
                    resource_id=round_record.id,
                    message=f"Jackpot dropped: {payout_amount} GTEX Coin has been credited to your wallet.",
                    metadata_json={
                        "round_id": round_record.id,
                        "round_number": round_record.round_number,
                        "trigger_mode": trigger_mode.value,
                        "amount": str(payout_amount),
                        "payout_rank": index,
                        "payout_ratio": str(self._amount(payout["ratio"])),
                    },
                )
            )
        next_round = self._roll_round(session, round_record=round_record, carryover_balance=Decimal("0.0000"))
        defer_session_callback_until_commit(
            session,
            callback=lambda winner_id=round_record.winning_user_id, trigger=trigger_mode.value: self.state_store.set_json(
                redis_keys.jackpot_last_winner(),
                {"user_id": winner_id, "trigger_mode": trigger, "round_id": round_record.id},
            ),
        )
        self._stage_event(
            session,
            name="JACKPOT_TRIGGERED",
            payload={
                "round_id": round_record.id,
                "round_number": round_record.round_number,
                "trigger_mode": trigger_mode.value,
                "balance": str(round_record.current_balance),
                "winners": [
                    {
                        "user_id": payout["user_id"],
                        "amount": str(payout["amount"]),
                        "ratio": str(payout["ratio"]),
                    }
                    for payout in payouts
                ],
                "next_round_id": next_round.id,
            },
            aggregate_id=round_record.id,
            aggregate_type="jackpot_round",
            partition_key=round_record.id,
            realtime_topic="jackpot.triggered",
        )
        return round_record

    def _build_payouts(self, *, round_record: GtexJackpotRound, eligible: list[dict[str, Any]]) -> list[dict[str, Any]]:
        total_balance = self._amount(round_record.current_balance)
        if round_record.distribution_mode == GtexJackpotDistributionMode.SINGLE_WINNER:
            winner = self._weighted_choice(eligible)
            return [
                {
                    "user_id": winner["user_id"],
                    "amount": total_balance,
                    "ratio": Decimal("1.0000"),
                    "weight": winner["weight"],
                }
            ]
        if round_record.distribution_mode == GtexJackpotDistributionMode.TOP_SPLIT:
            cutoff = max(1, math.ceil(len(eligible) * float(self.settings.jackpot_top_split_percent)))
            selected = sorted(eligible, key=lambda item: (-item["weight"], item["user_id"]))[:cutoff]
        else:
            selected = sorted(eligible, key=lambda item: (-item["weight"], item["user_id"]))[: min(5, len(eligible))]
        total_weight = sum(self._amount(item["weight"]) for item in selected) or Decimal("1.0000")
        payouts: list[dict[str, Any]] = []
        allocated = Decimal("0.0000")
        for index, participant in enumerate(selected):
            if index == len(selected) - 1:
                amount = self._amount(total_balance - allocated)
            else:
                ratio = self._amount(self._amount(participant["weight"]) / total_weight)
                amount = self._amount(total_balance * ratio)
                allocated += amount
            ratio = self._amount(amount / total_balance) if total_balance > Decimal("0.0000") else Decimal("0.0000")
            payouts.append(
                {
                    "user_id": participant["user_id"],
                    "amount": amount,
                    "ratio": ratio,
                    "weight": participant["weight"],
                }
            )
        return payouts

    def _weighted_choice(self, eligible: list[dict[str, Any]]) -> dict[str, Any]:
        total_weight = sum(float(self._amount(item["weight"])) for item in eligible)
        if total_weight <= 0:
            return eligible[0]
        pick = self._random.random() * total_weight
        cumulative = 0.0
        for item in eligible:
            cumulative += float(self._amount(item["weight"]))
            if cumulative >= pick:
                return item
        return eligible[-1]

    def _roll_round(
        self,
        session: Session,
        *,
        round_record: GtexJackpotRound,
        carryover_balance: Decimal,
    ) -> GtexJackpotRound:
        round_record.status = (
            GtexJackpotRoundStatus.CANCELLED
            if self._amount(carryover_balance) > Decimal("0.0000") and round_record.winning_user_id is None
            else GtexJackpotRoundStatus.SETTLED
        )
        round_record.settled_at = round_record.settled_at or utcnow()
        next_round = GtexJackpotRound(
            pool_key=round_record.pool_key,
            round_number=round_record.round_number + 1,
            status=GtexJackpotRoundStatus.OPEN,
            distribution_mode=GtexJackpotDistributionMode(self.settings.jackpot_distribution_mode),
            threshold_amount=self.settings.jackpot_threshold_amount,
            max_probability_limit=self.settings.jackpot_probability_limit,
            probability_cap=self.settings.jackpot_probability_cap,
            contribution_rate=self.settings.jackpot_contribution_rate,
            current_balance=self._amount(carryover_balance),
            winner_count=1,
            top_split_percent=self.settings.jackpot_top_split_percent,
            min_activity_score=self.settings.jackpot_min_activity_score,
            failsafe_at=utcnow() + timedelta(hours=self.settings.jackpot_failsafe_hours),
            metadata_json={"previous_round_id": round_record.id},
        )
        session.add(next_round)
        session.flush()
        self._schedule_round_cache(session, next_round)
        defer_session_callback_until_commit(
            session,
            callback=lambda round_id=round_record.id: self.state_store.delete(
                redis_keys.jackpot_participants(round_id)
            ),
        )
        return next_round

    def _schedule_round_cache(self, session: Session, round_record: GtexJackpotRound) -> None:
        payload = {
            "round_id": round_record.id,
            "round_number": round_record.round_number,
            "status": round_record.status.value,
            "balance": str(round_record.current_balance),
            "threshold_amount": str(round_record.threshold_amount),
            "probability_limit": str(round_record.max_probability_limit),
            "probability_cap": str(round_record.probability_cap),
            "contribution_rate": str(round_record.contribution_rate),
            "failsafe_at": round_record.failsafe_at.isoformat(),
            "distribution_mode": round_record.distribution_mode.value,
        }
        defer_session_callback_until_commit(
            session,
            callback=lambda body=dict(payload), round_id=round_record.id: self.state_store.set_json(
                redis_keys.jackpot_state(round_id),
                body,
            ),
        )


class CreatorMarketService(GtexBaseService):
    def ensure_asset_for_user(self, session: Session, user: User) -> GtexCreatorAsset:
        subject_key = self._subject_key(user=user)
        asset = session.scalar(select(GtexCreatorAsset).where(GtexCreatorAsset.subject_key == subject_key))
        if asset is not None:
            return asset
        display_name = (user.display_name or user.full_name or user.username or user.email).strip()
        asset = GtexCreatorAsset(
            subject_key=subject_key,
            subject_type=GtexAssetSubjectType.USER,
            subject_user_id=user.id,
            display_name=display_name or f"Creator {user.id[:8]}",
            base_price=self.settings.creator_default_base_price,
            current_price=self.settings.creator_default_base_price,
            total_shares=1000,
            available_shares=1000,
            circulating_shares=0,
            demand_score=Decimal("0.0000"),
            momentum_score=Decimal("0.0000"),
            win_rate=Decimal("0.0000"),
            total_matches=0,
            total_wins=0,
            total_trades=0,
            total_volume=Decimal("0.0000"),
            metadata_json={"seeded_for_user_id": user.id},
        )
        session.add(asset)
        session.flush()
        self._refresh_asset_cache(session, asset)
        return asset

    def get_asset(self, session: Session, player_id: str) -> GtexCreatorAsset:
        asset = session.get(GtexCreatorAsset, player_id)
        if asset is None:
            raise GtexNotFoundError(f"Creator market player {player_id} was not found.")
        return asset

    def get_view(self, session: Session, *, player_id: str, viewer: User | None = None) -> dict[str, Any]:
        asset = self.get_asset(session, player_id)
        holding = None
        if viewer is not None:
            holding = session.scalar(
                select(GtexCreatorHolding).where(
                    GtexCreatorHolding.user_id == viewer.id,
                    GtexCreatorHolding.player_id == asset.id,
                )
            )
        return {
            "id": asset.id,
            "subject_key": asset.subject_key,
            "subject_type": asset.subject_type.value,
            "display_name": asset.display_name,
            "base_price": self._amount(asset.base_price),
            "current_price": self._amount(asset.current_price),
            "total_shares": asset.total_shares,
            "available_shares": asset.available_shares,
            "circulating_shares": asset.circulating_shares,
            "demand_score": self._amount(asset.demand_score),
            "momentum_score": self._amount(asset.momentum_score),
            "win_rate": self._amount(asset.win_rate),
            "total_matches": asset.total_matches,
            "total_wins": asset.total_wins,
            "total_trades": asset.total_trades,
            "total_volume": self._amount(asset.total_volume),
            "holding": (
                None
                if holding is None
                else {
                    "shares_owned": self._amount(holding.shares_owned),
                    "reserved_shares": self._amount(holding.reserved_shares),
                    "avg_price": self._amount(holding.avg_price),
                }
            ),
        }

    def buy_shares(
        self,
        session: Session,
        *,
        buyer: User,
        player_id: str,
        shares: int,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> GtexCreatorTrade:
        if shares <= 0:
            raise GtexValidationError("Share quantity must be positive.")
        asset = self._get_asset_for_trade(session, player_id)
        self._assert_trade_cooldown(session, actor_id=buyer.id, player_id=player_id)
        holding = self._get_or_create_holding(session, user_id=buyer.id, player_id=player_id, for_update=True)
        max_allowed = Decimal(str(asset.total_shares)) * self.settings.creator_max_ownership_ratio
        if self._amount(holding.shares_owned + Decimal(shares)) > self._amount(max_allowed):
            raise GtexConflictError("Ownership cap exceeded for this asset.")
        if shares > asset.available_shares:
            raise GtexConflictError("Requested share volume exceeds available inventory.")
        buyer_account = self.wallet_service.get_user_account(session, buyer, LedgerUnit.COIN)
        liquidity_account = self.wallet_service.ensure_market_liquidity_account(session, LedgerUnit.COIN)
        wallet_before = self.wallet_service.get_balance(session, buyer_account)
        holding_before = self._amount(holding.shares_owned)
        avg_price_before = self._amount(holding.avg_price)
        asset_price_before = self._amount(asset.current_price)
        available_before = int(asset.available_shares)
        circulating_before = int(asset.circulating_shares)
        execution_price = self._trade_price(asset=asset, shares=shares, side=GtexTradeSide.BUY)
        gross_amount = self._amount(execution_price * Decimal(shares))
        try:
            entries = self.wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(account=buyer_account, amount=-gross_amount),
                    LedgerPosting(account=liquidity_account, amount=gross_amount),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                transaction_type=LedgerTransactionType.TRADE_BUY,
                reference=f"gtex-market-buy:{player_id}:{buyer.id}:{utcnow().timestamp()}",
                description=f"Purchased {shares} GTEX creator shares",
                actor=buyer,
            )
        except InsufficientBalanceError as exc:
            raise GtexConflictError(str(exc)) from exc
        transaction_id = entries[0].transaction_id if entries else None
        previous_cost = avg_price_before * holding_before
        new_share_count = holding_before + Decimal(shares)
        holding.shares_owned = self._amount(new_share_count)
        holding.avg_price = self._amount((previous_cost + gross_amount) / new_share_count)
        asset.available_shares -= shares
        asset.circulating_shares += shares
        asset.total_trades += 1
        asset.total_volume = self._amount(asset.total_volume + gross_amount)
        asset.demand_score = self._amount(asset.demand_score + Decimal(shares))
        asset.momentum_score = self._amount(asset.momentum_score + Decimal("1.2500"))
        asset.current_price = self._revalue_asset(asset)
        anomaly_flag = self._detect_trade_anomaly(
            session,
            actor_id=buyer.id,
            player_id=player_id,
            gross_amount=gross_amount,
        )
        wallet_after = self.wallet_service.get_balance(session, buyer_account)
        trade = GtexCreatorTrade(
            buyer_id=buyer.id,
            seller_id=None,
            player_id=player_id,
            side=GtexTradeSide.BUY,
            shares=Decimal(shares),
            price=execution_price,
            gross_amount=gross_amount,
            demand_impact=self._amount(asset.current_price - self._amount(asset.base_price)),
            anomaly_flag=anomaly_flag,
            metadata_json=self._build_trade_metadata(
                transaction_id=transaction_id,
                wallet_before=wallet_before,
                wallet_after=wallet_after,
                holding_before=holding_before,
                holding_after=self._amount(holding.shares_owned),
                avg_price_before=avg_price_before,
                avg_price_after=self._amount(holding.avg_price),
                asset_price_before=asset_price_before,
                asset_price_after=self._amount(asset.current_price),
                available_before=available_before,
                available_after=int(asset.available_shares),
                circulating_before=circulating_before,
                circulating_after=int(asset.circulating_shares),
                client_ip=client_ip,
                user_agent=user_agent,
            ),
        )
        session.add(trade)
        session.flush()
        extra_flag = self._record_trade_risk(
            session,
            actor=buyer,
            trade=trade,
            client_ip=client_ip,
        )
        trade.anomaly_flag = bool(trade.anomaly_flag or extra_flag)
        self._audit_trade(session, actor=buyer, trade=trade)
        self._record_price_history(session, asset=asset, reason="trade_buy")
        self._refresh_asset_cache(session, asset, cooldown_user_id=buyer.id)
        defer_session_callback_until_commit(
            session,
            callback=lambda player=player_id: self.state_store.enqueue(
                redis_keys.stream_valuation(),
                {"player_id": player, "reason": "trade_buy"},
            ),
        )
        self._stage_event(
            session,
            name="TRADE_EXECUTED",
            payload={
                "trade_id": trade.id,
                "player_id": player_id,
                "side": trade.side.value,
                "buyer_id": buyer.id,
                "shares": str(trade.shares),
                "price": str(trade.price),
                "current_price": str(asset.current_price),
                "available_shares": int(asset.available_shares),
                "circulating_shares": int(asset.circulating_shares),
                "gross_amount": str(trade.gross_amount),
                "anomaly_flag": trade.anomaly_flag,
            },
            aggregate_id=trade.id,
            aggregate_type="creator_trade",
            partition_key=player_id,
            realtime_topic="market.trade",
        )
        return trade

    def sell_shares(
        self,
        session: Session,
        *,
        seller: User,
        player_id: str,
        shares: int,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> GtexCreatorTrade:
        if shares <= 0:
            raise GtexValidationError("Share quantity must be positive.")
        asset = self._get_asset_for_trade(session, player_id)
        self._assert_trade_cooldown(session, actor_id=seller.id, player_id=player_id)
        holding = self._get_or_create_holding(session, user_id=seller.id, player_id=player_id, for_update=True)
        holding_before = self._amount(holding.shares_owned)
        avg_price_before = self._amount(holding.avg_price)
        if holding_before < Decimal(shares):
            raise GtexConflictError("Not enough shares are available to sell.")
        execution_price = self._trade_price(asset=asset, shares=shares, side=GtexTradeSide.SELL)
        gross_amount = self._amount(execution_price * Decimal(shares))
        seller_account = self.wallet_service.get_user_account(session, seller, LedgerUnit.COIN)
        liquidity_account = self.wallet_service.ensure_market_liquidity_account(session, LedgerUnit.COIN)
        wallet_before = self.wallet_service.get_balance(session, seller_account)
        asset_price_before = self._amount(asset.current_price)
        available_before = int(asset.available_shares)
        circulating_before = int(asset.circulating_shares)
        entries = self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=seller_account, amount=gross_amount),
                LedgerPosting(account=liquidity_account, amount=-gross_amount),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
            transaction_type=LedgerTransactionType.TRADE_SELL,
            reference=f"gtex-market-sell:{player_id}:{seller.id}:{utcnow().timestamp()}",
            description=f"Sold {shares} GTEX creator shares",
            actor=seller,
        )
        transaction_id = entries[0].transaction_id if entries else None
        holding.shares_owned = self._amount(holding_before - Decimal(shares))
        if self._amount(holding.shares_owned) <= Decimal("0.0000"):
            holding.avg_price = Decimal("0.0000")
        asset.available_shares += shares
        asset.circulating_shares = max(0, asset.circulating_shares - shares)
        asset.total_trades += 1
        asset.total_volume = self._amount(asset.total_volume + gross_amount)
        asset.demand_score = self._amount(max(Decimal("0.0000"), self._amount(asset.demand_score) - Decimal(shares)))
        asset.momentum_score = self._amount(
            max(Decimal("0.0000"), self._amount(asset.momentum_score) - Decimal("0.7500"))
        )
        asset.current_price = self._revalue_asset(asset)
        anomaly_flag = self._detect_trade_anomaly(
            session,
            actor_id=seller.id,
            player_id=player_id,
            gross_amount=gross_amount,
        )
        wallet_after = self.wallet_service.get_balance(session, seller_account)
        cost_basis = self._amount(avg_price_before * Decimal(shares))
        realized_profit = self._amount(gross_amount - cost_basis)
        profit_ratio = Decimal("0.0000")
        if cost_basis > Decimal("0.0000"):
            profit_ratio = self._amount(realized_profit / cost_basis)
        trade = GtexCreatorTrade(
            buyer_id=None,
            seller_id=seller.id,
            player_id=player_id,
            side=GtexTradeSide.SELL,
            shares=Decimal(shares),
            price=execution_price,
            gross_amount=gross_amount,
            demand_impact=self._amount(self._amount(asset.base_price) - self._amount(asset.current_price)),
            anomaly_flag=anomaly_flag,
            metadata_json=self._build_trade_metadata(
                transaction_id=transaction_id,
                wallet_before=wallet_before,
                wallet_after=wallet_after,
                holding_before=holding_before,
                holding_after=self._amount(holding.shares_owned),
                avg_price_before=avg_price_before,
                avg_price_after=self._amount(holding.avg_price),
                asset_price_before=asset_price_before,
                asset_price_after=self._amount(asset.current_price),
                available_before=available_before,
                available_after=int(asset.available_shares),
                circulating_before=circulating_before,
                circulating_after=int(asset.circulating_shares),
                client_ip=client_ip,
                user_agent=user_agent,
                realized_profit=realized_profit,
                profit_ratio=profit_ratio,
            ),
        )
        session.add(trade)
        session.flush()
        extra_flag = self._record_trade_risk(
            session,
            actor=seller,
            trade=trade,
            client_ip=client_ip,
            realized_profit=realized_profit,
            profit_ratio=profit_ratio,
        )
        trade.anomaly_flag = bool(trade.anomaly_flag or extra_flag)
        self._audit_trade(session, actor=seller, trade=trade)
        self._record_price_history(session, asset=asset, reason="trade_sell")
        self._refresh_asset_cache(session, asset, cooldown_user_id=seller.id)
        defer_session_callback_until_commit(
            session,
            callback=lambda player=player_id: self.state_store.enqueue(
                redis_keys.stream_valuation(),
                {"player_id": player, "reason": "trade_sell"},
            ),
        )
        self._stage_event(
            session,
            name="TRADE_EXECUTED",
            payload={
                "trade_id": trade.id,
                "player_id": player_id,
                "side": trade.side.value,
                "seller_id": seller.id,
                "shares": str(trade.shares),
                "price": str(trade.price),
                "current_price": str(asset.current_price),
                "available_shares": int(asset.available_shares),
                "circulating_shares": int(asset.circulating_shares),
                "gross_amount": str(trade.gross_amount),
                "anomaly_flag": trade.anomaly_flag,
            },
            aggregate_id=trade.id,
            aggregate_type="creator_trade",
            partition_key=player_id,
            realtime_topic="market.trade",
        )
        return trade

    def record_match_performance(
        self,
        session: Session,
        *,
        user: User,
        won: bool,
        source_match_id: str,
        score_delta: int,
    ) -> GtexCreatorAsset:
        asset = self.ensure_asset_for_user(session, user)
        asset.total_matches += 1
        if won:
            asset.total_wins += 1
            asset.momentum_score = self._amount(asset.momentum_score + Decimal("2.0000"))
        else:
            asset.momentum_score = self._amount(max(Decimal("0.0000"), asset.momentum_score - Decimal("0.5000")))
        asset.win_rate = self._amount(Decimal(asset.total_wins) / Decimal(max(asset.total_matches, 1)))
        asset.current_price = self._revalue_asset(asset)
        self._record_price_history(
            session,
            asset=asset,
            reason="match_completed",
            metadata={"match_id": source_match_id, "score_delta": score_delta},
        )
        self._refresh_asset_cache(session, asset)
        defer_session_callback_until_commit(
            session,
            callback=lambda player=asset.id: self.state_store.enqueue(
                redis_keys.stream_valuation(),
                {"player_id": player, "reason": "match_completed"},
            ),
        )
        return asset

    def recalculate_asset_price(self, session: Session, *, player_id: str, reason: str) -> GtexCreatorAsset:
        asset = self.get_asset(session, player_id)
        previous_price = self._amount(asset.current_price)
        asset.current_price = self._revalue_asset(asset)
        if asset.current_price != previous_price:
            self._record_price_history(session, asset=asset, reason=reason)
        self._refresh_asset_cache(session, asset)
        self._stage_event(
            session,
            name="PLAYER_VALUE_UPDATED",
            payload={
                "player_id": asset.id,
                "reason": reason,
                "current_price": str(asset.current_price),
                "win_rate": str(asset.win_rate),
                "demand_score": str(asset.demand_score),
            },
            aggregate_id=asset.id,
            aggregate_type="creator_asset",
            partition_key=asset.id,
            realtime_topic="market.valuation",
        )
        return asset

    def list_trending(self, session: Session, *, limit: int = 10, viewer: User | None = None) -> list[dict[str, Any]]:
        member_ids = [
            str(item) for item in self.state_store.zrevrange(redis_keys.trending_players(), 0, max(limit - 1, 0))
        ]
        if member_ids:
            assets = session.scalars(select(GtexCreatorAsset).where(GtexCreatorAsset.id.in_(member_ids))).all()
            asset_map = {asset.id: asset for asset in assets}
            return [
                self.get_view(session, player_id=member_id, viewer=viewer)
                for member_id in member_ids
                if member_id in asset_map
            ]
        assets = session.scalars(
            select(GtexCreatorAsset)
            .order_by(GtexCreatorAsset.demand_score.desc(), GtexCreatorAsset.current_price.desc())
            .limit(limit)
        ).all()
        return [self.get_view(session, player_id=asset.id, viewer=viewer) for asset in assets]

    def _get_asset_for_trade(self, session: Session, player_id: str) -> GtexCreatorAsset:
        statement = select(GtexCreatorAsset).where(GtexCreatorAsset.id == player_id)
        if self._supports_row_locks(session):
            statement = statement.with_for_update()
        asset = session.scalar(statement)
        if asset is None:
            raise GtexNotFoundError(f"Creator market player {player_id} was not found.")
        return asset

    def _get_or_create_holding(
        self,
        session: Session,
        *,
        user_id: str,
        player_id: str,
        for_update: bool = False,
    ) -> GtexCreatorHolding:
        statement = select(GtexCreatorHolding).where(
            GtexCreatorHolding.user_id == user_id,
            GtexCreatorHolding.player_id == player_id,
        )
        if for_update and self._supports_row_locks(session):
            statement = statement.with_for_update()
        holding = session.scalar(statement)
        if holding is None:
            holding = GtexCreatorHolding(
                user_id=user_id,
                player_id=player_id,
                shares_owned=Decimal("0.0000"),
                reserved_shares=Decimal("0.0000"),
                avg_price=Decimal("0.0000"),
            )
            savepoint = session.begin_nested()
            try:
                session.add(holding)
                session.flush()
            except IntegrityError:
                savepoint.rollback()
                holding = session.scalar(statement)
                if holding is None:
                    raise GtexConflictError("Unable to resolve holding state for this trade.")
            else:
                savepoint.commit()
        return holding

    def _build_trade_metadata(
        self,
        *,
        transaction_id: str | None,
        wallet_before: Decimal,
        wallet_after: Decimal,
        holding_before: Decimal,
        holding_after: Decimal,
        avg_price_before: Decimal,
        avg_price_after: Decimal,
        asset_price_before: Decimal,
        asset_price_after: Decimal,
        available_before: int,
        available_after: int,
        circulating_before: int,
        circulating_after: int,
        client_ip: str | None,
        user_agent: str | None,
        realized_profit: Decimal | None = None,
        profit_ratio: Decimal | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "transaction_id": transaction_id,
            "wallet_before": str(self._amount(wallet_before)),
            "wallet_after": str(self._amount(wallet_after)),
            "holding_before": str(self._amount(holding_before)),
            "holding_after": str(self._amount(holding_after)),
            "avg_price_before": str(self._amount(avg_price_before)),
            "avg_price_after": str(self._amount(avg_price_after)),
            "asset_price_before": str(self._amount(asset_price_before)),
            "asset_price_after": str(self._amount(asset_price_after)),
            "available_shares_before": available_before,
            "available_shares_after": available_after,
            "circulating_shares_before": circulating_before,
            "circulating_shares_after": circulating_after,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }
        if realized_profit is not None:
            payload["realized_profit"] = str(self._amount(realized_profit))
        if profit_ratio is not None:
            payload["profit_ratio"] = str(self._amount(profit_ratio))
        return payload

    def _record_trade_risk(
        self,
        session: Session,
        *,
        actor: User,
        trade: GtexCreatorTrade,
        client_ip: str | None,
        realized_profit: Decimal | None = None,
        profit_ratio: Decimal | None = None,
    ) -> bool:
        triggered_categories: list[str] = []
        if client_ip and self._flag_shared_ip_accounts(
            session,
            actor_id=actor.id,
            player_id=trade.player_id,
            client_ip=client_ip,
            trade_id=trade.id,
        ):
            triggered_categories.append("shared_ip_accounts")
        if self._flag_rapid_trade_loop(
            session,
            actor_id=actor.id,
            player_id=trade.player_id,
            trade_id=trade.id,
        ):
            triggered_categories.append("rapid_trade_loop")
        if realized_profit is not None and self._flag_abnormal_profit(
            session,
            actor_id=actor.id,
            player_id=trade.player_id,
            trade_id=trade.id,
            realized_profit=realized_profit,
            profit_ratio=profit_ratio or Decimal("0.0000"),
        ):
            triggered_categories.append("abnormal_profit")
        if triggered_categories:
            trade.metadata_json = {
                **dict(trade.metadata_json or {}),
                "risk_categories": sorted(set(triggered_categories)),
            }
            return True
        return False

    def _flag_shared_ip_accounts(
        self,
        session: Session,
        *,
        actor_id: str,
        player_id: str,
        client_ip: str,
        trade_id: str,
    ) -> bool:
        RiskOpsService(session).ingest_signal(
            actor_user_id=actor_id,
            user_id=actor_id,
            signal_type=RiskSignalType.IP_ADDRESS,
            signal_key="gtex_trade_ip",
            signal_value=client_ip,
            ip_address=client_ip,
            source="gtex_market_trade",
            confidence_score=Decimal("85.00"),
            metadata_json={"player_id": player_id, "trade_id": trade_id},
        )
        recent_cutoff = utcnow() - timedelta(hours=24)
        recent_trades = session.scalars(
            select(GtexCreatorTrade)
            .where(GtexCreatorTrade.created_at >= recent_cutoff)
            .order_by(GtexCreatorTrade.created_at.desc())
            .limit(250)
        ).all()
        linked_user_ids = sorted(
            {
                str(item.buyer_id or item.seller_id)
                for item in recent_trades
                if (item.metadata_json or {}).get("client_ip") == client_ip and (item.buyer_id or item.seller_id)
            }
        )
        if len(linked_user_ids) < 2:
            return False
        self._record_risk_flag(
            session,
            category="shared_ip_accounts",
            subject_key=f"user:{actor_id}",
            reference_id=trade_id,
            severity="high" if len(linked_user_ids) >= 3 else "medium",
            signal_score=self._amount(len(linked_user_ids)),
            detail="Multiple accounts traded from the same IP address inside the review window.",
            metadata={
                "client_ip": client_ip,
                "linked_user_ids": linked_user_ids,
                "player_id": player_id,
            },
        )
        return True

    def _flag_rapid_trade_loop(
        self,
        session: Session,
        *,
        actor_id: str,
        player_id: str,
        trade_id: str,
    ) -> bool:
        recent_cutoff = utcnow() - timedelta(minutes=15)
        recent_trades = session.scalars(
            select(GtexCreatorTrade)
            .where(
                GtexCreatorTrade.player_id == player_id,
                GtexCreatorTrade.created_at >= recent_cutoff,
                or_(GtexCreatorTrade.buyer_id == actor_id, GtexCreatorTrade.seller_id == actor_id),
            )
            .order_by(GtexCreatorTrade.created_at.desc())
            .limit(8)
        ).all()
        if len(recent_trades) < 4:
            return False
        alternating_count = 1
        last_side = recent_trades[0].side
        for item in recent_trades[1:]:
            if item.side != last_side:
                alternating_count += 1
                last_side = item.side
                continue
            break
        if alternating_count < 4:
            return False
        RiskOpsService(session).ingest_signal(
            actor_user_id=actor_id,
            user_id=actor_id,
            signal_type=RiskSignalType.TRANSACTION_PATTERN,
            signal_key="rapid_trade_loop",
            signal_value=f"{actor_id}:{player_id}",
            source="gtex_market_trade",
            confidence_score=Decimal("90.00"),
            metadata_json={
                "pattern": "rapid_trade_loop",
                "category": "rapid_trade_loop",
                "loop_count": alternating_count,
                "window_minutes": 15,
                "player_id": player_id,
                "trade_id": trade_id,
            },
        )
        self._record_risk_flag(
            session,
            category="rapid_trade_loop",
            subject_key=f"user:{actor_id}",
            reference_id=player_id,
            severity="high",
            signal_score=self._amount(alternating_count),
            detail="Rapid alternating buy and sell activity crossed the anti-loop threshold.",
            metadata={
                "loop_count": alternating_count,
                "window_minutes": 15,
                "trade_id": trade_id,
            },
        )
        return True

    def _flag_abnormal_profit(
        self,
        session: Session,
        *,
        actor_id: str,
        player_id: str,
        trade_id: str,
        realized_profit: Decimal,
        profit_ratio: Decimal,
    ) -> bool:
        resolved_profit = self._amount(realized_profit)
        resolved_ratio = self._amount(profit_ratio)
        if resolved_profit < Decimal("100.0000") or resolved_ratio < Decimal("1.5000"):
            return False
        RiskOpsService(session).ingest_signal(
            actor_user_id=actor_id,
            user_id=actor_id,
            signal_type=RiskSignalType.TRANSACTION_PATTERN,
            signal_key="abnormal_profit",
            signal_value=f"{actor_id}:{player_id}",
            source="gtex_market_trade",
            confidence_score=Decimal("88.00"),
            metadata_json={
                "category": "abnormal_profit",
                "profit_amount": str(resolved_profit),
                "profit_ratio": str(resolved_ratio),
                "player_id": player_id,
                "trade_id": trade_id,
            },
        )
        self._record_risk_flag(
            session,
            category="abnormal_profit",
            subject_key=f"user:{actor_id}",
            reference_id=player_id,
            severity="high" if resolved_ratio >= Decimal("3.0000") else "medium",
            signal_score=resolved_profit,
            detail="Realized trade profits crossed the abnormal-profit review threshold.",
            metadata={
                "profit_amount": str(resolved_profit),
                "profit_ratio": str(resolved_ratio),
                "trade_id": trade_id,
            },
        )
        return True

    def _record_risk_flag(
        self,
        session: Session,
        *,
        category: str,
        subject_key: str,
        reference_id: str | None,
        severity: str,
        signal_score: Decimal,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> GtexRiskFlag:
        recent_cutoff = utcnow() - timedelta(hours=24)
        existing = session.scalar(
            select(GtexRiskFlag)
            .where(
                GtexRiskFlag.category == category,
                GtexRiskFlag.subject_key == subject_key,
                GtexRiskFlag.reference_id == reference_id,
                GtexRiskFlag.status.in_((GtexRiskFlagStatus.OPEN, GtexRiskFlagStatus.REVIEWING)),
                GtexRiskFlag.created_at >= recent_cutoff,
            )
            .order_by(GtexRiskFlag.created_at.desc())
        )
        resolved_score = self._amount(signal_score)
        if existing is not None:
            existing.signal_score = max(self._amount(existing.signal_score), resolved_score)
            existing.detail = detail
            existing.metadata_json = {**(existing.metadata_json or {}), **dict(metadata or {})}
            if severity == "high":
                existing.severity = "high"
            return existing
        flag = GtexRiskFlag(
            category=category,
            subject_key=subject_key,
            reference_id=reference_id,
            severity=severity,
            signal_score=resolved_score,
            status=GtexRiskFlagStatus.OPEN,
            detail=detail,
            metadata_json=dict(metadata or {}),
        )
        session.add(flag)
        session.flush()
        return flag

    def _audit_trade(self, session: Session, *, actor: User, trade: GtexCreatorTrade) -> None:
        self._audit_log(
            session,
            actor_user_id=actor.id,
            action_key=f"gtex.trade.{trade.side.value}",
            resource_type="gtex_creator_trade",
            resource_id=trade.id,
            detail=f"GTEX creator market {trade.side.value} executed.",
            metadata_json={
                "player_id": trade.player_id,
                "shares": str(self._amount(trade.shares)),
                "price": str(self._amount(trade.price)),
                "gross_amount": str(self._amount(trade.gross_amount)),
                "anomaly_flag": bool(trade.anomaly_flag),
                **dict(trade.metadata_json or {}),
            },
        )

    def _trade_price(self, *, asset: GtexCreatorAsset, shares: int, side: GtexTradeSide) -> Decimal:
        share_ratio = Decimal(shares) / Decimal(max(asset.total_shares, 1))
        demand_bias = self._amount(asset.demand_score) / Decimal(max(asset.total_shares, 1))
        base_price = self._amount(asset.current_price)
        if side == GtexTradeSide.BUY:
            multiplier = Decimal("1.0000") + share_ratio + (demand_bias / Decimal("2.0000"))
        else:
            multiplier = max(Decimal("0.6500"), Decimal("1.0000") - share_ratio - (demand_bias / Decimal("3.0000")))
        return self._amount(base_price * multiplier)

    def _revalue_asset(self, asset: GtexCreatorAsset) -> Decimal:
        base = self._amount(asset.base_price)
        win_component = self._amount(asset.win_rate * self.settings.creator_win_rate_multiplier)
        demand_component = self._amount(asset.demand_score * self.settings.creator_demand_multiplier)
        momentum_component = self._amount(asset.momentum_score * self.settings.creator_momentum_multiplier)
        proposed = self._amount(base + win_component + demand_component + momentum_component)
        ceiling = self._amount(base * self.settings.creator_price_ceiling_multiplier)
        return min(max(proposed, self.settings.creator_price_floor), ceiling)

    def _record_price_history(
        self,
        session: Session,
        *,
        asset: GtexCreatorAsset,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        session.add(
            GtexCreatorPriceHistory(
                player_id=asset.id,
                price=self._amount(asset.current_price),
                win_rate=self._amount(asset.win_rate),
                demand_score=self._amount(asset.demand_score),
                reason=reason,
                metadata_json=dict(metadata or {}),
            )
        )

    def _refresh_asset_cache(
        self, session: Session, asset: GtexCreatorAsset, *, cooldown_user_id: str | None = None
    ) -> None:
        defer_session_callback_until_commit(
            session,
            callback=lambda player_id=asset.id, price=self._amount(asset.current_price): self.state_store.set_decimal(
                redis_keys.creator_price(player_id),
                price,
            ),
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda player_id=asset.id, demand=self._amount(asset.demand_score): self.state_store.set_decimal(
                redis_keys.creator_demand(player_id),
                demand,
            ),
        )
        trending_score = float(
            self._amount(asset.demand_score + asset.momentum_score + (asset.current_price / Decimal("10.0000")))
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda player_id=asset.id, score=trending_score: self.state_store.zadd(
                redis_keys.trending_players(),
                {player_id: score},
            ),
        )
        if cooldown_user_id is not None and self.settings.creator_trade_cooldown_seconds > 0:
            defer_session_callback_until_commit(
                session,
                callback=lambda user_id=cooldown_user_id, player_id=asset.id: self.state_store.set_json(
                    redis_keys.creator_cooldown(user_id, player_id),
                    {"active": True},
                    ttl_seconds=self.settings.creator_trade_cooldown_seconds,
                ),
            )

    def _assert_trade_cooldown(self, session: Session, *, actor_id: str, player_id: str) -> None:
        if self.settings.creator_trade_cooldown_seconds <= 0:
            return
        cached = self.state_store.get_json(redis_keys.creator_cooldown(actor_id, player_id))
        if cached is not None:
            raise GtexConflictError("Trade cooldown is still active for this asset.")
        recent_cutoff = utcnow() - timedelta(seconds=self.settings.creator_trade_cooldown_seconds)
        recent_trade = session.scalar(
            select(GtexCreatorTrade.id).where(
                GtexCreatorTrade.player_id == player_id,
                GtexCreatorTrade.created_at >= recent_cutoff,
                or_(GtexCreatorTrade.buyer_id == actor_id, GtexCreatorTrade.seller_id == actor_id),
            )
        )
        if recent_trade is not None:
            raise GtexConflictError("Trade cooldown is still active for this asset.")

    def _detect_trade_anomaly(self, session: Session, *, actor_id: str, player_id: str, gross_amount: Decimal) -> bool:
        window_start = utcnow() - timedelta(seconds=self.settings.creator_anomaly_window_seconds)
        recent_notional = self._amount(
            session.scalar(
                select(func.coalesce(func.sum(GtexCreatorTrade.gross_amount), 0)).where(
                    GtexCreatorTrade.player_id == player_id,
                    GtexCreatorTrade.created_at >= window_start,
                )
            )
            or Decimal("0.0000")
        )
        anomalous = self._amount(recent_notional + gross_amount) >= self.settings.creator_anomaly_notional_threshold
        if anomalous:
            total_notional = self._amount(recent_notional + gross_amount)
            RiskOpsService(session).ingest_signal(
                actor_user_id=actor_id,
                user_id=actor_id,
                signal_type=RiskSignalType.TRANSACTION_PATTERN,
                signal_key="suspicious_trading",
                signal_value=f"{actor_id}:{player_id}",
                source="gtex_market_trade",
                confidence_score=Decimal("92.00"),
                metadata_json={
                    "category": "suspicious_trading",
                    "player_id": player_id,
                    "recent_notional": str(recent_notional),
                    "gross_amount": str(self._amount(gross_amount)),
                    "total_notional": str(total_notional),
                    "window_seconds": self.settings.creator_anomaly_window_seconds,
                },
            )
            self._record_risk_flag(
                session,
                category="suspicious_trading",
                subject_key=f"user:{actor_id}",
                reference_id=player_id,
                severity="high",
                signal_score=total_notional,
                detail="Creator market volume breached the configured anomaly threshold.",
                metadata={
                    "player_id": player_id,
                    "recent_notional": str(recent_notional),
                    "gross_amount": str(self._amount(gross_amount)),
                    "total_notional": str(total_notional),
                    "window_seconds": self.settings.creator_anomaly_window_seconds,
                },
            )
        return anomalous


class UnifiedEconomyService(GtexBaseService):
    def __init__(
        self,
        *,
        settings: GtexSettings,
        wallet_service: WalletService,
        state_store: StateStore,
        jackpot_service: JackpotService,
        creator_market_service: CreatorMarketService,
        event_publisher: EventPublisher | None = None,
        realtime_channel: str = "gtex.realtime",
    ) -> None:
        super().__init__(
            settings=settings,
            wallet_service=wallet_service,
            state_store=state_store,
            event_publisher=event_publisher,
            realtime_channel=realtime_channel,
        )
        self.jackpot_service = jackpot_service
        self.creator_market_service = creator_market_service

    def settle_match_completion(self, session: Session, *, match: GtexMatch) -> GtexMatch:
        metadata = dict(match.metadata_json or {})
        settlement_key = f"gtex-match-settlement:{match.id}"
        if metadata.get("economy_settled_at"):
            return match
        match.metadata_json = {
            **metadata,
            "settlement_idempotency_key": settlement_key,
            "global_match_id": global_match_id(match.id),
        }
        human_users = [
            user
            for user in (
                session.get(User, match.home_user_id) if match.home_user_id else None,
                session.get(User, match.away_user_id) if match.away_user_id else None,
            )
            if user is not None
        ]
        actual_contribution = self._amount(
            Decimal(len(human_users)) * self._amount(match.entry_fee) * self.settings.jackpot_contribution_rate
        )
        match.jackpot_contribution = actual_contribution
        human_winner = session.get(User, match.winner_user_id) if match.winner_user_id else None
        operations_account = self.wallet_service.ensure_operations_account(session, LedgerUnit.COIN)
        lottery_pool = self.wallet_service.ensure_lottery_pool_account(session, LedgerUnit.COIN)
        postings: list[LedgerPosting] = []
        effective_pot = Decimal("0.0000")
        if len(human_users) == 2:
            for user in human_users:
                escrow_account = self.wallet_service.get_user_escrow_account(session, user, LedgerUnit.COIN)
                postings.append(LedgerPosting(account=escrow_account, amount=-self._amount(match.entry_fee)))
            effective_pot = self._amount(self._amount(match.entry_fee) * Decimal("2.0000"))
            prize_pool = self._amount(effective_pot - actual_contribution)
            postings.append(LedgerPosting(account=lottery_pool, amount=actual_contribution))
            if human_winner is None:
                refund_amount = self._amount(prize_pool / Decimal("2.0000"))
                for user in human_users:
                    postings.append(
                        LedgerPosting(
                            account=self.wallet_service.get_user_account(session, user, LedgerUnit.COIN),
                            amount=refund_amount,
                        )
                    )
            else:
                postings.append(
                    LedgerPosting(
                        account=self.wallet_service.get_user_account(session, human_winner, LedgerUnit.COIN),
                        amount=prize_pool,
                    )
                )
        elif len(human_users) == 1:
            user = human_users[0]
            escrow_account = self.wallet_service.get_user_escrow_account(session, user, LedgerUnit.COIN)
            postings.append(LedgerPosting(account=escrow_account, amount=-self._amount(match.entry_fee)))
            postings.append(LedgerPosting(account=lottery_pool, amount=actual_contribution))
            if human_winner is not None:
                sponsor_amount = self._amount(match.entry_fee)
                prize_pool = self._amount((self._amount(match.entry_fee) * Decimal("2.0000")) - actual_contribution)
                postings.append(LedgerPosting(account=operations_account, amount=-sponsor_amount))
                postings.append(
                    LedgerPosting(
                        account=self.wallet_service.get_user_account(session, user, LedgerUnit.COIN),
                        amount=prize_pool,
                    )
                )
                effective_pot = self._amount(self._amount(match.entry_fee) + sponsor_amount)
            else:
                house_take = self._amount(self._amount(match.entry_fee) - actual_contribution)
                postings.append(LedgerPosting(account=operations_account, amount=house_take))
                effective_pot = self._amount(match.entry_fee)
        match.effective_pot = effective_pot
        if postings:
            self.wallet_service.append_transaction(
                session,
                postings=postings,
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                transaction_type=LedgerTransactionType.MATCH_REWARD,
                reference=settlement_key,
                description="GTEX AI league match settlement",
                actor=human_winner if human_winner is not None else (human_users[0] if human_users else None),
                idempotency_key=settlement_key,
            )
        for user in human_users:
            self.jackpot_service.record_contribution(
                session,
                participant_user_id=user.id,
                source_type=GtexContributionSourceType.FAST_MATCH,
                source_id=match.id,
                entry_fee=self._amount(match.entry_fee),
                contribution_amount=self._amount(match.entry_fee * self.settings.jackpot_contribution_rate),
                eligibility_score=Decimal("1.0000"),
                metadata={"league_id": match.league_id},
            )
            won = human_winner is not None and human_winner.id == user.id
            score_delta = abs(match.home_score - match.away_score)
            self.creator_market_service.record_match_performance(
                session,
                user=user,
                won=won,
                source_match_id=match.id,
                score_delta=score_delta,
            )
        self._update_match_standings(session, match=match)
        self._emit_risk_flags(session, match=match)
        match.metadata_json = {
            **dict(match.metadata_json or {}),
            "economy_settled_at": utcnow().isoformat(),
        }
        self._stage_event(
            session,
            name="MATCH_COMPLETED",
            payload={
                "match_id": match.id,
                "global_match_id": global_match_id(match.id),
                "league_id": match.league_id,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "winner_user_id": match.winner_user_id,
                "winner_ai_id": match.winner_ai_id,
                "jackpot_contribution": str(match.jackpot_contribution),
                "effective_pot": str(match.effective_pot),
            },
            aggregate_id=match.id,
            aggregate_type="gtex_match",
            partition_key=match.league_id,
            realtime_topic="match.completed",
        )
        return match

    def _update_match_standings(self, session: Session, *, match: GtexMatch) -> None:
        participants = [
            (match.home_participant_type, match.home_user_id, match.home_ai_id, match.home_score, match.away_score),
            (match.away_participant_type, match.away_user_id, match.away_ai_id, match.away_score, match.home_score),
        ]
        for participant_type, user_id, ai_id, scored, conceded in participants:
            user = session.get(User, user_id) if user_id else None
            ai = session.get(GtexAIProfile, ai_id) if ai_id else None
            standing = self._get_or_create_standing(session, league_id=match.league_id, user=user, ai=ai)
            standing.matches_played += 1
            if scored > conceded:
                standing.wins += 1
                standing.points += 3
            elif scored == conceded:
                standing.draws += 1
                standing.points += 1
            else:
                standing.losses += 1
            standing.win_rate = self._amount(Decimal(standing.wins) / Decimal(max(standing.matches_played, 1)))
        self._apply_elo_updates(session, match=match)

    def _apply_elo_updates(self, session: Session, *, match: GtexMatch) -> None:
        home_standing = self._get_or_create_standing(
            session,
            league_id=match.league_id,
            user=session.get(User, match.home_user_id) if match.home_user_id else None,
            ai=session.get(GtexAIProfile, match.home_ai_id) if match.home_ai_id else None,
        )
        away_standing = self._get_or_create_standing(
            session,
            league_id=match.league_id,
            user=session.get(User, match.away_user_id) if match.away_user_id else None,
            ai=session.get(GtexAIProfile, match.away_ai_id) if match.away_ai_id else None,
        )
        if match.home_score > match.away_score:
            actual_home = Decimal("1.0000")
            actual_away = Decimal("0.0000")
        elif match.home_score < match.away_score:
            actual_home = Decimal("0.0000")
            actual_away = Decimal("1.0000")
        else:
            actual_home = Decimal("0.5000")
            actual_away = Decimal("0.5000")
        expected_home = Decimal("1.0000") / (
            Decimal("1.0000") + Decimal(10) ** (Decimal(away_standing.elo - home_standing.elo) / Decimal(400))
        )
        expected_away = Decimal("1.0000") - expected_home
        home_delta = int(round(self.settings.ai_ranked_k_factor * float(actual_home - expected_home)))
        away_delta = int(round(self.settings.ai_ranked_k_factor * float(actual_away - expected_away)))
        home_standing.elo += home_delta
        away_standing.elo += away_delta
        if match.home_ai_id:
            ai = session.get(GtexAIProfile, match.home_ai_id)
            if ai is not None:
                ai.elo = home_standing.elo
                if match.home_score > match.away_score:
                    ai.wins += 1
                elif match.home_score < match.away_score:
                    ai.losses += 1
                ai.state_json = {**(ai.state_json or {}), "last_result": f"{match.home_score}-{match.away_score}"}
                self._refresh_ai_cache(session, ai)
        if match.away_ai_id:
            ai = session.get(GtexAIProfile, match.away_ai_id)
            if ai is not None:
                ai.elo = away_standing.elo
                if match.away_score > match.home_score:
                    ai.wins += 1
                elif match.away_score < match.home_score:
                    ai.losses += 1
                ai.state_json = {**(ai.state_json or {}), "last_result": f"{match.away_score}-{match.home_score}"}
                self._refresh_ai_cache(session, ai)
        self._refresh_leaderboard_cache(session, league_id=match.league_id, standing=home_standing)
        self._refresh_leaderboard_cache(session, league_id=match.league_id, standing=away_standing)

    def _emit_risk_flags(self, session: Session, *, match: GtexMatch) -> None:
        for user_id in (match.home_user_id, match.away_user_id):
            if not user_id:
                continue
            standing = session.scalar(
                select(GtexLeagueStanding).where(
                    GtexLeagueStanding.league_id == match.league_id,
                    GtexLeagueStanding.user_id == user_id,
                )
            )
            if (
                standing is not None
                and standing.matches_played >= 5
                and self._amount(standing.win_rate) >= Decimal("0.9000")
            ):
                session.add(
                    GtexRiskFlag(
                        category="abnormal_win_rate",
                        subject_key=f"user:{user_id}",
                        reference_id=match.league_id,
                        severity="high",
                        signal_score=self._amount(standing.win_rate),
                        status=GtexRiskFlagStatus.OPEN,
                        detail="Win rate exceeded the configured abnormal performance threshold.",
                        metadata_json={"league_id": match.league_id, "matches_played": standing.matches_played},
                    )
                )
        if match.home_user_id and match.away_user_id:
            recent_cutoff = utcnow() - timedelta(minutes=self.settings.ai_recent_pair_window_minutes)
            repeated_matches = int(
                session.scalar(
                    select(func.count())
                    .select_from(GtexMatch)
                    .where(
                        GtexMatch.completed_at >= recent_cutoff,
                        or_(
                            (GtexMatch.home_user_id == match.home_user_id)
                            & (GtexMatch.away_user_id == match.away_user_id),
                            (GtexMatch.home_user_id == match.away_user_id)
                            & (GtexMatch.away_user_id == match.home_user_id),
                        ),
                    )
                )
                or 0
            )
            if repeated_matches >= 3:
                ordered = sorted((match.home_user_id, match.away_user_id))
                session.add(
                    GtexRiskFlag(
                        category="collusion_pattern",
                        subject_key=f"pair:{ordered[0]}:{ordered[1]}",
                        reference_id=match.id,
                        severity="medium",
                        signal_score=self._amount(repeated_matches),
                        status=GtexRiskFlagStatus.OPEN,
                        detail="Repeated human pairings crossed the collusion review threshold.",
                        metadata_json={"recent_pair_matches": repeated_matches},
                    )
                )

    def _get_or_create_standing(
        self, session: Session, *, league_id: str, user: User | None, ai: GtexAIProfile | None
    ) -> GtexLeagueStanding:
        subject_key = self._subject_key(user=user, ai=ai)
        standing = session.scalar(
            select(GtexLeagueStanding).where(
                GtexLeagueStanding.league_id == league_id,
                GtexLeagueStanding.subject_key == subject_key,
            )
        )
        if standing is None:
            starting_elo = ai.elo if ai is not None else 1000
            standing = GtexLeagueStanding(
                league_id=league_id,
                subject_key=subject_key,
                participant_type=GtexParticipantType.AI if ai is not None else GtexParticipantType.HUMAN,
                user_id=user.id if user is not None else None,
                ai_id=ai.id if ai is not None else None,
                matches_played=0,
                wins=0,
                losses=0,
                draws=0,
                elo=starting_elo,
                points=0,
                win_rate=Decimal("0.0000"),
                metadata_json={},
            )
            session.add(standing)
            session.flush()
        return standing

    def _refresh_ai_cache(self, session: Session, ai: GtexAIProfile) -> None:
        defer_session_callback_until_commit(
            session,
            callback=lambda ai_id=ai.id, elo=ai.elo: self.state_store.set_decimal(
                redis_keys.ai_elo(ai_id), Decimal(elo)
            ),
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda ai_id=ai.id, state=dict(ai.state_json or {}), elo=ai.elo: self.state_store.set_json(
                redis_keys.ai_state(ai_id),
                {"elo": elo, "state": state},
            ),
        )

    def _refresh_leaderboard_cache(self, session: Session, *, league_id: str, standing: GtexLeagueStanding) -> None:
        defer_session_callback_until_commit(
            session,
            callback=lambda lid=league_id, key=standing.subject_key, elo=standing.elo: self.state_store.zadd(
                redis_keys.league_leaderboard(lid),
                {key: float(elo)},
            ),
        )


class AiLeagueService(GtexBaseService):
    def __init__(
        self,
        *,
        settings: GtexSettings,
        wallet_service: WalletService,
        state_store: StateStore,
        creator_market_service: CreatorMarketService,
        economy_service: UnifiedEconomyService,
        event_publisher: EventPublisher | None = None,
        realtime_channel: str = "gtex.realtime",
    ) -> None:
        super().__init__(
            settings=settings,
            wallet_service=wallet_service,
            state_store=state_store,
            event_publisher=event_publisher,
            realtime_channel=realtime_channel,
        )
        self.creator_market_service = creator_market_service
        self.economy_service = economy_service
        self.simulation_bridge: Any | None = None

    def seed_defaults(self, session: Session) -> None:
        if session.scalar(select(GtexLeague.id).limit(1)) is None:
            leagues = [
                GtexLeague(
                    code="casual",
                    name="Casual Bots",
                    league_type=GtexLeagueType.CASUAL,
                    min_elo=0,
                    max_elo=1199,
                    default_entry_fee=self.settings.ai_default_entry_fee,
                    ai_backfill_enabled=True,
                    leaderboard_key="leaderboard:league:casual",
                    metadata_json={"tier": "starter"},
                ),
                GtexLeague(
                    code="ranked",
                    name="Ranked Bots",
                    league_type=GtexLeagueType.RANKED,
                    min_elo=1200,
                    max_elo=1999,
                    default_entry_fee=self._amount(self.settings.ai_default_entry_fee * Decimal("2.0000")),
                    ai_backfill_enabled=True,
                    leaderboard_key="leaderboard:league:ranked",
                    metadata_json={"tier": "competitive"},
                ),
                GtexLeague(
                    code="elite",
                    name="Elite Simulation Clubs",
                    league_type=GtexLeagueType.ELITE,
                    min_elo=2000,
                    max_elo=3500,
                    default_entry_fee=self._amount(self.settings.ai_default_entry_fee * Decimal("4.0000")),
                    ai_backfill_enabled=True,
                    leaderboard_key="leaderboard:league:elite",
                    metadata_json={"tier": "elite"},
                ),
            ]
            session.add_all(leagues)
            session.flush()
            for league in leagues:
                self._seed_ai_for_league(session, league)
        else:
            for league in session.scalars(select(GtexLeague)).all():
                existing = int(
                    session.scalar(
                        select(func.count()).select_from(GtexAIProfile).where(GtexAIProfile.league_id == league.id)
                    )
                    or 0
                )
                if existing == 0:
                    self._seed_ai_for_league(session, league)

    def list_leagues(self, session: Session) -> list[dict[str, Any]]:
        leagues = session.scalars(select(GtexLeague).order_by(GtexLeague.min_elo.asc())).all()
        items: list[dict[str, Any]] = []
        for league in leagues:
            leaderboard_members = self.state_store.zrevrange(
                redis_keys.league_leaderboard(league.id), 0, 4, withscores=True
            )
            if leaderboard_members:
                subject_keys = [str(member) for member, _ in leaderboard_members]
                standing_rows = session.scalars(
                    select(GtexLeagueStanding).where(
                        GtexLeagueStanding.league_id == league.id,
                        GtexLeagueStanding.subject_key.in_(subject_keys),
                    )
                ).all()
                standing_map = {standing.subject_key: standing for standing in standing_rows}
                ordered_rows = [standing_map[key] for key in subject_keys if key in standing_map]
            else:
                ordered_rows = session.scalars(
                    select(GtexLeagueStanding)
                    .where(GtexLeagueStanding.league_id == league.id)
                    .order_by(GtexLeagueStanding.elo.desc(), GtexLeagueStanding.points.desc())
                    .limit(5)
                ).all()
            leaderboard = [
                {
                    "subject_key": standing.subject_key,
                    "participant_type": standing.participant_type.value,
                    "elo": standing.elo,
                    "points": standing.points,
                    "matches_played": standing.matches_played,
                    "wins": standing.wins,
                    "losses": standing.losses,
                    "draws": standing.draws,
                    "win_rate": self._amount(standing.win_rate),
                }
                for standing in ordered_rows
            ]
            items.append(
                {
                    "id": league.id,
                    "code": league.code,
                    "name": league.name,
                    "league_type": league.league_type.value,
                    "min_elo": league.min_elo,
                    "max_elo": league.max_elo,
                    "default_entry_fee": self._amount(league.default_entry_fee),
                    "leaderboard": leaderboard,
                }
            )
        return items

    def queue_match_request(
        self,
        session: Session,
        *,
        user: User,
        league_ref: str | None,
        entry_fee: Decimal | None,
        metadata: dict[str, Any] | None = None,
    ) -> GtexMatchQueueEntry:
        existing = session.scalar(
            select(GtexMatchQueueEntry).where(
                GtexMatchQueueEntry.requester_user_id == user.id,
                GtexMatchQueueEntry.status == GtexQueueEntryStatus.QUEUED,
            )
        )
        if existing is not None:
            raise GtexConflictError("User already has a queued GTEX match request.")
        league = self._resolve_league(session, league_ref)
        fee = self._amount(entry_fee or league.default_entry_fee or self.settings.ai_default_entry_fee)
        try:
            self.wallet_service.reserve_order_funds(
                session,
                user=user,
                amount=fee,
                reference=f"gtex-match-reserve:{user.id}:{utcnow().timestamp()}",
                description="Reserve funds for GTEX AI league matchmaking",
                source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            )
        except InsufficientBalanceError as exc:
            raise GtexConflictError(str(exc)) from exc
        queue_entry = GtexMatchQueueEntry(
            requester_user_id=user.id,
            league_id=league.id,
            status=GtexQueueEntryStatus.QUEUED,
            entry_fee=fee,
            expires_at=utcnow() + timedelta(seconds=self.settings.ai_queue_timeout_seconds),
            metadata_json=dict(metadata or {}),
        )
        session.add(queue_entry)
        session.flush()
        defer_session_callback_until_commit(
            session,
            callback=lambda queue_id=queue_entry.id: self.state_store.zadd(
                redis_keys.queue_waiting(),
                {queue_id: utcnow().timestamp()},
            ),
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda queue_id=queue_entry.id: self.state_store.enqueue(
                redis_keys.stream_matchmaking(),
                {"queue_entry_id": queue_id},
            ),
        )
        return queue_entry

    def process_matchmaking(self, session: Session, *, queue_entry_id: str | None = None) -> MatchmakingResult | None:
        if queue_entry_id is not None:
            queue_entry = session.get(GtexMatchQueueEntry, queue_entry_id)
        else:
            queue_entry = session.scalar(
                select(GtexMatchQueueEntry)
                .where(GtexMatchQueueEntry.status == GtexQueueEntryStatus.QUEUED)
                .order_by(GtexMatchQueueEntry.created_at.asc())
            )
        if queue_entry is None or queue_entry.status != GtexQueueEntryStatus.QUEUED:
            return None
        league = session.get(GtexLeague, queue_entry.league_id)
        if league is None:
            raise GtexNotFoundError("League not found for queue entry.")
        now = utcnow()
        opponent_entry = session.scalar(
            select(GtexMatchQueueEntry)
            .where(
                GtexMatchQueueEntry.id != queue_entry.id,
                GtexMatchQueueEntry.league_id == queue_entry.league_id,
                GtexMatchQueueEntry.status == GtexQueueEntryStatus.QUEUED,
                GtexMatchQueueEntry.requester_user_id != queue_entry.requester_user_id,
            )
            .order_by(GtexMatchQueueEntry.created_at.asc())
        )
        home_user_id = queue_entry.requester_user_id
        away_user_id: str | None = None
        away_ai_id: str | None = None
        away_participant_type = GtexParticipantType.HUMAN
        if opponent_entry is not None:
            away_user_id = opponent_entry.requester_user_id
            opponent_entry.status = GtexQueueEntryStatus.MATCHED
            opponent_entry.matched_at = now
        else:
            ai_opponent = self._select_ai_opponent(session, league=league)
            away_ai_id = ai_opponent.id
            away_participant_type = GtexParticipantType.AI
        match = GtexMatch(
            league_id=league.id,
            requested_by_user_id=queue_entry.requester_user_id,
            status=GtexMatchStatus.MATCHED,
            home_participant_type=GtexParticipantType.HUMAN,
            home_user_id=home_user_id,
            home_ai_id=None,
            away_participant_type=away_participant_type,
            away_user_id=away_user_id,
            away_ai_id=away_ai_id,
            entry_fee=self._amount(queue_entry.entry_fee),
            effective_pot=Decimal("0.0000"),
            jackpot_contribution=Decimal("0.0000"),
            home_score=0,
            away_score=0,
            queued_at=now,
            started_at=now,
            metadata_json={"matched_with_ai": away_ai_id is not None},
        )
        session.add(match)
        session.flush()
        queue_entry.status = GtexQueueEntryStatus.MATCHED
        queue_entry.match_id = match.id
        queue_entry.matched_at = now
        if opponent_entry is not None:
            opponent_entry.match_id = match.id
        defer_session_callback_until_commit(
            session,
            callback=lambda match_id=match.id: self.state_store.enqueue(
                redis_keys.stream_ai_brain(),
                {"match_id": match_id},
            ),
        )
        defer_session_callback_until_commit(
            session,
            callback=lambda queue_id=queue_entry.id, opponent_id=(
                opponent_entry.id if opponent_entry is not None else None
            ): self.state_store.zrem(
                redis_keys.queue_waiting(),
                *tuple(member for member in (queue_id, opponent_id) if member is not None),
            ),
        )
        self._stage_event(
            session,
            name="MATCH_CREATED",
            payload={
                "match_id": match.id,
                "queue_entry_id": queue_entry.id,
                "league_id": league.id,
                "home_user_id": match.home_user_id,
                "away_user_id": match.away_user_id,
                "away_ai_id": match.away_ai_id,
            },
            aggregate_id=match.id,
            aggregate_type="gtex_match",
            partition_key=league.id,
            realtime_topic="match.created",
        )
        return MatchmakingResult(queue_entry=queue_entry, match=match)

    def simulate_match(self, session: Session, *, match_id: str) -> GtexMatch:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise GtexNotFoundError(f"GTEX match {match_id} was not found.")
        if match.status == GtexMatchStatus.COMPLETED:
            return match
        home = self._resolve_participant(session, match=match, side="home")
        away = self._resolve_participant(session, match=match, side="away")
        prior_metadata = dict(match.metadata_json or {})
        simulation_context: dict[str, Any] = {}
        if self.simulation_bridge is not None and hasattr(self.simulation_bridge, "prepare_match_context"):
            simulation_context = dict(
                self.simulation_bridge.prepare_match_context(
                    session,
                    match=match,
                    home=home,
                    away=away,
                )
                or {}
            )
        home_fatigue = float(prior_metadata.get("home_fatigue", 0.0) or 0.0)
        away_fatigue = float(prior_metadata.get("away_fatigue", 0.0) or 0.0)
        home_strength = max(1.0, float(home.strength) - (home_fatigue * 2.0)) * float(
            simulation_context.get("home_strength_multiplier") or 1.0
        )
        away_strength = max(1.0, float(away.strength) - (away_fatigue * 2.0)) * float(
            simulation_context.get("away_strength_multiplier") or 1.0
        )
        seed_material = "|".join(
            item
            for item in (
                match.id,
                str(match.home_user_id or ""),
                str(match.home_ai_id or ""),
                str(match.away_user_id or ""),
                str(match.away_ai_id or ""),
                str(simulation_context.get("seed_material") or ""),
            )
            if item
        )
        rng = random.Random(int(sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16))
        rivalry_meetings = int(
            session.scalar(
                select(func.count())
                .select_from(GtexMatch)
                .where(
                    GtexMatch.id != match.id,
                    GtexMatch.completed_at.is_not(None),
                    or_(
                        (GtexMatch.home_user_id == match.home_user_id) & (GtexMatch.away_user_id == match.away_user_id),
                        (GtexMatch.home_user_id == match.away_user_id) & (GtexMatch.away_user_id == match.home_user_id),
                    ),
                )
            )
            or 0
        )
        match.status = GtexMatchStatus.RUNNING
        match.started_at = match.started_at or utcnow()
        home_score = 0
        away_score = 0
        generated_events: list[GtexMatchEvent] = []
        event_count = max(
            3, self.settings.ai_simulation_event_count + int(simulation_context.get("intensity_bonus_events") or 0)
        )
        aggression_overrides = dict(simulation_context.get("aggression_overrides") or {})
        for index in range(1, event_count + 1):
            actor = home if rng.random() < float(home_strength / (home_strength + away_strength)) else away
            event_type = self._pick_event_type(
                actor=actor,
                rng=rng,
                aggression_bonus=float(aggression_overrides.get(actor.subject_key) or 0.0),
            )
            if event_type == "goal":
                if actor.subject_key == home.subject_key:
                    home_score += 1
                else:
                    away_score += 1
            generated_events.append(
                GtexMatchEvent(
                    match_id=match.id,
                    event_index=index,
                    phase="regulation" if index < event_count else "full_time",
                    actor_key=actor.subject_key,
                    event_type=event_type,
                    details_json={"home_score": home_score, "away_score": away_score, "actor": actor.label},
                )
            )
        session.add_all(generated_events)
        match.home_score = home_score
        match.away_score = away_score
        match.completed_at = utcnow()
        match.status = GtexMatchStatus.COMPLETED
        if home_score > away_score:
            match.winner_participant_type = home.participant_type
            match.winner_user_id = home.user.id if home.user is not None else None
            match.winner_ai_id = home.ai.id if home.ai is not None else None
        elif away_score > home_score:
            match.winner_participant_type = away.participant_type
            match.winner_user_id = away.user.id if away.user is not None else None
            match.winner_ai_id = away.ai.id if away.ai is not None else None
        else:
            match.winner_participant_type = None
            match.winner_user_id = None
            match.winner_ai_id = None
        key_moments = [
            f"{event.details_json.get('actor')} triggered {event.event_type} at beat {event.event_index}."
            for event in generated_events[: min(5, len(generated_events))]
        ]
        player_highlights = [
            {
                "actor_key": event.actor_key,
                "actor": event.details_json.get("actor"),
                "event_type": event.event_type,
                "event_index": event.event_index,
            }
            for event in generated_events
            if event.event_type in {"goal", "chance", "save"}
        ][:6]
        rivalry_level = "fierce" if rivalry_meetings >= 5 else "heated" if rivalry_meetings >= 2 else "fresh"
        winner_label = (
            home.label if home_score > away_score else away.label if away_score > home_score else "Neither side"
        )
        storyline = (
            f"{winner_label} emerged from a {rivalry_level} duel after {len(generated_events)} simulated phases."
            if winner_label != "Neither side"
            else f"A {rivalry_level} duel finished level after {len(generated_events)} simulated phases."
        )
        base_metadata = {
            **prior_metadata,
            "home_strength": str(home_strength),
            "away_strength": str(away_strength),
            "home_label": home.label,
            "away_label": away.label,
            "home_fatigue": round(home_fatigue + 0.35, 2),
            "away_fatigue": round(away_fatigue + 0.35, 2),
            "match_context": {
                "home_fatigue": home_fatigue,
                "away_fatigue": away_fatigue,
                "prior_meetings": rivalry_meetings,
                "injury_context": dict(prior_metadata.get("injury_context") or {}),
                "home_strength_multiplier": float(simulation_context.get("home_strength_multiplier") or 1.0),
                "away_strength_multiplier": float(simulation_context.get("away_strength_multiplier") or 1.0),
            },
            "rivalry": {"meetings": rivalry_meetings, "level": rivalry_level},
            "narrative_output": {
                "match_storyline": storyline,
                "key_moments": key_moments,
                "player_highlights": player_highlights,
            },
        }
        bridge_metadata: dict[str, Any] = {}
        if self.simulation_bridge is not None and hasattr(self.simulation_bridge, "finalize_match_context"):
            bridge_metadata = dict(
                self.simulation_bridge.finalize_match_context(
                    session,
                    match=match,
                    home=home,
                    away=away,
                    context=simulation_context,
                )
                or {}
            )
        if bridge_metadata:
            match.metadata_json = {
                **base_metadata,
                **bridge_metadata,
                "match_context": {
                    **dict(base_metadata.get("match_context") or {}),
                    **dict(bridge_metadata.get("match_context") or {}),
                },
                "rivalry": {
                    **dict(base_metadata.get("rivalry") or {}),
                    **dict(bridge_metadata.get("rivalry") or {}),
                },
                "narrative_output": {
                    **dict(base_metadata.get("narrative_output") or {}),
                    **dict(bridge_metadata.get("narrative_output") or {}),
                },
            }
        else:
            match.metadata_json = base_metadata
        self.economy_service.settle_match_completion(session, match=match)
        return match

    def get_match_view(self, session: Session, *, match_id: str) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise GtexNotFoundError(f"GTEX match {match_id} was not found.")
        events = session.scalars(
            select(GtexMatchEvent).where(GtexMatchEvent.match_id == match.id).order_by(GtexMatchEvent.event_index.asc())
        ).all()
        return {
            "id": match.id,
            "league_id": match.league_id,
            "status": match.status.value,
            "home_participant_type": match.home_participant_type.value,
            "home_user_id": match.home_user_id,
            "home_ai_id": match.home_ai_id,
            "away_participant_type": match.away_participant_type.value,
            "away_user_id": match.away_user_id,
            "away_ai_id": match.away_ai_id,
            "entry_fee": self._amount(match.entry_fee),
            "effective_pot": self._amount(match.effective_pot),
            "jackpot_contribution": self._amount(match.jackpot_contribution),
            "home_score": match.home_score,
            "away_score": match.away_score,
            "winner_participant_type": match.winner_participant_type.value if match.winner_participant_type else None,
            "winner_user_id": match.winner_user_id,
            "winner_ai_id": match.winner_ai_id,
            "queued_at": match.queued_at,
            "started_at": match.started_at,
            "completed_at": match.completed_at,
            "match_storyline": (match.metadata_json or {}).get("narrative_output", {}).get("match_storyline"),
            "key_moments": list((match.metadata_json or {}).get("narrative_output", {}).get("key_moments") or []),
            "player_highlights": list(
                (match.metadata_json or {}).get("narrative_output", {}).get("player_highlights") or []
            ),
            "rivalry": dict((match.metadata_json or {}).get("rivalry") or {}),
            "match_context": dict((match.metadata_json or {}).get("match_context") or {}),
            "home_manager": dict((match.metadata_json or {}).get("home_manager") or {}),
            "away_manager": dict((match.metadata_json or {}).get("away_manager") or {}),
            "commentary": list((match.metadata_json or {}).get("commentary") or []),
            "broadcast_package": dict((match.metadata_json or {}).get("broadcast_package") or {}),
            "news_article": dict((match.metadata_json or {}).get("news_article") or {}),
            "career_summary": dict((match.metadata_json or {}).get("career_summary") or {}),
            "fan_experience": dict((match.metadata_json or {}).get("fan_experience") or {}),
            "social_warfare": dict((match.metadata_json or {}).get("social_warfare") or {}),
            "real_world_sync": dict((match.metadata_json or {}).get("real_world_sync") or {}),
            "events": [
                {
                    "event_index": event.event_index,
                    "phase": event.phase,
                    "actor_key": event.actor_key,
                    "event_type": event.event_type,
                    "details": dict(event.details_json or {}),
                    "created_at": event.created_at,
                }
                for event in events
            ],
        }

    def _seed_ai_for_league(self, session: Session, league: GtexLeague) -> None:
        profiles: list[tuple[str, GtexAiProfileType, str, Decimal, Decimal, Decimal, int]] = [
            (
                "Tempo Nova",
                GtexAiProfileType.CASUAL_BOT,
                "pressing",
                Decimal("0.5800"),
                Decimal("0.4200"),
                Decimal("0.6100"),
                max(league.min_elo, 950),
            ),
            (
                "Calm Orbit",
                GtexAiProfileType.CASUAL_BOT,
                "possession",
                Decimal("0.5600"),
                Decimal("0.3600"),
                Decimal("0.4100"),
                max(league.min_elo, 990),
            ),
            (
                "Rank Forge",
                GtexAiProfileType.RANKED_BOT,
                "counter",
                Decimal("0.7200"),
                Decimal("0.5100"),
                Decimal("0.6600"),
                max(league.min_elo + 50, 1250),
            ),
            (
                "Signal Peak",
                GtexAiProfileType.RANKED_BOT,
                "balanced",
                Decimal("0.7500"),
                Decimal("0.4700"),
                Decimal("0.5000"),
                max(league.min_elo + 80, 1320),
            ),
            (
                "Atlas Circuit",
                GtexAiProfileType.ELITE_CLUB,
                "aggressive",
                Decimal("0.9100"),
                Decimal("0.6800"),
                Decimal("0.8200"),
                max(league.min_elo + 120, 2100),
            ),
            (
                "Mirage Union",
                GtexAiProfileType.ELITE_CLUB,
                "adaptive",
                Decimal("0.9300"),
                Decimal("0.7400"),
                Decimal("0.5400"),
                max(league.min_elo + 150, 2180),
            ),
        ]
        for name, profile_type, playstyle, skill_level, adaptation_rate, aggression, elo in profiles:
            if profile_type == GtexAiProfileType.CASUAL_BOT and league.league_type != GtexLeagueType.CASUAL:
                continue
            if profile_type == GtexAiProfileType.RANKED_BOT and league.league_type != GtexLeagueType.RANKED:
                continue
            if profile_type == GtexAiProfileType.ELITE_CLUB and league.league_type != GtexLeagueType.ELITE:
                continue
            ai = GtexAIProfile(
                league_id=league.id,
                profile_type=profile_type,
                name=name,
                skill_level=skill_level,
                playstyle=playstyle,
                adaptation_rate=adaptation_rate,
                aggression=aggression,
                elo=elo,
                wins=0,
                losses=0,
                state_json={"style": playstyle, "league_code": league.code},
                is_active=True,
            )
            session.add(ai)
            session.flush()
            self.economy_service._get_or_create_standing(session, league_id=league.id, user=None, ai=ai)
            self.economy_service._refresh_ai_cache(session, ai)

    def _resolve_league(self, session: Session, league_ref: str | None) -> GtexLeague:
        if league_ref is None:
            league = session.scalar(select(GtexLeague).where(GtexLeague.code == "ranked"))
        else:
            league = session.scalar(
                select(GtexLeague).where(or_(GtexLeague.id == league_ref, GtexLeague.code == league_ref))
            )
        if league is None:
            raise GtexNotFoundError("Requested GTEX league was not found.")
        return league

    def _select_ai_opponent(self, session: Session, *, league: GtexLeague) -> GtexAIProfile:
        ai = session.scalar(
            select(GtexAIProfile)
            .where(
                GtexAIProfile.league_id == league.id,
                GtexAIProfile.is_active.is_(True),
            )
            .order_by(GtexAIProfile.elo.asc(), GtexAIProfile.updated_at.asc())
        )
        if ai is None:
            raise GtexNotFoundError("No AI opponent is available for this league.")
        return ai

    def _resolve_participant(self, session: Session, *, match: GtexMatch, side: str) -> SimulatedParticipant:
        if side == "home":
            user = session.get(User, match.home_user_id) if match.home_user_id else None
            ai = session.get(GtexAIProfile, match.home_ai_id) if match.home_ai_id else None
            participant_type = match.home_participant_type
        else:
            user = session.get(User, match.away_user_id) if match.away_user_id else None
            ai = session.get(GtexAIProfile, match.away_ai_id) if match.away_ai_id else None
            participant_type = match.away_participant_type
        standing = self.economy_service._get_or_create_standing(session, league_id=match.league_id, user=user, ai=ai)
        if user is not None:
            asset = self.creator_market_service.ensure_asset_for_user(session, user)
            strength = self._amount(Decimal("0.7500") + asset.win_rate + (Decimal(standing.elo) / Decimal("2000.0000")))
            label = asset.display_name
        else:
            assert ai is not None
            strength = self._amount(
                ai.skill_level + ai.adaptation_rate + ai.aggression + (Decimal(ai.elo) / Decimal("2500.0000"))
            )
            label = ai.name
        return SimulatedParticipant(
            participant_type=participant_type,
            user=user,
            ai=ai,
            standing=standing,
            strength=max(strength, Decimal("0.2500")),
            label=label,
            subject_key=self._subject_key(user=user, ai=ai),
        )

    def _pick_event_type(
        self,
        *,
        actor: SimulatedParticipant,
        rng: random.Random | None = None,
        aggression_bonus: float = 0.0,
    ) -> str:
        aggression = float(actor.ai.aggression) if actor.ai is not None else 0.55
        aggression = max(0.05, min(0.95, aggression + aggression_bonus))
        roll = (rng or self._random).random()
        if roll < 0.12 + (aggression * 0.20):
            return "goal"
        if roll < 0.35:
            return "chance"
        if roll < 0.60:
            return "shot"
        if roll < 0.78:
            return "press"
        if roll < 0.90:
            return "save"
        return "turnover"
