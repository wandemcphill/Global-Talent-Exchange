from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.integrity import IntegrityIncident, IntegrityScore
from backend.app.models.moderation_report import ModerationReport, ModerationReportStatus
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.risk_ops import AmlCase, AuditLog, FraudCase, RiskCaseStatus, RiskSeverity, SystemEvent, SystemEventSeverity
from backend.app.models.treasury import DepositRequest, TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from backend.app.models.user import KycStatus, User
from backend.app.models.gift_transaction import GiftTransaction


@dataclass(slots=True)
class RiskOpsService:
    session: Session

    def get_overview(self) -> dict:
        open_aml = self.session.scalar(select(func.count()).select_from(AmlCase).where(AmlCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))) or 0
        open_fraud = self.session.scalar(select(func.count()).select_from(FraudCase).where(FraudCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))) or 0
        open_integrity = self.session.scalar(select(func.count()).select_from(IntegrityIncident).where(IntegrityIncident.status == "open")) or 0
        open_reports = self.session.scalar(select(func.count()).select_from(ModerationReport).where(ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]))) or 0
        critical_events = self.session.scalar(select(func.count()).select_from(SystemEvent).where(SystemEvent.severity == SystemEventSeverity.CRITICAL)) or 0
        recent_audits = self.session.scalar(select(func.count()).select_from(AuditLog)) or 0
        elevated = self.session.scalar(select(func.count()).select_from(IntegrityScore).where(IntegrityScore.risk_level.in_(["high", "critical"]))) or 0
        notes: list[str] = []
        if open_fraud:
            notes.append("Fraud queue has active cases pending review.")
        if critical_events:
            notes.append("Critical system events exist and should be triaged before new launches.")
        if elevated:
            notes.append("Some users have elevated integrity risk levels.")
        return {
            "open_aml_cases": int(open_aml),
            "open_fraud_cases": int(open_fraud),
            "open_integrity_incidents": int(open_integrity),
            "open_moderation_reports": int(open_reports),
            "critical_system_events": int(critical_events),
            "recent_audit_events": int(recent_audits),
            "users_with_elevated_risk": int(elevated),
            "notes": notes,
        }

    def get_user_overview(self, user: User) -> dict:
        score = self.session.scalar(select(IntegrityScore).where(IntegrityScore.user_id == user.id))
        open_aml = self.session.scalar(select(func.count()).select_from(AmlCase).where(AmlCase.user_id == user.id, AmlCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))) or 0
        open_fraud = self.session.scalar(select(func.count()).select_from(FraudCase).where(FraudCase.user_id == user.id, FraudCase.status.in_([RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW]))) or 0
        open_integrity = self.session.scalar(select(func.count()).select_from(IntegrityIncident).where(IntegrityIncident.user_id == user.id, IntegrityIncident.status == "open")) or 0
        open_reports = self.session.scalar(select(func.count()).select_from(ModerationReport).where(or_(ModerationReport.subject_user_id == user.id, ModerationReport.reporter_user_id == user.id), ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]))) or 0
        notes: list[str] = []
        if user.kyc_status != KycStatus.FULLY_VERIFIED:
            notes.append("KYC is not fully verified yet.")
        if score and score.risk_level in {"high", "critical"}:
            notes.append("Integrity risk is elevated and may affect payouts or competition eligibility.")
        if open_aml or open_fraud:
            notes.append("There are open compliance reviews attached to this account.")
        return {
            "user_id": user.id,
            "kyc_status": user.kyc_status.value if hasattr(user.kyc_status, 'value') else str(user.kyc_status),
            "integrity_score": str(score.score if score else Decimal("100.00")),
            "integrity_risk_level": score.risk_level if score else "low",
            "open_aml_cases": int(open_aml),
            "open_fraud_cases": int(open_fraud),
            "open_integrity_incidents": int(open_integrity),
            "open_moderation_reports": int(open_reports),
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

    def create_aml_case(self, *, actor_user_id: str | None, user_id: str | None, trigger_source: str, title: str, description: str, severity: RiskSeverity, amount_signal: Decimal, country_code: str | None, metadata_json: dict) -> AmlCase:
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
        self.log_audit(actor_user_id=actor_user_id, action_key="aml.case.created", resource_type="aml_case", resource_id=case.id, detail=f"AML case {case.case_key} created.", metadata_json={"user_id": user_id, "severity": case.severity.value})
        return case

    def list_fraud_cases(self, *, user_id: str | None = None, status: str | None = None, fraud_type: str | None = None, limit: int = 100) -> list[FraudCase]:
        stmt = select(FraudCase)
        if user_id:
            stmt = stmt.where(FraudCase.user_id == user_id)
        if status:
            stmt = stmt.where(FraudCase.status == status)
        if fraud_type:
            stmt = stmt.where(FraudCase.fraud_type == fraud_type)
        stmt = stmt.order_by(FraudCase.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_fraud_case(self, *, actor_user_id: str | None, user_id: str | None, fraud_type: str, title: str, description: str, severity: RiskSeverity, confidence_score: Decimal, metadata_json: dict) -> FraudCase:
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
        self.log_audit(actor_user_id=actor_user_id, action_key="fraud.case.created", resource_type="fraud_case", resource_id=case.id, detail=f"Fraud case {case.case_key} created.", metadata_json={"user_id": user_id, "fraud_type": case.fraud_type})
        return case

    def resolve_case(self, *, case_type: str, case_id: str, admin_user_id: str, resolution_note: str, dismissed: bool = False):
        model = AmlCase if case_type == "aml" else FraudCase
        case = self.session.get(model, case_id)
        if case is None:
            raise ValueError(f"Unknown {case_type} case {case_id}.")
        case.status = RiskCaseStatus.DISMISSED if dismissed else RiskCaseStatus.RESOLVED
        case.resolved_by_user_id = admin_user_id
        case.resolution_note = resolution_note.strip()
        self.session.flush()
        self.log_audit(actor_user_id=admin_user_id, action_key=f"{case_type}.case.resolved", resource_type=f"{case_type}_case", resource_id=case.id, detail=f"{case_type.upper()} case resolved.", metadata_json={"dismissed": dismissed})
        return case

    def list_system_events(self, *, severity: str | None = None, limit: int = 100) -> list[SystemEvent]:
        stmt = select(SystemEvent)
        if severity:
            stmt = stmt.where(SystemEvent.severity == severity)
        stmt = stmt.order_by(SystemEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create_system_event(self, *, actor_user_id: str | None, event_key: str, event_type: str, severity: SystemEventSeverity, title: str, body: str, subject_type: str | None, subject_id: str | None, metadata_json: dict) -> SystemEvent:
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
        self.log_audit(actor_user_id=actor_user_id, action_key="system.event.created", resource_type="system_event", resource_id=event.id, detail=f"System event {event.event_key} created.", metadata_json={"severity": event.severity.value})
        return event

    def list_audit_logs(self, *, action_key: str | None = None, limit: int = 100) -> list[AuditLog]:
        stmt = select(AuditLog)
        if action_key:
            stmt = stmt.where(AuditLog.action_key == action_key)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def log_audit(self, *, actor_user_id: str | None, action_key: str, resource_type: str, resource_id: str | None, detail: str, metadata_json: dict | None = None, outcome: str = "success") -> AuditLog:
        event = AuditLog(actor_user_id=actor_user_id, action_key=action_key, resource_type=resource_type, resource_id=resource_id, detail=detail, metadata_json=metadata_json or {}, outcome=outcome)
        self.session.add(event)
        self.session.flush()
        return event

    def run_automated_scan(self, *, admin_user_id: str) -> dict:
        aml_cases_created = 0
        fraud_cases_created = 0
        audit_created = 0
        notes: list[str] = []

        high_pending_withdrawals = self.session.scalars(
            select(TreasuryWithdrawalRequest).where(TreasuryWithdrawalRequest.status.in_([TreasuryWithdrawalStatus.PENDING_REVIEW, TreasuryWithdrawalStatus.PROCESSING]))
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

        notes.append("Scan reviewed treasury, gifting, and reward density surfaces.")
        audit_created += 1
        self.log_audit(actor_user_id=admin_user_id, action_key="risk.scan.run", resource_type="risk_scan", resource_id=None, detail="Automated risk scan completed.", metadata_json={"aml_cases_created": aml_cases_created, "fraud_cases_created": fraud_cases_created})
        return {
            "aml_cases_created": aml_cases_created,
            "fraud_cases_created": fraud_cases_created,
            "audit_events_created": audit_created,
            "notes": notes,
        }
