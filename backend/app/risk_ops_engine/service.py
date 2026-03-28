from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha1
from typing import Any, Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.gift_transaction import GiftTransaction
from app.models.integrity import IntegrityIncident, IntegrityScore
from app.models.moderation_report import ModerationReport, ModerationReportStatus
from app.models.reward_settlement import RewardSettlement
from app.models.risk_ops import (
    AmlCase,
    AuditLog,
    FraudCase,
    RiskAction,
    RiskActionStatus,
    RiskActionType,
    RiskCaseStatus,
    RiskSeverity,
    RiskSignal,
    RiskSignalType,
    SystemEvent,
    SystemEventSeverity,
)
from app.models.treasury import DepositRequest, TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from app.models.user import KycStatus, User

_SEVERITY_ORDER = {
    RiskSeverity.LOW: 0,
    RiskSeverity.MEDIUM: 1,
    RiskSeverity.HIGH: 2,
    RiskSeverity.CRITICAL: 3,
}


class RiskActionBlockedError(ValueError):
    pass


@dataclass(slots=True)
class RiskOpsService:
    session: Session

    def get_overview(self) -> dict:
        self._expire_actions()
        now = self._now()
        open_aml = self.session.scalar(
            select(func.count()).select_from(AmlCase).where(AmlCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))
        ) or 0
        open_fraud = self.session.scalar(
            select(func.count()).select_from(FraudCase).where(FraudCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))
        ) or 0
        open_integrity = self.session.scalar(
            select(func.count()).select_from(IntegrityIncident).where(IntegrityIncident.status == "open")
        ) or 0
        open_reports = self.session.scalar(
            select(func.count()).select_from(ModerationReport).where(
                ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW])
            )
        ) or 0
        critical_events = self.session.scalar(
            select(func.count()).select_from(SystemEvent).where(SystemEvent.severity == SystemEventSeverity.CRITICAL)
        ) or 0
        recent_audits = self.session.scalar(select(func.count()).select_from(AuditLog)) or 0
        elevated = self.session.scalar(
            select(func.count()).select_from(IntegrityScore).where(IntegrityScore.risk_level.in_(["high", "critical"]))
        ) or 0
        active_actions = self.session.scalar(
            select(func.count()).select_from(RiskAction).where(
                RiskAction.status == RiskActionStatus.ACTIVE,
                or_(RiskAction.expires_at.is_(None), RiskAction.expires_at > now),
            )
        ) or 0
        signals_24h = self.session.scalar(
            select(func.count()).select_from(RiskSignal).where(RiskSignal.created_at >= now - timedelta(hours=24))
        ) or 0
        notes: list[str] = []
        if open_fraud:
            notes.append("Fraud queue has active cases pending review.")
        if critical_events:
            notes.append("Critical system events exist and should be triaged before new launches.")
        if elevated:
            notes.append("Some users have elevated integrity risk levels.")
        if active_actions:
            notes.append("Automated restrictions are active on some accounts.")
        return {
            "open_aml_cases": int(open_aml),
            "open_fraud_cases": int(open_fraud),
            "open_integrity_incidents": int(open_integrity),
            "open_moderation_reports": int(open_reports),
            "critical_system_events": int(critical_events),
            "recent_audit_events": int(recent_audits),
            "users_with_elevated_risk": int(elevated),
            "active_risk_actions": int(active_actions),
            "signals_ingested_24h": int(signals_24h),
            "notes": notes,
        }

    def get_user_overview(self, user: User) -> dict:
        self._expire_actions()
        score = self.session.scalar(select(IntegrityScore).where(IntegrityScore.user_id == user.id))
        open_aml = self.session.scalar(
            select(func.count()).select_from(AmlCase).where(
                AmlCase.user_id == user.id,
                AmlCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]),
            )
        ) or 0
        open_fraud = self.session.scalar(
            select(func.count()).select_from(FraudCase).where(
                FraudCase.user_id == user.id,
                FraudCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]),
            )
        ) or 0
        open_integrity = self.session.scalar(
            select(func.count()).select_from(IntegrityIncident).where(
                IntegrityIncident.user_id == user.id,
                IntegrityIncident.status == "open",
            )
        ) or 0
        open_reports = self.session.scalar(
            select(func.count()).select_from(ModerationReport).where(
                or_(ModerationReport.subject_user_id == user.id, ModerationReport.reporter_user_id == user.id),
                ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]),
            )
        ) or 0
        restrictions = self.get_user_restrictions(user.id)
        notes: list[str] = []
        if user.kyc_status != KycStatus.FULLY_VERIFIED:
            notes.append("KYC is not fully verified yet.")
        if score and score.risk_level in {"high", "critical"}:
            notes.append("Integrity risk is elevated and may affect payouts or competition eligibility.")
        if open_aml or open_fraud:
            notes.append("There are open compliance reviews attached to this account.")
        if restrictions["wallet_frozen"]:
            notes.append("Wallet access is restricted pending fraud review.")
        if restrictions["trading_blocked"]:
            notes.append("Trading is blocked while the account is under review.")
        if restrictions["withdrawals_blocked"]:
            notes.append("Withdrawals are blocked while the account is under review.")
        return {
            "user_id": user.id,
            "kyc_status": user.kyc_status.value if hasattr(user.kyc_status, "value") else str(user.kyc_status),
            "integrity_score": str(score.score if score else Decimal("100.00")),
            "integrity_risk_level": score.risk_level if score else "low",
            "open_aml_cases": int(open_aml),
            "open_fraud_cases": int(open_fraud),
            "open_integrity_incidents": int(open_integrity),
            "open_moderation_reports": int(open_reports),
            "wallet_frozen": restrictions["wallet_frozen"],
            "withdrawals_blocked": restrictions["withdrawals_blocked"],
            "trading_blocked": restrictions["trading_blocked"],
            "manual_review_required": restrictions["manual_review_required"],
            "active_actions": [item.action_type.value for item in restrictions["active_actions"]],
            "notes": notes,
        }

    def list_aml_cases(self, *, user_id: str | None = None, status: str | None = None, limit: int = 100) -> list[AmlCase]:
        stmt = select(AmlCase)
        if user_id:
            stmt = stmt.where(AmlCase.user_id == user_id)
        if status:
            stmt = stmt.where(AmlCase.status == status)
        stmt = stmt.order_by(AmlCase.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_aml_case(
        self,
        *,
        actor_user_id: str | None,
        user_id: str | None,
        trigger_source: str,
        title: str,
        description: str,
        severity: RiskSeverity,
        amount_signal: Decimal,
        country_code: str | None,
        metadata_json: dict,
    ) -> AmlCase:
        case = AmlCase(
            user_id=user_id,
            case_key=f"aml-{(user_id or 'global')}-{int((self.session.scalar(select(func.count()).select_from(AmlCase)) or 0) + 1)}",
            trigger_source=trigger_source.strip().lower(),
            title=title.strip(),
            description=description.strip(),
            severity=severity,
            amount_signal=amount_signal,
            country_code=country_code.strip().upper() if country_code else None,
            metadata_json=metadata_json or {},
        )
        self.session.add(case)
        self.session.flush()
        self.log_audit(
            actor_user_id=actor_user_id,
            action_key="aml.case.created",
            resource_type="aml_case",
            resource_id=case.id,
            detail=f"AML case {case.case_key} created.",
            metadata_json={"user_id": user_id, "severity": case.severity.value},
        )
        return case

    def list_fraud_cases(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        fraud_type: str | None = None,
        limit: int = 100,
    ) -> list[FraudCase]:
        stmt = select(FraudCase)
        if user_id:
            stmt = stmt.where(FraudCase.user_id == user_id)
        if status:
            stmt = stmt.where(FraudCase.status == status)
        if fraud_type:
            stmt = stmt.where(FraudCase.fraud_type == fraud_type)
        stmt = stmt.order_by(FraudCase.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_fraud_case(
        self,
        *,
        actor_user_id: str | None,
        user_id: str | None,
        fraud_type: str,
        title: str,
        description: str,
        severity: RiskSeverity,
        confidence_score: Decimal,
        metadata_json: dict,
    ) -> FraudCase:
        case = FraudCase(
            user_id=user_id,
            case_key=f"fraud-{(user_id or 'global')}-{int((self.session.scalar(select(func.count()).select_from(FraudCase)) or 0) + 1)}",
            fraud_type=fraud_type.strip().lower(),
            title=title.strip(),
            description=description.strip(),
            severity=severity,
            confidence_score=confidence_score,
            metadata_json=metadata_json or {},
        )
        self.session.add(case)
        self.session.flush()
        self.log_audit(
            actor_user_id=actor_user_id,
            action_key="fraud.case.created",
            resource_type="fraud_case",
            resource_id=case.id,
            detail=f"Fraud case {case.case_key} created.",
            metadata_json={"user_id": user_id, "fraud_type": case.fraud_type},
        )
        return case

    def create_or_update_fraud_case(
        self,
        *,
        actor_user_id: str | None,
        user_id: str | None,
        fraud_type: str,
        title: str,
        description: str,
        severity: RiskSeverity,
        confidence_score: Decimal,
        metadata_json: dict[str, Any],
        case_key: str,
    ) -> tuple[FraudCase, bool]:
        existing = self.session.scalar(select(FraudCase).where(FraudCase.case_key == case_key))
        if existing is not None:
            if _SEVERITY_ORDER[severity] > _SEVERITY_ORDER[existing.severity]:
                existing.severity = severity
            if confidence_score > existing.confidence_score:
                existing.confidence_score = confidence_score
            existing.description = description.strip()
            existing.metadata_json = {**(existing.metadata_json or {}), **(metadata_json or {})}
            self.session.flush()
            return existing, False
        case = FraudCase(
            user_id=user_id,
            case_key=case_key,
            fraud_type=fraud_type.strip().lower(),
            title=title.strip(),
            description=description.strip(),
            severity=severity,
            confidence_score=confidence_score,
            metadata_json=metadata_json or {},
        )
        self.session.add(case)
        self.session.flush()
        self.log_audit(
            actor_user_id=actor_user_id,
            action_key="fraud.case.created",
            resource_type="fraud_case",
            resource_id=case.id,
            detail=f"Fraud case {case.case_key} created.",
            metadata_json={"user_id": user_id, "fraud_type": case.fraud_type, "automated": True},
        )
        return case, True

    def resolve_case(
        self,
        *,
        case_type: str,
        case_id: str,
        admin_user_id: str,
        resolution_note: str,
        dismissed: bool = False,
    ):
        model = AmlCase if case_type == "aml" else FraudCase
        case = self.session.get(model, case_id)
        if case is None:
            raise ValueError(f"Unknown {case_type} case {case_id}.")
        case.status = RiskCaseStatus.DISMISSED if dismissed else RiskCaseStatus.RESOLVED
        case.resolved_by_user_id = admin_user_id
        case.resolution_note = resolution_note.strip()
        self.session.flush()
        self.log_audit(
            actor_user_id=admin_user_id,
            action_key=f"{case_type}.case.resolved",
            resource_type=f"{case_type}_case",
            resource_id=case.id,
            detail=f"{case_type.upper()} case resolved.",
            metadata_json={"dismissed": dismissed},
        )
        return case

    def ingest_signal(
        self,
        *,
        actor_user_id: str | None,
        user_id: str | None,
        signal_type: RiskSignalType | str,
        signal_key: str | None = None,
        signal_value: str | None = None,
        device_id: str | None = None,
        ip_address: str | None = None,
        source: str = "manual",
        confidence_score: Decimal = Decimal("0.00"),
        occurred_at: datetime | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> RiskSignal:
        normalized_type = signal_type if isinstance(signal_type, RiskSignalType) else RiskSignalType(str(signal_type).strip().lower())
        cleaned_signal_value = self._clean(signal_value)
        cleaned_device_id = self._clean(device_id)
        cleaned_ip_address = self._clean(ip_address)
        payload = dict(metadata_json or {})
        if normalized_type == RiskSignalType.DEVICE_ID:
            cleaned_device_id = cleaned_device_id or cleaned_signal_value or self._clean(payload.get("device_id"))
            cleaned_signal_value = cleaned_signal_value or cleaned_device_id
        if normalized_type == RiskSignalType.IP_ADDRESS:
            cleaned_ip_address = cleaned_ip_address or cleaned_signal_value or self._clean(payload.get("ip_address"))
            cleaned_signal_value = cleaned_signal_value or cleaned_ip_address
        signal = RiskSignal(
            user_id=user_id,
            signal_type=normalized_type,
            signal_key=self._clean(signal_key) or normalized_type.value,
            signal_value=cleaned_signal_value,
            device_id=cleaned_device_id,
            ip_address=cleaned_ip_address,
            source=self._clean(source) or "manual",
            confidence_score=self._decimal(confidence_score),
            occurred_at=self._coerce_datetime(occurred_at) if occurred_at is not None else self._now(),
            metadata_json=payload,
        )
        self.session.add(signal)
        self.session.flush()
        self.log_audit(
            actor_user_id=actor_user_id,
            action_key="risk.signal.ingested",
            resource_type="risk_signal",
            resource_id=signal.id,
            detail=f"Risk signal {signal.signal_type.value} ingested.",
            metadata_json={"user_id": user_id, "signal_type": signal.signal_type.value, "source": signal.source},
        )
        return signal

    def list_signals(
        self,
        *,
        user_id: str | None = None,
        signal_type: str | None = None,
        limit: int = 100,
    ) -> list[RiskSignal]:
        stmt = select(RiskSignal)
        if user_id:
            stmt = stmt.where(RiskSignal.user_id == user_id)
        if signal_type:
            stmt = stmt.where(RiskSignal.signal_type == signal_type)
        stmt = stmt.order_by(RiskSignal.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_action(
        self,
        *,
        actor_user_id: str | None,
        user_id: str,
        action_type: RiskActionType | str,
        reason: str,
        source_rule_key: str = "manual",
        fraud_case_id: str | None = None,
        expires_at: datetime | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> tuple[RiskAction, bool]:
        self._expire_actions()
        normalized_type = action_type if isinstance(action_type, RiskActionType) else RiskActionType(str(action_type).strip().lower())
        normalized_rule = self._clean(source_rule_key) or "manual"
        existing = self.session.scalar(
            select(RiskAction).where(
                RiskAction.user_id == user_id,
                RiskAction.action_type == normalized_type,
                RiskAction.source_rule_key == normalized_rule,
                RiskAction.status == RiskActionStatus.ACTIVE,
                or_(RiskAction.expires_at.is_(None), RiskAction.expires_at > self._now()),
            )
        )
        if existing is not None:
            existing.metadata_json = {**(existing.metadata_json or {}), **(metadata_json or {})}
            self.session.flush()
            return existing, False
        action = RiskAction(
            user_id=user_id,
            action_type=normalized_type,
            status=RiskActionStatus.ACTIVE,
            reason=reason.strip(),
            source_rule_key=normalized_rule,
            created_by_user_id=actor_user_id,
            fraud_case_id=fraud_case_id,
            expires_at=self._coerce_datetime(expires_at) if expires_at is not None else None,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(action)
        self.session.flush()
        self.log_audit(
            actor_user_id=actor_user_id,
            action_key="risk.action.created",
            resource_type="risk_action",
            resource_id=action.id,
            detail=f"Risk action {action.action_type.value} created.",
            metadata_json={"user_id": user_id, "source_rule_key": normalized_rule},
        )
        self.create_system_event(
            actor_user_id=actor_user_id,
            event_key=f"risk-action-{action.id}",
            event_type="risk_action",
            severity=SystemEventSeverity.WARNING,
            title=f"Risk action applied: {action.action_type.value}",
            body=reason.strip(),
            subject_type="user",
            subject_id=user_id,
            metadata_json={"action_type": action.action_type.value, "source_rule_key": normalized_rule},
        )
        return action, True

    def release_action(
        self,
        *,
        action_id: str,
        admin_user_id: str,
        release_note: str,
    ) -> RiskAction:
        action = self.session.get(RiskAction, action_id)
        if action is None:
            raise ValueError(f"Unknown risk action {action_id}.")
        if action.status != RiskActionStatus.ACTIVE:
            return action
        action.status = RiskActionStatus.RELEASED
        action.released_by_user_id = admin_user_id
        action.release_note = release_note.strip()
        action.released_at = self._now()
        self.session.flush()
        self.log_audit(
            actor_user_id=admin_user_id,
            action_key="risk.action.released",
            resource_type="risk_action",
            resource_id=action.id,
            detail=f"Risk action {action.action_type.value} released.",
            metadata_json={"user_id": action.user_id},
        )
        return action

    def list_actions(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        action_type: str | None = None,
        limit: int = 100,
    ) -> list[RiskAction]:
        self._expire_actions()
        stmt = select(RiskAction)
        if user_id:
            stmt = stmt.where(RiskAction.user_id == user_id)
        if status:
            stmt = stmt.where(RiskAction.status == status)
        if action_type:
            stmt = stmt.where(RiskAction.action_type == action_type)
        stmt = stmt.order_by(RiskAction.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_user_restrictions(self, user_id: str) -> dict[str, Any]:
        self._expire_actions()
        actions = list(
            self.session.scalars(
                select(RiskAction).where(
                    RiskAction.user_id == user_id,
                    RiskAction.status == RiskActionStatus.ACTIVE,
                    or_(RiskAction.expires_at.is_(None), RiskAction.expires_at > self._now()),
                )
            ).all()
        )
        action_types = {item.action_type for item in actions}
        return {
            "user_id": user_id,
            "wallet_frozen": RiskActionType.FREEZE_WALLET in action_types,
            "withdrawals_blocked": (
                RiskActionType.FREEZE_WALLET in action_types or RiskActionType.BLOCK_WITHDRAWAL in action_types
            ),
            "trading_blocked": (
                RiskActionType.FREEZE_WALLET in action_types or RiskActionType.BLOCK_TRADING in action_types
            ),
            "manual_review_required": RiskActionType.MANUAL_REVIEW in action_types,
            "active_actions": actions,
        }

    def assert_trading_allowed(self, user_id: str) -> None:
        restrictions = self.get_user_restrictions(user_id)
        if restrictions["trading_blocked"]:
            raise RiskActionBlockedError("Trading is temporarily blocked due to an active risk restriction.")

    def assert_withdrawal_allowed(self, user_id: str) -> None:
        restrictions = self.get_user_restrictions(user_id)
        if restrictions["withdrawals_blocked"]:
            raise RiskActionBlockedError("Withdrawals are temporarily blocked due to an active risk restriction.")

    def evaluate_signals(self, *, admin_user_id: str, user_id: str | None = None) -> dict[str, Any]:
        self._expire_actions()
        all_signals = self.list_signals(limit=1000)
        signals = [signal for signal in all_signals if user_id is None or signal.user_id == user_id]
        if not signals:
            self.log_audit(
                actor_user_id=admin_user_id,
                action_key="risk.signal.evaluation.run",
                resource_type="risk_signal_scan",
                resource_id=None,
                detail="Signal evaluation completed with no eligible signals.",
                metadata_json={"user_id": user_id},
            )
            return {
                "signals_reviewed": 0,
                "users_flagged": 0,
                "fraud_cases_created": 0,
                "actions_created": 0,
                "notes": ["No eligible risk signals were available for evaluation."],
            }

        signals_by_user: dict[str, list[RiskSignal]] = {}
        device_clusters: dict[str, set[str]] = {}
        ip_clusters: dict[str, set[str]] = {}
        for signal in all_signals:
            if signal.user_id and (user_id is None or signal.user_id == user_id):
                signals_by_user.setdefault(signal.user_id, []).append(signal)
            if signal.user_id and signal.device_id:
                device_clusters.setdefault(signal.device_id, set()).add(signal.user_id)
            if signal.user_id and signal.ip_address:
                ip_clusters.setdefault(signal.ip_address, set()).add(signal.user_id)

        fraud_cases_created = 0
        actions_created = 0
        users_flagged: set[str] = set()
        notes: list[str] = []

        for device_id, user_ids in sorted(device_clusters.items()):
            if len(user_ids) < 2:
                continue
            for clustered_user_id in sorted(user_ids):
                case, created = self.create_or_update_fraud_case(
                    actor_user_id=admin_user_id,
                    user_id=clustered_user_id,
                    fraud_type="multi_account_farming",
                    title="Same-device multi-account farming cluster",
                    description="Multiple accounts are sharing a device fingerprint and should be reviewed for farming behavior.",
                    severity=RiskSeverity.HIGH,
                    confidence_score=Decimal("93.00"),
                    metadata_json={
                        "rule_key": "same_device_multiple_accounts",
                        "device_id": device_id,
                        "linked_user_ids": sorted(user_ids),
                        "supporting_ip_addresses": sorted(
                            ip for ip, ip_users in ip_clusters.items() if clustered_user_id in ip_users and len(ip_users) > 1
                        ),
                    },
                    case_key=self._rule_case_key(clustered_user_id, "same_device_multiple_accounts", device_id),
                )
                if created:
                    fraud_cases_created += 1
                _, created_action = self.create_action(
                    actor_user_id=admin_user_id,
                    user_id=clustered_user_id,
                    action_type=RiskActionType.MANUAL_REVIEW,
                    reason="Same-device multi-account cluster requires manual review.",
                    source_rule_key="same_device_multiple_accounts",
                    fraud_case_id=case.id,
                    metadata_json={"device_id": device_id, "linked_user_ids": sorted(user_ids)},
                )
                if created_action:
                    actions_created += 1
                users_flagged.add(clustered_user_id)

        for flagged_user_id, user_signals in signals_by_user.items():
            fake_deposit_signal = next((signal for signal in user_signals if self._is_fake_deposit_signal(signal)), None)
            if fake_deposit_signal is not None:
                case, created = self.create_or_update_fraud_case(
                    actor_user_id=admin_user_id,
                    user_id=flagged_user_id,
                    fraud_type="fake_deposit",
                    title="Fake deposit pattern detected",
                    description="Deposit signals indicate a possible spoofed, reversed, or mismatched funding flow.",
                    severity=RiskSeverity.CRITICAL,
                    confidence_score=max(fake_deposit_signal.confidence_score, Decimal("96.00")),
                    metadata_json={
                        "rule_key": "fake_deposit",
                        "signal_id": fake_deposit_signal.id,
                        "signal_key": fake_deposit_signal.signal_key,
                        "signal_value": fake_deposit_signal.signal_value,
                        **(fake_deposit_signal.metadata_json or {}),
                    },
                    case_key=self._rule_case_key(
                        flagged_user_id,
                        "fake_deposit",
                        fake_deposit_signal.signal_value or fake_deposit_signal.id,
                    ),
                )
                if created:
                    fraud_cases_created += 1
                for action_type in (
                    RiskActionType.FREEZE_WALLET,
                    RiskActionType.BLOCK_WITHDRAWAL,
                    RiskActionType.MANUAL_REVIEW,
                ):
                    _, created_action = self.create_action(
                        actor_user_id=admin_user_id,
                        user_id=flagged_user_id,
                        action_type=action_type,
                        reason="Potential fake deposit activity triggered an automated restriction.",
                        source_rule_key="fake_deposit",
                        fraud_case_id=case.id,
                        metadata_json={"signal_id": fake_deposit_signal.id},
                    )
                    if created_action:
                        actions_created += 1
                users_flagged.add(flagged_user_id)

            win_rate, sample_size, repeated_opponent_rate = self._match_behavior_metrics(user_signals)
            if win_rate > Decimal("0.9000") and sample_size >= 10:
                case, created = self.create_or_update_fraud_case(
                    actor_user_id=admin_user_id,
                    user_id=flagged_user_id,
                    fraud_type="match_collusion",
                    title="Abnormal win rate suggests collusion",
                    description="The account is sustaining a win rate above 90 percent and should be investigated for match collusion.",
                    severity=RiskSeverity.HIGH,
                    confidence_score=Decimal("88.00"),
                    metadata_json={
                        "rule_key": "abnormal_win_rate",
                        "win_rate": str(win_rate),
                        "sample_size": sample_size,
                        "repeated_opponent_rate": str(repeated_opponent_rate),
                    },
                    case_key=self._rule_case_key(flagged_user_id, "abnormal_win_rate", str(sample_size)),
                )
                if created:
                    fraud_cases_created += 1
                _, created_action = self.create_action(
                    actor_user_id=admin_user_id,
                    user_id=flagged_user_id,
                    action_type=RiskActionType.MANUAL_REVIEW,
                    reason="Abnormal win rate triggered an integrity investigation.",
                    source_rule_key="abnormal_win_rate",
                    fraud_case_id=case.id,
                    metadata_json={
                        "win_rate": str(win_rate),
                        "sample_size": sample_size,
                        "repeated_opponent_rate": str(repeated_opponent_rate),
                    },
                )
                if created_action:
                    actions_created += 1
                users_flagged.add(flagged_user_id)

            rapid_loop_signal = next((signal for signal in user_signals if self._is_rapid_trade_loop_signal(signal)), None)
            if rapid_loop_signal is not None:
                case, created = self.create_or_update_fraud_case(
                    actor_user_id=admin_user_id,
                    user_id=flagged_user_id,
                    fraud_type="bot_trading",
                    title="Rapid trade loop detected",
                    description="Trade telemetry indicates a rapid buy-sell loop consistent with automated bot trading.",
                    severity=RiskSeverity.HIGH,
                    confidence_score=max(rapid_loop_signal.confidence_score, Decimal("90.00")),
                    metadata_json={
                        "rule_key": "rapid_trade_loop",
                        "signal_id": rapid_loop_signal.id,
                        "signal_key": rapid_loop_signal.signal_key,
                        **(rapid_loop_signal.metadata_json or {}),
                    },
                    case_key=self._rule_case_key(flagged_user_id, "rapid_trade_loop", rapid_loop_signal.id),
                )
                if created:
                    fraud_cases_created += 1
                for action_type in (RiskActionType.BLOCK_TRADING, RiskActionType.MANUAL_REVIEW):
                    _, created_action = self.create_action(
                        actor_user_id=admin_user_id,
                        user_id=flagged_user_id,
                        action_type=action_type,
                        reason="Rapid trade-loop behavior triggered an automated trading block.",
                        source_rule_key="rapid_trade_loop",
                        fraud_case_id=case.id,
                        metadata_json={"signal_id": rapid_loop_signal.id},
                    )
                    if created_action:
                        actions_created += 1
                users_flagged.add(flagged_user_id)

        if users_flagged:
            notes.append("Signal evaluation flagged users for multi-account, fake deposit, collusion, or bot-trading review.")
        else:
            notes.append("Signal evaluation completed without new fraud actions.")
        self.log_audit(
            actor_user_id=admin_user_id,
            action_key="risk.signal.evaluation.run",
            resource_type="risk_signal_scan",
            resource_id=None,
            detail="Signal-based fraud evaluation completed.",
            metadata_json={
                "user_id": user_id,
                "signals_reviewed": len(signals),
                "users_flagged": len(users_flagged),
                "fraud_cases_created": fraud_cases_created,
                "actions_created": actions_created,
            },
        )
        return {
            "signals_reviewed": len(signals),
            "users_flagged": len(users_flagged),
            "fraud_cases_created": fraud_cases_created,
            "actions_created": actions_created,
            "notes": notes,
        }

    def list_system_events(self, *, severity: str | None = None, limit: int = 100) -> list[SystemEvent]:
        stmt = select(SystemEvent)
        if severity:
            stmt = stmt.where(SystemEvent.severity == severity)
        stmt = stmt.order_by(SystemEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_system_event(
        self,
        *,
        actor_user_id: str | None,
        event_key: str,
        event_type: str,
        severity: SystemEventSeverity,
        title: str,
        body: str,
        subject_type: str | None,
        subject_id: str | None,
        metadata_json: dict,
    ) -> SystemEvent:
        existing = self.session.scalar(select(SystemEvent).where(SystemEvent.event_key == event_key))
        if existing:
            return existing
        event = SystemEvent(
            event_key=event_key.strip().lower(),
            event_type=event_type.strip().lower(),
            severity=severity,
            title=title.strip(),
            body=body.strip(),
            subject_type=subject_type.strip().lower() if subject_type else None,
            subject_id=subject_id,
            created_by_user_id=actor_user_id,
            metadata_json=metadata_json or {},
        )
        self.session.add(event)
        self.session.flush()
        self.log_audit(
            actor_user_id=actor_user_id,
            action_key="system.event.created",
            resource_type="system_event",
            resource_id=event.id,
            detail=f"System event {event.event_key} created.",
            metadata_json={"severity": event.severity.value},
        )
        return event

    def list_audit_logs(self, *, action_key: str | None = None, limit: int = 100) -> list[AuditLog]:
        stmt = select(AuditLog)
        if action_key:
            stmt = stmt.where(AuditLog.action_key == action_key)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def log_audit(
        self,
        *,
        actor_user_id: str | None,
        action_key: str,
        resource_type: str,
        resource_id: str | None,
        detail: str,
        metadata_json: dict | None = None,
        outcome: str = "success",
    ) -> AuditLog:
        event = AuditLog(
            actor_user_id=actor_user_id,
            action_key=action_key,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata_json or {},
            outcome=outcome,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def run_automated_scan(self, *, admin_user_id: str) -> dict:
        aml_cases_created = 0
        fraud_cases_created = 0
        audit_created = 0
        notes: list[str] = []

        high_pending_withdrawals = self.session.scalars(
            select(TreasuryWithdrawalRequest).where(
                TreasuryWithdrawalRequest.status.in_(
                    [TreasuryWithdrawalStatus.PENDING_REVIEW, TreasuryWithdrawalStatus.PROCESSING]
                )
            )
        ).all()
        for withdrawal in high_pending_withdrawals:
            amount = Decimal(str(getattr(withdrawal, "amount_fiat", Decimal("0"))))
            if amount >= Decimal("5000"):
                self.create_aml_case(
                    actor_user_id=admin_user_id,
                    user_id=withdrawal.user_id,
                    trigger_source="withdrawal_scan",
                    title="Large withdrawal pending review",
                    description="A high-value withdrawal crossed the AML review threshold.",
                    severity=RiskSeverity.HIGH,
                    amount_signal=amount,
                    country_code=None,
                    metadata_json={"withdrawal_id": withdrawal.id},
                )
                aml_cases_created += 1

        high_pending_deposits = self.session.scalars(select(DepositRequest)).all()
        for deposit in high_pending_deposits:
            amount = Decimal(str(getattr(deposit, "amount_fiat", Decimal("0"))))
            if amount >= Decimal("5000"):
                self.create_aml_case(
                    actor_user_id=admin_user_id,
                    user_id=deposit.user_id,
                    trigger_source="deposit_scan",
                    title="Large deposit pending review",
                    description="A high-value deposit crossed the AML review threshold.",
                    severity=RiskSeverity.MEDIUM,
                    amount_signal=amount,
                    country_code=None,
                    metadata_json={"deposit_id": deposit.id},
                )
                aml_cases_created += 1

        suspicious_gifters = self.session.execute(
            select(GiftTransaction.sender_user_id, func.count(GiftTransaction.id).label("gift_count"))
            .group_by(GiftTransaction.sender_user_id)
            .having(func.count(GiftTransaction.id) >= 10)
        ).all()
        for row in suspicious_gifters:
            self.create_fraud_case(
                actor_user_id=admin_user_id,
                user_id=row.sender_user_id,
                fraud_type="gift_farming",
                title="High-frequency gifting pattern",
                description="Automated scan detected repeated gifting behavior above the review threshold.",
                severity=RiskSeverity.HIGH,
                confidence_score=Decimal("82.50"),
                metadata_json={"gift_count": int(row.gift_count)},
            )
            fraud_cases_created += 1

        dense_reward_users = self.session.execute(
            select(RewardSettlement.user_id, func.count(RewardSettlement.id).label("reward_count"))
            .group_by(RewardSettlement.user_id)
            .having(func.count(RewardSettlement.id) >= 8)
        ).all()
        for row in dense_reward_users:
            self.create_fraud_case(
                actor_user_id=admin_user_id,
                user_id=row.user_id,
                fraud_type="reward_cluster",
                title="Dense reward cluster detected",
                description="Automated scan detected an unusually dense reward-settlement pattern.",
                severity=RiskSeverity.MEDIUM,
                confidence_score=Decimal("70.00"),
                metadata_json={"reward_count": int(row.reward_count)},
            )
            fraud_cases_created += 1

        signal_scan = self.evaluate_signals(admin_user_id=admin_user_id)
        fraud_cases_created += signal_scan["fraud_cases_created"]
        if signal_scan["actions_created"]:
            notes.append(f"Signal engine created {signal_scan['actions_created']} active restriction(s).")

        notes.append("Scan reviewed treasury, gifting, reward density, and signal-driven fraud surfaces.")
        audit_created += 1
        self.log_audit(
            actor_user_id=admin_user_id,
            action_key="risk.scan.run",
            resource_type="risk_scan",
            resource_id=None,
            detail="Automated risk scan completed.",
            metadata_json={
                "aml_cases_created": aml_cases_created,
                "fraud_cases_created": fraud_cases_created,
                "signals_reviewed": signal_scan["signals_reviewed"],
                "actions_created": signal_scan["actions_created"],
            },
        )
        return {
            "aml_cases_created": aml_cases_created,
            "fraud_cases_created": fraud_cases_created,
            "audit_events_created": audit_created,
            "notes": notes,
        }

    def _expire_actions(self) -> None:
        now = self._now()
        expired_actions = self.session.scalars(
            select(RiskAction).where(
                RiskAction.status == RiskActionStatus.ACTIVE,
                RiskAction.expires_at.is_not(None),
                RiskAction.expires_at <= now,
            )
        ).all()
        for action in expired_actions:
            action.status = RiskActionStatus.EXPIRED
            action.released_at = action.released_at or now
        if expired_actions:
            self.session.flush()

    def _match_behavior_metrics(self, signals: Iterable[RiskSignal]) -> tuple[Decimal, int, Decimal]:
        best_win_rate = Decimal("0.0000")
        best_sample_size = 0
        best_repeated_rate = Decimal("0.0000")
        for signal in signals:
            if signal.signal_type != RiskSignalType.MATCH_BEHAVIOR:
                continue
            metadata = signal.metadata_json or {}
            win_rate = self._ratio(
                metadata.get("win_rate") or metadata.get("abnormal_win_rate") or signal.signal_value
            )
            sample_size = self._int(
                metadata.get("sample_size") or metadata.get("matches_sampled") or metadata.get("matches_played")
            )
            repeated_rate = self._ratio(
                metadata.get("repeated_opponent_rate") or metadata.get("opponent_repeat_ratio")
            )
            if win_rate > best_win_rate or (win_rate == best_win_rate and sample_size > best_sample_size):
                best_win_rate = win_rate
                best_sample_size = sample_size
                best_repeated_rate = repeated_rate
        return best_win_rate, best_sample_size, best_repeated_rate

    def _is_fake_deposit_signal(self, signal: RiskSignal) -> bool:
        if signal.signal_type != RiskSignalType.TRANSACTION_PATTERN:
            return False
        metadata = signal.metadata_json or {}
        normalized_blob = " ".join(
            filter(
                None,
                [
                    self._clean(signal.signal_key),
                    self._clean(signal.signal_value),
                    self._clean(metadata.get("pattern")),
                    self._clean(metadata.get("category")),
                ],
            )
        ).lower()
        if metadata.get("fake_deposit") or metadata.get("duplicate_deposit") or metadata.get("bank_reference_mismatch"):
            return True
        if self._int(metadata.get("chargeback_count")) > 0 or self._int(metadata.get("reversal_count")) > 0:
            return True
        return "deposit" in normalized_blob and any(
            token in normalized_blob for token in ("fake", "spoof", "duplicate", "mismatch", "reversal", "chargeback")
        )

    def _is_rapid_trade_loop_signal(self, signal: RiskSignal) -> bool:
        if signal.signal_type != RiskSignalType.TRANSACTION_PATTERN:
            return False
        metadata = signal.metadata_json or {}
        normalized_blob = " ".join(
            filter(
                None,
                [
                    self._clean(signal.signal_key),
                    self._clean(signal.signal_value),
                    self._clean(metadata.get("pattern")),
                    self._clean(metadata.get("category")),
                ],
            )
        ).lower()
        loop_count = max(
            self._int(metadata.get("loop_count")),
            self._int(metadata.get("trade_loop_count")),
            self._int(metadata.get("alternating_trade_count")),
        )
        window_minutes = self._int(metadata.get("window_minutes") or metadata.get("loop_window_minutes"))
        if loop_count >= 6 and 0 < window_minutes <= 15:
            return True
        return any(token in normalized_blob for token in ("rapid_trade_loop", "trade_loop", "bot_trading"))

    def _rule_case_key(self, user_id: str | None, rule_key: str, evidence_key: str) -> str:
        digest = sha1(f"{user_id or 'global'}|{rule_key}|{evidence_key}".encode("utf-8")).hexdigest()[:12]
        return f"{(rule_key or 'rule').strip().lower()}-{(user_id or 'global').strip().lower()}-{digest}"

    def _clean(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _decimal(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0.00")

    def _ratio(self, value: Any) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        try:
            numeric = Decimal(str(value))
        except Exception:
            return Decimal("0.0000")
        if numeric > Decimal("1.0000") and numeric <= Decimal("100.0000"):
            numeric = numeric / Decimal("100.0000")
        if numeric < Decimal("0.0000"):
            numeric = Decimal("0.0000")
        if numeric > Decimal("1.0000"):
            numeric = Decimal("1.0000")
        return numeric.quantize(Decimal("0.0001"))

    def _coerce_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _now(self) -> datetime:
        return datetime.now(UTC)
