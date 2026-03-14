from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.dispute import Dispute, DisputeMessage, DisputeStatus
from backend.app.models.notification_record import NotificationRecord
from backend.app.models.user import User


class DisputeEngineError(ValueError):
    pass


@dataclass(slots=True)
class DisputeEngineService:
    session: Session

    def list_for_user(self, *, user_id: str) -> list[Dispute]:
        stmt = select(Dispute).where(Dispute.user_id == user_id).order_by(Dispute.updated_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_for_admin(self, *, status: DisputeStatus | None = None) -> list[Dispute]:
        stmt = select(Dispute).order_by(Dispute.updated_at.desc())
        if status is not None:
            stmt = stmt.where(Dispute.status == status)
        return list(self.session.scalars(stmt).all())

    def get_dispute(self, dispute_id: str) -> Dispute:
        dispute = self.session.get(Dispute, dispute_id)
        if dispute is None:
            raise DisputeEngineError("Dispute was not found.")
        return dispute

    def get_messages(self, dispute_id: str) -> list[DisputeMessage]:
        stmt = select(DisputeMessage).where(DisputeMessage.dispute_id == dispute_id).order_by(DisputeMessage.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def open_count(self) -> int:
        return int(self.session.scalar(select(func.count(Dispute.id)).where(Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.AWAITING_ADMIN, DisputeStatus.AWAITING_USER]))) or 0)

    def create_dispute(
        self,
        *,
        user: User,
        resource_type: str,
        resource_id: str,
        reference: str,
        subject: str | None,
        message: str,
        metadata_json: dict[str, object],
    ) -> Dispute:
        existing = self.session.scalar(
            select(Dispute).where(
                Dispute.user_id == user.id,
                Dispute.resource_type == resource_type,
                Dispute.resource_id == resource_id,
                Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.AWAITING_ADMIN, DisputeStatus.AWAITING_USER]),
            )
        )
        if existing is not None:
            raise DisputeEngineError("An active dispute already exists for this resource.")
        dispute = Dispute(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            reference=reference,
            subject=subject,
            metadata_json=metadata_json,
            status=DisputeStatus.OPEN,
        )
        self.session.add(dispute)
        self.session.flush()
        self.add_message(dispute=dispute, sender=user, sender_role="user", message=message, attachment_id=None, touch_status=False)
        self._notify(
            user_id=user.id,
            title="Dispute opened",
            body=f"Your dispute for {resource_type} has been opened.",
            notification_type="dispute_opened",
            metadata_json={"dispute_id": dispute.id, "reference": reference},
        )
        return dispute

    def add_message(
        self,
        *,
        dispute: Dispute,
        sender: User,
        sender_role: str,
        message: str,
        attachment_id: str | None,
        touch_status: bool = True,
    ) -> DisputeMessage:
        dispute = self.get_dispute(dispute.id)
        entry = DisputeMessage(
            dispute_id=dispute.id,
            sender_user_id=sender.id,
            sender_role=sender_role,
            message=message,
            attachment_id=attachment_id,
        )
        self.session.add(entry)
        if touch_status:
            dispute.status = DisputeStatus.AWAITING_ADMIN if sender_role == "user" else DisputeStatus.AWAITING_USER
            dispute.last_message_at = func.now()
            self.session.add(dispute)
            recipient_id = dispute.user_id if sender_role != "user" else dispute.admin_user_id
            if recipient_id:
                self._notify(
                    user_id=recipient_id,
                    title="New dispute message",
                    body=f"There is a new message on dispute {dispute.reference}.",
                    notification_type="dispute_message",
                    metadata_json={"dispute_id": dispute.id},
                )
        self.session.flush()
        return entry

    def assign(self, *, dispute_id: str, admin_user_id: str | None) -> Dispute:
        dispute = self.get_dispute(dispute_id)
        dispute.admin_user_id = admin_user_id
        dispute.status = DisputeStatus.AWAITING_ADMIN
        self.session.add(dispute)
        self._notify(
            user_id=dispute.user_id,
            title="Dispute assigned",
            body=f"Your dispute {dispute.reference} is now being handled.",
            notification_type="dispute_assigned",
            metadata_json={"dispute_id": dispute.id},
        )
        self.session.flush()
        return dispute

    def update_status(self, *, dispute_id: str, status: DisputeStatus, note: str | None, actor: User) -> Dispute:
        dispute = self.get_dispute(dispute_id)
        dispute.status = status
        if status == DisputeStatus.RESOLVED:
            dispute.resolved_at = func.now()
        if status == DisputeStatus.CLOSED:
            dispute.closed_at = func.now()
        self.session.add(dispute)
        if note:
            self.add_message(dispute=dispute, sender=actor, sender_role="admin", message=note, attachment_id=None, touch_status=False)
        self._notify(
            user_id=dispute.user_id,
            title="Dispute status updated",
            body=f"Your dispute {dispute.reference} is now {status.value}.",
            notification_type="dispute_status",
            metadata_json={"dispute_id": dispute.id, "status": status.value},
        )
        self.session.flush()
        return dispute

    def _notify(self, *, user_id: str, title: str, body: str, notification_type: str, metadata_json: dict[str, object]) -> None:
        self.session.add(
            NotificationRecord(
                user_id=user_id,
                topic=notification_type,
                template_key=notification_type,
                resource_type=metadata_json.get("resource_type") if isinstance(metadata_json, dict) else None,
                resource_id=metadata_json.get("dispute_id") if isinstance(metadata_json, dict) else None,
                message=f"{title}: {body}"[:255],
                metadata_json=metadata_json,
            )
        )
