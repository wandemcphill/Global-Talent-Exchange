from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.event_backbone import defer_event_publish_until_commit
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.models.base import utcnow
from app.models.risk_ops import (
    RiskSeverity,
    SystemEvent,
    SystemEventSeverity,
)
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    PaymentEvent,
    PaymentStatus,
    PayoutRequest,
    PayoutStatus,
)
from app.risk_ops_engine.service import RiskOpsService


@dataclass(frozen=True, slots=True)
class FraudRuleHit:
    rule_key: str
    title: str
    description: str
    severity: RiskSeverity
    confidence_score: Decimal
    metadata_json: dict[str, Any]


@dataclass(slots=True)
class FraudDetectionService:
    session_factory: sessionmaker[Session]
    event_publisher: EventPublisher | None = None
    large_movement_threshold: Decimal = Decimal("1000.0000")
    velocity_window_minutes: int = 10
    velocity_entry_threshold: int = 6
    velocity_amount_threshold: Decimal = Decimal("2500.0000")
    deposit_to_withdrawal_window_minutes: int = 60
    withdrawal_burst_window_minutes: int = 360
    withdrawal_burst_threshold: int = 3
    withdrawal_burst_amount_threshold: Decimal = Decimal("1500.0000")

    def __post_init__(self) -> None:
        if self.event_publisher is None:
            self.event_publisher = InMemoryEventPublisher()

    def handle_event(self, event: DomainEvent) -> None:
        if event.name == "wallet.transaction.appended":
            self._process_transaction_event(event)
        elif event.name == "wallet.withdrawal.requested":
            self._process_withdrawal_event(event)

    def _process_transaction_event(self, event: DomainEvent) -> None:
        owner_user_ids = tuple(
            str(candidate).strip()
            for candidate in (event.payload.get("owner_user_ids") or [])
            if str(candidate).strip()
        )
        if not owner_user_ids:
            return
        with self.session_factory() as session:
            emitted = False
            for user_id in owner_user_ids:
                user = session.get(User, user_id)
                if user is None:
                    continue
                hits = self._detect_transaction_hits(session, user_id=user_id, event=event)
                if not hits:
                    continue
                if self._persist_hits(session, user=user, source_event=event, hits=hits):
                    emitted = True
            if emitted:
                session.commit()

    def _process_withdrawal_event(self, event: DomainEvent) -> None:
        user_id = str(event.payload.get("user_id") or "").strip()
        if not user_id:
            return
        with self.session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return
            hits = self._detect_withdrawal_hits(session, user_id=user_id, event=event)
            if not hits:
                return
            if self._persist_hits(session, user=user, source_event=event, hits=hits):
                session.commit()

    def _detect_transaction_hits(
        self,
        session: Session,
        *,
        user_id: str,
        event: DomainEvent,
    ) -> list[FraudRuleHit]:
        hits: list[FraudRuleHit] = []
        primary_entries = self._primary_user_entries(user_id=user_id, payload=event.payload)
        moved_amount = sum(
            (abs(self._decimal(item.get("amount"))) for item in primary_entries),
            start=Decimal("0.0000"),
        )
        if moved_amount >= self.large_movement_threshold:
            hits.append(
                FraudRuleHit(
                    rule_key="large_wallet_movement",
                    title="Large wallet movement detected",
                    description=(
                        "A single wallet transaction crossed the large-movement threshold "
                        "and was routed for fraud review."
                    ),
                    severity=RiskSeverity.HIGH,
                    confidence_score=Decimal("78.00"),
                    metadata_json={
                        "reason": event.payload.get("reason"),
                        "source_tag": event.payload.get("source_tag"),
                        "moved_amount": str(moved_amount),
                        "transaction_id": event.payload.get("transaction_id"),
                    },
                )
            )

        velocity_cutoff = utcnow() - timedelta(minutes=self.velocity_window_minutes)
        recent_entry_count = session.scalar(
            select(func.count(LedgerEntry.id))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.owner_user_id == user_id,
                LedgerAccount.kind == LedgerAccountKind.USER,
                LedgerEntry.created_at >= velocity_cutoff,
            )
        ) or 0
        recent_velocity_amount = session.scalar(
            select(func.coalesce(func.sum(func.abs(LedgerEntry.amount)), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.owner_user_id == user_id,
                LedgerAccount.kind == LedgerAccountKind.USER,
                LedgerEntry.created_at >= velocity_cutoff,
            )
        ) or Decimal("0.0000")
        normalized_velocity_amount = self._decimal(recent_velocity_amount)
        if (
            int(recent_entry_count) >= self.velocity_entry_threshold
            and normalized_velocity_amount >= self.velocity_amount_threshold
        ):
            hits.append(
                FraudRuleHit(
                    rule_key="wallet_velocity_spike",
                    title="Wallet velocity spike detected",
                    description=(
                        "A short burst of wallet activity crossed both the frequency and "
                        "movement thresholds for fraud review."
                    ),
                    severity=RiskSeverity.MEDIUM,
                    confidence_score=Decimal("72.50"),
                    metadata_json={
                        "recent_entry_count": int(recent_entry_count),
                        "recent_velocity_amount": str(normalized_velocity_amount),
                        "window_minutes": self.velocity_window_minutes,
                    },
                )
            )
        return hits

    def _detect_withdrawal_hits(
        self,
        session: Session,
        *,
        user_id: str,
        event: DomainEvent,
    ) -> list[FraudRuleHit]:
        hits: list[FraudRuleHit] = []
        requested_amount = self._decimal(event.payload.get("amount"))
        deposit_cutoff = utcnow() - timedelta(minutes=self.deposit_to_withdrawal_window_minutes)
        recent_verified_deposits = session.scalar(
            select(func.coalesce(func.sum(PaymentEvent.amount), 0))
            .where(
                PaymentEvent.user_id == user_id,
                PaymentEvent.status == PaymentStatus.VERIFIED,
                PaymentEvent.verified_at >= deposit_cutoff,
            )
        ) or Decimal("0.0000")
        normalized_recent_deposits = self._decimal(recent_verified_deposits)
        if (
            requested_amount >= self.large_movement_threshold
            and normalized_recent_deposits >= requested_amount * Decimal("0.80")
        ):
            hits.append(
                FraudRuleHit(
                    rule_key="rapid_cash_out",
                    title="Rapid deposit-to-withdrawal pattern",
                    description=(
                        "The withdrawal closely followed recent verified deposits and "
                        "matched the rapid cash-out profile."
                    ),
                    severity=RiskSeverity.CRITICAL,
                    confidence_score=Decimal("91.00"),
                    metadata_json={
                        "requested_amount": str(requested_amount),
                        "recent_verified_deposits": str(normalized_recent_deposits),
                        "window_minutes": self.deposit_to_withdrawal_window_minutes,
                        "payout_request_id": event.payload.get("payout_request_id"),
                    },
                )
            )

        burst_cutoff = utcnow() - timedelta(minutes=self.withdrawal_burst_window_minutes)
        pending_statuses = (
            PayoutStatus.REQUESTED,
            PayoutStatus.REVIEWING,
            PayoutStatus.HELD,
            PayoutStatus.PROCESSING,
        )
        recent_withdrawal_count = session.scalar(
            select(func.count(PayoutRequest.id)).where(
                PayoutRequest.user_id == user_id,
                PayoutRequest.status.in_(pending_statuses),
                PayoutRequest.created_at >= burst_cutoff,
            )
        ) or 0
        recent_withdrawal_total = session.scalar(
            select(func.coalesce(func.sum(PayoutRequest.amount), 0)).where(
                PayoutRequest.user_id == user_id,
                PayoutRequest.status.in_(pending_statuses),
                PayoutRequest.created_at >= burst_cutoff,
            )
        ) or Decimal("0.0000")
        normalized_withdrawal_total = self._decimal(recent_withdrawal_total)
        if (
            int(recent_withdrawal_count) >= self.withdrawal_burst_threshold
            and normalized_withdrawal_total >= self.withdrawal_burst_amount_threshold
        ):
            hits.append(
                FraudRuleHit(
                    rule_key="withdrawal_burst",
                    title="Withdrawal burst detected",
                    description=(
                        "Multiple pending withdrawals landed inside the same monitoring window "
                        "and exceeded the cumulative threshold."
                    ),
                    severity=RiskSeverity.HIGH,
                    confidence_score=Decimal("84.00"),
                    metadata_json={
                        "recent_withdrawal_count": int(recent_withdrawal_count),
                        "recent_withdrawal_total": str(normalized_withdrawal_total),
                        "window_minutes": self.withdrawal_burst_window_minutes,
                    },
                )
            )
        return hits

    def _persist_hits(
        self,
        session: Session,
        *,
        user: User,
        source_event: DomainEvent,
        hits: list[FraudRuleHit],
    ) -> bool:
        risk_ops = RiskOpsService(session)
        emitted = False
        for hit in hits:
            event_key = f"fraud:{hit.rule_key}:{source_event.event_id}:{user.id}"
            existing_alert = session.scalar(
                select(SystemEvent.id).where(SystemEvent.event_key == event_key)
            )
            if existing_alert is not None:
                continue
            case = risk_ops.create_fraud_case(
                actor_user_id=None,
                user_id=user.id,
                fraud_type=hit.rule_key,
                title=hit.title,
                description=hit.description,
                severity=hit.severity,
                confidence_score=hit.confidence_score,
                metadata_json={
                    **dict(hit.metadata_json),
                    "source_event_id": source_event.event_id,
                    "source_event_name": source_event.name,
                    "source_transaction_id": source_event.payload.get("transaction_id"),
                },
            )
            alert = risk_ops.create_system_event(
                actor_user_id=None,
                event_key=event_key,
                event_type="fraud_alert",
                severity=self._map_system_severity(hit.severity),
                title=hit.title,
                body=hit.description,
                subject_type="user",
                subject_id=user.id,
                metadata_json={
                    **dict(hit.metadata_json),
                    "fraud_case_id": case.id,
                    "user_id": user.id,
                    "source_event_id": source_event.event_id,
                },
            )
            session.flush()
            defer_event_publish_until_commit(
                session,
                publisher=self.event_publisher,
                event=DomainEvent(
                    name="risk.fraud.detected",
                    payload={
                        "fraud_case_id": case.id,
                        "system_event_id": alert.id,
                        "user_id": user.id,
                        "rule_key": hit.rule_key,
                        "severity": hit.severity.value,
                        "confidence_score": str(hit.confidence_score),
                        "title": hit.title,
                        "description": hit.description,
                        "source_event_id": source_event.event_id,
                        "source_event_name": source_event.name,
                        "metadata": dict(hit.metadata_json),
                    },
                    aggregate_id=case.id,
                    aggregate_type="fraud_case",
                    producer="fraud_detector",
                    partition_key=user.id,
                    headers={"alert": "true"},
                ),
            )
            emitted = True
        return emitted

    @staticmethod
    def _primary_user_entries(*, user_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        entries = [
            dict(item)
            for item in (payload.get("entries") or [])
            if isinstance(item, dict) and str(item.get("owner_user_id") or "").strip() == user_id
        ]
        primary_entries = [
            item for item in entries if str(item.get("account_kind") or "").strip().lower() == "user"
        ]
        return primary_entries or entries

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value))

    @staticmethod
    def _map_system_severity(value: RiskSeverity) -> SystemEventSeverity:
        if value == RiskSeverity.CRITICAL:
            return SystemEventSeverity.CRITICAL
        if value == RiskSeverity.HIGH:
            return SystemEventSeverity.ERROR
        if value == RiskSeverity.MEDIUM:
            return SystemEventSeverity.WARNING
        return SystemEventSeverity.INFO


__all__ = ["FraudDetectionService", "FraudRuleHit"]
