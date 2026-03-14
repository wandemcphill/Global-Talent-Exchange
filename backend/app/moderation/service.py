from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.moderation_report import (
    ModerationPriority,
    ModerationReport,
    ModerationReportStatus,
    ModerationResolutionAction,
)
from backend.app.models.user import User

ALLOWED_TARGET_TYPES = {
    "user",
    "competition",
    "gift_transaction",
    "story",
    "club",
    "message",
    "comment",
    "wallet",
}
ALLOWED_REASON_CODES = {
    "abuse",
    "spam",
    "fraud",
    "match_fixing",
    "impersonation",
    "hate",
    "scam",
    "payment_issue",
    "other",
}


class ModerationError(ValueError):
    pass


@dataclass(slots=True)
class ModerationService:
    session: Session

    def create_report(
        self,
        *,
        reporter: User,
        target_type: str,
        target_id: str,
        subject_user_id: str | None,
        reason_code: str,
        description: str,
        evidence_url: str | None,
    ) -> ModerationReport:
        normalized_target = target_type.strip().lower()
        normalized_reason = reason_code.strip().lower()
        if normalized_target not in ALLOWED_TARGET_TYPES:
            raise ModerationError("Unsupported moderation target type.")
        if normalized_reason not in ALLOWED_REASON_CODES:
            raise ModerationError("Unsupported moderation reason code.")
        if subject_user_id == reporter.id:
            raise ModerationError("Users cannot report themselves as the subject of a case.")

        duplicate_stmt = select(ModerationReport).where(
            ModerationReport.reporter_user_id == reporter.id,
            ModerationReport.target_type == normalized_target,
            ModerationReport.target_id == target_id,
            ModerationReport.reason_code == normalized_reason,
            ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]),
        )
        duplicate = self.session.scalar(duplicate_stmt)
        if duplicate is not None:
            raise ModerationError("An open report for this target and reason already exists.")

        target_count = int(
            self.session.scalar(
                select(func.count(ModerationReport.id)).where(
                    ModerationReport.target_type == normalized_target,
                    ModerationReport.target_id == target_id,
                )
            )
            or 0
        ) + 1
        priority = self._priority_for(reason_code=normalized_reason, report_count=target_count)

        report = ModerationReport(
            reporter_user_id=reporter.id,
            subject_user_id=subject_user_id,
            target_type=normalized_target,
            target_id=target_id,
            reason_code=normalized_reason,
            description=description.strip(),
            evidence_url=evidence_url.strip() if evidence_url else None,
            priority=priority,
            report_count_for_target=target_count,
        )
        self.session.add(report)
        self.session.flush()
        return report

    def list_reports_for_user(self, *, user: User, limit: int = 50) -> list[ModerationReport]:
        stmt = select(ModerationReport).where(ModerationReport.reporter_user_id == user.id).order_by(ModerationReport.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_report(self, report_id: str) -> ModerationReport | None:
        return self.session.get(ModerationReport, report_id)

    def list_reports(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        target_type: str | None = None,
        limit: int = 100,
    ) -> list[ModerationReport]:
        stmt = select(ModerationReport)
        if status:
            stmt = stmt.where(ModerationReport.status == ModerationReportStatus(status))
        if priority:
            stmt = stmt.where(ModerationReport.priority == ModerationPriority(priority))
        if target_type:
            stmt = stmt.where(ModerationReport.target_type == target_type.strip().lower())
        stmt = stmt.order_by(
            ModerationReport.priority.desc(),
            ModerationReport.created_at.desc(),
        ).limit(limit)
        return list(self.session.scalars(stmt).all())

    def assign_report(
        self,
        *,
        report_id: str,
        admin_user_id: str,
        priority: str | None = None,
    ) -> ModerationReport:
        report = self.session.get(ModerationReport, report_id)
        if report is None:
            raise ModerationError("Moderation report was not found.")
        report.assigned_admin_user_id = admin_user_id
        if report.status == ModerationReportStatus.OPEN:
            report.status = ModerationReportStatus.IN_REVIEW
        if priority is not None:
            report.priority = ModerationPriority(priority)
        self.session.flush()
        return report

    def resolve_report(
        self,
        *,
        report_id: str,
        admin_user_id: str,
        resolution_action: str,
        resolution_note: str,
        dismiss: bool,
    ) -> ModerationReport:
        report = self.session.get(ModerationReport, report_id)
        if report is None:
            raise ModerationError("Moderation report was not found.")
        report.assigned_admin_user_id = admin_user_id
        report.resolved_by_user_id = admin_user_id
        report.resolution_note = resolution_note.strip()
        if dismiss:
            report.status = ModerationReportStatus.DISMISSED
            report.resolution_action = ModerationResolutionAction.NONE
        else:
            report.status = ModerationReportStatus.ACTIONED
            report.resolution_action = ModerationResolutionAction(resolution_action)
        self.session.flush()
        return report

    def summary(self) -> dict[str, int | list[ModerationReport]]:
        def count_for(status: ModerationReportStatus) -> int:
            return int(self.session.scalar(select(func.count(ModerationReport.id)).where(ModerationReport.status == status)) or 0)

        critical_count = int(
            self.session.scalar(select(func.count(ModerationReport.id)).where(ModerationReport.priority == ModerationPriority.CRITICAL)) or 0
        )
        high_priority_count = int(
            self.session.scalar(
                select(func.count(ModerationReport.id)).where(ModerationReport.priority.in_([ModerationPriority.HIGH, ModerationPriority.CRITICAL]))
            )
            or 0
        )
        recent = list(
            self.session.scalars(select(ModerationReport).order_by(ModerationReport.created_at.desc()).limit(10)).all()
        )
        return {
            "open_count": count_for(ModerationReportStatus.OPEN),
            "in_review_count": count_for(ModerationReportStatus.IN_REVIEW),
            "actioned_count": count_for(ModerationReportStatus.ACTIONED),
            "dismissed_count": count_for(ModerationReportStatus.DISMISSED),
            "critical_count": critical_count,
            "high_priority_count": high_priority_count,
            "recent_reports": recent,
        }

    @staticmethod
    def _priority_for(*, reason_code: str, report_count: int) -> ModerationPriority:
        if reason_code in {"fraud", "match_fixing", "hate", "scam"}:
            return ModerationPriority.HIGH if report_count < 3 else ModerationPriority.CRITICAL
        if report_count >= 3:
            return ModerationPriority.HIGH
        return ModerationPriority.NORMAL
